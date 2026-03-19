# app/main.py

import asyncio
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import text
from starlette.requests import Request as StarletteRequest

from app.db import engine
from app.campaigns.engine import campaign_engine_tick, engine_settings, run_campaign_engine_forever

# ✅ Pipeline core (nuevo flujo real)
from app.pipeline.ingest_core import run_ingest, IngestMessage

# ✅ Woo sender (endpoint manual)
from app.pipeline.wc_sender import wc_send_product

# ✅ Router WhatsApp (webhook)
from app.routes.whatsapp import (
    router as whatsapp_router,
    upload_whatsapp_media,
)

# ✅ Woo utils (búsqueda UI)
from app.integrations.woocommerce import (
    wc_get,
    map_product_for_ui,
)

# ✅ Montar router IA (si existe)
try:
    from app.ai.router import router as ai_router
except Exception:
    ai_router = None


# =========================================================
# APP
# =========================================================

app = FastAPI()
_campaign_engine_stop: Optional[asyncio.Event] = None
_campaign_engine_task: Optional[asyncio.Task] = None

origins = [
    "https://app.perfumesverane.com",
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"^https://.*\.perfumesverane\.com$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(whatsapp_router)
if ai_router is not None:
    app.include_router(ai_router, prefix="/api/ai")

# Webhooks Woo
from app.routes.wc_webhooks import router as wc_webhooks_router
app.include_router(wc_webhooks_router)


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: StarletteRequest, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": str(exc),
            "path": str(request.url.path),
        },
    )


# =========================================================
# DATABASE SCHEMA
# =========================================================

