from __future__ import annotations

import os
from typing import Any, Dict, Tuple

import httpx


META_GRAPH_VERSION = str(os.getenv("META_GRAPH_VERSION", "v20.0")).strip() or "v20.0"

FACEBOOK_PAGE_ID = str(os.getenv("FACEBOOK_PAGE_ID", "")).strip()
FACEBOOK_PAGE_TOKEN = str(os.getenv("FACEBOOK_PAGE_TOKEN", "")).strip()

INSTAGRAM_ACCOUNT_ID = str(os.getenv("INSTAGRAM_ACCOUNT_ID", "")).strip()
INSTAGRAM_TOKEN = str(os.getenv("INSTAGRAM_TOKEN", "")).strip()

TIKTOK_API_BASE = str(os.getenv("TIKTOK_API_BASE", "https://business-api.tiktok.com")).strip().rstrip("/")
TIKTOK_SEND_PATH = str(os.getenv("TIKTOK_SEND_PATH", "/open_api/v1.3/message/send/")).strip() or "/open_api/v1.3/message/send/"
TIKTOK_ACCESS_TOKEN = str(os.getenv("TIKTOK_ACCESS_TOKEN", "")).strip()


def _normalize_channel(channel: str) -> str:
    ch = str(channel or "").strip().lower()
    if ch in ("whatsapp", "facebook", "instagram", "tiktok"):
        return ch
    return "whatsapp"


def _extract_meta_message_id(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    direct = payload.get("message_id") or payload.get("id")
    if direct:
        return str(direct)
    messages = payload.get("messages")
    if isinstance(messages, list) and messages:
        m0 = messages[0] if isinstance(messages[0], dict) else {}
        mid = m0.get("id") or m0.get("message_id")
        if mid:
            return str(mid)
    return ""


def _extract_tiktok_message_id(payload: Any) -> str:
    if not isinstance(payload, dict):
        return ""
    direct = payload.get("message_id") or payload.get("id")
    if direct:
        return str(direct)
    data = payload.get("data")
    if isinstance(data, dict):
        nested = data.get("message_id") or data.get("id")
        if nested:
            return str(nested)
    return ""


def _meta_credentials_for_channel(channel: str) -> Tuple[str, str]:
    ch = _normalize_channel(channel)
    if ch == "facebook":
        return FACEBOOK_PAGE_ID, FACEBOOK_PAGE_TOKEN
    if ch == "instagram":
        return INSTAGRAM_ACCOUNT_ID, INSTAGRAM_TOKEN
    return "", ""


async def _post_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout_sec: float = 20.0) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=timeout_sec) as client:
        r = await client.post(url, json=payload, headers=headers)

    if r.status_code >= 400:
        return {
            "ok": False,
            "status_code": int(r.status_code),
            "raw": r.text[:1200],
            "json": {},
        }

    try:
        body = r.json()
    except Exception:
        body = {}
    return {
        "ok": True,
        "status_code": int(r.status_code),
        "raw": r.text[:1200],
        "json": body if isinstance(body, dict) else {},
    }


