import os
import json
import asyncio
import httpx
from datetime import datetime
from app.db import engine
from sqlalchemy import create_engine, text




from fastapi import APIRouter, Request, Response, HTTPException


router = APIRouter()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
FORWARD_URLS = os.getenv("WHATSAPP_FORWARD_URLS", "")
FORWARD_ENABLED = os.getenv("WHATSAPP_FORWARD_ENABLED", "true").lower() == "true"
FORWARD_TIMEOUT = float(os.getenv("WHATSAPP_FORWARD_TIMEOUT", "3"))
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_GRAPH_VERSION = os.getenv("WHATSAPP_GRAPH_VERSION", "v20.0")


DATABASE_URL = os.getenv("DATABASE_URL", "")
engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None



async def send_whatsapp_text(to_phone: str, text_msg: str):
    # Si no está configurado WhatsApp, no explotes: responde "sent=false"
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        return {"saved": True, "sent": False, "reason": "WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID not set"}

    url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": "text",
        "text": {"body": text_msg},
    }

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(url, json=payload, headers=headers)

    # Si WhatsApp responde error, devuelve detalle (pero no 500 “ciego”)
    if r.status_code >= 400:
        return {"saved": True, "sent": False, "whatsapp_status": r.status_code, "whatsapp_body": r.text}

    return {"saved": True, "sent": True, "whatsapp": r.json()}

async def upload_whatsapp_media(file_bytes: bytes, mime_type: str) -> str:
    """
    Sube un archivo binario a WhatsApp Media API y devuelve media_id.
    """
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        raise HTTPException(status_code=500, detail="WhatsApp credentials not set")

    url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/media"

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
    }

    # multipart/form-data
    files = {
        "file": ("upload", file_bytes, mime_type),
    }
    data = {
        "messaging_product": "whatsapp",
        "type": mime_type,
    }

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
    """
    Envía media a WhatsApp usando media_id para que aparezca como adjunto real.
    media_type: image | video | audio | document
    """
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

    # caption aplica a image/video/document (audio normalmente no)
    if caption and media_type in ("image", "video", "document"):
        payload[media_type]["caption"] = caption

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload, headers=headers)

    if r.status_code >= 400:
        return {"saved": True, "sent": False, "whatsapp_status": r.status_code, "whatsapp_body": r.text}

    return {"saved": True, "sent": True, "whatsapp": r.json()}


async def send_whatsapp_media(to_phone: str, media_type: str, media_url: str, caption: str = ""):
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        return {"saved": True, "sent": False, "reason": "WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID not set"}

    media_type = (media_type or "").strip().lower()
    if media_type not in ("image", "video", "document"):
        return {"saved": True, "sent": False, "reason": f"Unsupported media_type: {media_type}"}

    if not media_url:
        return {"saved": True, "sent": False, "reason": "media_url is required"}

    url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"

    # WhatsApp descarga el archivo desde este link (debe ser URL pública https)
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": media_type,
        media_type: {
            "link": media_url
        }
    }

    if caption and media_type in ("image", "video", "document"):
        payload[media_type]["caption"] = caption

    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload, headers=headers)

    if r.status_code >= 400:
        return {"saved": True, "sent": False, "whatsapp_status": r.status_code, "whatsapp_body": r.text}

    return {"saved": True, "sent": True, "whatsapp": r.json()}


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
    # Permite separar por coma y limpiar espacios
    urls = []
    for part in (FORWARD_URLS or "").split(","):
        u = (part or "").strip()
        if u:
            urls.append(u)
    return urls


async def _forward_to_targets(raw_body: bytes):
    """
    Fanout múltiple: reenvía el webhook a N destinos en background.
    No bloquea el ACK a WhatsApp.
    """
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
            # Silencioso: no queremos romper el webhook por un destino caído
            return

    async with httpx.AsyncClient(timeout=FORWARD_TIMEOUT) as client:
        await asyncio.gather(*[_post_one(client, u) for u in urls])



