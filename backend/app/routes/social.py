from __future__ import annotations

from datetime import datetime
import hashlib
import hmac
import json
import os
from typing import Any, Dict, Iterable, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import text

from app.ai.context_builder import build_ai_meta
from app.ai.engine import process_message
from app.automation.trigger_engine import execute_comment_triggers
from app.db import engine
from app.integrations.social_channels import send_comment_reply

router = APIRouter()


META_VERIFY_TOKEN = str(os.getenv("META_VERIFY_TOKEN", "")).strip()
META_WEBHOOK_VERIFY_TOKEN = str(os.getenv("META_WEBHOOK_VERIFY_TOKEN", META_VERIFY_TOKEN)).strip()
FACEBOOK_VERIFY_TOKEN = str(os.getenv("FACEBOOK_VERIFY_TOKEN", META_VERIFY_TOKEN)).strip()
INSTAGRAM_VERIFY_TOKEN = str(os.getenv("INSTAGRAM_VERIFY_TOKEN", META_VERIFY_TOKEN)).strip()
TIKTOK_VERIFY_TOKEN = str(os.getenv("TIKTOK_VERIFY_TOKEN", "")).strip()

META_MESSENGER_VERIFY_TOKEN = str(os.getenv("META_MESSENGER_VERIFY_TOKEN", FACEBOOK_VERIFY_TOKEN or META_WEBHOOK_VERIFY_TOKEN)).strip()
META_PAGE_VERIFY_TOKEN = str(os.getenv("META_PAGE_VERIFY_TOKEN", FACEBOOK_VERIFY_TOKEN or META_WEBHOOK_VERIFY_TOKEN)).strip()
META_LEADS_VERIFY_TOKEN = str(os.getenv("META_LEADS_VERIFY_TOKEN", META_WEBHOOK_VERIFY_TOKEN or FACEBOOK_VERIFY_TOKEN)).strip()
META_ADS_VERIFY_TOKEN = str(os.getenv("META_ADS_VERIFY_TOKEN", META_WEBHOOK_VERIFY_TOKEN or FACEBOOK_VERIFY_TOKEN)).strip()
META_APP_SECRET = str(os.getenv("META_APP_SECRET", "")).strip()
META_ENFORCE_SIGNATURE = str(os.getenv("META_ENFORCE_SIGNATURE", "false")).strip().lower() == "true"

_SOCIAL_TABLES_READY = False


def _norm_channel(channel: str, default: str = "facebook") -> str:
    ch = str(channel or "").strip().lower()
    if ch in ("whatsapp", "facebook", "instagram", "tiktok"):
        return ch
    return default