def ensure_schema():
    """
    Crea/actualiza el schema mínimo que el CRM + pipeline necesita.
    (Seguro si ya existe; usa IF NOT EXISTS / ALTER ... IF NOT EXISTS)
    """
    with engine.begin() as conn:
        # -------------------------
        # conversations
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations (
                phone TEXT PRIMARY KEY,
                takeover BOOLEAN NOT NULL DEFAULT FALSE,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),

                first_name TEXT,
                last_name TEXT,
                city TEXT,
                customer_type TEXT,
                interests TEXT,
                tags TEXT,
                notes TEXT,

                last_read_at TIMESTAMP,

                ai_state TEXT,

                wc_last_options JSONB,
                wc_last_options_at TIMESTAMP
            )
        """))

        # ✅ columnas extra para memoria del último producto (best-effort)
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_product_id BIGINT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS crm_meta JSONB"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS crm_slots JSONB"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_product_featured_image TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_product_real_image TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_product_permalink TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_current TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_confidence DOUBLE PRECISION"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_stage TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_product_query TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_product_candidates JSONB"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS intent_preferences JSONB"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS payment_status TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS payment_reference TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS payment_amount TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS payment_currency TEXT"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_reconstructed_at TIMESTAMP"""))

        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations (updated_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_conversations_intent_current ON conversations (intent_current)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_conversations_payment_status ON conversations (payment_status)"""))

        # -------------------------
        # messages
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                phone TEXT NOT NULL,
                direction TEXT NOT NULL,
                msg_type TEXT NOT NULL DEFAULT 'text',
                text TEXT NOT NULL DEFAULT '',

                media_url TEXT,
                media_caption TEXT,

                media_id TEXT,
                mime_type TEXT,
                file_name TEXT,
                file_size INTEGER,
                duration_sec INTEGER,

                featured_image TEXT,
                real_image TEXT,
                permalink TEXT,

                extracted_text TEXT,
                ai_meta JSONB,

                wa_message_id TEXT,
                wa_status TEXT,
                wa_error TEXT,
                wa_ts_sent TIMESTAMP,
                wa_ts_delivered TIMESTAMP,
                wa_ts_read TIMESTAMP,

                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

        # Índices útiles para tu UI
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_messages_phone_created_at ON messages (phone, created_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_messages_phone_direction_created_at ON messages (phone, direction, created_at)"""))

        # -------------------------
        # ai_settings
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_settings (
                id SERIAL PRIMARY KEY,

                is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                provider TEXT NOT NULL DEFAULT 'google',
                model TEXT NOT NULL DEFAULT 'gemini-2.5-flash',
                system_prompt TEXT NOT NULL DEFAULT '',
                max_tokens INTEGER NOT NULL DEFAULT 512,
                temperature DOUBLE PRECISION NOT NULL DEFAULT 0.7,

                fallback_provider TEXT NOT NULL DEFAULT 'groq',
                fallback_model TEXT NOT NULL DEFAULT 'llama-3.1-8b-instant',

                timeout_sec INTEGER NOT NULL DEFAULT 25,
                max_retries INTEGER NOT NULL DEFAULT 1,

                reply_chunk_chars INTEGER,
                reply_delay_ms INTEGER,
                typing_delay_ms INTEGER,

                voice_enabled BOOLEAN,
                voice_gender TEXT,
                voice_language TEXT,
                voice_accent TEXT,
                voice_style_prompt TEXT,
                voice_max_notes_per_reply INTEGER,
                voice_prefer_voice BOOLEAN,
                voice_speaking_rate DOUBLE PRECISION,

                voice_tts_provider TEXT,
                voice_tts_voice_id TEXT,
                voice_tts_model_id TEXT,

                mm_enabled BOOLEAN,
                mm_provider TEXT,
                mm_model TEXT,
                mm_timeout_sec INTEGER,
                mm_max_retries INTEGER,

                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

        # Insertar 1 fila default si la tabla está vacía
        conn.execute(text("""
            INSERT INTO ai_settings (
                is_enabled, provider, model, system_prompt,
                max_tokens, temperature,
                fallback_provider, fallback_model,
                timeout_sec, max_retries,

                reply_chunk_chars, reply_delay_ms, typing_delay_ms,

                voice_enabled, voice_prefer_voice, voice_max_notes_per_reply,
                voice_tts_provider, voice_tts_voice_id, voice_tts_model_id,

                mm_enabled, mm_provider, mm_model, mm_timeout_sec, mm_max_retries
            )
            SELECT
                TRUE, 'google', 'gemini-2.5-flash', '',
                512, 0.7,
                'groq', 'llama-3.1-8b-instant',
                25, 1,

                480, 900, 450,

                FALSE, FALSE, 1,
                'google', '', '',

                TRUE, 'google', 'gemini-2.5-flash', 75, 2
            WHERE NOT EXISTS (SELECT 1 FROM ai_settings)
        """))

        # Asegurar defaults si quedaron NULL
        conn.execute(text("""
            UPDATE ai_settings
            SET
                reply_chunk_chars = COALESCE(reply_chunk_chars, 480),
                reply_delay_ms = COALESCE(reply_delay_ms, 900),
                typing_delay_ms = COALESCE(typing_delay_ms, 450),

                voice_enabled = COALESCE(voice_enabled, FALSE),
                voice_prefer_voice = COALESCE(voice_prefer_voice, FALSE),
                voice_max_notes_per_reply = COALESCE(voice_max_notes_per_reply, 1),

                voice_tts_provider = COALESCE(NULLIF(TRIM(voice_tts_provider), ''), 'google'),
                voice_tts_voice_id = COALESCE(NULLIF(TRIM(voice_tts_voice_id), ''), ''),
                voice_tts_model_id = COALESCE(NULLIF(TRIM(voice_tts_model_id), ''), ''),

                mm_enabled = COALESCE(mm_enabled, TRUE),
                mm_provider = COALESCE(NULLIF(TRIM(mm_provider), ''), 'google'),
                mm_model = COALESCE(NULLIF(TRIM(mm_model), ''), 'gemini-2.5-flash'),
                mm_timeout_sec = COALESCE(mm_timeout_sec, 75),
                mm_max_retries = COALESCE(mm_max_retries, 2)
            WHERE id = (SELECT id FROM ai_settings ORDER BY id ASC LIMIT 1)
        """))

        # -------------------------
        # wc_products_cache (Plan B) - V2 (cache_repo compatible)
        # -------------------------
        try:
            conn.execute(text("""CREATE EXTENSION IF NOT EXISTS pg_trgm"""))
        except Exception:
            pass

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS wc_products_cache (
                product_id BIGINT PRIMARY KEY,
                data JSONB NOT NULL DEFAULT '{}'::jsonb,

                name TEXT NOT NULL DEFAULT '',
                price TEXT NOT NULL DEFAULT '',
                permalink TEXT NOT NULL DEFAULT '',

                featured_image TEXT NOT NULL DEFAULT '',
                real_image TEXT NOT NULL DEFAULT '',
                stock_status TEXT NOT NULL DEFAULT '',

                updated_at_woo TIMESTAMP NULL,
                synced_at TIMESTAMP NOT NULL DEFAULT NOW(),

                search_blob TEXT NOT NULL DEFAULT ''
            )
        """))

        # índices
        try:
            conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_wc_cache_name_trgm ON wc_products_cache USING gin (name gin_trgm_ops)"""))
        except Exception:
            pass

        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_wc_cache_synced_at ON wc_products_cache (synced_at)"""))

        # -------------------------
        # customer_segments
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS customer_segments (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                rules_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_customer_segments_active ON customer_segments (is_active)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_customer_segments_updated_at ON customer_segments (updated_at DESC)"""))

        # -------------------------
        # message_templates
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS message_templates (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL DEFAULT 'general',
                body TEXT NOT NULL DEFAULT '',
                variables_json JSONB NOT NULL DEFAULT '[]'::jsonb,
                status TEXT NOT NULL DEFAULT 'draft',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_message_templates_status ON message_templates (status)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_message_templates_updated_at ON message_templates (updated_at DESC)"""))

        # -------------------------
        # campaigns
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS campaigns (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                objective TEXT NOT NULL DEFAULT '',
                segment_id INTEGER REFERENCES customer_segments(id) ON DELETE SET NULL,
                template_id INTEGER REFERENCES message_templates(id) ON DELETE SET NULL,
                status TEXT NOT NULL DEFAULT 'draft',
                scheduled_at TIMESTAMP NULL,
                launched_at TIMESTAMP NULL,
                channel TEXT NOT NULL DEFAULT 'whatsapp',
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaigns_status ON campaigns (status)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaigns_scheduled_at ON campaigns (scheduled_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaigns_updated_at ON campaigns (updated_at DESC)"""))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS campaign_recipients (
                id SERIAL PRIMARY KEY,
                campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
                phone TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                sent_at TIMESTAMP NULL,
                delivered_at TIMESTAMP NULL,
                read_at TIMESTAMP NULL,
                replied_at TIMESTAMP NULL,
                error TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (campaign_id, phone)
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaign_recipients_campaign_id ON campaign_recipients (campaign_id)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaign_recipients_status ON campaign_recipients (status)"""))
        conn.execute(text("""ALTER TABLE campaign_recipients ADD COLUMN IF NOT EXISTS wa_message_id TEXT"""))
        conn.execute(text("""ALTER TABLE campaign_recipients ADD COLUMN IF NOT EXISTS message_id INTEGER"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaign_recipients_wa_message_id ON campaign_recipients (wa_message_id)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_campaign_recipients_message_id ON campaign_recipients (message_id)"""))

        # -------------------------
        # automation_triggers
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS automation_triggers (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                event_type TEXT NOT NULL,
                conditions_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                action_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                cooldown_minutes INTEGER NOT NULL DEFAULT 60,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                last_run_at TIMESTAMP NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_automation_triggers_active ON automation_triggers (is_active)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_automation_triggers_event_type ON automation_triggers (event_type)"""))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS trigger_executions (
                id SERIAL PRIMARY KEY,
                trigger_id INTEGER NOT NULL REFERENCES automation_triggers(id) ON DELETE CASCADE,
                phone TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'ok',
                executed_at TIMESTAMP NOT NULL DEFAULT NOW(),
                error TEXT
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_trigger_executions_trigger_id ON trigger_executions (trigger_id)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_trigger_executions_executed_at ON trigger_executions (executed_at DESC)"""))

        # -------------------------
        # remarketing flows
        # -------------------------
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS remarketing_flows (
                id SERIAL PRIMARY KEY,
                name TEXT NOT NULL,
                entry_rules_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                exit_rules_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                is_active BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_remarketing_flows_active ON remarketing_flows (is_active)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_remarketing_flows_updated_at ON remarketing_flows (updated_at DESC)"""))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS remarketing_steps (
                id SERIAL PRIMARY KEY,
                flow_id INTEGER NOT NULL REFERENCES remarketing_flows(id) ON DELETE CASCADE,
                step_order INTEGER NOT NULL DEFAULT 1,
                wait_minutes INTEGER NOT NULL DEFAULT 1440,
                template_id INTEGER REFERENCES message_templates(id) ON DELETE SET NULL,
                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                UNIQUE (flow_id, step_order)
            )
        """))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_remarketing_steps_flow_id ON remarketing_steps (flow_id)"""))


@app.on_event("startup")
def _startup():
    # ✅ IMPORTANTE: NO recursión. Se ejecuta una sola vez al levantar el server.
    ensure_schema()


@app.on_event("startup")
async def _startup_campaign_engine():
    global _campaign_engine_stop, _campaign_engine_task

    cfg = engine_settings()
    if not cfg.get("enabled"):
        print("[CAMPAIGN_ENGINE] disabled")
        return

    if _campaign_engine_task and not _campaign_engine_task.done():
        return

    _campaign_engine_stop = asyncio.Event()
    _campaign_engine_task = asyncio.create_task(run_campaign_engine_forever(_campaign_engine_stop))
    print(
        "[CAMPAIGN_ENGINE] started",
        {
            "interval_sec": cfg.get("interval_sec"),
            "batch_size": cfg.get("batch_size"),
            "send_delay_ms": cfg.get("send_delay_ms"),
        },
    )


@app.on_event("shutdown")
async def _shutdown_campaign_engine():
    global _campaign_engine_stop, _campaign_engine_task

    if _campaign_engine_stop:
        _campaign_engine_stop.set()

    if _campaign_engine_task:
        try:
            await _campaign_engine_task
        except Exception:
            pass

    _campaign_engine_task = None
    _campaign_engine_stop = None


# =========================================================
# MODELS (solo los que son de API/UI)
# =========================================================

class CRMIn(BaseModel):
    phone: str
    first_name: str = ""
    last_name: str = ""
    city: str = ""
    customer_type: str = ""
    interests: str = ""
    tags: str = ""
    notes: str = ""


class TakeoverPayload(BaseModel):
    phone: str
    takeover: bool


class CustomerPatch(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    city: Optional[str] = None
    customer_type: Optional[str] = None
    interests: Optional[str] = None
    tags: Optional[str] = None
    notes: Optional[str] = None
    payment_status: Optional[str] = None
    payment_reference: Optional[str] = None


class SegmentIn(BaseModel):
    name: str
    rules_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True


class SegmentPatch(BaseModel):
    name: Optional[str] = None
    rules_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class TemplateIn(BaseModel):
    name: str
    category: str = "general"
    body: str = ""
    variables_json: List[str] = Field(default_factory=list)
    status: str = "draft"


class TemplatePatch(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None
    body: Optional[str] = None
    variables_json: Optional[List[str]] = None
    status: Optional[str] = None


class TemplatePreviewIn(BaseModel):
    variables: Dict[str, Any] = Field(default_factory=dict)


class CampaignIn(BaseModel):
    name: str
    objective: str = ""
    segment_id: Optional[int] = None
    template_id: Optional[int] = None
    status: str = "draft"
    scheduled_at: Optional[datetime] = None
    channel: str = "whatsapp"


class CampaignPatch(BaseModel):
    name: Optional[str] = None
    objective: Optional[str] = None
    segment_id: Optional[int] = None
    template_id: Optional[int] = None
    status: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    channel: Optional[str] = None


class TriggerIn(BaseModel):
    name: str
    event_type: str
    conditions_json: Dict[str, Any] = Field(default_factory=dict)
    action_json: Dict[str, Any] = Field(default_factory=dict)
    cooldown_minutes: int = 60
    is_active: bool = True


class TriggerPatch(BaseModel):
    name: Optional[str] = None
    event_type: Optional[str] = None
    conditions_json: Optional[Dict[str, Any]] = None
    action_json: Optional[Dict[str, Any]] = None
    cooldown_minutes: Optional[int] = None
    is_active: Optional[bool] = None


class RemarketingFlowIn(BaseModel):
    name: str
    entry_rules_json: Dict[str, Any] = Field(default_factory=dict)
    exit_rules_json: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = False


class RemarketingFlowPatch(BaseModel):
    name: Optional[str] = None
    entry_rules_json: Optional[Dict[str, Any]] = None
    exit_rules_json: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class RemarketingStepIn(BaseModel):
    step_order: int = 1
    wait_minutes: int = 1440
    template_id: Optional[int] = None


class RemarketingStepPatch(BaseModel):
    step_order: Optional[int] = None
    wait_minutes: Optional[int] = None
    template_id: Optional[int] = None


# =========================================================
# HELPERS
# =========================================================

def _parse_tags_param(tags: str) -> List[str]:
    if not tags:
        return []
    out: List[str] = []
    for t in tags.split(","):
        tt = (t or "").strip().lower()
        if tt:
            out.append(tt)
    return out


def _parse_range_days(raw: str, default_days: int = 7, max_days: int = 365) -> int:
    token = (raw or "").strip().lower()
    if not token:
        return default_days

    if token.endswith("d"):
        token = token[:-1]

    try:
        days = int(token)
    except Exception:
        return default_days

    return max(1, min(days, max_days))


def _safe_json_dict(val: Any) -> Dict[str, Any]:
    if isinstance(val, dict):
        return val
    return {}


def _normalize_status(raw: str, allowed: set[str], default: str) -> str:
    v = (raw or "").strip().lower()
    if v in allowed:
        return v
    return default


def _render_template(body: str, variables: Dict[str, Any]) -> str:
    out = body or ""
    if not variables:
        return out

    for k, v in variables.items():
        key = (k or "").strip()
        if not key:
            continue
        out = out.replace(f"{{{{{key}}}}}", str(v if v is not None else ""))
    return out


def _segment_filter_sql(rules: Dict[str, Any], prefix: str = "r") -> tuple[str, Dict[str, Any]]:
    rules = rules if isinstance(rules, dict) else {}
    conds: List[str] = []
    params: Dict[str, Any] = {}

    tag = str(rules.get("tag") or "").strip().lower()
    if tag:
        params[f"{prefix}_tag"] = f"%{tag}%"
        conds.append(f"LOWER(COALESCE(c.tags,'')) LIKE :{prefix}_tag")

    intent = str(rules.get("intent") or "").strip().upper()
    if intent:
        params[f"{prefix}_intent"] = intent
        conds.append(f"UPPER(COALESCE(c.intent_current,'')) = :{prefix}_intent")

    payment_status = str(rules.get("payment_status") or "").strip().lower()
    if payment_status:
        params[f"{prefix}_payment"] = payment_status
        conds.append(f"LOWER(COALESCE(c.payment_status,'')) = :{prefix}_payment")

    takeover = rules.get("takeover")
    if isinstance(takeover, bool):
        params[f"{prefix}_takeover"] = takeover
        conds.append(f"c.takeover = :{prefix}_takeover")

    city = str(rules.get("city") or "").strip().lower()
    if city:
        params[f"{prefix}_city"] = f"%{city}%"
        conds.append(f"LOWER(COALESCE(c.city,'')) LIKE :{prefix}_city")

    if not conds:
        return "TRUE", params
    return " AND ".join(conds), params


# =========================================================
# ENDPOINTS
# =========================================================

@app.get("/api/health")
def health():
    return {"ok": True, "build": "2026-02-22-api-main-clean-1"}


# -------------------------
# Woo endpoints UI
# -------------------------

@app.get("/api/wc/products")
async def wc_products(
    q: str = Query("", description="texto de búsqueda"),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
):
    params = {"search": q or "", "page": page, "per_page": per_page, "status": "publish"}
    data = await wc_get("/products", params=params)
    items = [map_product_for_ui(p) for p in (data or [])]
    return {"products": items}


@app.post("/api/wc/send-product")
async def send_wc_product(payload: dict):
    phone = payload.get("phone")
    product_id = payload.get("product_id")
    custom_caption = payload.get("caption", "")

    if not phone or not product_id:
        raise HTTPException(status_code=400, detail="phone and product_id required")

    wa = await wc_send_product(
        phone=str(phone),
        product_id=int(product_id),
        custom_caption=str(custom_caption or ""),
    )

    return {"ok": True, "sent": bool(wa.get("sent")), "wa": wa}


# -------------------------
# Media upload (UI)
# -------------------------

@app.post("/api/media/upload")
async def upload_media(file: UploadFile = File(...), kind: str = Form("image")):
    import tempfile
    import subprocess

    kind = (kind or "image").lower().strip()
    if kind not in ("image", "video", "audio", "document"):
        raise HTTPException(status_code=400, detail="Invalid kind")

    content = await file.read()
    mime = (file.content_type or "application/octet-stream").split(";")[0].strip().lower()
    filename = file.filename or "upload"

    # Si suben webm (browser), lo convertimos a ogg/opus para WhatsApp
    if kind == "audio" and mime == "audio/webm":
        with tempfile.TemporaryDirectory() as tmp:
            in_path = os.path.join(tmp, "in.webm")
            out_path = os.path.join(tmp, "out.ogg")

            with open(in_path, "wb") as f:
                f.write(content)

            cmd = ["ffmpeg", "-y", "-i", in_path, "-c:a", "libopus", "-b:a", "24k", "-vn", out_path]
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if p.returncode != 0:
                err = p.stderr.decode("utf-8", errors="ignore")
                raise HTTPException(status_code=500, detail=f"ffmpeg convert failed: {err[:900]}")

            with open(out_path, "rb") as f:
                content = f.read()

        mime = "audio/ogg"
        filename = "audio.ogg"

    media_id = await upload_whatsapp_media(content, mime)
    return {"ok": True, "media_id": media_id, "mime_type": mime, "filename": filename, "kind": kind}


# -------------------------
# Conversations / CRM
# -------------------------

@app.post("/api/conversations/{phone}/read")
def mark_conversation_read(phone: str):
    phone = (phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phone required")

    ts = datetime.utcnow()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, last_read_at)
            VALUES (:phone, :ts)
            ON CONFLICT (phone)
            DO UPDATE SET last_read_at = EXCLUDED.last_read_at
        """), {"phone": phone, "ts": ts})

    return {"ok": True}


