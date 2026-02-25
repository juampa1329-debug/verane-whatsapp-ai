from __future__ import annotations

import os
import json
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple

import httpx
from pydantic import BaseModel
from sqlalchemy import text

from app.db import engine

# IA
from app.ai.engine import process_message
from app.ai.context_builder import build_ai_meta

# Multimodal
from app.ai.multimodal import extract_text_from_media, is_effectively_empty_text

# Intent router V3
from app.ai.intent_router import detect_intent

# Woo (assistant)
from app.ai.wc_assistant import handle_wc_if_applicable
from app.integrations.woocommerce import wc_enabled

# ✅ Woo sender oficial (el bueno)
from app.pipeline.wc_sender import wc_send_product

# CRM intelligence
from app.crm.crm_writer import update_intent, update_preferences_structured, update_summary_auto, update_last_products

# Sender helpers + DB helpers
from app.pipeline.reply_sender import (
    save_message,
    set_wa_send_result,
    set_extracted_text,
    send_ai_reply_in_chunks,
    send_ai_reply_as_voice,
)

# CRM memory writer
from app.crm.crm_writer import (
    ensure_conversation_row,
    apply_wc_slots_to_crm,
    update_crm_fields,
    get_last_product_sent,  # ✅ NUEVO
)



# =========================================================
# Helpers: recuperar último extracted_text de media (para "tienes este?")
# =========================================================

def _get_recent_media_extracted(phone: str, minutes: int = 15) -> str:
    phone = (phone or "").strip()
    if not phone:
        return ""
    try:
        with engine.begin() as conn:
            r = conn.execute(text("""
                SELECT extracted_text
                FROM messages
                WHERE phone = :phone
                  AND direction = 'in'
                  AND msg_type IN ('image','document')
                  AND extracted_text IS NOT NULL
                  AND created_at >= (NOW() - (:mins || ' minutes')::interval)
                ORDER BY created_at DESC
                LIMIT 1
            """), {"phone": phone, "mins": int(minutes)}).mappings().first()
        return (r.get("extracted_text") if r else "") or ""
    except Exception:
        return ""

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
# ✅ Intent detector: "envíame la foto"
# =========================================================

def _norm_text(s: str) -> str:
    s = (s or "").strip().lower()
    replacements = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    for a, b in replacements.items():
        s = s.replace(a, b)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _is_photo_request(text: str) -> bool:
    """
    Detecta mensajes como:
      - "si enviame la foto"
      - "envia la imagen"
      - "mandame la foto real"
      - "quiero ver la foto"
      - "pasa foto"
      - "enviala"
    Evita dispararse por cosas genéricas.
    """
    t = _norm_text(text)
    if not t:
        return False

    if t in {"ok", "dale", "listo", "gracias", "perfecto", "vale", "bien", "👍", "👌", "✅"}:
        return False

    if t in {"si", "sí"}:
        return False

    photo_tokens = [
        "foto", "imagen", "picture", "pic", "phot",
        "ver foto", "ver la foto", "ver imagen", "foto real", "imagen real"
    ]
    send_tokens = [
        "envia", "enviame", "mandame", "manda", "pasame", "pasa",
        "muestrame", "muestra", "compart", "reenvi", "enviala", "enviarla"
    ]

    has_photo = any(p in t for p in photo_tokens)
    has_send = any(s in t for s in send_tokens)

    if has_photo and (has_send or "quiero ver" in t or "me la puedes" in t or "me puedes" in t):
        return True

    if t in {"enviala", "enviarla", "enviala por favor", "mandala", "mandala por favor"}:
        return True

    return False


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


def _has_recent_wc_last_options(phone: str, max_age_minutes: int = 120) -> bool:
    """
    Si el usuario vio opciones hace poco (wc_last_options_at), permitimos selección por número
    aunque no haya ai_state wc_*.
    """
    try:
        with engine.begin() as conn:
            r = conn.execute(text("""
                SELECT wc_last_options_at
                FROM conversations
                WHERE phone = :phone
                LIMIT 1
            """), {"phone": phone}).mappings().first()

        dt = (r or {}).get("wc_last_options_at")
        if not dt:
            return False

        try:
            age = datetime.utcnow() - dt
        except Exception:
            return False

        return age <= timedelta(minutes=max(5, int(max_age_minutes)))
    except Exception:
        return False


# =========================================================
# Guard: cuándo SÍ debemos entrar al Woo assistant (anti-loop)
# =========================================================