def _safe_obj(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _safe_list(value: Any) -> List[Any]:
    if isinstance(value, list):
        return value
    return []


def _headers_subset(headers: Any) -> Dict[str, str]:
    out: Dict[str, str] = {}
    if not headers:
        return out
    for key in ("x-hub-signature-256", "x-hub-signature", "user-agent", "x-forwarded-for", "x-real-ip"):
        try:
            val = headers.get(key)
        except Exception:
            val = None
        if val:
            out[key] = str(val)
    return out


def _ensure_social_tables() -> None:
    global _SOCIAL_TABLES_READY
    if _SOCIAL_TABLES_READY:
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS social_webhook_events (
                    id BIGSERIAL PRIMARY KEY,
                    provider TEXT NOT NULL,
                    route_key TEXT NOT NULL,
                    object_name TEXT,
                    channel TEXT,
                    processed INTEGER NOT NULL DEFAULT 0,
                    errors INTEGER NOT NULL DEFAULT 0,
                    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    headers_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_social_webhook_events_created_at ON social_webhook_events (created_at DESC)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_social_webhook_events_route_key ON social_webhook_events (route_key)"))

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS meta_lead_events (
                    id BIGSERIAL PRIMARY KEY,
                    leadgen_id TEXT NOT NULL,
                    page_id TEXT,
                    form_id TEXT,
                    ad_id TEXT,
                    adgroup_id TEXT,
                    object_name TEXT,
                    route_key TEXT NOT NULL,
                    payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    UNIQUE (leadgen_id)
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_meta_lead_events_created_at ON meta_lead_events (created_at DESC)"))

        conn.execute(
            text(
                """
                CREATE TABLE IF NOT EXISTS social_comments (
                    id BIGSERIAL PRIMARY KEY,
                    channel TEXT NOT NULL DEFAULT 'facebook',
                    network_account_id TEXT,
                    external_comment_id TEXT NOT NULL,
                    parent_external_comment_id TEXT,
                    post_id TEXT,
                    direction TEXT NOT NULL DEFAULT 'in',
                    author_id TEXT,
                    author_name TEXT,
                    message TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'new',
                    assigned_to TEXT,
                    provider_payload_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    UNIQUE(channel, external_comment_id, direction)
                )
                """
            )
        )
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_social_comments_channel_status_created ON social_comments (channel, status, created_at DESC)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_social_comments_external ON social_comments (channel, external_comment_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_social_comments_parent ON social_comments (channel, parent_external_comment_id)"))

    _SOCIAL_TABLES_READY = True


def _save_social_webhook_event(
    *,
    provider: str,
    route_key: str,
    object_name: str,
    channel: str,
    processed: int,
    errors: int,
    payload: Dict[str, Any],
    headers: Dict[str, Any],
) -> None:
    _ensure_social_tables()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO social_webhook_events (
                    provider, route_key, object_name, channel,
                    processed, errors, payload_json, headers_json, created_at
                )
                VALUES (
                    :provider, :route_key, :object_name, :channel,
                    :processed, :errors, CAST(:payload_json AS jsonb), CAST(:headers_json AS jsonb), NOW()
                )
                """
            ),
            {
                "provider": str(provider or "meta").strip().lower() or "meta",
                "route_key": str(route_key or "").strip().lower() or "meta",
                "object_name": str(object_name or "").strip().lower() or None,
                "channel": _norm_channel(channel, default="facebook"),
                "processed": int(processed or 0),
                "errors": int(errors or 0),
                "payload_json": json.dumps(payload or {}, ensure_ascii=False),
                "headers_json": json.dumps(headers or {}, ensure_ascii=False),
            },
        )


def _verify_meta_signature_or_skip(request: Request, raw_body: bytes) -> None:
    secret = str(META_APP_SECRET or "").strip()
    if not secret:
        return

    raw_sig = str(request.headers.get("x-hub-signature-256") or "").strip()
    if not raw_sig:
        if META_ENFORCE_SIGNATURE:
            raise HTTPException(status_code=403, detail="Missing X-Hub-Signature-256")
        return

    digest = hmac.new(secret.encode("utf-8"), raw_body or b"", hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    if not hmac.compare_digest(expected, raw_sig):
        raise HTTPException(status_code=403, detail="Invalid X-Hub-Signature-256")


def _extract_sender_id(value: Any) -> str:
    if isinstance(value, dict):
        direct = value.get("id") or value.get("sender_id") or value.get("from")
        if isinstance(direct, dict):
            nested = direct.get("id") or direct.get("user_id")
            if nested:
                return str(nested).strip()
        if direct:
            return str(direct).strip()
    if value:
        return str(value).strip()
    return ""


def _infer_msg_type_from_attachment(atype: str) -> str:
    token = str(atype or "").strip().lower()
    if token in ("image", "video", "audio"):
        return token
    if token in ("file", "document"):
        return "document"
    return "text"


def _parse_meta_attachment(att: Any) -> Dict[str, Any]:
    obj = _safe_obj(att)
    payload = _safe_obj(obj.get("payload"))

    atype = str(obj.get("type") or payload.get("type") or "").strip().lower()
    msg_type = _infer_msg_type_from_attachment(atype)
    media_ref = str(
        payload.get("url")
        or payload.get("attachment_url")
        or payload.get("attachment_id")
        or obj.get("id")
        or ""
    ).strip()
    mime_type = str(payload.get("mime_type") or obj.get("mime_type") or "").strip().lower() or None
    fallback_text = str(payload.get("title") or payload.get("text") or "").strip()

    return {
        "msg_type": msg_type,
        "media_id": media_ref or None,
        "mime_type": mime_type,
        "text": fallback_text,
    }


def _normalize_meta_message_record(sender_id: str, event_obj: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    sender = str(sender_id or "").strip()
    if not sender:
        return None

    message = _safe_obj(event_obj.get("message"))
    postback = _safe_obj(event_obj.get("postback"))

    text_val = str(message.get("text") or "").strip()
    quick_payload = str(_safe_obj(message.get("quick_reply")).get("payload") or "").strip()

    attachments = _safe_list(message.get("attachments"))
    if attachments:
        parsed = _parse_meta_attachment(attachments[0])
        parsed_text = text_val or parsed.get("text") or ""
        return {
            "phone": sender,
            "msg_type": str(parsed.get("msg_type") or "text"),
            "text": str(parsed_text).strip(),
            "media_id": parsed.get("media_id"),
            "mime_type": parsed.get("mime_type"),
        }

    if text_val:
        return {"phone": sender, "msg_type": "text", "text": text_val, "media_id": None, "mime_type": None}

    if quick_payload:
        return {"phone": sender, "msg_type": "text", "text": quick_payload, "media_id": None, "mime_type": None}

    if postback:
        pb_text = str(postback.get("title") or postback.get("payload") or "").strip()
        if pb_text:
            return {"phone": sender, "msg_type": "text", "text": pb_text, "media_id": None, "mime_type": None}

    return None


def _iter_meta_records(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    entries = _safe_list(payload.get("entry"))
    for entry in entries:
        eobj = _safe_obj(entry)

        for evt in _safe_list(eobj.get("messaging")):
            e = _safe_obj(evt)
            sender = _extract_sender_id(e.get("sender"))
            row = _normalize_meta_message_record(sender, e)
            if row:
                yield row

        for change in _safe_list(eobj.get("changes")):
            cobj = _safe_obj(change)
            value = _safe_obj(cobj.get("value"))

            for evt in _safe_list(value.get("messaging")):
                e = _safe_obj(evt)
                sender = _extract_sender_id(e.get("sender"))
                row = _normalize_meta_message_record(sender, e)
                if row:
                    yield row

            for raw_msg in _safe_list(value.get("messages")):
                m = _safe_obj(raw_msg)
                sender = _extract_sender_id(m.get("from"))
                if not sender:
                    sender = _extract_sender_id(_safe_obj(m.get("sender")))
                if not sender:
                    continue

                text_val = str(m.get("text") or "").strip()
                attachments = _safe_list(m.get("attachments"))
                if attachments:
                    parsed = _parse_meta_attachment(attachments[0])
                    yield {
                        "phone": sender,
                        "msg_type": str(parsed.get("msg_type") or "text"),
                        "text": str(text_val or parsed.get("text") or "").strip(),
                        "media_id": parsed.get("media_id"),
                        "mime_type": parsed.get("mime_type"),
                    }
                elif text_val:
                    yield {
                        "phone": sender,
                        "msg_type": "text",
                        "text": text_val,
                        "media_id": None,
                        "mime_type": None,
                    }


def _iter_meta_lead_events(payload: Dict[str, Any], route_key: str) -> Iterable[Dict[str, Any]]:
    object_name = str(payload.get("object") or "").strip().lower()
    entries = _safe_list(payload.get("entry"))
    for entry in entries:
        eobj = _safe_obj(entry)
        entry_id = str(eobj.get("id") or "").strip()
        for change in _safe_list(eobj.get("changes")):
            cobj = _safe_obj(change)
            field = str(cobj.get("field") or "").strip().lower()
            if field != "leadgen":
                continue

            value = _safe_obj(cobj.get("value"))
            leadgen_id = str(value.get("leadgen_id") or value.get("leadgenid") or "").strip()
            if not leadgen_id:
                continue

            page_id = str(value.get("page_id") or entry_id or "").strip() or None
            form_id = str(value.get("form_id") or value.get("formid") or "").strip() or None
            ad_id = str(value.get("ad_id") or "").strip() or None
            adgroup_id = str(value.get("adgroup_id") or "").strip() or None

            yield {
                "leadgen_id": leadgen_id,
                "page_id": page_id,
                "form_id": form_id,
                "ad_id": ad_id,
                "adgroup_id": adgroup_id,
                "object_name": object_name or "page",
                "route_key": str(route_key or "meta").strip().lower(),
                "payload_json": value,
            }


def _save_meta_lead_events(payload: Dict[str, Any], route_key: str) -> int:
    events = list(_iter_meta_lead_events(payload, route_key=route_key))
    if not events:
        return 0

    _ensure_social_tables()
    with engine.begin() as conn:
        for evt in events:
            conn.execute(
                text(
                    """
                    INSERT INTO meta_lead_events (
                        leadgen_id, page_id, form_id, ad_id, adgroup_id,
                        object_name, route_key, payload_json, created_at
                    )
                    VALUES (
                        :leadgen_id, :page_id, :form_id, :ad_id, :adgroup_id,
                        :object_name, :route_key, CAST(:payload_json AS jsonb), NOW()
                    )
                    ON CONFLICT (leadgen_id)
                    DO UPDATE SET
                        page_id = COALESCE(EXCLUDED.page_id, meta_lead_events.page_id),
                        form_id = COALESCE(EXCLUDED.form_id, meta_lead_events.form_id),
                        ad_id = COALESCE(EXCLUDED.ad_id, meta_lead_events.ad_id),
                        adgroup_id = COALESCE(EXCLUDED.adgroup_id, meta_lead_events.adgroup_id),
                        object_name = COALESCE(EXCLUDED.object_name, meta_lead_events.object_name),
                        route_key = COALESCE(EXCLUDED.route_key, meta_lead_events.route_key),
                        payload_json = EXCLUDED.payload_json
                    """
                ),
                {
                    "leadgen_id": str(evt.get("leadgen_id") or "").strip(),
                    "page_id": evt.get("page_id"),
                    "form_id": evt.get("form_id"),
                    "ad_id": evt.get("ad_id"),
                    "adgroup_id": evt.get("adgroup_id"),
                    "object_name": evt.get("object_name"),
                    "route_key": evt.get("route_key"),
                    "payload_json": json.dumps(evt.get("payload_json") or {}, ensure_ascii=False),
                },
            )
    return len(events)


def _iter_tiktok_records(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    data = _safe_obj(payload.get("data"))
    candidates: List[Any] = []

    if _safe_list(payload.get("messages")):
        candidates.extend(_safe_list(payload.get("messages")))
    if _safe_list(data.get("messages")):
        candidates.extend(_safe_list(data.get("messages")))
    if not candidates:
        candidates.append(payload)

    for item in candidates:
        obj = _safe_obj(item)
        sender = _extract_sender_id(obj.get("sender"))
        if not sender:
            sender = _extract_sender_id(obj.get("from"))
        if not sender:
            sender = _extract_sender_id(obj.get("sender_id"))
        if not sender:
            continue

        content = _safe_obj(obj.get("content"))
        text_val = str(
            obj.get("text")
            or content.get("text")
            or obj.get("message")
            or ""
        ).strip()
        msg_type = str(obj.get("type") or content.get("type") or "text").strip().lower() or "text"
        media_ref = str(
            obj.get("media_url")
            or content.get("media_url")
            or obj.get("media_id")
            or content.get("media_id")
            or ""
        ).strip() or None
        mime_type = str(obj.get("mime_type") or content.get("mime_type") or "").strip().lower() or None

        if msg_type not in ("text", "image", "video", "audio", "document"):
            msg_type = "text"

        if msg_type == "text" and not text_val and not media_ref:
            continue

        yield {
            "phone": sender,
            "msg_type": msg_type,
            "text": text_val,
            "media_id": media_ref,
            "mime_type": mime_type,
        }


def _meta_payload_channel(payload: Dict[str, Any], default_channel: str) -> str:
    obj_name = str(payload.get("object") or "").strip().lower()
    if obj_name == "instagram":
        return "instagram"
    if obj_name == "page" and default_channel == "instagram":
        return "instagram"
    return _norm_channel(default_channel, default="facebook")


def _normalize_comment_status(raw: str, default: str = "new") -> str:
    token = str(raw or "").strip().lower()
    aliases = {
        "nuevo": "new",
        "pendiente": "new",
        "en_revision": "review",
        "revision": "review",
        "respondido": "replied",
        "resuelto": "resolved",
        "ignorado": "ignored",
    }
    token = aliases.get(token, token)
    allowed = {"new", "review", "replied", "resolved", "ignored", "error"}
    if token in allowed:
        return token
    return default


def _iter_meta_comment_records(payload: Dict[str, Any], default_channel: str) -> Iterable[Dict[str, Any]]:
    channel = _meta_payload_channel(payload, default_channel=default_channel)
    entries = _safe_list(payload.get("entry"))
    for entry in entries:
        eobj = _safe_obj(entry)
        entry_id = str(eobj.get("id") or "").strip()
        for change in _safe_list(eobj.get("changes")):
            cobj = _safe_obj(change)
            field = str(cobj.get("field") or "").strip().lower()
            value = _safe_obj(cobj.get("value"))
            if not value:
                continue

            item = str(value.get("item") or "").strip().lower()
            verb = str(value.get("verb") or value.get("event") or "add").strip().lower()

            is_comment_event = False
            if field == "feed" and item == "comment":
                is_comment_event = True
            elif field in ("comments", "comment", "live_comments"):
                is_comment_event = True
            if not is_comment_event:
                continue

            external_comment_id = str(
                value.get("comment_id")
                or value.get("id")
                or value.get("commentid")
                or ""
            ).strip()
            if not external_comment_id:
                continue

            from_obj = _safe_obj(value.get("from") or value.get("sender"))
            author_id = str(
                from_obj.get("id")
                or value.get("from_id")
                or value.get("sender_id")
                or ""
            ).strip()
            author_name = str(
                from_obj.get("name")
                or value.get("from_name")
                or value.get("username")
                or ""
            ).strip()
            if author_id and entry_id and author_id == entry_id:
                # Evita loops de auto-respuesta del propio negocio.
                continue

            message = str(
                value.get("message")
                or value.get("text")
                or value.get("comment_text")
                or ""
            ).strip()
            parent_external_comment_id = str(
                value.get("parent_id")
                or value.get("reply_to_comment_id")
                or ""
            ).strip() or None

            media = _safe_obj(value.get("media"))
            post_id = str(
                value.get("post_id")
                or value.get("media_id")
                or media.get("id")
                or ""
            ).strip() or None

            if not message and verb not in ("remove", "delete", "hide", "unhide"):
                continue

            yield {
                "channel": channel,
                "entry_id": entry_id or None,
                "external_comment_id": external_comment_id,
                "parent_external_comment_id": parent_external_comment_id,
                "post_id": post_id,
                "author_id": author_id or None,
                "author_name": author_name or None,
                "message": message,
                "verb": verb or "add",
                "payload_json": value,
            }


def _upsert_inbound_comment(event: Dict[str, Any]) -> Dict[str, Any]:
    _ensure_social_tables()
    channel = _norm_channel(str(event.get("channel") or "facebook"), default="facebook")
    external_comment_id = str(event.get("external_comment_id") or "").strip()
    if not external_comment_id:
        return {"ok": False, "error": "external_comment_id_required"}

    message = str(event.get("message") or "").strip()
    verb = str(event.get("verb") or "add").strip().lower()
    status = "ignored" if verb in ("hide", "delete", "remove") else "new"

    with engine.begin() as conn:
        existing = conn.execute(
            text(
                """
                SELECT id
                FROM social_comments
                WHERE LOWER(COALESCE(channel, 'facebook')) = :channel
                  AND external_comment_id = :external_comment_id
                  AND direction = 'in'
                LIMIT 1
                """
            ),
            {"channel": channel, "external_comment_id": external_comment_id},
        ).mappings().first()

        if existing:
            conn.execute(
                text(
                    """
                    UPDATE social_comments
                    SET network_account_id = COALESCE(:network_account_id, network_account_id),
                        parent_external_comment_id = COALESCE(:parent_external_comment_id, parent_external_comment_id),
                        post_id = COALESCE(:post_id, post_id),
                        author_id = COALESCE(:author_id, author_id),
                        author_name = COALESCE(:author_name, author_name),
                        message = CASE WHEN :message <> '' THEN :message ELSE message END,
                        status = :status,
                        provider_payload_json = CAST(:provider_payload_json AS jsonb),
                        updated_at = NOW()
                    WHERE id = :id
                    """
                ),
                {
                    "id": int(existing.get("id") or 0),
                    "network_account_id": str(event.get("entry_id") or "").strip() or None,
                    "parent_external_comment_id": str(event.get("parent_external_comment_id") or "").strip() or None,
                    "post_id": str(event.get("post_id") or "").strip() or None,
                    "author_id": str(event.get("author_id") or "").strip() or None,
                    "author_name": str(event.get("author_name") or "").strip() or None,
                    "message": message,
                    "status": status,
                    "provider_payload_json": json.dumps(_safe_obj(event.get("payload_json")), ensure_ascii=False),
                },
            )
            return {"ok": True, "id": int(existing.get("id") or 0), "is_new": False}

        row = conn.execute(
            text(
                """
                INSERT INTO social_comments (
                    channel,
                    network_account_id,
                    external_comment_id,
                    parent_external_comment_id,
                    post_id,
                    direction,
                    author_id,
                    author_name,
                    message,
                    status,
                    provider_payload_json,
                    created_at,
                    updated_at
                )
                VALUES (
                    :channel,
                    :network_account_id,
                    :external_comment_id,
                    :parent_external_comment_id,
                    :post_id,
                    'in',
                    :author_id,
                    :author_name,
                    :message,
                    :status,
                    CAST(:provider_payload_json AS jsonb),
                    NOW(),
                    NOW()
                )
                RETURNING id
                """
            ),
            {
                "channel": channel,
                "network_account_id": str(event.get("entry_id") or "").strip() or None,
                "external_comment_id": external_comment_id,
                "parent_external_comment_id": str(event.get("parent_external_comment_id") or "").strip() or None,
                "post_id": str(event.get("post_id") or "").strip() or None,
                "author_id": str(event.get("author_id") or "").strip() or None,
                "author_name": str(event.get("author_name") or "").strip() or None,
                "message": message,
                "status": status,
                "provider_payload_json": json.dumps(_safe_obj(event.get("payload_json")), ensure_ascii=False),
            },
        ).mappings().first()

    return {"ok": True, "id": int((row or {}).get("id") or 0), "is_new": True}


def _build_comment_ai_prompt(comment_row: Dict[str, Any], extra_instructions: str = "") -> str:
    author = str(comment_row.get("author_name") or "cliente").strip()
    channel = str(comment_row.get("channel") or "facebook").strip().lower()
    comment_text = str(comment_row.get("message") or "").strip()
    instructions = str(extra_instructions or "").strip()
    base = (
        "Eres un asistente comercial de redes sociales.\n"
        f"Canal: {channel}\n"
        f"Autor del comentario: {author}\n"
        f"Comentario del cliente: {comment_text}\n"
        "Responde en espanol, tono profesional y cercano, maximo 2-3 lineas."
    )
    if instructions:
        base += f"\nInstrucciones adicionales: {instructions}"
    return base


async def _suggest_comment_reply(comment_row: Dict[str, Any], instructions: str = "") -> str:
    channel = str(comment_row.get("channel") or "facebook").strip().lower()
    comment_id = str(comment_row.get("external_comment_id") or "").strip() or "0"
    author_id = str(comment_row.get("author_id") or "").strip() or "anon"
    pseudo_phone = f"comment:{channel}:{author_id}:{comment_id}"
    prompt_text = _build_comment_ai_prompt(comment_row, extra_instructions=instructions)
    try:
        meta = build_ai_meta(pseudo_phone, prompt_text)
        ai_result = await process_message(phone=pseudo_phone, text=prompt_text, meta=meta)
        return str(ai_result.get("reply_text") or "").strip()
    except Exception:
        return ""


def _mark_campaign_reply(phone: str, channel: str) -> None:
    p = str(phone or "").strip()
    ch = _norm_channel(channel, default="facebook")
    if not p:
        return

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE campaign_recipients cr
                SET status = 'replied',
                    replied_at = COALESCE(cr.replied_at, NOW())
                WHERE cr.id = (
                    SELECT cr2.id
                    FROM campaign_recipients cr2
                    JOIN campaigns c ON c.id = cr2.campaign_id
                    WHERE cr2.phone = :phone
                      AND LOWER(COALESCE(c.channel, 'whatsapp')) = :channel
                      AND LOWER(cr2.status) IN ('sent', 'delivered', 'read')
                      AND COALESCE(cr2.sent_at, cr2.delivered_at, cr2.read_at, cr2.created_at) >= NOW() - INTERVAL '14 days'
                    ORDER BY COALESCE(cr2.read_at, cr2.delivered_at, cr2.sent_at, cr2.created_at) DESC
                    LIMIT 1
                )
                """
            ),
            {"phone": p, "channel": ch},
        )


async def _ingest_internal(
    *,
    phone: str,
    channel: str,
    msg_type: str,
    text_msg: str,
    media_id: Optional[str] = None,
    mime_type: Optional[str] = None,
) -> None:
    from app.pipeline.ingest_core import IngestMessage as CoreIngestMessage
    from app.pipeline.ingest_core import run_ingest

    payload = CoreIngestMessage(
        phone=str(phone or "").strip(),
        channel=_norm_channel(channel, default="facebook"),
        direction="in",
        msg_type=str(msg_type or "text").strip().lower() or "text",
        text=str(text_msg or "").strip(),
        media_id=str(media_id or "").strip() or None,
        mime_type=str(mime_type or "").strip().lower() or None,
    )
    await run_ingest(payload)


def _verify_with_token(request: Request, verify_token: str) -> Response:
    qp = request.query_params
    mode = qp.get("hub.mode")
    token = qp.get("hub.verify_token")
    challenge = qp.get("hub.challenge")

    if mode == "subscribe" and challenge is not None:
        if verify_token and token != verify_token:
            raise HTTPException(status_code=403, detail="Verification failed")
        return Response(content=str(challenge), media_type="text/plain")

    # Fallback (TikTok-style) query params
    challenge2 = qp.get("challenge")
    token2 = qp.get("verify_token")
    if challenge2 is not None:
        if verify_token and token2 != verify_token:
            raise HTTPException(status_code=403, detail="Verification failed")
        return Response(content=str(challenge2), media_type="text/plain")

    raise HTTPException(status_code=403, detail="Verification failed")


async def _process_meta_payload(payload: Dict[str, Any], default_channel: str) -> Dict[str, Any]:
    channel = _meta_payload_channel(payload, default_channel=default_channel)
    processed_messages = 0
    message_errors = 0

    for rec in _iter_meta_records(payload):
        phone = str(rec.get("phone") or "").strip()
        if not phone:
            continue

        try:
            _mark_campaign_reply(phone, channel)
        except Exception:
            pass

        try:
            await _ingest_internal(
                phone=phone,
                channel=channel,
                msg_type=str(rec.get("msg_type") or "text"),
                text_msg=str(rec.get("text") or ""),
                media_id=str(rec.get("media_id") or "").strip() or None,
                mime_type=str(rec.get("mime_type") or "").strip().lower() or None,
            )
            processed_messages += 1
        except Exception:
            message_errors += 1

    processed_comments = 0
    comment_errors = 0
    comment_trigger_matches = 0
    for evt in _iter_meta_comment_records(payload, default_channel=default_channel):
        try:
            saved = _upsert_inbound_comment(evt)
            if not saved.get("ok"):
                comment_errors += 1
                continue
            processed_comments += 1

            if bool(saved.get("is_new")) and str(evt.get("verb") or "add").lower() not in ("remove", "delete", "hide"):
                trigger_result = await execute_comment_triggers(
                    comment_id=str(evt.get("external_comment_id") or ""),
                    user_text=str(evt.get("message") or ""),
                    channel=str(evt.get("channel") or channel),
                    phone=str(evt.get("author_id") or "").strip(),
                    event_context={
                        "entry_id": evt.get("entry_id"),
                        "comment_id": evt.get("external_comment_id"),
                        "post_id": evt.get("post_id"),
                        "author_id": evt.get("author_id"),
                        "author_name": evt.get("author_name"),
                    },
                )
                if bool(trigger_result.get("matched")):
                    comment_trigger_matches += 1
        except Exception:
            comment_errors += 1

    return {
        "ok": True,
        "channel": channel,
        "processed": int(processed_messages + processed_comments),
        "errors": int(message_errors + comment_errors),
        "messages_processed": processed_messages,
        "message_errors": message_errors,
        "comments_processed": processed_comments,
        "comment_errors": comment_errors,
        "comment_trigger_matches": comment_trigger_matches,
    }


async def _process_tiktok_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    processed = 0
    errors = 0
    channel = "tiktok"

    for rec in _iter_tiktok_records(payload):
        phone = str(rec.get("phone") or "").strip()
        if not phone:
            continue

        try:
            _mark_campaign_reply(phone, channel)
        except Exception:
            pass

        try:
            await _ingest_internal(
                phone=phone,
                channel=channel,
                msg_type=str(rec.get("msg_type") or "text"),
                text_msg=str(rec.get("text") or ""),
                media_id=str(rec.get("media_id") or "").strip() or None,
                mime_type=str(rec.get("mime_type") or "").strip().lower() or None,
            )
            processed += 1
        except Exception:
            errors += 1

    return {"ok": True, "channel": channel, "processed": processed, "errors": errors}


async def _handle_meta_webhook_post(
    request: Request,
    *,
    route_key: str,
    default_channel: str,
) -> Dict[str, Any]:
    raw = await request.body()
    _verify_meta_signature_or_skip(request, raw)

    try:
        payload = json.loads(raw.decode("utf-8", errors="ignore") or "{}")
    except Exception:
        payload = {}

    payload_obj = _safe_obj(payload)
    object_name = str(payload_obj.get("object") or "").strip().lower() or "page"

    lead_count = 0
    try:
        lead_count = _save_meta_lead_events(payload_obj, route_key=route_key)
    except Exception:
        lead_count = 0

    result = await _process_meta_payload(payload_obj, default_channel=default_channel)
    processed_total = int(result.get("processed") or 0) + int(lead_count or 0)
    result["processed"] = processed_total
    if lead_count:
        result["lead_events"] = int(lead_count)

    try:
        _save_social_webhook_event(
            provider="meta",
            route_key=route_key,
            object_name=object_name,
            channel=str(result.get("channel") or default_channel or "facebook"),
            processed=int(result.get("processed") or 0),
            errors=int(result.get("errors") or 0),
            payload=payload_obj,
            headers=_headers_subset(request.headers),
        )
    except Exception:
        pass

    return result


def _meta_token_with_fallback(primary: str) -> str:
    token = str(primary or "").strip()
    if token:
        return token
    token = str(META_WEBHOOK_VERIFY_TOKEN or "").strip()
    if token:
        return token
    return str(META_VERIFY_TOKEN or "").strip()


class SocialCommentPatchIn(BaseModel):
    status: Optional[str] = None
    assigned_to: Optional[str] = None


class SocialCommentSuggestIn(BaseModel):
    instructions: str = ""


class SocialCommentReplyIn(BaseModel):
    message: str = ""
    use_ai: bool = False
    instructions: str = ""
    status_after: str = "replied"


def _load_comment_row(comment_row_id: int) -> Dict[str, Any]:
    _ensure_social_tables()
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    id,
                    channel,
                    network_account_id,
                    external_comment_id,
                    parent_external_comment_id,
                    post_id,
                    direction,
                    author_id,
                    author_name,
                    message,
                    status,
                    assigned_to,
                    provider_payload_json,
                    created_at,
                    updated_at
                FROM social_comments
                WHERE id = :id
                LIMIT 1
                """
            ),
            {"id": int(comment_row_id)},
        ).mappings().first()
    return dict(row or {})


@router.get("/api/social/comments")
async def list_social_comments(
    channel: str = Query("all", description="all|facebook|instagram|tiktok"),
    status: str = Query("all", description="all|new|review|replied|resolved|ignored|error"),
    q: str = Query("", description="texto libre"),
    limit: int = Query(120, ge=1, le=500),
    offset: int = Query(0, ge=0, le=100000),
):
    _ensure_social_tables()
    where: List[str] = ["c.direction = 'in'"]
    params: Dict[str, Any] = {"limit": int(limit), "offset": int(offset)}

    ch = str(channel or "all").strip().lower()
    if ch != "all":
        where.append("LOWER(COALESCE(c.channel, 'facebook')) = :channel")
        params["channel"] = _norm_channel(ch, default="facebook")

    st = str(status or "all").strip().lower()
    if st != "all":
        where.append("LOWER(COALESCE(c.status, 'new')) = :status")
        params["status"] = _normalize_comment_status(st, default="new")

    qv = str(q or "").strip()
    if qv:
        where.append(
            """
            (
                c.message ILIKE :q
                OR c.author_name ILIKE :q
                OR c.author_id ILIKE :q
                OR c.external_comment_id ILIKE :q
                OR c.post_id ILIKE :q
            )
            """
        )
        params["q"] = f"%{qv}%"

    where_sql = " AND ".join(where)
    if not where_sql:
        where_sql = "TRUE"

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                f"""
                SELECT
                    c.id,
                    c.channel,
                    c.network_account_id,
                    c.external_comment_id,
                    c.parent_external_comment_id,
                    c.post_id,
                    c.direction,
                    c.author_id,
                    c.author_name,
                    c.message,
                    c.status,
                    c.assigned_to,
                    c.created_at,
                    c.updated_at,
                    (
                        SELECT COUNT(*)
                        FROM social_comments r
                        WHERE LOWER(COALESCE(r.channel, 'facebook')) = LOWER(COALESCE(c.channel, 'facebook'))
                          AND r.parent_external_comment_id = c.external_comment_id
                          AND r.direction = 'out'
                    ) AS replies_count,
                    (
                        SELECT MAX(r2.created_at)
                        FROM social_comments r2
                        WHERE LOWER(COALESCE(r2.channel, 'facebook')) = LOWER(COALESCE(c.channel, 'facebook'))
                          AND r2.parent_external_comment_id = c.external_comment_id
                          AND r2.direction = 'out'
                    ) AS last_reply_at
                FROM social_comments c
                WHERE {where_sql}
                ORDER BY c.updated_at DESC, c.id DESC
                LIMIT :limit
                OFFSET :offset
                """
            ),
            params,
        ).mappings().all()

        total = conn.execute(
            text(
                f"""
                SELECT COUNT(*)
                FROM social_comments c
                WHERE {where_sql}
                """
            ),
            params,
        ).scalar()

    return {
        "ok": True,
        "comments": [dict(r) for r in rows],
        "total": int(total or 0),
        "limit": int(limit),
        "offset": int(offset),
    }


@router.get("/api/social/comments/{comment_row_id}")
async def get_social_comment(comment_row_id: int):
    row = _load_comment_row(comment_row_id)
    if not row:
        raise HTTPException(status_code=404, detail="comment not found")

    channel = _norm_channel(str(row.get("channel") or "facebook"), default="facebook")
    root_external = str(row.get("parent_external_comment_id") or "").strip() or str(row.get("external_comment_id") or "").strip()
    if not root_external:
        root_external = str(row.get("external_comment_id") or "").strip()

    with engine.begin() as conn:
        thread = conn.execute(
            text(
                """
                SELECT
                    id,
                    channel,
                    external_comment_id,
                    parent_external_comment_id,
                    direction,
                    author_id,
                    author_name,
                    message,
                    status,
                    assigned_to,
                    created_at,
                    updated_at
                FROM social_comments
                WHERE LOWER(COALESCE(channel, 'facebook')) = :channel
                  AND (
                        external_comment_id = :root_external
                        OR parent_external_comment_id = :root_external
                  )
                ORDER BY created_at ASC, id ASC
                """
            ),
            {"channel": channel, "root_external": root_external},
        ).mappings().all()

    return {"ok": True, "comment": row, "thread": [dict(r) for r in thread]}


@router.patch("/api/social/comments/{comment_row_id}")
async def patch_social_comment(comment_row_id: int, payload: SocialCommentPatchIn):
    data = payload.model_dump(exclude_unset=True)
    if not data:
        raise HTTPException(status_code=400, detail="no fields to update")

    sets: List[str] = ["updated_at = NOW()"]
    params: Dict[str, Any] = {"id": int(comment_row_id)}

    if "status" in data:
        sets.append("status = :status")
        params["status"] = _normalize_comment_status(str(data.get("status") or ""), default="new")

    if "assigned_to" in data:
        assigned_to = str(data.get("assigned_to") or "").strip()
        sets.append("assigned_to = :assigned_to")
        params["assigned_to"] = assigned_to or None

    with engine.begin() as conn:
        row = conn.execute(
            text(
                f"""
                UPDATE social_comments
                SET {", ".join(sets)}
                WHERE id = :id
                RETURNING
                    id, channel, external_comment_id, parent_external_comment_id,
                    direction, author_id, author_name, message, status, assigned_to, created_at, updated_at
                """
            ),
            params,
        ).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="comment not found")
    return {"ok": True, "comment": dict(row)}


@router.post("/api/social/comments/{comment_row_id}/suggest")
async def suggest_social_comment_reply(comment_row_id: int, payload: SocialCommentSuggestIn):
    row = _load_comment_row(comment_row_id)
    if not row:
        raise HTTPException(status_code=404, detail="comment not found")

    suggestion = await _suggest_comment_reply(row, instructions=str(payload.instructions or ""))
    if not suggestion:
        suggestion = "Gracias por tu comentario. Te ayudamos por interno con toda la informacion."

    return {"ok": True, "suggestion": suggestion, "comment_id": int(comment_row_id)}


@router.post("/api/social/comments/{comment_row_id}/reply")
async def reply_social_comment(comment_row_id: int, payload: SocialCommentReplyIn):
    row = _load_comment_row(comment_row_id)
    if not row:
        raise HTTPException(status_code=404, detail="comment not found")

    if str(row.get("direction") or "in").strip().lower() != "in":
        raise HTTPException(status_code=400, detail="can only reply to inbound comment rows")

    channel = _norm_channel(str(row.get("channel") or "facebook"), default="facebook")
    external_comment_id = str(row.get("external_comment_id") or "").strip()
    if not external_comment_id:
        raise HTTPException(status_code=400, detail="missing external_comment_id")

    reply_text = str(payload.message or "").strip()
    if bool(payload.use_ai) and not reply_text:
        reply_text = await _suggest_comment_reply(row, instructions=str(payload.instructions or ""))
    if not reply_text:
        raise HTTPException(status_code=400, detail="reply message required")

    send = await send_comment_reply(channel=channel, comment_id=external_comment_id, text_msg=reply_text)
    if not bool(send.get("sent")):
        detail = str(send.get("reason") or send.get("whatsapp_body") or "provider_reply_failed")
        raise HTTPException(status_code=502, detail=detail[:900])

    provider_comment_id = str(send.get("provider_message_id") or send.get("wa_message_id") or "").strip()
    local_reply_id = provider_comment_id or f"manual-{int(datetime.utcnow().timestamp() * 1000)}-{external_comment_id}"
    status_after = _normalize_comment_status(payload.status_after, default="replied")

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE social_comments
                SET status = :status,
                    updated_at = NOW()
                WHERE id = :id
                """
            ),
            {"id": int(comment_row_id), "status": status_after},
        )

        conn.execute(
            text(
                """
                INSERT INTO social_comments (
                    channel,
                    network_account_id,
                    external_comment_id,
                    parent_external_comment_id,
                    post_id,
                    direction,
                    author_id,
                    author_name,
                    message,
                    status,
                    assigned_to,
                    provider_payload_json,
                    created_at,
                    updated_at
                )
                VALUES (
                    :channel,
                    :network_account_id,
                    :external_comment_id,
                    :parent_external_comment_id,
                    :post_id,
                    'out',
                    :author_id,
                    :author_name,
                    :message,
                    'sent',
                    :assigned_to,
                    CAST(:provider_payload_json AS jsonb),
                    NOW(),
                    NOW()
                )
                ON CONFLICT (channel, external_comment_id, direction)
                DO NOTHING
                """
            ),
            {
                "channel": channel,
                "network_account_id": str(row.get("network_account_id") or "").strip() or None,
                "external_comment_id": local_reply_id,
                "parent_external_comment_id": external_comment_id,
                "post_id": str(row.get("post_id") or "").strip() or None,
                "author_id": "system:manual",
                "author_name": "Asesor",
                "message": reply_text,
                "assigned_to": str(row.get("assigned_to") or "").strip() or None,
                "provider_payload_json": json.dumps(_safe_obj(send.get("provider_response")), ensure_ascii=False),
            },
        )

    updated = _load_comment_row(comment_row_id)
    return {
        "ok": True,
        "comment": updated,
        "reply_text": reply_text,
        "provider_comment_id": provider_comment_id or None,
        "send": send,
    }


