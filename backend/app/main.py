import os
import re
import json
import asyncio
from datetime import datetime
from typing import Optional, List, Tuple

import httpx
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import text
from starlette.requests import Request as StarletteRequest

# ✅ Router externo WhatsApp
from app.routes.whatsapp import (
    router as whatsapp_router,
    send_whatsapp_text,
    send_whatsapp_media_id,
    upload_whatsapp_media,
)

# ✅ IA
from app.ai.engine import process_message
from app.ai.context_builder import build_ai_meta

# ✅ TTS
from app.ai.tts import tts_synthesize

# ✅ Multimodal robusto (audio->wav16k->gemini, images/docs->gemini)
from app.ai.multimodal import extract_text_from_media, is_effectively_empty_text

# ✅ Montar router IA
try:
    from app.ai.router import router as ai_router
except Exception:
    ai_router = None

# ✅ Woo
from app.ai.wc_assistant import handle_wc_if_applicable
from app.integrations.woocommerce import (
    wc_enabled,
    wc_get,
    map_product_for_ui,
    build_caption,
    download_image_bytes,
    ensure_whatsapp_image_compat,
    wc_fetch_product,
    WC_BASE_URL,
    WC_CONSUMER_KEY,
    WC_CONSUMER_SECRET,
)

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

from app.db import engine  # noqa: E402

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

        # Extracción de datos
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS extracted_text TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS ai_meta JSONB"""))

        # Control de tráfico
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_messages_phone_created_at ON messages (phone, created_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_messages_phone_direction_created_at ON messages (phone, direction, created_at)"""))
        conn.execute(text("""CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations (updated_at)"""))

        # Media extra
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS media_id TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS mime_type TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS file_name TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS file_size INTEGER"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS duration_sec INTEGER"""))

        # Estados WhatsApp (checkmarks)
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_message_id TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_status TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_error TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_ts_sent TIMESTAMP"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_ts_delivered TIMESTAMP"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_ts_read TIMESTAMP"""))

        # Unread tracking
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_read_at TIMESTAMP"""))

        # Estado IA estructural
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS ai_state TEXT"""))

        # Tabla settings IA
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

        # VOICE settings
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS voice_enabled BOOLEAN"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS voice_gender TEXT"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS voice_language TEXT"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS voice_accent TEXT"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS voice_style_prompt TEXT"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS voice_max_notes_per_reply INTEGER"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS voice_prefer_voice BOOLEAN"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS voice_speaking_rate DOUBLE PRECISION"""))

        # TTS provider selector
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS voice_tts_provider TEXT"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS voice_tts_voice_id TEXT"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS voice_tts_model_id TEXT"""))

        # Asegurar defaults si quedaron NULL
        conn.execute(text("""
            UPDATE ai_settings
                SET
                voice_enabled = COALESCE(voice_enabled, FALSE),
                voice_gender = COALESCE(NULLIF(TRIM(voice_gender), ''), 'neutral'),
                voice_language = COALESCE(NULLIF(TRIM(voice_language), ''), 'es-CO'),
                voice_accent = COALESCE(NULLIF(TRIM(voice_accent), ''), 'colombiano'),
                voice_style_prompt = COALESCE(voice_style_prompt, ''),
                voice_max_notes_per_reply = COALESCE(voice_max_notes_per_reply, 1),
                voice_prefer_voice = COALESCE(voice_prefer_voice, FALSE),
                voice_speaking_rate = COALESCE(voice_speaking_rate, 1.0),

                voice_tts_provider = COALESCE(NULLIF(TRIM(voice_tts_provider), ''), 'google'),
                voice_tts_voice_id = COALESCE(NULLIF(TRIM(voice_tts_voice_id), ''), ''),
                voice_tts_model_id = COALESCE(NULLIF(TRIM(voice_tts_model_id), ''), '')
                WHERE id = (SELECT id FROM ai_settings ORDER BY id ASC LIMIT 1)
        """))

        # settings humanización
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS reply_chunk_chars INTEGER"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS reply_delay_ms INTEGER"""))
        conn.execute(text("""ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS typing_delay_ms INTEGER"""))

        # Woo recovery cache
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS wc_last_options JSONB"""))
        conn.execute(text("""ALTER TABLE conversations ADD COLUMN IF NOT EXISTS wc_last_options_at TIMESTAMP"""))

        # Insertar 1 fila default si la tabla está vacía
        conn.execute(text("""
            INSERT INTO ai_settings (
                is_enabled, provider, model, system_prompt,
                max_tokens, temperature,
                fallback_provider, fallback_model,
                timeout_sec, max_retries,
                reply_chunk_chars, reply_delay_ms, typing_delay_ms,
                voice_tts_provider, voice_tts_voice_id, voice_tts_model_id
            )
            SELECT
                TRUE, 'google', 'gemma-3.4b-it', '',
                512, 0.7,
                'groq', 'llama-3.1-8b-instant',
                25, 1,
                480, 900, 450,
                'google', '', ''
            WHERE NOT EXISTS (SELECT 1 FROM ai_settings)
        """))

        # Asegurar defaults humanización
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
    msg_type: str = "text"
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


def _new_trace_id() -> str:
    try:
        import uuid
        return uuid.uuid4().hex[:10]
    except Exception:
        return str(int(datetime.utcnow().timestamp()))


def _log(trace_id: str, event: str, **kv):
    try:
        payload = {"trace": trace_id, "event": event, **kv}
        print("[INGEST]", json.dumps(payload, ensure_ascii=False))
    except Exception:
        print("[INGEST]", trace_id, event, kv)


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
        "wa_status": "sent" if direction == "out" else None,
        "wa_ts_sent": datetime.utcnow() if direction == "out" else None,
    })

    message_id = int(r.scalar())

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


def set_extracted_text(conn, message_id: int, extracted_text: str, ai_meta: Optional[dict] = None) -> None:
    try:
        conn.execute(text("""
            UPDATE messages
            SET extracted_text = :t,
                ai_meta = COALESCE(:m::jsonb, ai_meta)
            WHERE id = :id
        """), {
            "id": int(message_id),
            "t": (extracted_text or ""),
            "m": json.dumps(ai_meta or {}, ensure_ascii=False) if ai_meta is not None else None
        })
    except Exception:
        return


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
    s = _get_ai_send_settings()
    max_chars = int(s.get("reply_chunk_chars") or 480)
    reply_delay = int(s.get("reply_delay_ms") or 900) / 1000.0
    typing_delay = int(s.get("typing_delay_ms") or 450) / 1000.0

    chunks = _split_long_text(full_text or "", max_chars=max_chars) or [""]
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


def _get_voice_settings() -> dict:
    defaults = {
        "voice_enabled": False,
        "voice_prefer_voice": False,
        "voice_max_notes_per_reply": 1,
    }
    try:
        with engine.begin() as conn:
            r = conn.execute(text("""
                SELECT
                    COALESCE(voice_enabled, FALSE) AS voice_enabled,
                    COALESCE(voice_prefer_voice, FALSE) AS voice_prefer_voice,
                    COALESCE(voice_max_notes_per_reply, 1) AS voice_max_notes_per_reply
                FROM ai_settings
                ORDER BY id ASC
                LIMIT 1
            """)).mappings().first()

        if not r:
            return defaults

        d = dict(r)
        d["voice_enabled"] = bool(d.get("voice_enabled"))
        d["voice_prefer_voice"] = bool(d.get("voice_prefer_voice"))
        try:
            d["voice_max_notes_per_reply"] = int(d.get("voice_max_notes_per_reply") or 1)
        except Exception:
            d["voice_max_notes_per_reply"] = 1
        return d
    except Exception:
        return defaults


def _norm_tts_provider(p: str) -> str:
    raw = (p or "").strip().lower()
    raw = raw.replace("_", "").replace("-", "").replace(" ", "")
    if raw in ("", "default", "auto"):
        return "google"
    if raw in ("elevenlabs", "11labs", "eleven", "xi"):
        return "elevenlabs"
    if raw in ("google", "gcp", "googletts", "cloudtts", "texttospeech"):
        return "google"
    if raw in ("piper", "pipertts"):
        return "piper"
    return raw


def _get_tts_provider_settings() -> dict:
    defaults = {
        "voice_tts_provider": "google",
        "voice_tts_voice_id": "",
        "voice_tts_model_id": "",
    }
    try:
        with engine.begin() as conn:
            r = conn.execute(text("""
                SELECT
                    COALESCE(NULLIF(TRIM(voice_tts_provider), ''), 'google') AS voice_tts_provider,
                    COALESCE(NULLIF(TRIM(voice_tts_voice_id), ''), '') AS voice_tts_voice_id,
                    COALESCE(NULLIF(TRIM(voice_tts_model_id), ''), '') AS voice_tts_model_id
                FROM ai_settings
                ORDER BY id ASC
                LIMIT 1
            """)).mappings().first()

        if not r:
            return defaults

        d = dict(r)
        d["voice_tts_provider"] = _norm_tts_provider(d.get("voice_tts_provider") or "google")
        d["voice_tts_voice_id"] = (d.get("voice_tts_voice_id") or "").strip()
        d["voice_tts_model_id"] = (d.get("voice_tts_model_id") or "").strip()
        return d
    except Exception:
        return defaults


async def _send_ai_reply_as_voice(phone: str, text_to_say: str) -> dict:
    text_to_say = (text_to_say or "").strip()
    if not text_to_say:
        return {"sent": False, "reason": "empty text"}

    tts_cfg = _get_tts_provider_settings()
    tts_provider = (tts_cfg.get("voice_tts_provider") or "google").strip().lower()
    tts_voice_id = (tts_cfg.get("voice_tts_voice_id") or "").strip()
    tts_model_id = (tts_cfg.get("voice_tts_model_id") or "").strip()

    _log(_new_trace_id(), "TTS_PROVIDER_SELECTED", provider=tts_provider, voice_id=tts_voice_id, model_id=tts_model_id)

    # Fallback ENV para ElevenLabs si en DB está vacío
    if tts_provider == "elevenlabs" and not tts_voice_id:
        tts_voice_id = (os.getenv("ELEVENLABS_VOICE_ID", "") or "").strip()
    if tts_provider == "elevenlabs" and not tts_model_id:
        tts_model_id = (os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2") or "eleven_multilingual_v2").strip()

    voice_settings = _get_voice_settings()
    max_notes = int(voice_settings.get("voice_max_notes_per_reply", 1))

    # Chunking para voz
    chunks = [text_to_say]
    if max_notes > 1 and "\n\n" in text_to_say:
        chunks = [p.strip() for p in text_to_say.split("\n\n") if p.strip()][:max_notes]
    elif len(text_to_say) > 600 and max_notes > 1:
        chunks = _split_long_text(text_to_say, 600)[:max_notes]

    sent_any = False
    last_wa_resp = {}
    media_ids = []

    for idx, chunk in enumerate(chunks):
        _log(_new_trace_id(), "TTS_GENERATING", provider=tts_provider, chunk=idx + 1, total=len(chunks))

        tts_kwargs = {"text": chunk, "provider": tts_provider}
        if tts_voice_id:
            tts_kwargs["voice_id"] = tts_voice_id
        if tts_model_id:
            tts_kwargs["model_id"] = tts_model_id

        try:
            audio_bytes, mime, filename, meta = await tts_synthesize(**tts_kwargs)
        except TypeError:
            audio_bytes, mime, filename, meta = await tts_synthesize(text=chunk, provider=tts_provider)

        if (not audio_bytes) or (not isinstance(meta, dict)) or (meta.get("ok") is not True):
            continue

        media_id = await upload_whatsapp_media(audio_bytes, mime)
        media_ids.append(media_id)

        with engine.begin() as conn:
            local_out_id = save_message(
                conn,
                phone=phone,
                direction="out",
                msg_type="audio",
                text_msg="",
                media_id=media_id,
                mime_type=mime,
                file_name=filename,
                file_size=len(audio_bytes),
                duration_sec=None,
            )

        wa_resp = await send_whatsapp_media_id(
            to_phone=phone,
            media_type="audio",
            media_id=media_id,
            caption=""
        )

        last_wa_resp = wa_resp
        wa_message_id = wa_resp.get("wa_message_id") if isinstance(wa_resp, dict) else None

        with engine.begin() as conn:
            if isinstance(wa_resp, dict) and wa_resp.get("sent") is True and wa_message_id:
                set_wa_send_result(conn, local_out_id, wa_message_id, True, "")
                sent_any = True
            else:
                err = (wa_resp.get("whatsapp_body") if isinstance(wa_resp, dict) else "") \
                      or (wa_resp.get("reason") if isinstance(wa_resp, dict) else "") \
                      or (wa_resp.get("error") if isinstance(wa_resp, dict) else "") \
                      or "WhatsApp send failed"
                set_wa_send_result(conn, local_out_id, None, False, str(err)[:900])

        if idx < len(chunks) - 1:
            await asyncio.sleep(1.5)

    return {
        "sent": sent_any,
        "wa": last_wa_resp,
        "media_ids": media_ids,
        "tts_provider": tts_provider,
        "tts_voice_id": tts_voice_id,
        "tts_model_id": tts_model_id,
    }


# =========================================================
# WhatsApp media download (Graph API)
# =========================================================

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_GRAPH_VERSION = os.getenv("WHATSAPP_GRAPH_VERSION", "v20.0")


async def download_whatsapp_media_bytes(media_id: str) -> Tuple[bytes, str]:
    if not WHATSAPP_TOKEN:
        raise RuntimeError("WHATSAPP_TOKEN not configured")
    if not media_id:
        raise RuntimeError("media_id is required")

    meta_url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    async with httpx.AsyncClient(timeout=25) as client:
        r_meta = await client.get(meta_url, headers=headers)
        if r_meta.status_code >= 400:
            raise RuntimeError(f"Graph meta failed: {r_meta.status_code} {r_meta.text[:400]}")

        meta = r_meta.json() or {}
        dl_url = meta.get("url")
        mime_type = (meta.get("mime_type") or "application/octet-stream").split(";")[0].strip().lower()

        if not dl_url:
            raise RuntimeError(f"No url in meta: {str(meta)[:200]}")

        r_bin = await client.get(dl_url, headers=headers)
        if r_bin.status_code >= 400:
            raise RuntimeError(f"Graph download failed: {r_bin.status_code} {r_bin.text[:400]}")

        return (bytes(r_bin.content), mime_type)


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


def _save_wc_options(phone: str, options: list[dict]) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO conversations (phone, wc_last_options, wc_last_options_at, updated_at)
                VALUES (:phone, :opts::jsonb, NOW(), :updated_at)
                ON CONFLICT (phone)
                DO UPDATE SET
                    wc_last_options = EXCLUDED.wc_last_options,
                    wc_last_options_at = EXCLUDED.wc_last_options_at,
                    updated_at = EXCLUDED.updated_at
            """), {
                "phone": phone,
                "opts": json.dumps(options, ensure_ascii=False),
                "updated_at": datetime.utcnow(),
            })
    except Exception:
        return


