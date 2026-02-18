import os
import re
import json
import requests
import asyncio
from datetime import datetime
from typing import Optional, List

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

# ✅ Router externo WhatsApp
from app.routes.whatsapp import router as whatsapp_router
from app.routes.whatsapp import send_whatsapp_text, send_whatsapp_media_id

# ✅ IA
from app.ai.engine import process_message
from app.ai.context_builder import build_ai_meta

# ✅ (Recomendado) Montar router IA (/api/ai/settings, /api/ai/knowledge, etc.)
try:
    from app.ai.router import router as ai_router
except Exception:
    ai_router = None


# =========================================================
# APP
# =========================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

from fastapi.responses import JSONResponse
from starlette.requests import Request as StarletteRequest

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

app.include_router(whatsapp_router)

if ai_router is not None:
    app.include_router(ai_router, prefix="/api/ai")

# =========================================================
# DATABASE
# =========================================================

from app.db import engine

LAST_PRODUCT_CACHE: dict[str, dict] = {}


def ensure_schema():
    with engine.begin() as conn:

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
                notes TEXT
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                phone TEXT NOT NULL,
                direction TEXT NOT NULL,
                msg_type TEXT NOT NULL DEFAULT 'text',
                text TEXT NOT NULL DEFAULT '',
                media_url TEXT,
                media_caption TEXT,
                featured_image TEXT,
                real_image TEXT,
                permalink TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

        # ✅ Extraccion de datos
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS extracted_text TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS ai_meta JSONB"""))

        # ✅ Control de tráfico
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_messages_phone_created_at ON messages (phone, created_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_messages_phone_direction_created_at ON messages (phone, direction, created_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations (updated_at)"""))

        # ✅ Media extra
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS media_id TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS mime_type TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS file_name TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS file_size INTEGER"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS duration_sec INTEGER"""))

        # ✅ Estados WhatsApp (checkmarks)
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_message_id TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_status TEXT"""))  # sent|delivered|read|failed
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_error TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_ts_sent TIMESTAMP"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_ts_delivered TIMESTAMP"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_ts_read TIMESTAMP"""))

        # ✅ Unread tracking (para filtros "no leído")
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_read_at TIMESTAMP"""))

        # ✅ Estado IA estructural
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS ai_state TEXT"""))

        # ✅ Tabla settings IA
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_settings (
                id SERIAL PRIMARY KEY,
                is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
                provider TEXT NOT NULL DEFAULT 'google',
                model TEXT NOT NULL DEFAULT 'gemma-3-4b-it',
                system_prompt TEXT NOT NULL DEFAULT '',
                max_tokens INTEGER NOT NULL DEFAULT 512,
                temperature DOUBLE PRECISION NOT NULL DEFAULT 0.7,

                fallback_provider TEXT NOT NULL DEFAULT 'groq',
                fallback_model TEXT NOT NULL DEFAULT 'llama-3.1-8b-instant',

                timeout_sec INTEGER NOT NULL DEFAULT 25,
                max_retries INTEGER NOT NULL DEFAULT 1,

                created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

        # ✅ settings humanización (para envío por chunks)
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS reply_chunk_chars INTEGER"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS reply_delay_ms INTEGER"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS typing_delay_ms INTEGER"""))

        # Insertar 1 fila default si la tabla está vacía
        conn.execute(text("""
            INSERT INTO ai_settings (
                is_enabled, provider, model, system_prompt,
                max_tokens, temperature,
                fallback_provider, fallback_model,
                timeout_sec, max_retries,
                reply_chunk_chars, reply_delay_ms, typing_delay_ms
            )
            SELECT
                TRUE, 'google', 'gemma-3-4b-it', '',
                512, 0.7,
                'groq', 'llama-3.1-8b-instant',
                25, 1,
                480, 900, 450
            WHERE NOT EXISTS (SELECT 1 FROM ai_settings)
        """))

        # ✅ Si ya existía la fila, aseguramos defaults si quedaron NULL
        conn.execute(text("""
            UPDATE ai_settings
            SET
                reply_chunk_chars = COALESCE(reply_chunk_chars, 480),
                reply_delay_ms = COALESCE(reply_delay_ms, 900),
                typing_delay_ms = COALESCE(typing_delay_ms, 450)
            WHERE id = (SELECT id FROM ai_settings ORDER BY id ASC LIMIT 1)
        """))


ensure_schema()

# =========================================================
# MODELS
# =========================================================

class IngestMessage(BaseModel):
    model_config = {"extra": "allow"}

    phone: str
    direction: str
    msg_type: str = "text"  # text | image | video | audio | document | product

    text: str = ""

    media_url: Optional[str] = None
    media_caption: Optional[str] = None
    media_id: Optional[str] = None
    mime_type: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    duration_sec: Optional[int] = None

    featured_image: Optional[str] = None
    real_image: Optional[str] = None
    permalink: Optional[str] = None


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

def save_message(
    conn,
    phone: str,
    direction: str,
    text_msg: str = "",
    msg_type: str = "text",

    media_url: Optional[str] = None,
    media_caption: Optional[str] = None,
    media_id: Optional[str] = None,
    mime_type: Optional[str] = None,
    file_name: Optional[str] = None,
    file_size: Optional[int] = None,
    duration_sec: Optional[int] = None,

    featured_image: Optional[str] = None,
    real_image: Optional[str] = None,
    permalink: Optional[str] = None,
) -> int:
    r = conn.execute(text("""
        INSERT INTO messages (
            phone, direction, msg_type, text,
            media_url, media_caption, media_id, mime_type, file_name, file_size, duration_sec,
            featured_image, real_image, permalink, created_at,
            wa_status, wa_ts_sent
        )
        VALUES (
            :phone, :direction, :msg_type, :text,
            :media_url, :media_caption, :media_id, :mime_type, :file_name, :file_size, :duration_sec,
            :featured_image, :real_image, :permalink, :created_at,
            :wa_status, :wa_ts_sent
        )
        RETURNING id
    """), {
        "phone": phone,
        "direction": direction,
        "msg_type": msg_type,
        "text": text_msg,
        "media_url": media_url,
        "media_caption": media_caption,
        "media_id": media_id,
        "mime_type": mime_type,
        "file_name": file_name,
        "file_size": file_size,
        "duration_sec": duration_sec,
        "featured_image": featured_image,
        "real_image": real_image,
        "permalink": permalink,
        "created_at": datetime.utcnow(),

        # ✅ si es OUT, estado inicial visual "sent"
        "wa_status": "sent" if direction == "out" else None,
        "wa_ts_sent": datetime.utcnow() if direction == "out" else None,
    })

    message_id = int(r.scalar())

    # subir conversación al inbox
    conn.execute(text("""
        INSERT INTO conversations (phone, updated_at)
        VALUES (:phone, :updated_at)
        ON CONFLICT (phone) DO UPDATE SET updated_at = EXCLUDED.updated_at
    """), {"phone": phone, "updated_at": datetime.utcnow()})

    return message_id


def set_wa_send_result(conn, local_message_id: int, wa_message_id: Optional[str], sent_ok: bool, wa_error: str = ""):
    if not wa_message_id or not sent_ok:
        conn.execute(text("""
            UPDATE messages
            SET wa_status = 'failed',
                wa_error = :wa_error
            WHERE id = :id
        """), {"id": local_message_id, "wa_error": wa_error or "WhatsApp send failed"})
        return

    conn.execute(text("""
        UPDATE messages
        SET wa_message_id = :wa_message_id,
            wa_status = 'sent',
            wa_error = NULL,
            wa_ts_sent = COALESCE(wa_ts_sent, NOW())
        WHERE id = :id
    """), {"id": local_message_id, "wa_message_id": wa_message_id})


def _parse_tags_param(tags: str) -> List[str]:
    if not tags:
        return []
    out = []
    for t in tags.split(","):
        tt = (t or "").strip().lower()
        if tt:
            out.append(tt)
    return out


def _get_ai_send_settings() -> dict:
    """
    Lee chunk/delay desde ai_settings.
    """
    defaults = {"reply_chunk_chars": 480, "reply_delay_ms": 900, "typing_delay_ms": 450}
    try:
        with engine.begin() as conn:
            r = conn.execute(text("""
                SELECT
                    COALESCE(reply_chunk_chars, 480) AS reply_chunk_chars,
                    COALESCE(reply_delay_ms, 900) AS reply_delay_ms,
                    COALESCE(typing_delay_ms, 450) AS typing_delay_ms
                FROM ai_settings
                ORDER BY id ASC
                LIMIT 1
            """)).mappings().first()
        if not r:
            return defaults
        d = dict(r)
        d["reply_chunk_chars"] = int(max(120, min(int(d.get("reply_chunk_chars") or 480), 2000)))
        d["reply_delay_ms"] = int(max(0, min(int(d.get("reply_delay_ms") or 900), 15000)))
        d["typing_delay_ms"] = int(max(0, min(int(d.get("typing_delay_ms") or 450), 15000)))
        return d
    except Exception:
        return defaults


def _normalize_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\r\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _split_long_text(text_msg: str, max_chars: int) -> list[str]:
    """
    Splitter igual al de whatsapp.py para que el UI y la DB queden 1:1 con lo enviado.
    """
    text_msg = _normalize_text(text_msg)
    if not text_msg:
        return [""]

    if max_chars <= 0:
        return [text_msg]

    paras = [p.strip() for p in text_msg.split("\n\n") if p.strip()]
    out: list[str] = []

    sentence_split_re = re.compile(r"(?<=[\.\!\?])\s+")

    def _push_piece(piece: str):
        piece = piece.strip()
        if not piece:
            return
        if len(piece) <= max_chars:
            out.append(piece)
            return

        sents = sentence_split_re.split(piece)
        if len(sents) <= 1:
            i = 0
            while i < len(piece):
                chunk = piece[i:i + max_chars].strip()
                if chunk:
                    out.append(chunk)
                i += max_chars
            return

        buf = ""
        for s in sents:
            s = s.strip()
            if not s:
                continue
            cand = (buf + " " + s).strip() if buf else s
            if len(cand) <= max_chars:
                buf = cand
            else:
                if buf:
                    out.append(buf)
                if len(s) <= max_chars:
                    buf = s
                else:
                    j = 0
                    while j < len(s):
                        c = s[j:j + max_chars].strip()
                        if c:
                            out.append(c)
                        j += max_chars
                    buf = ""
        if buf:
            out.append(buf)

    buf = ""
    for p in paras:
        if not buf:
            if len(p) <= max_chars:
                buf = p
            else:
                _push_piece(p)
                buf = ""
            continue

        cand = (buf + "\n\n" + p).strip()
        if len(cand) <= max_chars:
            buf = cand
        else:
            out.append(buf)
            if len(p) <= max_chars:
                buf = p
            else:
                _push_piece(p)
                buf = ""

    if buf:
        out.append(buf)

    out = [x.strip() for x in out if x.strip()]
    return out or [""]


async def _send_ai_reply_in_chunks(phone: str, full_text: str) -> dict:
    """
    - Divide texto en chunks (según ai_settings)
    - Por CADA chunk:
        - guarda mensaje OUT en DB
        - envía a WhatsApp
        - actualiza wa_message_id / status
        - espera delay
    """
    s = _get_ai_send_settings()
    max_chars = int(s.get("reply_chunk_chars") or 480)
    reply_delay = int(s.get("reply_delay_ms") or 900) / 1000.0
    typing_delay = int(s.get("typing_delay_ms") or 450) / 1000.0

    chunks = _split_long_text(full_text or "", max_chars=max_chars)
    if not chunks:
        chunks = [""]

    if typing_delay > 0:
        await asyncio.sleep(typing_delay)

    sent_any = False
    wa_ids: list[str] = []
    local_ids: list[int] = []
    last_wa_resp: dict = {"saved": True, "sent": False, "reason": "no chunks"}

    for idx, chunk in enumerate(chunks):
        with engine.begin() as conn:
            local_out_id = save_message(
                conn,
                phone=phone,
                direction="out",
                msg_type="text",
                text_msg=chunk,
            )
        local_ids.append(local_out_id)

        wa_resp = await send_whatsapp_text(phone, chunk)
        last_wa_resp = wa_resp if isinstance(wa_resp, dict) else {"sent": False, "reason": "invalid wa_resp"}

        wa_message_id = None
        if isinstance(last_wa_resp, dict) and last_wa_resp.get("sent") is True:
            sent_any = True
            wa_message_id = last_wa_resp.get("wa_message_id")
            if wa_message_id:
                wa_ids.append(str(wa_message_id))

        with engine.begin() as conn:
            if last_wa_resp.get("sent") is True and wa_message_id:
                set_wa_send_result(conn, local_out_id, wa_message_id, True, "")
            else:
                err = last_wa_resp.get("whatsapp_body") or last_wa_resp.get("reason") or last_wa_resp.get("error") or "WhatsApp send failed"
                set_wa_send_result(conn, local_out_id, None, False, str(err)[:900])

        if idx < len(chunks) - 1 and reply_delay > 0:
            await asyncio.sleep(reply_delay)

    return {
        "sent": sent_any,
        "chunks_sent": len(chunks),
        "local_message_ids": local_ids,
        "wa_message_ids": wa_ids,
        "last_wa": last_wa_resp,
        "humanized": True,
        "settings_used": {
            "reply_chunk_chars": max_chars,
            "reply_delay_ms": int(reply_delay * 1000),
            "typing_delay_ms": int(typing_delay * 1000),
        },
    }


# =========================================================
# AI STATE helpers (WooCommerce selection)
# =========================================================

def _get_ai_state(phone: str) -> str:
    try:
        with engine.begin() as conn:
            r = conn.execute(text("""
                SELECT COALESCE(ai_state,'') AS ai_state
                FROM conversations
                WHERE phone = :phone
                LIMIT 1
            """), {"phone": phone}).mappings().first()
        return str((r or {}).get("ai_state") or "")
    except Exception:
        return ""


def _set_ai_state(phone: str, state: str) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO conversations (phone, ai_state, updated_at)
                VALUES (:phone, :ai_state, :updated_at)
                ON CONFLICT (phone)
                DO UPDATE SET ai_state = EXCLUDED.ai_state,
                              updated_at = EXCLUDED.updated_at
            """), {"phone": phone, "ai_state": state or "", "updated_at": datetime.utcnow()})
    except Exception:
        return