@app.get("/api/crm/tags")
def list_crm_tags(limit: int = Query(200, ge=1, le=2000)):
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT DISTINCT TRIM(LOWER(x)) AS tag
            FROM conversations c
            CROSS JOIN LATERAL regexp_split_to_table(COALESCE(c.tags,''), ',') AS x
            WHERE TRIM(x) <> ''
            ORDER BY tag ASC
            LIMIT :limit
        """), {"limit": limit}).mappings().all()

    return {"tags": [r["tag"] for r in rows]}


@app.get("/api/conversations")
def get_conversations(
    search: str = Query("", description="Buscar por phone, nombre CRM o texto preview"),
    takeover: str = Query("all", description="all|on|off"),
    unread: str = Query("all", description="all|yes|no"),
    tags: str = Query("", description="Filtro por tags CRM. Ej: vip,pago pendiente"),
):
    takeover = (takeover or "all").strip().lower()
    unread = (unread or "all").strip().lower()
    term = (search or "").strip().lower()
    tag_list = _parse_tags_param(tags)

    where = []
    params = {}

    if takeover == "on":
        where.append("c.takeover = TRUE")
    elif takeover == "off":
        where.append("c.takeover = FALSE")

    if term:
        params["term"] = f"%{term}%"
        where.append("""
            (
              LOWER(c.phone) LIKE :term
              OR LOWER(COALESCE(c.first_name,'') || ' ' || COALESCE(c.last_name,'')) LIKE :term
              OR LOWER(COALESCE(m.text, '')) LIKE :term
            )
        """)

    if tag_list:
        tag_clauses = []
        for i, t in enumerate(tag_list):
            k = f"tag{i}"
            params[k] = f"%{t}%"
            tag_clauses.append(f"LOWER(COALESCE(c.tags,'')) LIKE :{k}")
        where.append("(" + " OR ".join(tag_clauses) + ")")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    if unread in ("yes", "no"):
        unread_cond = """
            EXISTS (
                SELECT 1
                FROM messages mi
                WHERE mi.phone = c.phone
                  AND mi.direction = 'in'
                  AND mi.created_at > COALESCE(c.last_read_at, TIMESTAMP 'epoch')
            )
        """
        extra = f" AND {unread_cond} " if unread == "yes" else f" AND NOT ({unread_cond}) "

        if where_sql:
            where_sql = where_sql + extra
        else:
            where_sql = "WHERE 1=1 " + extra

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT
                c.phone,
                c.takeover,
                c.updated_at,
                c.first_name,
                c.last_name,
                c.city,
                c.customer_type,
                c.interests,
                c.tags,
                c.notes,
                c.last_read_at,

                m.text AS last_text,
                m.msg_type AS last_msg_type,
                m.direction AS last_direction,
                m.created_at AS last_created_at,

                EXISTS (
                    SELECT 1
                    FROM messages mi
                    WHERE mi.phone = c.phone
                      AND mi.direction = 'in'
                      AND mi.created_at > COALESCE(c.last_read_at, TIMESTAMP 'epoch')
                ) AS has_unread,

                (
                    SELECT COUNT(*)
                    FROM messages mi2
                    WHERE mi2.phone = c.phone
                      AND mi2.direction = 'in'
                      AND mi2.created_at > COALESCE(c.last_read_at, TIMESTAMP 'epoch')
                ) AS unread_count

            FROM conversations c
            LEFT JOIN LATERAL (
                SELECT text, msg_type, direction, created_at
                FROM messages
                WHERE phone = c.phone
                ORDER BY created_at DESC
                LIMIT 1
            ) m ON TRUE

            {where_sql}

            ORDER BY c.updated_at DESC
            LIMIT 200
        """), params).mappings().all()

    out = []
    for r in rows:
        d = dict(r)
        d["text"] = d.get("last_text") or ""
        try:
            d["unread_count"] = int(d.get("unread_count") or 0)
        except Exception:
            d["unread_count"] = 0
        d["has_unread"] = bool(d.get("has_unread"))
        out.append(d)

    return {"conversations": out}


