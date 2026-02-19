import os
import json
import asyncio
import httpx
import re
from datetime import datetime
from typing import Optional, Tuple, Dict, Any

from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text

from app.db import engine  # ✅ usa SOLO este engine

router = APIRouter()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
FORWARD_URLS = os.getenv("WHATSAPP_FORWARD_URLS", "")
FORWARD_ENABLED = os.getenv("WHATSAPP_FORWARD_ENABLED", "true").lower() == "true"
FORWARD_TIMEOUT = float(os.getenv("WHATSAPP_FORWARD_TIMEOUT", "3"))

WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_GRAPH_VERSION = os.getenv("WHATSAPP_GRAPH_VERSION", "v20.0")


# =========================================================
# Settings helpers (ai_settings)
# =========================================================

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


# =========================================================
# WhatsApp utils
# =========================================================

def _extract_wa_message_id(resp_json: dict) -> str | None:
    try:
        msgs = resp_json.get("messages") or []
        if msgs and isinstance(msgs, list):
            return (msgs[0] or {}).get("id")
    except Exception:
        pass
    return None


async def send_whatsapp_text(to_phone: str, text_msg: str):
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        return {"saved": True, "sent": False, "reason": "WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID not set"}

    url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text_msg},
    }
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload, headers=headers)

    if r.status_code >= 400:
        return {"saved": True, "sent": False, "whatsapp_status": r.status_code, "whatsapp_body": r.text}

    j = r.json()
    return {"saved": True, "sent": True, "wa_message_id": _extract_wa_message_id(j), "whatsapp": j}


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


async def send_whatsapp_text_humanized(to_phone: str, text_msg: str) -> dict:
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        return {"saved": True, "sent": False, "reason": "WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID not set"}

    s = _get_ai_send_settings()
    max_chars = int(s.get("reply_chunk_chars") or 480)
    reply_delay = int(s.get("reply_delay_ms") or 900) / 1000.0
    typing_delay = int(s.get("typing_delay_ms") or 450) / 1000.0

    chunks = _split_long_text(text_msg or "", max_chars=max_chars)
    if not chunks:
        chunks = [""]

    wa_ids: list[str] = []
    last_resp: dict = {"saved": True, "sent": False, "reason": "no chunks"}

    if typing_delay > 0:
        await asyncio.sleep(typing_delay)

    for idx, chunk in enumerate(chunks):
        last_resp = await send_whatsapp_text(to_phone, chunk)
        if isinstance(last_resp, dict) and last_resp.get("sent") is True:
            mid = last_resp.get("wa_message_id")
            if mid:
                wa_ids.append(str(mid))

        if idx < len(chunks) - 1 and reply_delay > 0:
            await asyncio.sleep(reply_delay)

    last_resp["chunks_sent"] = len(chunks)
    last_resp["chunk_message_ids"] = wa_ids
    last_resp["humanized"] = True
    last_resp["settings_used"] = {
        "reply_chunk_chars": max_chars,
        "reply_delay_ms": int(reply_delay * 1000),
        "typing_delay_ms": int(typing_delay * 1000),
    }
    return last_resp


async def upload_whatsapp_media(file_bytes: bytes, mime_type: str) -> str:
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        raise HTTPException(status_code=500, detail="WhatsApp credentials not set")

    url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    files = {"file": ("upload", file_bytes, mime_type)}
    data = {"messaging_product": "whatsapp", "type": mime_type}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, data=data, files=files)

    if r.status_code >= 400:
        raise HTTPException(status_code=500, detail=f"Media upload failed: {r.status_code} {r.text}")

    j = r.json()
    media_id = j.get("id")
    if not media_id:
        raise HTTPException(status_code=500, detail=f"No media id returned: {j}")

    return media_id


async def send_whatsapp_media_id(to_phone: str, media_type: str, media_id: str, caption: str = ""):
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        return {"saved": True, "sent": False, "reason": "WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID not set"}

    media_type = (media_type or "").strip().lower()
    if media_type not in ("image", "video", "audio", "document"):
        return {"saved": True, "sent": False, "reason": f"Unsupported media_type: {media_type}"}

    url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": media_type,
        media_type: {"id": media_id}
    }

    if caption and media_type in ("image", "video", "document"):
        payload[media_type]["caption"] = caption

    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=payload, headers=headers)

    if r.status_code >= 400:
        return {"saved": True, "sent": False, "whatsapp_status": r.status_code, "whatsapp_body": r.text}

    j = r.json()
    return {"saved": True, "sent": True, "wa_message_id": _extract_wa_message_id(j), "whatsapp": j}