_WC_KEYWORDS = {
    "perfume", "perfumes", "colonia", "fragancia", "fragancias",
    "precio", "vale", "cuánto", "cuanto", "costo", "coste",
    "comprar", "pedido", "orden", "carrito", "envío", "envio",
    "stock", "disponible", "disponibilidad", "promoción", "promocion",
    "catálogo", "catalogo", "recomienda", "recomendación", "recomendacion",
    "para hombre", "para mujer", "unisex", "dulce", "amaderado", "cítrico", "citrico",
}


def _should_call_wc_assistant(phone: str, user_text: str, *, msg_type: str = "text", extracted_text: str = "") -> tuple[bool, str]:
    """
    Evita el loop: solo llamamos Woo si realmente aplica.
    - Si el estado actual ya es wc_* -> True
    - Si el texto tiene señales de intención de compra/búsqueda -> True
    - Si el usuario manda un número y hay wc_last_options recientes -> True ✅
    """
    st = (_get_ai_state(phone) or "").strip().lower()
    if st.startswith("wc_") or st.startswith("wc:") or st.startswith("wc_state") or st.startswith("wc_await"):
        return True, "state_active"

    t = (user_text or "").strip().lower()
    if not t:
        # Si es media (imagen/doc/audio) y tenemos extracted_text, dejamos que Woo intente.
        mt = (msg_type or "").strip().lower()
        et = (extracted_text or "").strip()
        if mt in ("image", "document") and et:
            return True, "media_with_extracted_text"
        return False, "empty_text"

    # ✅ Selección por número si hay “memoria” reciente de opciones
    if t.isdigit():
        if _has_recent_wc_last_options(phone, max_age_minutes=120):
            return True, "digit_with_recent_wc_last_options"
        return False, "digit_without_state_or_options"

    for kw in _WC_KEYWORDS:
        if kw in t:
            return True, f"keyword:{kw}"

    mt = (msg_type or "").strip().lower()
    et = (extracted_text or "").strip()
    if mt in ("image", "document") and et:
        return True, "media_with_extracted_text"

    return False, "no_intent"


# =========================================================
# MAIN: run_ingest
# =========================================================