@app.get("/api/conversations/{phone}/messages")
def get_messages(phone: str):
    with engine.begin() as conn:
        rows = conn.execute(text("""
            WITH latest AS (
                SELECT
                    id, phone, direction, msg_type, text,
                    media_url, media_caption, media_id, mime_type, file_name, file_size, duration_sec,
                    featured_image, real_image, permalink, created_at,
                    extracted_text, ai_meta,
                    wa_message_id, wa_status, wa_error, wa_ts_sent, wa_ts_delivered, wa_ts_read
                FROM messages
                WHERE phone = :phone
                ORDER BY created_at DESC
                LIMIT 500
            )
            SELECT *
            FROM latest
            ORDER BY created_at ASC
        """), {"phone": phone}).mappings().all()

    return {"messages": [dict(r) for r in rows]}


# -------------------------
# Ingest (core pipeline)
# -------------------------

@app.post("/api/messages/ingest")
async def ingest(msg: IngestMessage):
    return await run_ingest(msg)


@app.post("/api/conversations/takeover")
def set_takeover(payload: TakeoverPayload):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, takeover, updated_at)
            VALUES (:phone, :takeover, :updated_at)
            ON CONFLICT (phone)
            DO UPDATE SET takeover = EXCLUDED.takeover,
                          updated_at = EXCLUDED.updated_at
        """), {"phone": payload.phone, "takeover": payload.takeover, "updated_at": datetime.utcnow()})
    return {"ok": True}


@app.post("/api/crm")
def save_crm(payload: CRMIn):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (
                phone, updated_at, first_name, last_name,
                city, customer_type, interests, tags, notes
            )
            VALUES (
                :phone, :updated_at, :first_name, :last_name,
                :city, :customer_type, :interests, :tags, :notes
            )
            ON CONFLICT (phone) DO UPDATE SET
              updated_at = EXCLUDED.updated_at,
              first_name = EXCLUDED.first_name,
              last_name = EXCLUDED.last_name,
              city = EXCLUDED.city,
              customer_type = EXCLUDED.customer_type,
              interests = EXCLUDED.interests,
              tags = EXCLUDED.tags,
              notes = EXCLUDED.notes
        """), {
            "phone": payload.phone,
            "updated_at": datetime.utcnow(),
            "first_name": payload.first_name,
            "last_name": payload.last_name,
            "city": payload.city,
            "customer_type": payload.customer_type,
            "interests": payload.interests,
            "tags": payload.tags,
            "notes": payload.notes,
        })
    return {"ok": True}