def _clear_ai_state(phone: str) -> None:
    _set_ai_state(phone, "")


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9áéíóúñü\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


# =========================================================
# WOOCOMMERCE (CATÁLOGO + ENVÍO COMO ADJUNTO REAL)
# =========================================================

WC_BASE_URL = os.getenv("WC_BASE_URL", "").rstrip("/")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY", "")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET", "")

def _wc_enabled() -> bool:
    return bool(WC_BASE_URL and WC_CONSUMER_KEY and WC_CONSUMER_SECRET)

def _wc_get(path: str, params: dict | None = None):
    if not (WC_BASE_URL and WC_CONSUMER_KEY and WC_CONSUMER_SECRET):
        raise HTTPException(status_code=500, detail="WooCommerce env vars not set")

    url = f"{WC_BASE_URL}/wp-json/wc/v3{path}"
    params = params or {}
    params["consumer_key"] = WC_CONSUMER_KEY
    params["consumer_secret"] = WC_CONSUMER_SECRET

    try:
        r = requests.get(url, params=params, timeout=20)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"WooCommerce request error: {e}")

    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"WooCommerce error {r.status_code}: {r.text}")

    return r.json()

def _pick_first_image(product: dict) -> str | None:
    imgs = product.get("images") or []
    if imgs and isinstance(imgs, list):
        src = (imgs[0] or {}).get("src")
        return src
    return None