@router.get("/api/facebook/webhook")
async def facebook_verify(request: Request):
    return _verify_with_token(request, _meta_token_with_fallback(FACEBOOK_VERIFY_TOKEN))


@router.post("/api/facebook/webhook")
async def facebook_receive(request: Request):
    return await _handle_meta_webhook_post(request, route_key="facebook_legacy", default_channel="facebook")


@router.get("/api/instagram/webhook")
async def instagram_verify(request: Request):
    return _verify_with_token(request, _meta_token_with_fallback(INSTAGRAM_VERIFY_TOKEN))


@router.post("/api/instagram/webhook")
async def instagram_receive(request: Request):
    return await _handle_meta_webhook_post(request, route_key="instagram_legacy", default_channel="instagram")


@router.get("/api/meta/webhook")
async def meta_verify(request: Request):
    return _verify_with_token(request, _meta_token_with_fallback(META_WEBHOOK_VERIFY_TOKEN))


@router.post("/api/meta/webhook")
async def meta_receive(request: Request):
    return await _handle_meta_webhook_post(request, route_key="meta_generic", default_channel="facebook")


@router.get("/api/meta/messenger/webhook")
async def meta_messenger_verify(request: Request):
    return _verify_with_token(request, _meta_token_with_fallback(META_MESSENGER_VERIFY_TOKEN))