@app.get("/api/crm/{phone}")
def get_crm(phone: str):
    phone = (phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phone required")

    try:
        with engine.begin() as conn:
            r = conn.execute(text("""
                SELECT
                    phone,
                    takeover,
                    first_name,
                    last_name,
                    city,
                    customer_type,
                    interests,
                    tags,
                    notes,
                    COALESCE(intent_current, '') AS intent_current,
                    COALESCE(intent_stage, '') AS intent_stage,
                    COALESCE(payment_status, '') AS payment_status,
                    COALESCE(payment_reference, '') AS payment_reference,
                    COALESCE(crm_meta, '{}'::jsonb) AS crm_meta
                FROM conversations
                WHERE phone = :phone
            """), {"phone": phone}).mappings().first()

        if not r:
            return {
                "phone": phone,
                "takeover": False,
                "first_name": "",
                "last_name": "",
                "city": "",
                "customer_type": "",
                "interests": "",
                "tags": "",
                "notes": "",
                "intent_current": "",
                "intent_stage": "",
                "payment_status": "",
                "payment_reference": "",
                "crm_meta": {},
                "memory_summary": "",
            }

        data = dict(r)
        crm_meta = data.get("crm_meta") if isinstance(data.get("crm_meta"), dict) else {}
        ai_memory = crm_meta.get("ai_memory") if isinstance(crm_meta, dict) else {}
        data["memory_summary"] = str((ai_memory or {}).get("summary") or "").strip()
        return data

    except Exception as e:
        return {"ok": False, "error": str(e), "phone": phone}


# =========================================================
# Dashboard
# =========================================================

@app.get("/api/dashboard/overview")
def dashboard_overview(range: str = Query("7d")):
    days = _parse_range_days(range, default_days=7, max_days=365)
    since = datetime.utcnow() - timedelta(days=days)

    with engine.begin() as conn:
        r = conn.execute(text("""
            SELECT
                (SELECT COUNT(*) FROM conversations) AS conversations_total,
                (SELECT COUNT(*) FROM conversations WHERE updated_at >= :since) AS active_conversations,
                (SELECT COUNT(*) FROM conversations WHERE takeover = TRUE) AS takeover_on,
                (
                    SELECT COUNT(*)
                    FROM conversations c
                    WHERE EXISTS (
                        SELECT 1
                        FROM messages mi
                        WHERE mi.phone = c.phone
                          AND mi.direction = 'in'
                          AND mi.created_at > COALESCE(c.last_read_at, TIMESTAMP 'epoch')
                    )
                ) AS unread_conversations,
                (SELECT COUNT(*) FROM messages WHERE direction = 'in' AND created_at >= :since) AS messages_in,
                (SELECT COUNT(*) FROM messages WHERE direction = 'out' AND created_at >= :since) AS messages_out,
                (
                    SELECT COUNT(*)
                    FROM (
                        SELECT phone, MIN(created_at) AS first_seen
                        FROM messages
                        WHERE direction = 'in'
                        GROUP BY phone
                    ) f
                    WHERE f.first_seen >= :since
                ) AS new_customers,
                (
                    SELECT COUNT(*)
                    FROM campaigns
                    WHERE LOWER(status) IN ('running', 'scheduled')
                ) AS campaigns_live
        """), {"since": since}).mappings().first()

    data = dict(r or {})
    msg_in = int(data.get("messages_in") or 0)
    msg_out = int(data.get("messages_out") or 0)
    response_rate = round((msg_out / msg_in) * 100, 2) if msg_in > 0 else 0.0

    return {
        "range_days": days,
        "since": since,
        "kpis": {
            "conversations_total": int(data.get("conversations_total") or 0),
            "active_conversations": int(data.get("active_conversations") or 0),
            "new_customers": int(data.get("new_customers") or 0),
            "unread_conversations": int(data.get("unread_conversations") or 0),
            "takeover_on": int(data.get("takeover_on") or 0),
            "campaigns_live": int(data.get("campaigns_live") or 0),
            "messages_in": msg_in,
            "messages_out": msg_out,
            "response_rate_pct": response_rate,
        },
    }


@app.get("/api/dashboard/funnel")
def dashboard_funnel():
    with engine.begin() as conn:
        r = conn.execute(text("""
            SELECT
                COUNT(*) AS contacted,
                COUNT(*) FILTER (
                    WHERE UPPER(COALESCE(intent_current,'')) IN (
                        'PRODUCT_SEARCH',
                        'PREFERENCE_RECO',
                        'PRICE_STOCK',
                        'VARIANT_SELECTION'
                    )
                ) AS interest,
                COUNT(*) FILTER (
                    WHERE UPPER(COALESCE(intent_current,'')) = 'BUY_FLOW'
                ) AS buy_intent,
                COUNT(*) FILTER (
                    WHERE LOWER(COALESCE(payment_status,'')) IN ('pending', 'initiated', 'awaiting', 'processing')
                ) AS payment_pending,
                COUNT(*) FILTER (
                    WHERE LOWER(COALESCE(payment_status,'')) IN ('paid', 'completed', 'approved', 'success')
                ) AS paid
            FROM conversations
        """)).mappings().first()

    d = dict(r or {})
    contacted = int(d.get("contacted") or 0)
    interest = int(d.get("interest") or 0)
    buy_intent = int(d.get("buy_intent") or 0)
    payment_pending = int(d.get("payment_pending") or 0)
    paid = int(d.get("paid") or 0)

    def _ratio(num: int, den: int) -> float:
        if den <= 0:
            return 0.0
        return round((num / den) * 100, 2)

    return {
        "steps": [
            {"id": "contacted", "label": "Contactados", "value": contacted, "pct_prev": 100.0},
            {"id": "interest", "label": "Interes", "value": interest, "pct_prev": _ratio(interest, contacted)},
            {"id": "buy_intent", "label": "Intencion de compra", "value": buy_intent, "pct_prev": _ratio(buy_intent, interest)},
            {"id": "payment_pending", "label": "Pago pendiente", "value": payment_pending, "pct_prev": _ratio(payment_pending, buy_intent)},
            {"id": "paid", "label": "Pago confirmado", "value": paid, "pct_prev": _ratio(paid, payment_pending)},
        ]
    }


@app.get("/api/dashboard/campaigns")
def dashboard_campaigns(range: str = Query("30d")):
    days = _parse_range_days(range, default_days=30, max_days=365)
    since = datetime.utcnow() - timedelta(days=days)

    with engine.begin() as conn:
        r = conn.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'pending') AS pending,
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'processing') AS processing,
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'sent') AS sent,
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'delivered') AS delivered,
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'read') AS read,
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'replied') AS replied,
                COUNT(*) FILTER (WHERE LOWER(cr.status) = 'failed') AS failed
            FROM campaign_recipients cr
            JOIN campaigns c ON c.id = cr.campaign_id
            WHERE c.created_at >= :since
        """), {"since": since}).mappings().first()

    d = dict(r or {})
    sent = int(d.get("sent") or 0)
    delivered = int(d.get("delivered") or 0)
    read = int(d.get("read") or 0)
    replied = int(d.get("replied") or 0)

    return {
        "range_days": days,
        "since": since,
        "metrics": {
            "pending": int(d.get("pending") or 0),
            "processing": int(d.get("processing") or 0),
            "sent": sent,
            "delivered": delivered,
            "read": read,
            "replied": replied,
            "failed": int(d.get("failed") or 0),
            "delivery_rate_pct": round((delivered / sent) * 100, 2) if sent else 0.0,
            "read_rate_pct": round((read / delivered) * 100, 2) if delivered else 0.0,
            "reply_rate_pct": round((replied / read) * 100, 2) if read else 0.0,
        },
    }


@app.get("/api/dashboard/remarketing")
def dashboard_remarketing():
    with engine.begin() as conn:
        r = conn.execute(text("""
            SELECT
                COUNT(*) AS flows_total,
                COUNT(*) FILTER (WHERE is_active = TRUE) AS active_flows
            FROM remarketing_flows
        """)).mappings().first()

        rs = conn.execute(text("""
            SELECT COUNT(*) AS steps_total
            FROM remarketing_steps
        """)).mappings().first()

    return {
        "flows_total": int((r or {}).get("flows_total") or 0),
        "active_flows": int((r or {}).get("active_flows") or 0),
        "steps_total": int((rs or {}).get("steps_total") or 0),
    }


# =========================================================
# Customers + Segments
# =========================================================

@app.get("/api/customers/segments")
def list_customer_segments(active: str = Query("all", description="all|yes|no")):
    active = (active or "all").strip().lower()
    where_sql = ""
    if active == "yes":
        where_sql = "WHERE is_active = TRUE"
    elif active == "no":
        where_sql = "WHERE is_active = FALSE"

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT id, name, rules_json, is_active, created_at, updated_at
            FROM customer_segments
            {where_sql}
            ORDER BY updated_at DESC, id DESC
        """)).mappings().all()

    return {"segments": [dict(r) for r in rows]}


@app.post("/api/customers/segments")
def create_customer_segment(payload: SegmentIn):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO customer_segments (name, rules_json, is_active, created_at, updated_at)
            VALUES (:name, CAST(:rules_json AS jsonb), :is_active, NOW(), NOW())
            RETURNING id, name, rules_json, is_active, created_at, updated_at
        """), {
            "name": name,
            "rules_json": json.dumps(_safe_json_dict(payload.rules_json), ensure_ascii=False),
            "is_active": bool(payload.is_active),
        }).mappings().first()

    return {"segment": dict(row or {})}


@app.patch("/api/customers/segments/{segment_id}")
def update_customer_segment(segment_id: int, payload: SegmentPatch):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets: List[str] = ["updated_at = NOW()"]
    params: Dict[str, Any] = {"segment_id": int(segment_id)}

    if "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        sets.append("name = :name")
        params["name"] = name

    if "rules_json" in data:
        sets.append("rules_json = CAST(:rules_json AS jsonb)")
        params["rules_json"] = json.dumps(_safe_json_dict(data.get("rules_json")), ensure_ascii=False)

    if "is_active" in data:
        sets.append("is_active = :is_active")
        params["is_active"] = bool(data.get("is_active"))

    with engine.begin() as conn:
        row = conn.execute(text(f"""
            UPDATE customer_segments
            SET {", ".join(sets)}
            WHERE id = :segment_id
            RETURNING id, name, rules_json, is_active, created_at, updated_at
        """), params).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="segment not found")

    return {"segment": dict(row)}


@app.get("/api/customers")
def list_customers(
    search: str = Query("", description="Buscar por telefono/nombre/texto"),
    tag: str = Query("", description="Tag contiene"),
    intent: str = Query("", description="Intent exacto"),
    payment_status: str = Query("", description="payment_status exacto"),
    takeover: str = Query("all", description="all|on|off"),
    unread: str = Query("all", description="all|yes|no"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    term = (search or "").strip().lower()
    tag = (tag or "").strip().lower()
    intent = (intent or "").strip().upper()
    payment_status = (payment_status or "").strip().lower()
    takeover = (takeover or "all").strip().lower()
    unread = (unread or "all").strip().lower()

    where: List[str] = []
    params: Dict[str, Any] = {"limit": page_size, "offset": (page - 1) * page_size}

    if term:
        where.append("""
            (
                LOWER(c.phone) LIKE :term
                OR LOWER(COALESCE(c.first_name,'') || ' ' || COALESCE(c.last_name,'')) LIKE :term
                OR EXISTS (
                    SELECT 1
                    FROM messages mx
                    WHERE mx.phone = c.phone
                      AND LOWER(COALESCE(mx.text, '')) LIKE :term
                )
            )
        """)
        params["term"] = f"%{term}%"

    if tag:
        where.append("LOWER(COALESCE(c.tags,'')) LIKE :tag")
        params["tag"] = f"%{tag}%"

    if intent:
        where.append("UPPER(COALESCE(c.intent_current,'')) = :intent")
        params["intent"] = intent

    if payment_status:
        where.append("LOWER(COALESCE(c.payment_status,'')) = :payment_status")
        params["payment_status"] = payment_status

    if takeover == "on":
        where.append("c.takeover = TRUE")
    elif takeover == "off":
        where.append("c.takeover = FALSE")

    unread_sql = """
        EXISTS (
            SELECT 1
            FROM messages mi
            WHERE mi.phone = c.phone
              AND mi.direction = 'in'
              AND mi.created_at > COALESCE(c.last_read_at, TIMESTAMP 'epoch')
        )
    """
    if unread == "yes":
        where.append(unread_sql)
    elif unread == "no":
        where.append(f"NOT ({unread_sql})")

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT
                c.phone,
                c.takeover,
                c.updated_at,
                c.first_name,
                c.last_name,
                c.city,
                c.customer_type,
                c.interests,
                c.tags,
                c.notes,
                c.intent_current,
                c.intent_stage,
                c.payment_status,
                c.payment_reference,
                m.text AS last_text,
                m.created_at AS last_message_at,
                (
                    SELECT COUNT(*)
                    FROM messages mm
                    WHERE mm.phone = c.phone
                ) AS messages_total,
                {unread_sql} AS has_unread
            FROM conversations c
            LEFT JOIN LATERAL (
                SELECT text, created_at
                FROM messages
                WHERE phone = c.phone
                ORDER BY created_at DESC
                LIMIT 1
            ) m ON TRUE
            {where_sql}
            ORDER BY c.updated_at DESC
            LIMIT :limit OFFSET :offset
        """), params).mappings().all()

        total_row = conn.execute(text(f"""
            SELECT COUNT(*) AS total
            FROM conversations c
            {where_sql}
        """), params).mappings().first()

    return {
        "page": page,
        "page_size": page_size,
        "total": int((total_row or {}).get("total") or 0),
        "customers": [dict(r) for r in rows],
    }


