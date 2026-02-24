# app/main.py

import os
import json
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from starlette.requests import Request as StarletteRequest

from app.db import engine

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

origins = [
    "https://app.perfumesverane.com",
    "http://localhost:5173",
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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


# Routers
app.include_router(whatsapp_router)
if ai_router is not None:
    app.include_router(ai_router, prefix="/api/ai")


# =========================================================
# DATABASE SCHEMA
# =========================================================

def ensure_schema():
    """
    Crea/actualiza el schema mínimo que el CRM + pipeline necesita.
    (Seguro si ya existe; usa IF NOT EXISTS)
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

        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations (updated_at)"""))

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
        # wc_products_cache (Plan B)
        # -------------------------
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

        ensure_schema()


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
                    notes
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
            }

        return dict(r)

    except Exception as e:
        return {"ok": False, "error": str(e), "phone": phone}