def _extract_aromas(product: dict) -> list[str]:
    out: list[str] = []
    attrs = product.get("attributes") or []
    for a in attrs:
        if not isinstance(a, dict):
            continue
        name = (a.get("name") or "").strip().lower()
        if name == "aromas":
            opts = a.get("options") or []
            if isinstance(opts, list):
                out = [str(x).strip() for x in opts if str(x).strip()]
    return out

def _extract_brand(product: dict) -> str:
    for md in (product.get("meta_data") or []):
        if not isinstance(md, dict):
            continue
        k = (md.get("key") or "").lower().strip()
        if k in ("brand", "_brand", "pa_brand", "product_brand", "yith_wcbm_brand"):
            v = md.get("value")
            if isinstance(v, str) and v.strip():
                return v.strip()

    for a in (product.get("attributes") or []):
        if not isinstance(a, dict):
            continue
        nm = (a.get("name") or "").lower().strip()
        if nm in ("brand", "marca"):
            opts = a.get("options") or []
            if isinstance(opts, list) and opts:
                return str(opts[0]).strip()

    tags = product.get("tags") or []
    if isinstance(tags, list) and tags:
        t0 = tags[0]
        if isinstance(t0, dict) and (t0.get("name") or "").strip():
            return (t0.get("name") or "").strip()

    return ""