def _store_in_db(phone: str, direction: str, msg_type: str, text_msg: str, media_id: str | None = None):

    if not  phone:
        return
    with engine.begin() as conn:
        # upsert conversation
        conn.execute(text("""
            INSERT INTO messages (phone, direction, msg_type, text, media_id, created_at)
            VALUES (:phone, :direction, :msg_type, :text, :media_id, :created_at)
            ON CONFLICT (phone) DO UPDATE SET updated_at = EXCLUDED.updated_at
        """), {"phone": phone, "updated_at": datetime.utcnow()})

        # insert message
        conn.execute(text("""
            INSERT INTO messages (phone, direction, msg_type, text, created_at)
            VALUES (:phone, :direction, :msg_type, :text, :created_at)
        """), {
            "phone": phone,
            "direction": direction,
            "msg_type": msg_type or "text",
            "text": text_msg or "",
            "created_at": datetime.utcnow(),
            "media_id": media_id,

        })



@router.post("/api/whatsapp/webhook")
async def whatsapp_receive(request: Request):
    raw = await request.body()
    print("✅ WEBHOOK HIT:", raw[:200])
    print("HEADERS:", dict(request.headers))


    # 1) ACK rápido + forward en background
    asyncio.create_task(_forward_to_targets(raw))


    # 2) Parse + store (sin romper si cambia el payload)
    try:
        data = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        return {"ok": True}

    try:
        entry = (data.get("entry") or [])[0]
        change = (entry.get("changes") or [])[0]
        value = change.get("value") or {}
                # ✅ 0) Status updates (DELIVERED / FAILED / READ)
        statuses = value.get("statuses") or []
        if statuses:
            s = statuses[0]
            print("WA_STATUS:", json.dumps(s, ensure_ascii=False))

            # Opcional: si falla, imprime el error completo
            if s.get("status") == "failed":
                print("WA_STATUS_FAILED:", json.dumps(s, ensure_ascii=False))


        # WhatsApp messages
        messages = value.get("messages") or []
        if messages:
            m = messages[0]
            phone = m.get("from")
            msg_type = (m.get("type") or "text").strip().lower()

            text_msg = ""
            if msg_type == "text":
                text_msg = (m.get("text") or {}).get("body", "") or ""
            text_msg = ""
            media_id = None

            if msg_type == "text":
                text_msg = (m.get("text") or {}).get("body", "") or ""

            elif msg_type in ("image", "video", "audio", "document"):
                media_obj = m.get(msg_type) or {}
                media_id = media_obj.get("id")
                caption = media_obj.get("caption") or ""
                text_msg = caption or f"[{msg_type}]"

            else:
                text_msg = f"[{msg_type}]"

            _store_in_db(
                phone=phone,
                direction="in",
                msg_type=msg_type,
                text_msg=text_msg,
                media_id=media_id
            )

    except Exception:
        # no rompemos el webhook por payloads raros (statuses, etc.)
        pass

    return {"ok": True}

from fastapi.responses import StreamingResponse

@router.get("/api/media/proxy/{media_id}")
async def proxy_media(media_id: str):
    """
    Devuelve el binario del media_id usando Graph API.
    Sirve para previsualizar audio/video/imagen/documento en el dashboard.
    """
    if not (WHATSAPP_TOKEN and WHATSAPP_GRAPH_VERSION):
        raise HTTPException(status_code=500, detail="WHATSAPP_TOKEN not configured")

    # 1) Obtener URL temporal del media
    meta_url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}

    async with httpx.AsyncClient(timeout=20) as client:
        r_meta = await client.get(meta_url, headers=headers)
        if r_meta.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Graph meta failed: {r_meta.status_code} {r_meta.text}")

        meta = r_meta.json()
        dl_url = meta.get("url")
        ct = meta.get("mime_type") or "application/octet-stream"
        if not dl_url:
            raise HTTPException(status_code=502, detail=f"No url in meta: {meta}")

        # 2) Descargar el binario y streamearlo al frontend
        r_bin = await client.get(dl_url, headers=headers)
        if r_bin.status_code >= 400:
            raise HTTPException(status_code=502, detail=f"Graph download failed: {r_bin.status_code} {r_bin.text}")

        return StreamingResponse(iter([r_bin.content]), media_type=ct)