async def send_channel_text(channel: str, to: str, text_msg: str) -> Dict[str, Any]:
    ch = _normalize_channel(channel)
    to_id = str(to or "").strip()
    body = str(text_msg or "").strip()

    if not to_id:
        return {"saved": True, "sent": False, "reason": "recipient_required", "channel": ch}
    if not body:
        return {"saved": True, "sent": False, "reason": "text_required", "channel": ch}

    if ch == "whatsapp":
        from app.routes.whatsapp import send_whatsapp_text

        out = await send_whatsapp_text(to_id, body)
        if isinstance(out, dict):
            out["channel"] = "whatsapp"
        return out

    if ch in ("facebook", "instagram"):
        account_id, token = _meta_credentials_for_channel(ch)
        if not account_id or not token:
            return {
                "saved": True,
                "sent": False,
                "reason": f"{ch.upper()} credentials not set",
                "channel": ch,
            }

        url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{account_id}/messages"
        payload = {
            "recipient": {"id": to_id},
            "message": {"text": body},
            "messaging_type": "RESPONSE",
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        resp = await _post_json(url, payload, headers)
        if not resp.get("ok"):
            return {
                "saved": True,
                "sent": False,
                "channel": ch,
                "whatsapp_status": resp.get("status_code"),
                "whatsapp_body": resp.get("raw"),
            }
        mid = _extract_meta_message_id(resp.get("json"))
        return {
            "saved": True,
            "sent": True,
            "channel": ch,
            "wa_message_id": mid,
            "provider_message_id": mid,
            "provider_response": resp.get("json"),
        }

    if ch == "tiktok":
        if not TIKTOK_API_BASE or not TIKTOK_ACCESS_TOKEN:
            return {
                "saved": True,
                "sent": False,
                "reason": "TIKTOK_API_BASE / TIKTOK_ACCESS_TOKEN not set",
                "channel": ch,
            }

        path = TIKTOK_SEND_PATH if TIKTOK_SEND_PATH.startswith("/") else f"/{TIKTOK_SEND_PATH}"
        url = f"{TIKTOK_API_BASE}{path}"
        payload = {
            "recipient_id": to_id,
            "text": body,
        }
        headers = {
            "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        resp = await _post_json(url, payload, headers)
        if not resp.get("ok"):
            return {
                "saved": True,
                "sent": False,
                "channel": ch,
                "whatsapp_status": resp.get("status_code"),
                "whatsapp_body": resp.get("raw"),
            }
        mid = _extract_tiktok_message_id(resp.get("json"))
        return {
            "saved": True,
            "sent": True,
            "channel": ch,
            "wa_message_id": mid,
            "provider_message_id": mid,
            "provider_response": resp.get("json"),
        }

    return {"saved": True, "sent": False, "reason": "channel_not_supported", "channel": ch}


async def send_channel_media(
    *,
    channel: str,
    to: str,
    media_type: str,
    media_id: str = "",
    media_url: str = "",
    caption: str = "",
) -> Dict[str, Any]:
    ch = _normalize_channel(channel)
    to_id = str(to or "").strip()
    mtype = str(media_type or "").strip().lower()
    mid = str(media_id or "").strip()
    murl = str(media_url or "").strip()
    cap = str(caption or "").strip()

    if not to_id:
        return {"saved": True, "sent": False, "reason": "recipient_required", "channel": ch}

    if ch == "whatsapp":
        if not mid:
            return {"saved": True, "sent": False, "reason": "media_id_required", "channel": ch}
        from app.routes.whatsapp import send_whatsapp_media_id

        out = await send_whatsapp_media_id(to_id, mtype, mid, cap)
        if isinstance(out, dict):
            out["channel"] = "whatsapp"
        return out

    if ch in ("facebook", "instagram"):
        account_id, token = _meta_credentials_for_channel(ch)
        if not account_id or not token:
            return {
                "saved": True,
                "sent": False,
                "reason": f"{ch.upper()} credentials not set",
                "channel": ch,
            }
        if not murl and not mid:
            return {
                "saved": True,
                "sent": False,
                "reason": "media_url_or_media_id_required",
                "channel": ch,
            }

        attach_type = "file" if mtype in ("document", "file") else mtype
        if attach_type not in ("image", "video", "audio", "file"):
            attach_type = "file"

        payload_data: Dict[str, Any] = {"is_reusable": True}
        if murl:
            payload_data["url"] = murl
        elif mid:
            payload_data["attachment_id"] = mid

        url = f"https://graph.facebook.com/{META_GRAPH_VERSION}/{account_id}/messages"
        payload = {
            "recipient": {"id": to_id},
            "message": {
                "attachment": {
                    "type": attach_type,
                    "payload": payload_data,
                }
            },
            "messaging_type": "RESPONSE",
        }
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
        media_resp = await _post_json(url, payload, headers)
        if not media_resp.get("ok"):
            return {
                "saved": True,
                "sent": False,
                "channel": ch,
                "whatsapp_status": media_resp.get("status_code"),
                "whatsapp_body": media_resp.get("raw"),
            }

        media_mid = _extract_meta_message_id(media_resp.get("json"))

        if cap:
            cap_resp = await send_channel_text(ch, to_id, cap)
            return {
                "saved": True,
                "sent": True,
                "channel": ch,
                "wa_message_id": media_mid or str(cap_resp.get("wa_message_id") or ""),
                "provider_message_id": media_mid or str(cap_resp.get("provider_message_id") or ""),
                "provider_response": media_resp.get("json"),
                "caption_sent": bool(cap_resp.get("sent")),
                "caption_response": cap_resp,
            }

        return {
            "saved": True,
            "sent": True,
            "channel": ch,
            "wa_message_id": media_mid,
            "provider_message_id": media_mid,
            "provider_response": media_resp.get("json"),
        }

    if ch == "tiktok":
        if not TIKTOK_API_BASE or not TIKTOK_ACCESS_TOKEN:
            return {
                "saved": True,
                "sent": False,
                "reason": "TIKTOK_API_BASE / TIKTOK_ACCESS_TOKEN not set",
                "channel": ch,
            }
        if not murl and not mid:
            return {
                "saved": True,
                "sent": False,
                "reason": "media_url_or_media_id_required",
                "channel": ch,
            }

        path = TIKTOK_SEND_PATH if TIKTOK_SEND_PATH.startswith("/") else f"/{TIKTOK_SEND_PATH}"
        url = f"{TIKTOK_API_BASE}{path}"
        payload = {
            "recipient_id": to_id,
            "media_type": mtype or "file",
            "media_url": murl,
            "media_id": mid,
            "caption": cap,
        }
        headers = {
            "Authorization": f"Bearer {TIKTOK_ACCESS_TOKEN}",
            "Content-Type": "application/json",
        }
        resp = await _post_json(url, payload, headers)
        if not resp.get("ok"):
            return {
                "saved": True,
                "sent": False,
                "channel": ch,
                "whatsapp_status": resp.get("status_code"),
                "whatsapp_body": resp.get("raw"),
            }
        mid_value = _extract_tiktok_message_id(resp.get("json"))
        return {
            "saved": True,
            "sent": True,
            "channel": ch,
            "wa_message_id": mid_value,
            "provider_message_id": mid_value,
            "provider_response": resp.get("json"),
        }

    return {"saved": True, "sent": False, "reason": "channel_not_supported", "channel": ch}
