from __future__ import annotations

import hashlib
import hmac
import json
import os
from typing import Any, Dict, Iterable, List, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import text

from app.db import engine

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
    processed = 0
    errors = 0

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
            processed += 1
        except Exception:
            errors += 1

    return {"ok": True, "channel": channel, "processed": processed, "errors": errors}


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