@app.get("/api/customers/{phone}")
def get_customer(phone: str):
    phone = (phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phone required")

    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT
                c.phone,
                c.takeover,
                c.updated_at,
                c.first_name,
                c.last_name,
                c.city,
                c.customer_type,
                c.interests,
                c.tags,
                c.notes,
                c.intent_current,
                c.intent_stage,
                c.payment_status,
                c.payment_reference,
                c.payment_amount,
                c.payment_currency,
                COALESCE(c.crm_meta, '{}'::jsonb) AS crm_meta,
                (
                    SELECT COUNT(*)
                    FROM messages m
                    WHERE m.phone = c.phone
                ) AS messages_total
            FROM conversations c
            WHERE c.phone = :phone
            LIMIT 1
        """), {"phone": phone}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="customer not found")

    return {"customer": dict(row)}


@app.patch("/api/customers/{phone}")
def patch_customer(phone: str, payload: CustomerPatch):
    phone = (phone or "").strip()
    if not phone:
        raise HTTPException(status_code=400, detail="phone required")

    data = payload.model_dump(exclude_unset=True)
    if not data:
        return get_customer(phone)

    allowed = {
        "first_name",
        "last_name",
        "city",
        "customer_type",
        "interests",
        "tags",
        "notes",
        "payment_status",
        "payment_reference",
    }
    fields = {k: v for k, v in data.items() if k in allowed}
    if not fields:
        raise HTTPException(status_code=400, detail="no valid fields to update")

    set_parts = ["updated_at = :updated_at"]
    params: Dict[str, Any] = {"phone": phone, "updated_at": datetime.utcnow()}

    for k, v in fields.items():
        set_parts.append(f"{k} = :{k}")
        params[k] = "" if v is None else str(v)

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, updated_at)
            VALUES (:phone, :updated_at)
            ON CONFLICT (phone) DO NOTHING
        """), {"phone": phone, "updated_at": params["updated_at"]})

        conn.execute(text(f"""
            UPDATE conversations
            SET {", ".join(set_parts)}
            WHERE phone = :phone
        """), params)

    return get_customer(phone)


# =========================================================
# Templates
# =========================================================

@app.get("/api/templates")
def list_templates(
    status: str = Query("all", description="all|draft|approved|archived"),
    category: str = Query("", description="Categoria"),
    search: str = Query("", description="Buscar por nombre/body"),
):
    status = (status or "all").strip().lower()
    category = (category or "").strip().lower()
    search = (search or "").strip().lower()

    where: List[str] = []
    params: Dict[str, Any] = {}

    if status != "all":
        where.append("LOWER(t.status) = :status")
        params["status"] = status

    if category:
        where.append("LOWER(t.category) = :category")
        params["category"] = category

    if search:
        where.append("(LOWER(t.name) LIKE :search OR LOWER(t.body) LIKE :search)")
        params["search"] = f"%{search}%"

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT
                t.id, t.name, t.category, t.body, t.variables_json, t.status, t.created_at, t.updated_at
            FROM message_templates t
            {where_sql}
            ORDER BY t.updated_at DESC, t.id DESC
        """), params).mappings().all()

    return {"templates": [dict(r) for r in rows]}


@app.post("/api/templates")
def create_template(payload: TemplateIn):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    status = _normalize_status(
        payload.status,
        allowed={"draft", "approved", "archived"},
        default="draft",
    )

    vars_clean = []
    seen = set()
    for raw in payload.variables_json or []:
        key = str(raw or "").strip()
        if not key:
            continue
        key_low = key.lower()
        if key_low in seen:
            continue
        seen.add(key_low)
        vars_clean.append(key)

    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO message_templates (
                name, category, body, variables_json, status, created_at, updated_at
            )
            VALUES (
                :name, :category, :body, CAST(:variables_json AS jsonb), :status, NOW(), NOW()
            )
            RETURNING id, name, category, body, variables_json, status, created_at, updated_at
        """), {
            "name": name,
            "category": (payload.category or "general").strip().lower() or "general",
            "body": payload.body or "",
            "variables_json": json.dumps(vars_clean, ensure_ascii=False),
            "status": status,
        }).mappings().first()

    return {"template": dict(row or {})}


@app.patch("/api/templates/{template_id}")
def update_template(template_id: int, payload: TemplatePatch):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets: List[str] = ["updated_at = NOW()"]
    params: Dict[str, Any] = {"template_id": int(template_id)}

    if "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        sets.append("name = :name")
        params["name"] = name

    if "category" in data:
        sets.append("category = :category")
        params["category"] = (str(data.get("category") or "").strip().lower() or "general")

    if "body" in data:
        sets.append("body = :body")
        params["body"] = str(data.get("body") or "")

    if "variables_json" in data:
        vars_clean = []
        seen = set()
        for raw in (data.get("variables_json") or []):
            key = str(raw or "").strip()
            if not key:
                continue
            kl = key.lower()
            if kl in seen:
                continue
            seen.add(kl)
            vars_clean.append(key)
        sets.append("variables_json = CAST(:variables_json AS jsonb)")
        params["variables_json"] = json.dumps(vars_clean, ensure_ascii=False)

    if "status" in data:
        sets.append("status = :status")
        params["status"] = _normalize_status(
            str(data.get("status") or ""),
            allowed={"draft", "approved", "archived"},
            default="draft",
        )

    with engine.begin() as conn:
        row = conn.execute(text(f"""
            UPDATE message_templates
            SET {", ".join(sets)}
            WHERE id = :template_id
            RETURNING id, name, category, body, variables_json, status, created_at, updated_at
        """), params).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="template not found")

    return {"template": dict(row)}


@app.post("/api/templates/{template_id}/preview")
def preview_template(template_id: int, payload: TemplatePreviewIn):
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT id, name, body, variables_json
            FROM message_templates
            WHERE id = :template_id
            LIMIT 1
        """), {"template_id": int(template_id)}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="template not found")

    template = dict(row)
    rendered = _render_template(template.get("body") or "", payload.variables or {})
    return {"preview": rendered, "template": template}


# =========================================================
# Campaigns
# =========================================================

@app.get("/api/campaigns")
def list_campaigns(
    status: str = Query("all", description="all|draft|scheduled|running|paused|completed|archived"),
):
    status = (status or "all").strip().lower()
    params: Dict[str, Any] = {}
    where_sql = ""
    if status != "all":
        where_sql = "WHERE LOWER(c.status) = :status"
        params["status"] = status

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT
                c.id, c.name, c.objective, c.segment_id, c.template_id,
                c.status, c.scheduled_at, c.launched_at, c.channel,
                c.created_at, c.updated_at,
                s.name AS segment_name,
                t.name AS template_name
            FROM campaigns c
            LEFT JOIN customer_segments s ON s.id = c.segment_id
            LEFT JOIN message_templates t ON t.id = c.template_id
            {where_sql}
            ORDER BY c.updated_at DESC, c.id DESC
        """), params).mappings().all()

    return {"campaigns": [dict(r) for r in rows]}