def _load_recent_wc_options(phone: str, max_age_sec: int = 180) -> list[dict]:
    try:
        with engine.begin() as conn:
            r = conn.execute(text("""
                SELECT wc_last_options, wc_last_options_at
                FROM conversations
                WHERE phone = :phone
                LIMIT 1
            """), {"phone": phone}).mappings().first()

        if not r:
            return []

        ts = r.get("wc_last_options_at")
        opts = r.get("wc_last_options")
        if not ts or not opts:
            return []

        now = datetime.utcnow()
        age = (now - ts).total_seconds()
        if age > float(max_age_sec):
            return []

        if isinstance(opts, list):
            return opts
        if isinstance(opts, dict) and isinstance(opts.get("options"), list):
            return opts["options"]
        return []
    except Exception:
        return []


def _clear_wc_options(phone: str) -> None:
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE conversations
                SET wc_last_options = NULL,
                    wc_last_options_at = NULL
                WHERE phone = :phone
            """), {"phone": phone})
    except Exception:
        return


# =========================================================
# WOOCOMMERCE ENDPOINTS
# =========================================================

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


async def _wc_send_product_internal(phone: str, product_id: int, custom_caption: str = "") -> dict:
    try:
        import pillow_avif  # noqa: F401
    except Exception:
        pass

    if not phone or not product_id:
        raise HTTPException(status_code=400, detail="phone and product_id required")

    if not (WC_BASE_URL and WC_CONSUMER_KEY and WC_CONSUMER_SECRET):
        raise HTTPException(status_code=500, detail="WC env vars not configured")

    product = await wc_fetch_product(int(product_id))

    images = product.get("images") or []
    if not images:
        raise HTTPException(status_code=400, detail="Product has no image")

    featured_image = (images[0] or {}).get("src") or ""
    real_image = (images[1] or {}).get("src") if len(images) > 1 else ""

    img_bytes, content_type = await download_image_bytes(featured_image)
    img_bytes, mime_type = ensure_whatsapp_image_compat(img_bytes, content_type, featured_image)

    media_id = await upload_whatsapp_media(img_bytes, mime_type)

    caption = build_caption(
        product=product,
        featured_image=featured_image,
        real_image=real_image,
        custom_caption=(custom_caption or "")
    )

    permalink = product.get("permalink", "") or ""

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
    return {"ok": True, "build": "2026-02-21-multimodal-ffmpeg-wav16k-1"}


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
            SELECT
                id, phone, direction, msg_type, text,
                media_url, media_caption, media_id, mime_type, file_name, file_size, duration_sec,
                featured_image, real_image, permalink, created_at,
                extracted_text, ai_meta,
                wa_message_id, wa_status, wa_error, wa_ts_sent, wa_ts_delivered, wa_ts_read
            FROM messages
            WHERE phone = :phone
            ORDER BY created_at ASC
            LIMIT 500
        """), {"phone": phone}).mappings().all()
    return {"messages": [dict(r) for r in rows]}