async def run_ingest(msg: IngestMessage) -> dict:
    # Import local para evitar circular imports con routes.whatsapp
    from app.routes.whatsapp import (
        send_whatsapp_text,
        send_whatsapp_media_id,
        download_whatsapp_media_bytes,
    )

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
        except Exception as e:
            _log(trace_id, "IDEMPOTENCY_FAIL", error=str(e)[:300])

    # ✅ 2) Guardar mensaje en DB + bump updated_at SIEMPRE
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
        _log(trace_id, "DB_IN_SAVED", local_id=local_id)
    except Exception as e:
        _log(trace_id, "DB_SAVE_FAIL", error=str(e)[:900])
        return {"saved": False, "sent": False, "stage": "db", "error": str(e)}

    # ✅ 3) Si es OUT: enviamos y marcamos estado
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

            _log(trace_id, "WHATSAPP_OUT_SENT", ok=bool(isinstance(wa_resp, dict) and wa_resp.get("sent")))
            return {"saved": True, "sent": bool(isinstance(wa_resp, dict) and wa_resp.get("sent")), "wa": wa_resp}

        except Exception as e:
            with engine.begin() as conn:
                set_wa_send_result(conn, local_id, None, False, str(e)[:900])
            _log(trace_id, "WHATSAPP_OUT_EXCEPTION", error=str(e)[:900])
            return {"saved": True, "sent": False, "stage": "whatsapp", "error": str(e)}

    # ✅ 4) Si es IN: decidir si IA corre (takeover off + ai enabled)
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

            extracted = ""  # always defined (used later)

            # Si el usuario escribió algo corto tipo "tienes este?" y antes envió una imagen,
            # usamos el extracted_text de la imagen reciente como contexto de búsqueda.
            try:
                t_norm = _norm_text(user_text)
                if msg_type == "text" and t_norm in {"tienes este?", "tienes este", "lo tienes?", "lo tienes", "tienes ese?", "tienes ese", "disponible?", "disponible"}:
                    prev = _get_recent_media_extracted(msg.phone, minutes=20)
                    if prev:
                        user_text = f"{user_text} | contexto_imagen: {prev[:280]}".strip()
            except Exception:
                pass
            mm_parsed = None

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

                    # Si Gemini devolvió JSON estructurado, lo guardamos para decisiones posteriores
                    try:
                        mm_parsed = (mm_meta or {}).get("parsed_json")
                    except Exception:
                        mm_parsed = None

                    if extracted:
                        user_text = extracted

                    # Si es un JSON (PERFUME/PAYMENT), usamos campos para mejorar routing y CRM
                    if isinstance(mm_parsed, dict):
                        mm_type = str(mm_parsed.get("type") or "").strip().upper()
                        if mm_type == "PERFUME":
                            perf = mm_parsed.get("perfume") or {}
                            b = (perf.get("brand") or "").strip()
                            n = (perf.get("name") or "").strip()
                            v = (perf.get("variant") or "").strip()
                            q = " ".join([x for x in [n, v, b] if x]).strip()
                            if q:
                                user_text = q
                        elif mm_type == "PAYMENT":
                            pay = mm_parsed.get("payment") or {}
                            note_lines = []
                            amt = (pay.get("amount") or "").strip()
                            cur = (pay.get("currency") or "").strip()
                            ref = (pay.get("reference") or "").strip()
                            dt = (pay.get("date") or "").strip()
                            bank = (pay.get("bank") or "").strip()
                            payer = (pay.get("payer") or "").strip()
                            payee = (pay.get("payee") or "").strip()
                            if amt or cur:
                                note_lines.append(f"Pago detectado: {amt} {cur}".strip())
                            if ref:
                                note_lines.append(f"Referencia: {ref}")
                            if dt:
                                note_lines.append(f"Fecha: {dt}")
                            if bank:
                                note_lines.append(f"Banco: {bank}")
                            if payer:
                                note_lines.append(f"Pagador: {payer}")
                            if payee:
                                note_lines.append(f"Beneficiario: {payee}")
                            note = " | ".join([x for x in note_lines if x]).strip()
                            if note:
                                try:
                                    update_crm_fields(msg.phone, tags_add=["pago_detectado"], notes_append=note)
                                except Exception:
                                    pass
                                try:
                                    update_intent(msg.phone, intent_current="PAYMENT", intent_confidence=0.95)
                                except Exception:
                                    pass


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
                _log(trace_id, "FALLBACK_NO_TEXT", sent=bool(send_result.get("sent")))
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
                st_now = (_get_ai_state(msg.phone) or "").strip().lower()
                if st_now.startswith("wc_") or st_now.startswith("wc_state") or st_now.startswith("wc_await"):
                    _clear_ai_state(msg.phone)

            
            # =========================================================
            # ✅ Intent Router V3 (PHOTO_REQUEST / PRODUCT_SEARCH / PREFERENCE_RECO / etc.)
            # =========================================================
            st_now = (_get_ai_state(msg.phone) or "").strip()
            intent_res = detect_intent(
                user_text=user_text,
                msg_type=msg_type,
                state=st_now,
                extracted_text=(extracted or ""),
                crm_snapshot=None,
            )
            update_intent(msg.phone, intent_current=intent_res.intent, intent_confidence=float(intent_res.confidence or 0.0))

            # Resumen corto (muy simple, sin LLM)
            try:
                summary = f"Intent={intent_res.intent} conf={intent_res.confidence:.2f}. Último mensaje: {user_text[:160]}"
                update_summary_auto(msg.phone, summary)
            except Exception:
                pass