# =========================================================
# ✅ Download media bytes from WhatsApp
# =========================================================

async def get_whatsapp_media_metadata(media_id: str) -> dict:
    if not WHATSAPP_TOKEN:
        raise HTTPException(status_code=500, detail="WHATSAPP_TOKEN not configured")

    meta_url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(meta_url, headers=headers)

    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Graph meta failed: {r.status_code} {r.text[:900]}")

    return r.json() or {}


async def download_whatsapp_media_bytes(media_id: str) -> tuple[bytes, str]:
    """
    Returns (bytes, mime_type).
    """
    meta = await get_whatsapp_media_metadata(media_id)
    dl_url = meta.get("url")
    ct = (meta.get("mime_type") or "application/octet-stream").split(";")[0].strip()

    if not dl_url:
        raise HTTPException(status_code=502, detail=f"No url in meta: {str(meta)[:400]}")

    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    async with httpx.AsyncClient(timeout=30) as client:
        r_bin = await client.get(dl_url, headers=headers)

    if r_bin.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Graph download failed: {r_bin.status_code} {r_bin.text[:900]}")

    return (r_bin.content or b""), ct


@router.get("/api/whatsapp/webhook")
async def whatsapp_verify(request: Request):
    qp = request.query_params
    mode = qp.get("hub.mode")
    token = qp.get("hub.verify_token")
    challenge = qp.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN and challenge is not None:
        return Response(content=str(challenge), media_type="text/plain")

    raise HTTPException(status_code=403, detail="Verification failed")


def _parse_forward_urls() -> list[str]:
    urls = []
    for part in (FORWARD_URLS or "").split(","):
        u = (part or "").strip()
        if u:
            urls.append(u)
    return urls


async def _forward_to_targets(raw_body: bytes):
    if not FORWARD_ENABLED:
        return
    urls = _parse_forward_urls()
    if not urls:
        return

    headers = {"Content-Type": "application/json", "X-Verane-Forwarded": "1"}

    async def _post_one(client: httpx.AsyncClient, url: str):
        try:
            await client.post(url, content=raw_body, headers=headers)
        except Exception:
            return

    async with httpx.AsyncClient(timeout=FORWARD_TIMEOUT) as client:
        await asyncio.gather(*[_post_one(client, u) for u in urls])


def _update_status_in_db(status_obj: dict):
    wa_id = status_obj.get("id")
    st = (status_obj.get("status") or "").lower().strip()
    ts = status_obj.get("timestamp")

    if not wa_id or not st:
        return

    dt = None
    try:
        if ts:
            dt = datetime.utcfromtimestamp(int(ts))
    except Exception:
        dt = None

    wa_error = ""
    if st == "failed":
        try:
            errs = status_obj.get("errors") or []
            if errs and isinstance(errs, list):
                wa_error = json.dumps(errs[0], ensure_ascii=False)[:900]
        except Exception:
            wa_error = "failed"

    with engine.begin() as conn:
        if st == "delivered":
            conn.execute(text("""
                UPDATE messages
                SET wa_status='delivered',
                    wa_ts_delivered = COALESCE(wa_ts_delivered, :dt)
                WHERE wa_message_id = :wa_id
            """), {"wa_id": wa_id, "dt": dt or datetime.utcnow()})

        elif st == "read":
            conn.execute(text("""
                UPDATE messages
                SET wa_status='read',
                    wa_ts_read = COALESCE(wa_ts_read, :dt)
                WHERE wa_message_id = :wa_id
            """), {"wa_id": wa_id, "dt": dt or datetime.utcnow()})

        elif st == "failed":
            conn.execute(text("""
                UPDATE messages
                SET wa_status='failed',
                    wa_error = :wa_error
                WHERE wa_message_id = :wa_id
            """), {"wa_id": wa_id, "wa_error": wa_error or "failed"})

        elif st == "sent":
            conn.execute(text("""
                UPDATE messages
                SET wa_status='sent',
                    wa_ts_sent = COALESCE(wa_ts_sent, :dt)
                WHERE wa_message_id = :wa_id
            """), {"wa_id": wa_id, "dt": dt or datetime.utcnow()})


