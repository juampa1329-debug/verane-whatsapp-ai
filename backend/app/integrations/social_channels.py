from __future__ import annotations

import os
from typing import Any, Dict, Tuple

import httpx


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


def _env_first(*names: str) -> str:
    for name in names:
        value = str(os.getenv(name, "")).strip()
        if value:
            return value
    return ""


def _meta_graph_version() -> str:
    return _env_first("META_GRAPH_VERSION", "FACEBOOK_GRAPH_VERSION", "META_API_VERSION") or "v20.0"


def _meta_credentials_for_channel(channel: str) -> Tuple[str, str]:
    ch = _normalize_channel(channel)
    if ch == "facebook":
        return (
            _env_first("FACEBOOK_PAGE_ID", "META_PAGE_ID", "META_MESSENGER_PAGE_ID", "MESSENGER_PAGE_ID"),
            _env_first(
                "FACEBOOK_PAGE_TOKEN",
                "META_PAGE_TOKEN",
                "META_MESSENGER_PAGE_TOKEN",
                "PAGE_ACCESS_TOKEN",
                "META_ACCESS_TOKEN",
            ),
        )
    if ch == "instagram":
        return (
            _env_first(
                "INSTAGRAM_ACCOUNT_ID",
                "META_INSTAGRAM_ACCOUNT_ID",
                "INSTAGRAM_BUSINESS_ACCOUNT_ID",
                "IG_ACCOUNT_ID",
            ),
            _env_first(
                "INSTAGRAM_TOKEN",
                "META_INSTAGRAM_TOKEN",
                "FACEBOOK_PAGE_TOKEN",
                "META_PAGE_TOKEN",
                "PAGE_ACCESS_TOKEN",
                "META_ACCESS_TOKEN",
            ),
        )
    return "", ""


def _meta_missing_reason(channel: str, account_id: str, token: str) -> str:
    ch = _normalize_channel(channel)
    if ch == "facebook":
        if token:
            return "FACEBOOK credentials not set"
        return "FACEBOOK credentials not set (missing token: FACEBOOK_PAGE_TOKEN or META_PAGE_TOKEN)"
    if ch == "instagram":
        missing = []
        if not account_id:
            missing.append("INSTAGRAM_ACCOUNT_ID")
        if not token:
            missing.append("INSTAGRAM_TOKEN/FACEBOOK_PAGE_TOKEN")
        if missing:
            return f"INSTAGRAM credentials not set (missing: {', '.join(missing)})"
        return "INSTAGRAM credentials not set"
    return f"{ch.upper()} credentials not set"


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
        if ch == "facebook":
            if not token:
                return {
                    "saved": True,
                    "sent": False,
                    "reason": _meta_missing_reason(ch, account_id, token),
                    "channel": ch,
                }
            account_path = account_id or "me"
        else:
            if not account_id or not token:
                return {
                    "saved": True,
                    "sent": False,
                    "reason": _meta_missing_reason(ch, account_id, token),
                    "channel": ch,
                }
            account_path = account_id

        url = f"https://graph.facebook.com/{_meta_graph_version()}/{account_path}/messages"
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


async def send_comment_reply(channel: str, comment_id: str, text_msg: str) -> Dict[str, Any]:
    ch = _normalize_channel(channel)
    cid = str(comment_id or "").strip()
    body = str(text_msg or "").strip()

    if ch not in ("facebook", "instagram"):
        return {
            "saved": True,
            "sent": False,
            "reason": "channel_not_supported_for_comment_reply",
            "channel": ch,
        }
    if not cid:
        return {"saved": True, "sent": False, "reason": "comment_id_required", "channel": ch}
    if not body:
        return {"saved": True, "sent": False, "reason": "text_required", "channel": ch}

    fb_token = _env_first(
        "FACEBOOK_PAGE_TOKEN",
        "META_PAGE_TOKEN",
        "META_MESSENGER_PAGE_TOKEN",
        "PAGE_ACCESS_TOKEN",
        "META_ACCESS_TOKEN",
    )
    ig_token = _env_first("INSTAGRAM_TOKEN", "META_INSTAGRAM_TOKEN")
    token = fb_token if ch == "facebook" else (ig_token or fb_token)
    if not token:
        return {
            "saved": True,
            "sent": False,
            "reason": "missing_meta_token_for_comment_reply",
            "channel": ch,
        }

    endpoint = "replies" if ch == "instagram" else "comments"
    url = f"https://graph.facebook.com/{_meta_graph_version()}/{cid}/{endpoint}"
    params = {"access_token": token}
    payload = {"message": body}

    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(url, params=params, data=payload)

    if r.status_code >= 400:
        return {
            "saved": True,
            "sent": False,
            "channel": ch,
            "whatsapp_status": int(r.status_code),
            "whatsapp_body": r.text[:1200],
        }

    try:
        data = r.json()
    except Exception:
        data = {}

    reply_id = str((data or {}).get("id") or "").strip()
    return {
        "saved": True,
        "sent": True,
        "channel": ch,
        "wa_message_id": reply_id,
        "provider_message_id": reply_id,
        "provider_response": data if isinstance(data, dict) else {},
    }


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
        if ch == "facebook":
            if not token:
                return {
                    "saved": True,
                    "sent": False,
                    "reason": _meta_missing_reason(ch, account_id, token),
                    "channel": ch,
                }
            account_path = account_id or "me"
        else:
            if not account_id or not token:
                return {
                    "saved": True,
                    "sent": False,
                    "reason": _meta_missing_reason(ch, account_id, token),
                    "channel": ch,
                }
            account_path = account_id
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

        url = f"https://graph.facebook.com/{_meta_graph_version()}/{account_path}/messages"
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