# =========================================================
            # ✅ si el usuario pide "envíame la foto" -> reenviar tarjeta del último producto
            # =========================================================
            if intent_res.intent == "PHOTO_REQUEST" or (msg_type == "text" and _is_photo_request(user_text)):
                last = get_last_product_sent(msg.phone)
                _log(trace_id, "PHOTO_REQUEST_DETECTED", ok=bool(last.get("ok")), last=last.get("raw", "")[:220])

                if isinstance(last, dict) and last.get("ok") is True:
                    pid = int(last.get("product_id") or 0)
                    if pid > 0:
                        update_crm_fields(
                            msg.phone,
                            tags_add=["intencion:ver_foto"],
                            notes_append=f"Cliente pidió foto -> reenviar tarjeta (product_id={pid})"
                        )

                        try:
                            wa = await wc_send_product(phone=msg.phone, product_id=pid, custom_caption="")
                        except Exception as e:
                            wa = {"sent": False, "reason": "wc_send_exception", "error": str(e)[:900]}

                        sent_ok = bool(isinstance(wa, dict) and wa.get("sent") is True)

                        _log(trace_id, "PHOTO_REQUEST_SENT_CARD", sent=sent_ok, product_id=pid)
                        return {
                            "saved": True,
                            "sent": sent_ok,
                            "ai": False,
                            "woo": True,
                            "reason": "photo_request_resend_last_product",
                            "product_id": pid,
                            "wa": wa,
                        }

                update_crm_fields(
                    msg.phone,
                    tags_add=["intencion:ver_foto"],
                    notes_append="Cliente pidió foto pero no hay producto previo registrado"
                )

                txt = (
                    "¡Claro! 😊\n\n"
                    "¿De cuál perfume quieres la foto?\n"
                    "Dime el nombre del producto o envíame un mensaje con el perfume que estás mirando."
                )
                send_result = await send_ai_reply_in_chunks(msg.phone, txt)
                return {
                    "saved": True,
                    "sent": bool(send_result.get("sent")),
                    "ai": False,
                    "reason": "photo_request_no_last_product",
                    "wa_last": send_result.get("last_wa") or {},
                }

            # =========================================================
            # WooCommerce assistant (SOLO si aplica)
            # =========================================================
            if wc_enabled() and user_text:
                should_wc, reason_wc = _should_call_wc_assistant(msg.phone, user_text, msg_type=msg.msg_type, extracted_text=user_text)
                _log(trace_id, "ROUTER_WC_DECISION", should_wc=should_wc, reason=reason_wc)

                if should_wc:
                    async def _send_product_and_cleanup(phone: str, product_id: int, caption: str = "") -> dict:
                        return await wc_send_product(phone=phone, product_id=product_id, custom_caption=caption)

                    wc_result = await handle_wc_if_applicable(
                        phone=msg.phone,
                        user_text=user_text,
                        msg_type=msg.msg_type,
                        get_state=_get_ai_state,
                        set_state=_set_ai_state,
                        clear_state=_clear_ai_state,
                        send_product_fn=_send_product_and_cleanup,
                        send_text_fn=lambda phone, text: send_ai_reply_in_chunks(phone, text),
                        intent=intent_res.intent,
                        intent_payload=intent_res.payload,
                        extracted_text=(extracted or ''),
                    )

                    if isinstance(wc_result, dict) and wc_result.get("handled") is True:
                        slots = wc_result.get("slots")
                        if isinstance(slots, dict) and slots:
                            apply_wc_slots_to_crm(msg.phone, slots)
                            update_preferences_structured(msg.phone, slots)

                        update_crm_fields(
                            msg.phone,
                            tags_add=["estado:asesoria_woo"],
                            notes_append=_human_wc_note(text, wc_result)
                        )

                        # CRM state: productos vistos / etapa / follow-up (best-effort)
                        try:
                            pid = wc_result.get("product_id")
                            opts = wc_result.get("options") or wc_result.get("candidates") or []
                            ids = []
                            if isinstance(opts, list):
                                for o in opts:
                                    if isinstance(o, dict):
                                        try:
                                            ids.append(int(o.get("id") or 0))
                                        except Exception:
                                            pass
                            update_last_products(
                                msg.phone,
                                last_product_id=int(pid) if pid else None,
                                last_products_seen=ids if ids else None,
                                last_stage=str((wc_result.get("reason") or ""))[:80],
                                last_followup_question="",
                            )
                        except Exception:
                            pass

                        _log(trace_id, "WOO_HANDLED", reason=wc_result.get("reason", ""))
                        return {
                            "saved": True,
                            "sent": True,
                            "ai": False,
                            **{k: v for k, v in wc_result.items() if k != "handled"}
                        }

            # =========================================================
            # Flujo IA normal
            # =========================================================
            _log(trace_id, "ROUTER_AI", reason="default_ai")
            meta = build_ai_meta(msg.phone, user_text)

            ai_result = await process_message(
                phone=msg.phone,
                text=user_text,
                meta=meta,
            )

            reply_text = (ai_result.get("reply_text") or "").strip()
            if not reply_text:
                _log(trace_id, "AI_EMPTY_REPLY")
                return {"saved": True, "sent": False, "ai": True, "reply": ""}

            from app.pipeline.reply_sender import _get_voice_settings  # import local
            voice = _get_voice_settings()

            if voice.get("voice_enabled") and voice.get("voice_prefer_voice"):
                send_result = await send_ai_reply_as_voice(msg.phone, reply_text)
                _log(trace_id, "AI_SENT_VOICE", sent=bool(send_result.get("sent")))
                return {
                    "saved": True,
                    "sent": bool(send_result.get("sent")),
                    "ai": True,
                    "reply": reply_text,
                    "voice": True,
                    "wa": send_result.get("wa") or {},
                }

            send_result = await send_ai_reply_in_chunks(msg.phone, reply_text)
            _log(trace_id, "AI_SENT_TEXT", sent=bool(send_result.get("sent")), chunks=int(send_result.get("chunks_sent") or 0))

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
            _log(trace_id, "INGEST_EXCEPTION", error=str(e)[:900])
            return {"saved": True, "sent": False, "ai": False, "ai_error": str(e)[:900]}

    return {"saved": True, "sent": False}