@app.post("/api/campaigns")
def create_campaign(payload: CampaignIn):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    status = _normalize_status(
        payload.status,
        allowed={"draft", "scheduled", "running", "paused", "completed", "archived"},
        default="draft",
    )

    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO campaigns (
                name, objective, segment_id, template_id, status, scheduled_at, channel, created_at, updated_at
            )
            VALUES (
                :name, :objective, :segment_id, :template_id, :status, :scheduled_at, :channel, NOW(), NOW()
            )
            RETURNING
                id, name, objective, segment_id, template_id, status, scheduled_at, launched_at, channel, created_at, updated_at
        """), {
            "name": name,
            "objective": payload.objective or "",
            "segment_id": payload.segment_id,
            "template_id": payload.template_id,
            "status": status,
            "scheduled_at": payload.scheduled_at,
            "channel": (payload.channel or "whatsapp").strip().lower() or "whatsapp",
        }).mappings().first()

    return {"campaign": dict(row or {})}


@app.patch("/api/campaigns/{campaign_id}")
def update_campaign(campaign_id: int, payload: CampaignPatch):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets: List[str] = ["updated_at = NOW()"]
    params: Dict[str, Any] = {"campaign_id": int(campaign_id)}

    if "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        sets.append("name = :name")
        params["name"] = name

    if "objective" in data:
        sets.append("objective = :objective")
        params["objective"] = str(data.get("objective") or "")

    if "segment_id" in data:
        sets.append("segment_id = :segment_id")
        params["segment_id"] = data.get("segment_id")

    if "template_id" in data:
        sets.append("template_id = :template_id")
        params["template_id"] = data.get("template_id")

    if "status" in data:
        sets.append("status = :status")
        params["status"] = _normalize_status(
            str(data.get("status") or ""),
            allowed={"draft", "scheduled", "running", "paused", "completed", "archived"},
            default="draft",
        )

    if "scheduled_at" in data:
        sets.append("scheduled_at = :scheduled_at")
        params["scheduled_at"] = data.get("scheduled_at")

    if "channel" in data:
        sets.append("channel = :channel")
        params["channel"] = (str(data.get("channel") or "").strip().lower() or "whatsapp")

    with engine.begin() as conn:
        row = conn.execute(text(f"""
            UPDATE campaigns
            SET {", ".join(sets)}
            WHERE id = :campaign_id
            RETURNING
                id, name, objective, segment_id, template_id, status, scheduled_at, launched_at, channel, created_at, updated_at
        """), params).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="campaign not found")

    return {"campaign": dict(row)}


@app.post("/api/campaigns/{campaign_id}/launch")
def launch_campaign(campaign_id: int, max_recipients: int = Query(300, ge=1, le=5000)):
    now = datetime.utcnow()
    with engine.begin() as conn:
        campaign = conn.execute(text("""
            SELECT id, segment_id, scheduled_at
            FROM campaigns
            WHERE id = :campaign_id
            LIMIT 1
        """), {"campaign_id": int(campaign_id)}).mappings().first()

        if not campaign:
            raise HTTPException(status_code=404, detail="campaign not found")

        rules: Dict[str, Any] = {}
        if campaign.get("segment_id"):
            s = conn.execute(text("""
                SELECT rules_json
                FROM customer_segments
                WHERE id = :segment_id
                LIMIT 1
            """), {"segment_id": int(campaign.get("segment_id"))}).mappings().first()
            rules = _safe_json_dict((s or {}).get("rules_json"))

        where_sql, seg_params = _segment_filter_sql(rules, prefix="seg")
        seg_params["campaign_id"] = int(campaign_id)
        seg_params["limit"] = int(max_recipients)

        conn.execute(text(f"""
            WITH picked AS (
                SELECT c.phone
                FROM conversations c
                WHERE {where_sql}
                ORDER BY c.updated_at DESC
                LIMIT :limit
            )
            INSERT INTO campaign_recipients (campaign_id, phone, status, created_at)
            SELECT :campaign_id, p.phone, 'pending', NOW()
            FROM picked p
            ON CONFLICT (campaign_id, phone) DO NOTHING
        """), seg_params)

        status = "scheduled" if campaign.get("scheduled_at") and campaign.get("scheduled_at") > now else "running"
        launched_at = None if status == "scheduled" else now

        conn.execute(text("""
            UPDATE campaigns
            SET status = :status,
                launched_at = COALESCE(:launched_at, launched_at),
                updated_at = NOW()
            WHERE id = :campaign_id
        """), {"status": status, "launched_at": launched_at, "campaign_id": int(campaign_id)})

        stats = conn.execute(text("""
            SELECT
                COUNT(*) AS total_recipients,
                COUNT(*) FILTER (WHERE LOWER(status) = 'pending') AS pending
            FROM campaign_recipients
            WHERE campaign_id = :campaign_id
        """), {"campaign_id": int(campaign_id)}).mappings().first()

    return {
        "ok": True,
        "campaign_id": int(campaign_id),
        "status": status,
        "total_recipients": int((stats or {}).get("total_recipients") or 0),
        "pending": int((stats or {}).get("pending") or 0),
    }


@app.get("/api/campaigns/{campaign_id}/stats")
def campaign_stats(campaign_id: int):
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE LOWER(status) = 'pending') AS pending,
                COUNT(*) FILTER (WHERE LOWER(status) = 'processing') AS processing,
                COUNT(*) FILTER (WHERE LOWER(status) = 'sent') AS sent,
                COUNT(*) FILTER (WHERE LOWER(status) = 'delivered') AS delivered,
                COUNT(*) FILTER (WHERE LOWER(status) = 'read') AS read,
                COUNT(*) FILTER (WHERE LOWER(status) = 'replied') AS replied,
                COUNT(*) FILTER (WHERE LOWER(status) = 'failed') AS failed
            FROM campaign_recipients
            WHERE campaign_id = :campaign_id
        """), {"campaign_id": int(campaign_id)}).mappings().first()

    d = dict(row or {})
    sent = int(d.get("sent") or 0)
    delivered = int(d.get("delivered") or 0)
    read = int(d.get("read") or 0)
    replied = int(d.get("replied") or 0)
    total = int(d.get("total") or 0)

    return {
        "campaign_id": int(campaign_id),
        "total": total,
        "pending": int(d.get("pending") or 0),
        "processing": int(d.get("processing") or 0),
        "sent": sent,
        "delivered": delivered,
        "read": read,
        "replied": replied,
        "failed": int(d.get("failed") or 0),
        "delivery_rate_pct": round((delivered / sent) * 100, 2) if sent else 0.0,
        "read_rate_pct": round((read / delivered) * 100, 2) if delivered else 0.0,
        "reply_rate_pct": round((replied / read) * 100, 2) if read else 0.0,
        "coverage_pct": round((sent / total) * 100, 2) if total else 0.0,
    }


@app.get("/api/campaigns/engine/status")
def campaign_engine_status():
    cfg = engine_settings()
    running = bool(_campaign_engine_task and not _campaign_engine_task.done())
    return {
        "enabled": bool(cfg.get("enabled")),
        "running": running,
        "interval_sec": int(cfg.get("interval_sec") or 0),
        "batch_size": int(cfg.get("batch_size") or 0),
        "send_delay_ms": int(cfg.get("send_delay_ms") or 0),
    }


@app.post("/api/campaigns/engine/tick")
async def campaign_engine_tick_now(
    batch_size: int = Query(20, ge=1, le=500),
    send_delay_ms: int = Query(0, ge=0, le=2000),
):
    data = await campaign_engine_tick(batch_size=batch_size, send_delay_ms=send_delay_ms)
    return data


# =========================================================
# Triggers
# =========================================================