def _extract_gender(product: dict) -> str:
    cats = product.get("categories") or []
    names = []
    for c in cats:
        if isinstance(c, dict) and c.get("name"):
            names.append(str(c["name"]).lower())

    if any("hombre" in n for n in names):
        return "hombre"
    if any("mujer" in n for n in names):
        return "mujer"
    if any("unisex" in n for n in names):
        return "unisex"
    return ""

def _map_product_for_ui(product: dict) -> dict:
    price = product.get("price") or product.get("regular_price") or ""
    return {
        "id": product.get("id"),
        "name": product.get("name") or "",
        "price": str(price),
        "permalink": product.get("permalink") or "",
        "featured_image": _pick_first_image(product),
        "short_description": (product.get("short_description") or "").strip(),
        "aromas": _extract_aromas(product),
        "brand": _extract_brand(product),
        "gender": _extract_gender(product),
        "stock_status": product.get("stock_status") or "",
    }

def _wc_search_products(query: str, per_page: int = 8) -> list[dict]:
    q = (query or "").strip()
    if not q:
        return []
    params = {"search": q, "page": 1, "per_page": int(per_page), "status": "publish"}
    data = _wc_get("/products", params=params)
    items = [_map_product_for_ui(p) for p in (data or [])]
    # prioriza in-stock primero
    items.sort(key=lambda x: (0 if (x.get("stock_status") == "instock") else 1, (x.get("name") or "")))
    return items

