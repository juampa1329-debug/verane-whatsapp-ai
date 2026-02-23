# app/pipeline/reply_sender.py

from __future__ import annotations

import os
import re
import json
import asyncio
from datetime import datetime
from typing import Optional, List

from sqlalchemy import text

from app.db import engine

# WhatsApp sender
from app.routes.whatsapp import (
    send_whatsapp_text,
    send_whatsapp_media_id,
    upload_whatsapp_media,
)

# TTS
from app.ai.tts import tts_synthesize


# -------------------------
# Internal helpers: safe conversation updates
# -------------------------

def _safe_set_last_product_in_conversation(phone: str, product_id: int, featured_image: str = "", real_image: str = "", permalink: str = "") -> None:
    """
    Guarda el último producto enviado por conversación.
    Intentamos varias columnas posibles sin romper si no existen.

    Esto sirve para el caso: "sí envíame la foto" -> enviar tarjeta del último producto.
    """
    phone = (phone or "").strip()
    if not phone or not product_id:
        return

    payload = {
        "last_product_id": int(product_id),
        "last_product_featured_image": (featured_image or "")[:500],
        "last_product_real_image": (real_image or "")[:500],
        "last_product_permalink": (permalink or "")[:500],
        "ts": datetime.utcnow().isoformat(),
    }

    # Intento 1: columna dedicada last_product_id
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE conversations
                SET last_product_id = :pid,
                    updated_at = COALESCE(updated_at, NOW())
                WHERE phone = :phone
            """), {"phone": phone, "pid": int(product_id)})
        return
    except Exception:
        pass

    # Intento 2: guardar en crm_meta JSONB (si existe)
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE conversations
                SET crm_meta = COALESCE(crm_meta, '{}'::jsonb) || CAST(:m AS jsonb),
                    updated_at = COALESCE(updated_at, NOW())
                WHERE phone = :phone
            """), {"phone": phone, "m": json.dumps(payload, ensure_ascii=False)})
        return
    except Exception:
        pass

    # Intento 3: guardar en crm_slots JSONB (si existe)
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE conversations
                SET crm_slots = COALESCE(crm_slots, '{}'::jsonb) || CAST(:m AS jsonb),
                    updated_at = COALESCE(updated_at, NOW())
                WHERE phone = :phone
            """), {"phone": phone, "m": json.dumps(payload, ensure_ascii=False)})
        return
    except Exception:
        pass

    # Si no existe ninguna, no hacemos nada (silencioso).
    return


# -------------------------
# DB helpers
# -------------------------

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
    """
    Guarda un mensaje (IN/OUT) y SIEMPRE hace bump de conversations.updated_at
    Importante:
      - OUT se guarda como wa_status='queued' (no 'sent') hasta confirmar WhatsApp.
    """
    direction = (direction or "in").strip().lower()
    if direction not in ("in", "out"):
        direction = "in"

    msg_type = (msg_type or "text").strip().lower()
    now = datetime.utcnow()

    initial_wa_status = None
    initial_wa_ts_sent = None
    if direction == "out":
        # NO marcar como sent todavía
        initial_wa_status = "queued"
        initial_wa_ts_sent = None

    r = conn.execute(
        text("""
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
        """),
        {
            "phone": phone,
            "direction": direction,
            "msg_type": msg_type,
            "text": text_msg or "",
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
            "created_at": now,
            "wa_status": initial_wa_status,
            "wa_ts_sent": initial_wa_ts_sent,
        },
    )

    message_id = int(r.scalar())

    # Bump updated_at SIEMPRE que entra o sale un mensaje
    conn.execute(
        text("""
            INSERT INTO conversations (phone, updated_at)
            VALUES (:phone, :updated_at)
            ON CONFLICT (phone) DO UPDATE SET updated_at = EXCLUDED.updated_at
        """),
        {"phone": phone, "updated_at": now},
    )

    return message_id


def set_wa_send_result(
    conn,
    local_message_id: int,
    wa_message_id: Optional[str],
    sent_ok: bool,
    wa_error: str = "",
):
    """
    Ajusta estado de WhatsApp para un mensaje OUT.
    """
    if not sent_ok or not wa_message_id:
        conn.execute(
            text("""
                UPDATE messages
                SET wa_status = 'failed',
                    wa_error  = :wa_error
                WHERE id = :id
            """),
            {"id": int(local_message_id), "wa_error": (wa_error or "WhatsApp send failed")[:900]},
        )
        return

    conn.execute(
        text("""
            UPDATE messages
            SET wa_message_id = :wa_message_id,
                wa_status     = 'sent',
                wa_error      = NULL,
                wa_ts_sent    = COALESCE(wa_ts_sent, NOW())
            WHERE id = :id
        """),
        {"id": int(local_message_id), "wa_message_id": str(wa_message_id)},
    )


def set_extracted_text(conn, message_id: int, extracted_text: str, ai_meta: Optional[dict] = None) -> None:
    """
    Guarda extracted_text y (opcionalmente) ai_meta como JSONB.
    """
    try:
        conn.execute(
            text("""
                UPDATE messages
                SET extracted_text = :t,
                    ai_meta = CASE
                        WHEN :m IS NULL THEN ai_meta
                        ELSE COALESCE(CAST(:m AS JSONB), ai_meta)
                    END
                WHERE id = :id
            """),
            {
                "id": int(message_id),
                "t": (extracted_text or ""),
                "m": json.dumps(ai_meta or {}, ensure_ascii=False) if ai_meta is not None else None,
            },
        )
    except Exception:
        return


# -------------------------
# Settings helpers
# -------------------------

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


# -------------------------
# Text chunking
# -------------------------

def _normalize_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\r\n", "\n", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return s.strip()


def _split_long_text(text_msg: str, max_chars: int) -> List[str]:
    text_msg = _normalize_text(text_msg)
    if not text_msg:
        return [""]

    if max_chars <= 0:
        return [text_msg]

    paras = [p.strip() for p in text_msg.split("\n\n") if p.strip()]
    out: List[str] = []
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


# -------------------------
# Public: send AI reply as text chunks
# -------------------------

async def send_ai_reply_in_chunks(phone: str, full_text: str) -> dict:
    s = _get_ai_send_settings()
    max_chars = int(s.get("reply_chunk_chars") or 480)
    reply_delay = int(s.get("reply_delay_ms") or 900) / 1000.0
    typing_delay = int(s.get("typing_delay_ms") or 450) / 1000.0

    chunks = _split_long_text(full_text or "", max_chars=max_chars) or [""]

    if typing_delay > 0:
        await asyncio.sleep(typing_delay)

    sent_any = False
    wa_ids: List[str] = []
    local_ids: List[int] = []
    last_wa_resp: dict = {"sent": False, "reason": "no chunks"}

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

        try:
            wa_resp = await send_whatsapp_text(phone, chunk)
        except Exception as e:
            wa_resp = {"sent": False, "error": str(e)[:900], "reason": "send_exception"}

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


# -------------------------
# Public: send AI reply as voice notes (TTS)
# -------------------------

async def send_ai_reply_as_voice(phone: str, text_to_say: str) -> dict:
    text_to_say = (text_to_say or "").strip()
    if not text_to_say:
        return {"sent": False, "reason": "empty text"}

    tts_cfg = _get_tts_provider_settings()
    tts_provider = (tts_cfg.get("voice_tts_provider") or "google").strip().lower()
    tts_voice_id = (tts_cfg.get("voice_tts_voice_id") or "").strip()
    tts_model_id = (tts_cfg.get("voice_tts_model_id") or "").strip()

    if tts_provider == "elevenlabs" and not tts_voice_id:
        tts_voice_id = (os.getenv("ELEVENLABS_VOICE_ID", "") or "").strip()
    if tts_provider == "elevenlabs" and not tts_model_id:
        tts_model_id = (os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2") or "eleven_multilingual_v2").strip()

    voice_settings = _get_voice_settings()
    max_notes = int(voice_settings.get("voice_max_notes_per_reply", 1))

    chunks = [text_to_say]
    if max_notes > 1 and "\n\n" in text_to_say:
        chunks = [p.strip() for p in text_to_say.split("\n\n") if p.strip()][:max_notes]
    elif len(text_to_say) > 600 and max_notes > 1:
        chunks = _split_long_text(text_to_say, 600)[:max_notes]

    sent_any = False
    last_wa_resp: dict = {}
    media_ids: List[str] = []

    for idx, chunk in enumerate(chunks):
        tts_kwargs = {"text": chunk, "provider": tts_provider}
        if tts_voice_id:
            tts_kwargs["voice_id"] = tts_voice_id
        if tts_model_id:
            tts_kwargs["model_id"] = tts_model_id

        try:
            try:
                audio_bytes, mime, filename, meta = await tts_synthesize(**tts_kwargs)
            except TypeError:
                audio_bytes, mime, filename, meta = await tts_synthesize(text=chunk, provider=tts_provider)
        except Exception as e:
            last_wa_resp = {"sent": False, "reason": "tts_exception", "error": str(e)[:900]}
            continue

        if (not audio_bytes) or (not isinstance(meta, dict)) or (meta.get("ok") is not True):
            last_wa_resp = {"sent": False, "reason": "tts_failed", "meta": meta or {}}
            continue

        try:
            media_id = await upload_whatsapp_media(audio_bytes, mime)
        except Exception as e:
            last_wa_resp = {"sent": False, "reason": "upload_exception", "error": str(e)[:900]}
            continue

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

        try:
            wa_resp = await send_whatsapp_media_id(
                to_phone=phone,
                media_type="audio",
                media_id=media_id,
                caption=""
            )
        except Exception as e:
            wa_resp = {"sent": False, "reason": "send_exception", "error": str(e)[:900]}

        last_wa_resp = wa_resp if isinstance(wa_resp, dict) else {"sent": False, "reason": "invalid wa_resp"}
        wa_message_id = last_wa_resp.get("wa_message_id") if isinstance(last_wa_resp, dict) else None

        with engine.begin() as conn:
            if isinstance(last_wa_resp, dict) and last_wa_resp.get("sent") is True and wa_message_id:
                set_wa_send_result(conn, local_out_id, wa_message_id, True, "")
                sent_any = True
            else:
                err = (last_wa_resp.get("whatsapp_body") if isinstance(last_wa_resp, dict) else "") \
                      or (last_wa_resp.get("reason") if isinstance(last_wa_resp, dict) else "") \
                      or (last_wa_resp.get("error") if isinstance(last_wa_resp, dict) else "") \
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


# -------------------------
# Public: helper for other modules
# -------------------------

def remember_last_product_sent(phone: str, product_id: int, featured_image: str = "", real_image: str = "", permalink: str = "") -> None:
    """
    Llamar esto cuando se envía una tarjeta/producto.
    No rompe si tu DB no tiene columnas: hace best-effort.
    """
    _safe_set_last_product_in_conversation(phone, product_id, featured_image, real_image, permalink)