@app.get("/api/triggers")
def list_triggers(active: str = Query("all", description="all|yes|no")):
    active = (active or "all").strip().lower()
    where_sql = ""
    if active == "yes":
        where_sql = "WHERE is_active = TRUE"
    elif active == "no":
        where_sql = "WHERE is_active = FALSE"

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT
                id, name, event_type, conditions_json, action_json,
                cooldown_minutes, is_active, last_run_at, created_at, updated_at
            FROM automation_triggers
            {where_sql}
            ORDER BY updated_at DESC, id DESC
        """)).mappings().all()

    return {"triggers": [dict(r) for r in rows]}


@app.post("/api/triggers")
def create_trigger(payload: TriggerIn):
    name = (payload.name or "").strip()
    event_type = (payload.event_type or "").strip().lower()
    if not name or not event_type:
        raise HTTPException(status_code=400, detail="name and event_type are required")

    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO automation_triggers (
                name, event_type, conditions_json, action_json,
                cooldown_minutes, is_active, created_at, updated_at
            )
            VALUES (
                :name, :event_type, CAST(:conditions_json AS jsonb), CAST(:action_json AS jsonb),
                :cooldown_minutes, :is_active, NOW(), NOW()
            )
            RETURNING
                id, name, event_type, conditions_json, action_json,
                cooldown_minutes, is_active, last_run_at, created_at, updated_at
        """), {
            "name": name,
            "event_type": event_type,
            "conditions_json": json.dumps(_safe_json_dict(payload.conditions_json), ensure_ascii=False),
            "action_json": json.dumps(_safe_json_dict(payload.action_json), ensure_ascii=False),
            "cooldown_minutes": max(0, min(int(payload.cooldown_minutes or 0), 10080)),
            "is_active": bool(payload.is_active),
        }).mappings().first()

    return {"trigger": dict(row or {})}


@app.patch("/api/triggers/{trigger_id}")
def update_trigger(trigger_id: int, payload: TriggerPatch):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets: List[str] = ["updated_at = NOW()"]
    params: Dict[str, Any] = {"trigger_id": int(trigger_id)}

    if "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        sets.append("name = :name")
        params["name"] = name

    if "event_type" in data:
        event_type = str(data.get("event_type") or "").strip().lower()
        if not event_type:
            raise HTTPException(status_code=400, detail="event_type cannot be empty")
        sets.append("event_type = :event_type")
        params["event_type"] = event_type

    if "conditions_json" in data:
        sets.append("conditions_json = CAST(:conditions_json AS jsonb)")
        params["conditions_json"] = json.dumps(_safe_json_dict(data.get("conditions_json")), ensure_ascii=False)

    if "action_json" in data:
        sets.append("action_json = CAST(:action_json AS jsonb)")
        params["action_json"] = json.dumps(_safe_json_dict(data.get("action_json")), ensure_ascii=False)

    if "cooldown_minutes" in data:
        sets.append("cooldown_minutes = :cooldown_minutes")
        params["cooldown_minutes"] = max(0, min(int(data.get("cooldown_minutes") or 0), 10080))

    if "is_active" in data:
        sets.append("is_active = :is_active")
        params["is_active"] = bool(data.get("is_active"))

    with engine.begin() as conn:
        row = conn.execute(text(f"""
            UPDATE automation_triggers
            SET {", ".join(sets)}
            WHERE id = :trigger_id
            RETURNING
                id, name, event_type, conditions_json, action_json,
                cooldown_minutes, is_active, last_run_at, created_at, updated_at
        """), params).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="trigger not found")

    return {"trigger": dict(row)}


# =========================================================
# Remarketing
# =========================================================

@app.get("/api/remarketing/flows")
def list_remarketing_flows():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT
                f.id, f.name, f.entry_rules_json, f.exit_rules_json, f.is_active, f.created_at, f.updated_at,
                (
                    SELECT COUNT(*)
                    FROM remarketing_steps s
                    WHERE s.flow_id = f.id
                ) AS steps_count
            FROM remarketing_flows f
            ORDER BY f.updated_at DESC, f.id DESC
        """)).mappings().all()

    return {"flows": [dict(r) for r in rows]}


@app.post("/api/remarketing/flows")
def create_remarketing_flow(payload: RemarketingFlowIn):
    name = (payload.name or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO remarketing_flows (
                name, entry_rules_json, exit_rules_json, is_active, created_at, updated_at
            )
            VALUES (
                :name, CAST(:entry_rules_json AS jsonb), CAST(:exit_rules_json AS jsonb), :is_active, NOW(), NOW()
            )
            RETURNING id, name, entry_rules_json, exit_rules_json, is_active, created_at, updated_at
        """), {
            "name": name,
            "entry_rules_json": json.dumps(_safe_json_dict(payload.entry_rules_json), ensure_ascii=False),
            "exit_rules_json": json.dumps(_safe_json_dict(payload.exit_rules_json), ensure_ascii=False),
            "is_active": bool(payload.is_active),
        }).mappings().first()

    return {"flow": dict(row or {})}


@app.patch("/api/remarketing/flows/{flow_id}")
def update_remarketing_flow(flow_id: int, payload: RemarketingFlowPatch):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets: List[str] = ["updated_at = NOW()"]
    params: Dict[str, Any] = {"flow_id": int(flow_id)}

    if "name" in data:
        name = str(data.get("name") or "").strip()
        if not name:
            raise HTTPException(status_code=400, detail="name cannot be empty")
        sets.append("name = :name")
        params["name"] = name

    if "entry_rules_json" in data:
        sets.append("entry_rules_json = CAST(:entry_rules_json AS jsonb)")
        params["entry_rules_json"] = json.dumps(_safe_json_dict(data.get("entry_rules_json")), ensure_ascii=False)

    if "exit_rules_json" in data:
        sets.append("exit_rules_json = CAST(:exit_rules_json AS jsonb)")
        params["exit_rules_json"] = json.dumps(_safe_json_dict(data.get("exit_rules_json")), ensure_ascii=False)

    if "is_active" in data:
        sets.append("is_active = :is_active")
        params["is_active"] = bool(data.get("is_active"))

    with engine.begin() as conn:
        row = conn.execute(text(f"""
            UPDATE remarketing_flows
            SET {", ".join(sets)}
            WHERE id = :flow_id
            RETURNING id, name, entry_rules_json, exit_rules_json, is_active, created_at, updated_at
        """), params).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="flow not found")

    return {"flow": dict(row)}


@app.get("/api/remarketing/flows/{flow_id}/steps")
def list_remarketing_steps(flow_id: int):
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT
                s.id, s.flow_id, s.step_order, s.wait_minutes, s.template_id, s.created_at,
                t.name AS template_name
            FROM remarketing_steps s
            LEFT JOIN message_templates t ON t.id = s.template_id
            WHERE s.flow_id = :flow_id
            ORDER BY s.step_order ASC
        """), {"flow_id": int(flow_id)}).mappings().all()

    return {"steps": [dict(r) for r in rows]}


@app.post("/api/remarketing/flows/{flow_id}/steps")
def create_remarketing_step(flow_id: int, payload: RemarketingStepIn):
    with engine.begin() as conn:
        row = conn.execute(text("""
            INSERT INTO remarketing_steps (flow_id, step_order, wait_minutes, template_id, created_at)
            VALUES (:flow_id, :step_order, :wait_minutes, :template_id, NOW())
            RETURNING id, flow_id, step_order, wait_minutes, template_id, created_at
        """), {
            "flow_id": int(flow_id),
            "step_order": max(1, int(payload.step_order or 1)),
            "wait_minutes": max(0, int(payload.wait_minutes or 0)),
            "template_id": payload.template_id,
        }).mappings().first()

    return {"step": dict(row or {})}


@app.patch("/api/remarketing/steps/{step_id}")
def update_remarketing_step(step_id: int, payload: RemarketingStepPatch):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets: List[str] = []
    params: Dict[str, Any] = {"step_id": int(step_id)}

    if "step_order" in data:
        sets.append("step_order = :step_order")
        params["step_order"] = max(1, int(data.get("step_order") or 1))

    if "wait_minutes" in data:
        sets.append("wait_minutes = :wait_minutes")
        params["wait_minutes"] = max(0, int(data.get("wait_minutes") or 0))

    if "template_id" in data:
        sets.append("template_id = :template_id")
        params["template_id"] = data.get("template_id")

    with engine.begin() as conn:
        row = conn.execute(text(f"""
            UPDATE remarketing_steps
            SET {", ".join(sets)}
            WHERE id = :step_id
            RETURNING id, flow_id, step_order, wait_minutes, template_id, created_at
        """), params).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="step not found")

    return {"step": dict(row)}