def _looks_like_product_question(user_text: str) -> bool:
    t = _norm(user_text)
    if not t:
        return False
    # señales típicas
    triggers = [
        "tienes", "tienen", "hay", "disponible", "disponibles",
        "precio", "vale", "cuanto", "cuánto",
        "nitro", "aqua", "giorgio", "perfume", "fragancia", "colonia"
    ]
    if any(w in t for w in triggers):
        # evitar dispararse por saludos
        if t in ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches"):
            return False
        return True
    # si el texto es “corto” pero parece nombre de producto
    if len(t.split()) <= 6 and len(t) >= 6:
        return True
    return False

def _score_product_match(query: str, product_name: str) -> int:
    q = _norm(query)
    n = _norm(product_name)
    if not q or not n:
        return 0
    if n == q:
        return 100
    if q in n:
        # más score si cubre bastante
        cover = int(50 + min(40, (len(q) * 40) / max(1, len(n))))
        return cover
    # match por palabras
    qwords = [w for w in q.split() if len(w) >= 3]
    if not qwords:
        return 0
    hit = sum(1 for w in qwords if w in n)
    if hit == 0:
        return 0
    return 20 + hit * 10

def _parse_choice_number(user_text: str) -> int | None:
    m = re.search(r"\b([1-9])\b", (user_text or "").strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


@app.get("/api/wc/products")
def wc_products(
    q: str = Query("", description="texto de búsqueda"),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
):
    params = {"search": q or "", "page": page, "per_page": per_page, "status": "publish"}
    data = _wc_get("/products", params=params)
    items = [_map_product_for_ui(p) for p in (data or [])]
    return {"products": items}


# =========================================================
# ✅ FUNCIÓN INTERNA ROBUSTA (no llamar endpoint como función)
# =========================================================
async def _wc_send_product_internal(phone: str, product_id: int, custom_caption: str = "") -> dict:
    import io
    from PIL import Image

    try:
        import pillow_avif  # noqa: F401
    except Exception:
        pillow_avif = None  # noqa: F841

    if not phone or not product_id:
        raise HTTPException(status_code=400, detail="phone and product_id required")

    if not (WC_BASE_URL and WC_CONSUMER_KEY and WC_CONSUMER_SECRET):
        raise HTTPException(status_code=500, detail="WC env vars not configured")

    url = f"{WC_BASE_URL}/wp-json/wc/v3/products/{product_id}"
    params = {"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}

    r = requests.get(url, params=params, timeout=25)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"WooCommerce product fetch failed: {r.status_code} {r.text}")

    product = r.json()

    images = product.get("images") or []
    if not images:
        raise HTTPException(status_code=400, detail="Product has no image")

    featured_image = (images[0] or {}).get("src") or ""
    real_image = (images[1] or {}).get("src") if len(images) > 1 else ""

    img_response = requests.get(featured_image, timeout=25)
    if img_response.status_code != 200 or not img_response.content:
        raise HTTPException(status_code=502, detail=f"Image download failed: {img_response.status_code}")

    image_bytes = img_response.content
    content_type = (img_response.headers.get("Content-Type") or "").lower()

    def _to_jpeg_bytes(src_bytes: bytes) -> bytes:
        im = Image.open(io.BytesIO(src_bytes))
        im = im.convert("RGB")
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=88, optimize=True)
        return out.getvalue()

    lower_url = featured_image.lower()
    needs_convert = (
        ("image/avif" in content_type) or ("image/webp" in content_type) or
        lower_url.endswith(".avif") or lower_url.endswith(".webp")
    )

    try:
        if needs_convert:
            image_bytes = _to_jpeg_bytes(image_bytes)
            mime_type = "image/jpeg"
        else:
            mime_type = content_type if content_type.startswith("image/") else "image/jpeg"
            if mime_type not in ("image/jpeg", "image/png"):
                image_bytes = _to_jpeg_bytes(image_bytes)
                mime_type = "image/jpeg"
    except Exception as e:
        try:
            image_bytes = _to_jpeg_bytes(image_bytes)
            mime_type = "image/jpeg"
        except Exception:
            raise HTTPException(status_code=500, detail=f"Image decode/convert failed: {e}")

    from app.routes.whatsapp import upload_whatsapp_media
    media_id = await upload_whatsapp_media(image_bytes, mime_type)

    name = product.get("name", "") or ""
    price = product.get("price") or product.get("regular_price") or ""
    short_description = re.sub('<[^<]+?>', '', product.get("short_description", "") or "").strip()
    permalink = product.get("permalink", "") or ""

    brand = _extract_brand(product)
    gender = _extract_gender(product)
    gender_label = "Hombre" if gender == "hombre" else "Mujer" if gender == "mujer" else "Unisex" if gender == "unisex" else ""

    aromas_list = _extract_aromas(product)
    aromas = ", ".join(aromas_list) if aromas_list else ""

    caption_lines = [f"✨ {name}"]
    if gender_label:
        caption_lines.append(f"👤 Para: {gender_label}")
    if brand:
        caption_lines.append(f"🏷️ Marca: {brand}")
    if aromas:
        caption_lines.append(f"🌿 Aromas: {aromas}")
    if price:
        caption_lines.append(f"💰 Precio: ${price}")
    if short_description:
        caption_lines.append(f"\n{short_description}")
    if permalink:
        caption_lines.append(f"\n🛒 Ver producto: {permalink}")
    if real_image:
        caption_lines.append(f"📸 Ver foto real: {real_image}")

    caption = (custom_caption or "").strip() or "\n".join(caption_lines)

    # Guardar en DB (OUT) + luego enviar por WhatsApp (imagen real)
    with engine.begin() as conn:
        local_id = save_message(
            conn,
            phone=phone,
            direction="out",
            msg_type="product",
            text_msg=caption,
            featured_image=featured_image,
            real_image=real_image or None,
            permalink=permalink,
        )

    wa_resp = await send_whatsapp_media_id(
        to_phone=phone,
        media_type="image",
        media_id=media_id,
        caption=caption
    )

    wa_message_id = wa_resp.get("wa_message_id") if isinstance(wa_resp, dict) else None
    with engine.begin() as conn:
        if isinstance(wa_resp, dict) and wa_resp.get("sent") is True and wa_message_id:
            set_wa_send_result(conn, local_id, wa_message_id, True, "")
        else:
            err = (wa_resp.get("whatsapp_body") if isinstance(wa_resp, dict) else "") or (wa_resp.get("reason") if isinstance(wa_resp, dict) else "") or "WhatsApp send failed"
            set_wa_send_result(conn, local_id, None, False, str(err)[:900])

    return wa_resp if isinstance(wa_resp, dict) else {"sent": False, "reason": "invalid wa_resp"}