def _extract_incoming(m: dict) -> Tuple[str, str, str, Optional[str], Optional[str]]:
    """
    Returns:
      (original_msg_type, effective_msg_type, text_msg, media_id, mime_type)

    - original_msg_type: el tipo real (audio/image/video/document/text/etc.)
    - effective_msg_type: "text" si hay texto útil; si no, el original.
    """
    original_type = (m.get("type") or "text").strip().lower()
    text_msg = ""
    media_id = None
    mime_type = None

    if original_type == "text":
        text_msg = (m.get("text") or {}).get("body", "") or ""

    elif original_type == "interactive":
        inter = m.get("interactive") or {}
        lr = inter.get("list_reply") or {}
        br = inter.get("button_reply") or {}
        text_msg = (
            lr.get("title") or lr.get("description") or lr.get("id") or
            br.get("title") or br.get("id") or ""
        ) or ""

    elif original_type == "button":
        btn = m.get("button") or {}
        text_msg = (btn.get("text") or btn.get("payload") or "") or ""

    elif original_type in ("image", "video", "audio", "document"):
        media_obj = m.get(original_type) or {}
        media_id = media_obj.get("id")
        text_msg = (media_obj.get("caption") or "") or ""

        # WhatsApp a veces manda mime_type dentro del objeto (no siempre)
        mime_type = (media_obj.get("mime_type") or "").strip() or None

    else:
        text_msg = ""

    text_msg = (text_msg or "").strip()
    effective_type = "text" if text_msg else original_type
    return original_type, effective_type, text_msg, media_id, mime_type


async def _ingest_internal(
    phone: str,
    msg_type: str,
    text_msg: str,
    media_id: Optional[str] = None,
    mime_type: Optional[str] = None,
):
    """
    Llama el pipeline único (/api/messages/ingest) dentro del mismo proceso.
    """
    try:
        from app.main import ingest, IngestMessage  # type: ignore

        payload = IngestMessage(
            phone=phone or "",
            direction="in",
            msg_type=msg_type or "text",
            text=text_msg or "",
            media_id=media_id,
            mime_type=mime_type,
        )
        await ingest(payload)
    except Exception as e:
        print("INGEST_INTERNAL_ERROR:", str(e)[:300])


@router.post("/api/whatsapp/webhook")
async def whatsapp_receive(request: Request):
    raw = await request.body()
    print("WA_WEBHOOK_RAW:", raw.decode("utf-8"))

    if request.headers.get("X-Verane-Forwarded") != "1":
        asyncio.create_task(_forward_to_targets(raw))

    try:
        data = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        return {"ok": True}

    try:
        entry = (data.get("entry") or [])[0]
        change = (entry.get("changes") or [])[0]
        value = change.get("value") or {}

        # 1) Status updates -> ACTUALIZA DB
        statuses = value.get("statuses") or []
        for s in statuses:
            _update_status_in_db(s)

        # 2) Mensajes entrantes -> pasan por ingest (pipeline único)
        messages = value.get("messages") or []
        for m in messages:
            phone = (m.get("from") or "").strip()
            if not phone:
                continue

            original_type, eff_type, text_msg, media_id, mime_type = _extract_incoming(m)

            # ✅ IMPORTANTE:
            # - Si hay caption/botón/etc: eff_type="text", pero AÚN enviamos media_id (si existe)
            # - Si NO hay texto: eff_type=audio/image/etc y media_id para multimodal en main.py
            await _ingest_internal(
                phone=phone,
                msg_type=eff_type,
                text_msg=text_msg or "",
                media_id=media_id,
                mime_type=mime_type,
            )

    except Exception as e:
        print("WEBHOOK_ERROR:", str(e))

    return {"ok": True}


@router.get("/api/media/proxy/{media_id}")
async def proxy_media(media_id: str):
    content, ct = await download_whatsapp_media_bytes(media_id)
    return StreamingResponse(iter([content]), media_type=ct)