# =========================================================
# Ingest (core pipeline)
# =========================================================

@app.post("/api/messages/ingest")
async def ingest(msg: IngestMessage):
    trace_id = _new_trace_id()

    direction = msg.direction if msg.direction in ("in", "out") else "in"
    msg_type = (msg.msg_type or "text").strip().lower()
    user_text_original = (msg.text or "").strip()
    mime_in = (msg.mime_type or "").strip()
    media_id_in = (msg.media_id or "").strip()

    _log(
        trace_id,
        "ENTER_INGEST",
        phone=msg.phone,
        direction=direction,
        msg_type=msg_type,
        text_len=len(user_text_original),
        media_id=media_id_in,
        mime=mime_in,
    )

    # ✅ 1) CONTROL DE IDEMPOTENCIA (Previene el bucle de 3 repeticiones por Timeout de Meta Webhook)
    if direction == "in":
        try:
            with engine.begin() as conn:
                recent = conn.execute(text("""
                    SELECT id FROM messages
                    WHERE phone = :phone
                      AND direction = 'in'
                      AND msg_type = :msg_type
                      AND text = :text
                      AND COALESCE(media_id, '') = COALESCE(:media_id, '')
                      AND created_at > NOW() - INTERVAL '20 seconds'
                """), {
                    "phone": msg.phone,
                    "msg_type": msg_type,
                    "text": user_text_original,
                    "media_id": media_id_in
                }).first()

                if recent:
                    _log(trace_id, "IDEMPOTENCY_SKIP", reason="webhook_retry_ignored")
                    return {"saved": True, "sent": False, "reason": "idempotency_skip_duplicate"}
        except Exception:
            pass

    # 2) Guardar en DB
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
        _log(trace_id, "DB_SAVE_FAIL", error=str(e)[:300])
        return {"saved": False, "sent": False, "stage": "db", "error": str(e)}

    # 3) Enviar a WhatsApp si es OUT + guardar wa_message_id
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
                    err = (wa_resp.get("whatsapp_body") if isinstance(wa_resp, dict) else "") \
                          or (wa_resp.get("reason") if isinstance(wa_resp, dict) else "") \
                          or (wa_resp.get("error") if isinstance(wa_resp, dict) else "") \
                          or "WhatsApp send failed"
                    set_wa_send_result(conn, local_id, None, False, str(err)[:900])

            return {"saved": True, "sent": bool(isinstance(wa_resp, dict) and wa_resp.get("sent")), "wa": wa_resp}

        except Exception as e:
            with engine.begin() as conn:
                set_wa_send_result(conn, local_id, None, False, str(e)[:900])
            return {"saved": True, "sent": False, "stage": "whatsapp", "error": str(e)}

    # 4) Disparar IA/Woo si es IN, IA habilitada, y takeover está OFF
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
                _log(trace_id, "AI_SKIPPED", reason="ai_disabled_or_takeover_on", takeover=takeover_on, enabled=ai_enabled)
                return {"saved": True, "sent": False, "ai": False, "reason": "ai_disabled_or_takeover_on"}

            user_text = (msg.text or "").strip()
            if is_effectively_empty_text(user_text):
                user_text = ""

            # ✅ Multimodal robusto: extraer texto de audio/imagen/documento
            if (not user_text) and msg_type in ("audio", "image", "document") and msg.media_id:
                _log(trace_id, "ENTER_MULTIMODAL", media_id=msg.media_id, mime=mime_in)

                stage_meta: dict = {
                    "ok": False,
                    "trace_id": trace_id,
                    "msg_type": msg_type,
                    "media_id": msg.media_id,
                    "mime_in": mime_in,
                    "stages": {}
                }

                try:
                    media_bytes, real_mime = await download_whatsapp_media_bytes(msg.media_id)
                    stage_meta["stages"]["download"] = {
                        "ok": bool(media_bytes),
                        "mime": (real_mime or ""),
                        "bytes_len": int(len(media_bytes) if media_bytes else 0),
                    }

                    extracted = ""
                    if media_bytes:
                        extracted, mm_meta = await extract_text_from_media(
                            msg_type=msg_type,
                            media_bytes=media_bytes,
                            mime_type=(real_mime or msg.mime_type or "application/octet-stream"),
                        )
                        stage_meta["stages"]["multimodal"] = mm_meta
                        extracted = (extracted or "").strip()
                    else:
                        stage_meta["stages"]["multimodal"] = {"ok": False, "reason": "no_media_bytes"}

                    stage_meta["ok"] = bool(extracted)
                    stage_meta["extracted_len"] = int(len(extracted))

                    _log(trace_id, "AFTER_MULTIMODAL", ok=stage_meta["ok"], extracted_len=stage_meta["extracted_len"])

                    with engine.begin() as conn:
                        set_extracted_text(conn, local_id, extracted or "", ai_meta={"multimodal": stage_meta})

                    if extracted:
                        user_text = extracted

                except Exception as e:
                    stage_meta["stages"]["exception"] = {"ok": False, "error": str(e)[:900]}
                    _log(trace_id, "MULTIMODAL_EXCEPTION", error=str(e)[:300])
                    with engine.begin() as conn:
                        set_extracted_text(conn, local_id, "", ai_meta={"multimodal": stage_meta})
                    user_text = ""

            if is_effectively_empty_text(user_text):
                user_text = ""

            # Fallback si falla todo
            if not user_text:
                fallback_text = (
                    "📩 Recibí tu audio, imagen o documento, pero no pude interpretarlo bien.\n\n"
                    "¿Me lo puedes escribir en texto o reenviar el archivo? 🙏"
                )
                send_result = await _send_ai_reply_in_chunks(msg.phone, fallback_text)
                return {
                    "saved": True,
                    "sent": bool(send_result.get("sent")),
                    "ai": False,
                    "reason": "no_text_after_multimodal",
                    "fallback_replied": True,
                    "wa_last": send_result.get("last_wa") or {},
                }

            # Limpieza wc_await si venimos de media
            if msg_type != "text":
                st_now = _get_ai_state(msg.phone) or ""
                if st_now.startswith("wc_await:"):
                    _clear_ai_state(msg.phone)

            # =========================================================
            # WooCommerce assistant
            # =========================================================
            if wc_enabled() and user_text:
                async def _send_product_and_cleanup(phone: str, product_id: int, caption: str = "") -> dict:
                    wa = await _wc_send_product_internal(phone=phone, product_id=product_id, custom_caption=caption)
                    _clear_wc_options(phone)
                    return wa

                wc_result = await handle_wc_if_applicable(
                    phone=msg.phone,
                    user_text=user_text,
                    msg_type="text",  # lo procesamos como texto

                    get_state=_get_ai_state,
                    set_state=_set_ai_state,
                    clear_state=_clear_ai_state,

                    save_options_fn=_save_wc_options,
                    load_recent_options_fn=lambda p: _load_recent_wc_options(p, max_age_sec=180),

                    send_product_fn=_send_product_and_cleanup,
                    send_text_fn=lambda phone, text: _send_ai_reply_in_chunks(phone, text),
                )

                if wc_result.get("handled") is True:
                    return {
                        "saved": True,
                        "sent": True,
                        "ai": False,
                        **{k: v for k, v in wc_result.items() if k != "handled"}
                    }

            # =========================================================
            # Flujo IA normal (texto / chat)
            # =========================================================
            meta = build_ai_meta(msg.phone, user_text)

            ai_result = await process_message(
                phone=msg.phone,
                text=user_text,
                meta=meta,
            )

            reply_text = (ai_result.get("reply_text") or "").strip()
            if not reply_text:
                return {"saved": True, "sent": False, "ai": True, "reply": ""}

            voice = _get_voice_settings()

            if voice.get("voice_enabled") and voice.get("voice_prefer_voice"):
                send_result = await _send_ai_reply_as_voice(msg.phone, reply_text)
                return {
                    "saved": True,
                    "sent": bool(send_result.get("sent")),
                    "ai": True,
                    "reply": reply_text,
                    "voice": True,
                    "wa": send_result.get("wa") or {},
                }

            send_result = await _send_ai_reply_in_chunks(msg.phone, reply_text)

            return {
                "saved": True,
                "sent": bool(send_result.get("sent")),
                "ai": True,
                "reply": reply_text,
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
            _log(trace_id, "INGEST_EXCEPTION", error=str(e)[:300])
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