@app.post("/api/wc/send-product")
async def send_wc_product(payload: dict):
    phone = payload.get("phone")
    product_id = payload.get("product_id")
    custom_caption = payload.get("caption", "")

    if not phone or not product_id:
        raise HTTPException(status_code=400, detail="phone and product_id required")

    wa = await _wc_send_product_internal(
        phone=str(phone),
        product_id=int(product_id),
        custom_caption=str(custom_caption or "")
    )
    return {"ok": True, "sent": bool(wa.get("sent")), "wa": wa}


# =========================================================
# ENDPOINTS
# =========================================================

@app.get("/api/health")
def health():
    return {"ok": True, "build": "2026-02-16-wc-assistant-1"}


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

    # ✅ Audio webm -> ogg/opus
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

    from app.routes.whatsapp import upload_whatsapp_media
    media_id = await upload_whatsapp_media(content, mime)

    return {"ok": True, "media_id": media_id, "mime_type": mime, "filename": filename, "kind": kind}


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
        if unread == "yes":
            extra = f" AND {unread_cond} "
        else:
            extra = f" AND NOT ({unread_cond}) "

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
            SELECT
                id, phone, direction, msg_type, text,
                media_url, media_caption, media_id, mime_type, file_name, file_size, duration_sec,
                featured_image, real_image, permalink, created_at,
                wa_message_id, wa_status, wa_error, wa_ts_sent, wa_ts_delivered, wa_ts_read
            FROM messages
            WHERE phone = :phone
            ORDER BY created_at ASC
            LIMIT 500
        """), {"phone": phone}).mappings().all()
    return {"messages": [dict(r) for r in rows]}


@app.post("/api/messages/ingest")
async def ingest(msg: IngestMessage):
    direction = msg.direction if msg.direction in ("in", "out") else "in"
    msg_type = (msg.msg_type or "text").strip().lower()

    # 1) Guardar en DB
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO conversations (phone, takeover, updated_at)
                VALUES (:phone, FALSE, :updated_at)
                ON CONFLICT (phone) DO UPDATE SET updated_at = EXCLUDED.updated_at
            """), {"phone": msg.phone, "updated_at": datetime.utcnow()})

            local_id = save_message(
                conn,
                phone=msg.phone,
                direction=direction,
                msg_type=msg_type,
                text_msg=msg.text or "",
                media_url=msg.media_url,
                media_caption=msg.media_caption,
                media_id=msg.media_id,
                mime_type=msg.mime_type,
                file_name=msg.file_name,
                file_size=msg.file_size,
                duration_sec=msg.duration_sec,
                featured_image=msg.featured_image,
                real_image=msg.real_image,
                permalink=msg.permalink,
            )
    except Exception as e:
        return {"saved": False, "sent": False, "stage": "db", "error": str(e)}

    # 2) Enviar a WhatsApp si es OUT + guardar wa_message_id
    if direction == "out":
        try:
            wa_resp = None

            if msg_type in ("image", "video", "audio", "document"):
                if not msg.media_id:
                    with engine.begin() as conn:
                        set_wa_send_result(conn, local_id, None, False, "media_id is required")
                    return {"saved": True, "sent": False, "reason": "media_id is required for media messages"}

                wa_resp = await send_whatsapp_media_id(
                    to_phone=msg.phone,
                    media_type=msg_type,
                    media_id=msg.media_id,
                    caption=msg.media_caption or msg.text or ""
                )

            elif msg_type == "product":
                body = (msg.text or "").strip()
                extra_lines = []
                if msg.permalink:
                    extra_lines.append(f"🛒 Ver producto: {msg.permalink}")
                if msg.real_image:
                    extra_lines.append(f"📸 Ver foto real: {msg.real_image}")
                if extra_lines:
                    body = (body + "\n\n" + "\n".join(extra_lines)).strip()

                wa_resp = await send_whatsapp_text(msg.phone, body)

            else:
                wa_resp = await send_whatsapp_text(msg.phone, msg.text or "")

            wa_message_id = None
            if isinstance(wa_resp, dict) and wa_resp.get("sent") is True:
                wa_message_id = wa_resp.get("wa_message_id")

            with engine.begin() as conn:
                if isinstance(wa_resp, dict) and wa_resp.get("sent") is True and wa_message_id:
                    set_wa_send_result(conn, local_id, wa_message_id, True, "")
                else:
                    err = (wa_resp.get("whatsapp_body") if isinstance(wa_resp, dict) else "") or (wa_resp.get("reason") if isinstance(wa_resp, dict) else "") or (wa_resp.get("error") if isinstance(wa_resp, dict) else "") or "WhatsApp send failed"
                    set_wa_send_result(conn, local_id, None, False, str(err)[:900])

            return {"saved": True, "sent": bool(isinstance(wa_resp, dict) and wa_resp.get("sent")), "wa": wa_resp}

        except Exception as e:
            with engine.begin() as conn:
                set_wa_send_result(conn, local_id, None, False, str(e)[:900])
            return {"saved": True, "sent": False, "stage": "whatsapp", "error": str(e)}

    # 3) Disparar IA si es IN, IA habilitada, y takeover está OFF (bot mode)
    if direction == "in":
        try:
            with engine.begin() as conn:
                c = conn.execute(text("""
                    SELECT takeover
                    FROM conversations
                    WHERE phone = :phone
                """), {"phone": msg.phone}).mappings().first()

                s = conn.execute(text("""
                    SELECT is_enabled
                    FROM ai_settings
                    ORDER BY id ASC
                    LIMIT 1
                """)).mappings().first()

            takeover_on = bool(c and c.get("takeover") is True)
            ai_enabled = bool(s and s.get("is_enabled") is True)

            if (not ai_enabled) or takeover_on:
                return {"saved": True, "sent": False, "ai": False, "reason": "ai_disabled_or_takeover_on"}

            user_text = (msg.text or "").strip()

            print("DEBUG WC CHECK:", _wc_enabled(), msg_type, user_text)


            # =========================================================
            # ✅ WooCommerce assistant (solo texto IN)
            # =========================================================
            if _wc_enabled() and msg_type == "text" and user_text:
                try:
                    # 1) si venimos esperando que el cliente elija variante
                    st = _get_ai_state(msg.phone)
                    if st.startswith("wc_await:"):
                        try:
                            payload = json.loads(st[len("wc_await:"):].strip() or "{}")
                        except Exception:
                            payload = {}

                        options = payload.get("options") or []
                        if isinstance(options, list) and options:
                            # elección por número
                            n = _parse_choice_number(user_text)
                            chosen = None
                            if n is not None and 1 <= n <= len(options):
                                chosen = options[n - 1]
                            else:
                                # elección por texto
                                ut = _norm(user_text)
                                best = None
                                best_score = 0
                                for opt in options:
                                    name = str((opt or {}).get("name") or "")
                                    sc = _score_product_match(ut, name)
                                    if sc > best_score:
                                        best_score = sc
                                        best = opt
                                if best and best_score >= 30:
                                    chosen = best

                            if chosen and chosen.get("id"):
                                _clear_ai_state(msg.phone)
                                wa = await _wc_send_product_internal(
                                    phone=msg.phone,
                                    product_id=int(chosen.get("id")),
                                    custom_caption=""
                                )
                                return {"saved": True, "sent": bool(wa.get("sent")), "ai": False, "wc": True, "reason": "choice_send", "wa": wa}

                            # si no entendimos, repreguntamos
                            txt = "¿Cuál opción deseas? Responde con el número (1, 2, 3...) o el nombre exacto 🙂"
                            await _send_ai_reply_in_chunks(msg.phone, txt)
                            return {"saved": True, "sent": True, "ai": False, "wc": True, "reason": "awaiting_choice"}

                    # 2) detectar pregunta de producto
                    if _looks_like_product_question(user_text):
                        items = _wc_search_products(user_text, per_page=8)

                        if items:
                            # score
                            scored = []
                            for it in items:
                                sc = _score_product_match(user_text, it.get("name") or "")
                                scored.append((sc, it))
                            scored.sort(key=lambda x: x[0], reverse=True)

                            best_score, best_item = scored[0]
                            strong = best_score >= 65
                            second_score = scored[1][0] if len(scored) > 1 else 0

                            if strong and (best_score - second_score >= 15):
                                wa = await _wc_send_product_internal(
                                    phone=msg.phone,
                                    product_id=int(best_item.get("id")),
                                    custom_caption=""
                                )
                                return {"saved": True, "sent": bool(wa.get("sent")), "ai": False, "wc": True, "reason": "strong_match_send", "wa": wa}

                            # si hay varias variantes, preguntamos cuál
                            top = [x[1] for x in scored[:5]]
                            lines = ["Encontré estas opciones: 👇"]
                            opts = []
                            for i, it in enumerate(top, start=1):
                                name = str(it.get("name") or "")
                                price = str(it.get("price") or "")
                                stock = str(it.get("stock_status") or "")
                                stock_label = "✅ disponible" if stock == "instock" else "⛔ agotado"
                                price_label = f" — ${price}" if price else ""
                                lines.append(f"{i}) {name}{price_label} ({stock_label})")
                                opts.append({"id": it.get("id"), "name": name})

                            lines.append("")
                            lines.append("¿Cuál deseas? Responde con el número (1,2,3...) o el nombre exacto.")
                            msg_out = "\n".join(lines).strip()

                            _set_ai_state(msg.phone, "wc_await:" + json.dumps({"options": opts}, ensure_ascii=False))
                            await _send_ai_reply_in_chunks(msg.phone, msg_out)

                            return {"saved": True, "sent": True, "ai": False, "wc": True, "reason": "multiple_options"}

                except HTTPException:
                    # Si WooCommerce falla, NO se cae el chat: seguimos al flujo IA normal
                    pass
                except Exception:
                    pass
                
                print("DEBUG WC TRIGGERED")


            # =========================================================
            # ✅ Flujo IA normal (si no aplicó WC)
            # =========================================================
            meta = build_ai_meta(msg.phone, msg.text or "")

            ai_result = await process_message(
                phone=msg.phone,
                text=(msg.text or ""),
                meta=meta,
            )

            reply_text = (ai_result.get("reply_text") or "").strip()
            if not reply_text:
                return {"saved": True, "sent": False, "ai": True, "reply": ""}

            send_result = await _send_ai_reply_in_chunks(msg.phone, reply_text)

            return {
                "saved": True,
                "sent": bool(send_result.get("sent")),
                "ai": True,
                "reply": reply_text,
                "ai_meta": True,
                "humanized": True,
                "chunks": {
                    "count": int(send_result.get("chunks_sent") or 0),
                    "local_message_ids": send_result.get("local_message_ids") or [],
                    "wa_message_ids": send_result.get("wa_message_ids") or [],
                    "settings_used": send_result.get("settings_used") or {},
                },
                "wa_last": send_result.get("last_wa") or {},
            }

        except Exception as e:
            return {"saved": True, "sent": False, "ai": False, "ai_error": str(e)[:900]}

    return {"saved": True, "sent": False}


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