@router.post("/api/meta/messenger/webhook")
async def meta_messenger_receive(request: Request):
    return await _handle_meta_webhook_post(request, route_key="meta_messenger", default_channel="facebook")


@router.get("/api/meta/page/webhook")
async def meta_page_verify(request: Request):
    return _verify_with_token(request, _meta_token_with_fallback(META_PAGE_VERIFY_TOKEN))


@router.post("/api/meta/page/webhook")
async def meta_page_receive(request: Request):
    return await _handle_meta_webhook_post(request, route_key="meta_page", default_channel="facebook")


@router.get("/api/meta/instagram/webhook")
async def meta_instagram_verify(request: Request):
    return _verify_with_token(request, _meta_token_with_fallback(INSTAGRAM_VERIFY_TOKEN))


@router.post("/api/meta/instagram/webhook")
async def meta_instagram_receive(request: Request):
    return await _handle_meta_webhook_post(request, route_key="meta_instagram", default_channel="instagram")


@router.get("/api/meta/leads/webhook")
async def meta_leads_verify(request: Request):
    return _verify_with_token(request, _meta_token_with_fallback(META_LEADS_VERIFY_TOKEN))


@router.post("/api/meta/leads/webhook")
async def meta_leads_receive(request: Request):
    return await _handle_meta_webhook_post(request, route_key="meta_leads", default_channel="facebook")


