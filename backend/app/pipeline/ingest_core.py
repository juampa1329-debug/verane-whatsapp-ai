# app/pipeline/ingest_core.py

from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Optional, Tuple, Any, Dict

import httpx
from pydantic import BaseModel
from sqlalchemy import text

from app.db import engine

# WhatsApp / Graph helpers
from app.routes.whatsapp import (
    send_whatsapp_text,
    send_whatsapp_media_id,
    download_whatsapp_media_bytes,
)

# IA
from app.ai.engine import process_message
from app.ai.context_builder import build_ai_meta

# Multimodal
from app.ai.multimodal import extract_text_from_media, is_effectively_empty_text

# Woo
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
from app.routes.whatsapp import upload_whatsapp_media

# Sender helpers (text chunks + voice) + DB helpers
from app.pipeline.reply_sender import (
    save_message,
    set_wa_send_result,
    set_extracted_text,
    send_ai_reply_in_chunks,
    send_ai_reply_as_voice,
)

# CRM memory writer
from app.crm.crm_writer import ensure_conversation_row, apply_wc_slots_to_crm, update_crm_fields


# =========================================================
# Models
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


# =========================================================
# Logging helpers (simple)
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


# =========================================================
# Settings helpers (multimodal)
# =========================================================

def _get_multimodal_settings() -> dict:
    defaults = {
        "mm_enabled": True,
        "mm_provider": "google",
        "mm_model": "gemini-2.5-flash",
        "mm_timeout_sec": 75,
        "mm_max_retries": 2,
    }
    try:
        with engine.begin() as conn:
            r = conn.execute(text("""
                SELECT
                    COALESCE(mm_enabled, TRUE) AS mm_enabled,
                    COALESCE(NULLIF(TRIM(mm_provider), ''), 'google') AS mm_provider,
                    COALESCE(NULLIF(TRIM(mm_model), ''), 'gemini-2.5-flash') AS mm_model,
                    COALESCE(mm_timeout_sec, 75) AS mm_timeout_sec,
                    COALESCE(mm_max_retries, 2) AS mm_max_retries
                FROM ai_settings
                ORDER BY id ASC
                LIMIT 1
            """)).mappings().first()

        if not r:
            return defaults

        d = dict(r)
        d["mm_enabled"] = bool(d.get("mm_enabled"))
        d["mm_provider"] = (d.get("mm_provider") or "google").strip().lower()
        d["mm_model"] = (d.get("mm_model") or "gemini-2.5-flash").strip().lower()
        d["mm_timeout_sec"] = int(max(10, min(int(d.get("mm_timeout_sec") or 75), 180)))
        d["mm_max_retries"] = int(max(0, min(int(d.get("mm_max_retries") or 2), 8)))
        return d
    except Exception:
        return defaults


# =========================================================
# Whisper (Groq) para audios
# =========================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "").strip()

async def _groq_transcribe_audio(media_bytes: bytes, mime_type: str) -> tuple[str, dict]:
    if not GROQ_API_KEY:
        return "", {"ok": False, "reason": "GROQ_API_KEY missing"}

    url = "https://api.groq.com/openai/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}"}

    files = {"file": ("audio.ogg", media_bytes, (mime_type or "audio/ogg"))}
    data = {
        "model": "whisper-large-v3-turbo",
        "response_format": "json",
        "temperature": "0",
    }

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(url, headers=headers, data=data, files=files)
    except Exception as e:
        return "", {"ok": False, "stage": "http", "error": str(e)[:900]}

    if r.status_code >= 400:
        return "", {"ok": False, "stage": "transcribe", "status": r.status_code, "body": r.text[:900]}

    j = r.json() or {}
    return (j.get("text") or "").strip(), {"ok": True, "stage": "transcribe", "model": data["model"]}


# =========================================================
# AI state helpers (Woo)
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


# =========================================================
# Woo send product (mismo comportamiento que tu main)
# =========================================================

async def _wc_send_product_internal(phone: str, product_id: int, custom_caption: str = "") -> dict:
    if not phone or not product_id:
        raise RuntimeError("phone and product_id required")

    if not (WC_BASE_URL and WC_CONSUMER_KEY and WC_CONSUMER_SECRET):
        raise RuntimeError("WC env vars not configured")

    product = await wc_fetch_product(int(product_id))

    images = product.get("images") or []
    if not images:
        raise RuntimeError("Product has no image")

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


# =========================================================
# MAIN: run_ingest (esto reemplaza la función ingest de main.py)
# =========================================================

