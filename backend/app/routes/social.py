from __future__ import annotations

import json
import os
from typing import Any, Dict, Iterable, List, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from sqlalchemy import text

from app.db import engine

router = APIRouter()


META_VERIFY_TOKEN = str(os.getenv("META_VERIFY_TOKEN", "")).strip()
FACEBOOK_VERIFY_TOKEN = str(os.getenv("FACEBOOK_VERIFY_TOKEN", META_VERIFY_TOKEN)).strip()
INSTAGRAM_VERIFY_TOKEN = str(os.getenv("INSTAGRAM_VERIFY_TOKEN", META_VERIFY_TOKEN)).strip()
TIKTOK_VERIFY_TOKEN = str(os.getenv("TIKTOK_VERIFY_TOKEN", "")).strip()


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


@router.get("/api/facebook/webhook")
async def facebook_verify(request: Request):
    return _verify_with_token(request, FACEBOOK_VERIFY_TOKEN)


@router.post("/api/facebook/webhook")
async def facebook_receive(request: Request):
    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8", errors="ignore") or "{}")
    except Exception:
        return {"ok": True, "processed": 0, "errors": 0}
    return await _process_meta_payload(_safe_obj(payload), default_channel="facebook")


@router.get("/api/instagram/webhook")
async def instagram_verify(request: Request):
    return _verify_with_token(request, INSTAGRAM_VERIFY_TOKEN)


@router.post("/api/instagram/webhook")
async def instagram_receive(request: Request):
    raw = await request.body()
    try:
        payload = json.loads(raw.decode("utf-8", errors="ignore") or "{}")
    except Exception:
        return {"ok": True, "processed": 0, "errors": 0}
    return await _process_meta_payload(_safe_obj(payload), default_channel="instagram")


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