@router.get("/api/meta/ads/webhook")
async def meta_ads_verify(request: Request):
    return _verify_with_token(request, _meta_token_with_fallback(META_ADS_VERIFY_TOKEN))


@router.post("/api/meta/ads/webhook")
async def meta_ads_receive(request: Request):
    return await _handle_meta_webhook_post(request, route_key="meta_ads", default_channel="facebook")


@router.get("/api/meta/webhooks/routes")
async def meta_webhook_routes():
    return {
        "ok": True,
        "provider": "meta",
        "routes": {
            "generic": "/api/meta/webhook",
            "messenger": "/api/meta/messenger/webhook",
            "pages": "/api/meta/page/webhook",
            "instagram": "/api/meta/instagram/webhook",
            "leads": "/api/meta/leads/webhook",
            "ads": "/api/meta/ads/webhook",
            "legacy_facebook": "/api/facebook/webhook",
            "legacy_instagram": "/api/instagram/webhook",
        },
        "verify_tokens": {
            "generic": "META_WEBHOOK_VERIFY_TOKEN",
            "messenger": "META_MESSENGER_VERIFY_TOKEN",
            "pages": "META_PAGE_VERIFY_TOKEN",
            "instagram": "INSTAGRAM_VERIFY_TOKEN",
            "leads": "META_LEADS_VERIFY_TOKEN",
            "ads": "META_ADS_VERIFY_TOKEN",
        },
        "signature": {
            "header": "X-Hub-Signature-256",
            "secret_env": "META_APP_SECRET",
            "enforced": bool(META_ENFORCE_SIGNATURE),
        },
    }


@router.get("/api/tiktok/webhook")
async def tiktok_verify(request: Request):
    return _verify_with_token(request, TIKTOK_VERIFY_TOKEN)


@router.post("/api/tiktok/webhook")
async def tiktok_receive(request: Request):
    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8", errors="ignore") or "{}")
    except Exception:
        return {"ok": True, "processed": 0, "errors": 0}
    return await _process_tiktok_payload(_safe_obj(payload))