async def run_ingest(msg: IngestMessage) -> dict:
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

    # ✅ Asegura fila CRM desde el inicio
    ensure_conversation_row(msg.phone)

    # ✅ 1) Idempotencia (evita duplicados por retry webhook)
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

    # ✅ 2) Guardar mensaje en DB
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

    # ✅ 3) Si es OUT, aquí solo enviamos (pero normalmente tu sistema manda OUT desde otros lados)
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

    # ✅ 4) Si es IN: decidir si IA corre (y si takeover está off)
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

            # ✅ Multimodal: si no hay texto y llega audio/imagen/doc
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
                    mm_meta = {}

                    if media_bytes:
                        if msg_type == "audio":
                            extracted, mm_meta = await _groq_transcribe_audio(
                                media_bytes=media_bytes,
                                mime_type=(real_mime or msg.mime_type or "audio/ogg"),
                            )
                            stage_meta["stages"]["multimodal"] = {
                                "provider": "groq",
                                **(mm_meta or {}),
                            }
                            extracted = (extracted or "").strip()

                        else:
                            mm_cfg = _get_multimodal_settings()
                            if not mm_cfg.get("mm_enabled", True):
                                extracted, mm_meta = "", {"ok": False, "reason": "mm_disabled"}
                            else:
                                os.environ["GEMINI_MM_MODEL"] = str(mm_cfg.get("mm_model") or "gemini-2.5-flash").strip()
                                extracted, mm_meta = await extract_text_from_media(
                                    msg_type=msg_type,
                                    media_bytes=media_bytes,
                                    mime_type=(real_mime or msg.mime_type or "application/octet-stream"),
                                )

                            stage_meta["stages"]["multimodal"] = {
                                "provider": mm_cfg.get("mm_provider", "google"),
                                "model": mm_cfg.get("mm_model", ""),
                                "mm_enabled": bool(mm_cfg.get("mm_enabled", True)),
                                **(mm_meta or {}),
                            }
                            extracted = (extracted or "").strip()

                    stage_meta["ok"] = bool(extracted)
                    stage_meta["extracted_len"] = int(len(extracted))

                    with engine.begin() as conn:
                        set_extracted_text(conn, local_id, extracted or "", ai_meta={"multimodal": stage_meta})

                    if extracted:
                        user_text = extracted

                except Exception as e:
                    stage_meta["stages"]["exception"] = {"ok": False, "error": str(e)[:900]}
                    with engine.begin() as conn:
                        set_extracted_text(conn, local_id, "", ai_meta={"multimodal": stage_meta})
                    user_text = ""

            if is_effectively_empty_text(user_text):
                user_text = ""

            if not user_text:
                fallback_text = (
                    "📩 Recibí tu audio, imagen o documento, pero no pude interpretarlo bien.\n\n"
                    "¿Me lo puedes escribir en texto o reenviar el archivo? 🙏"
                )
                send_result = await send_ai_reply_in_chunks(msg.phone, fallback_text)
                return {
                    "saved": True,
                    "sent": bool(send_result.get("sent")),
                    "ai": False,
                    "reason": "no_text_after_multimodal",
                    "fallback_replied": True,
                    "wa_last": send_result.get("last_wa") or {},
                }

            # Limpieza Woo state si venimos de media
            if msg_type != "text":
                st_now = _get_ai_state(msg.phone) or ""
                if st_now.startswith("wc_await:") or st_now.startswith("wc_state:"):
                    _clear_ai_state(msg.phone)

            # =========================================================
            # WooCommerce assistant (si aplica)
            # =========================================================
            if wc_enabled() and user_text:
                async def _send_product_and_cleanup(phone: str, product_id: int, caption: str = "") -> dict:
                    wa = await wc_send_product(phone=phone, product_id=product_id, custom_caption=caption)
                    return wa

                wc_result = await handle_wc_if_applicable(
                    phone=msg.phone,
                    user_text=user_text,
                    msg_type="text",
                    get_state=_get_ai_state,
                    set_state=_set_ai_state,
                    clear_state=_clear_ai_state,
                    send_product_fn=_send_product_and_cleanup,
                    send_text_fn=lambda phone, text: send_ai_reply_in_chunks(phone, text),
                )

                if wc_result.get("handled") is True:
                    # ✅ memoria CRM (si wc_assistant devuelve slots más adelante)
                    slots = wc_result.get("slots") if isinstance(wc_result, dict) else None
                    if isinstance(slots, dict) and slots:
                        apply_wc_slots_to_crm(msg.phone, slots)

                    update_crm_fields(
                        msg.phone,
                        tags_add=["estado:asesoria_woo"],
                        notes_append=f"Woo handled: {wc_result.get('reason','')}"
                    )

                    return {
                        "saved": True,
                        "sent": True,
                        "ai": False,
                        **{k: v for k, v in wc_result.items() if k != "handled"}
                    }

            # =========================================================
            # Flujo IA normal
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

            # Decide si enviar voz o texto (usa settings en reply_sender)
            # - si voice_enabled y prefer_voice -> voz
            # - sino -> texto en chunks
            from app.pipeline.reply_sender import _get_voice_settings  # import local para evitar líos
            voice = _get_voice_settings()

            if voice.get("voice_enabled") and voice.get("voice_prefer_voice"):
                send_result = await send_ai_reply_as_voice(msg.phone, reply_text)
                return {
                    "saved": True,
                    "sent": bool(send_result.get("sent")),
                    "ai": True,
                    "reply": reply_text,
                    "voice": True,
                    "wa": send_result.get("wa") or {},
                }

            send_result = await send_ai_reply_in_chunks(msg.phone, reply_text)

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