import os
import json
import asyncio
import httpx
from datetime import datetime

from fastapi import APIRouter, Request, Response, HTTPException
from sqlalchemy import create_engine, text

router = APIRouter()

# Variables
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_TOKEN = os.getenv("WHATSAPP_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_GRAPH_VERSION = os.getenv("WHATSAPP_GRAPH_VERSION", "v20.0")
DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None

# Funciones de Envío (Client)
async def send_whatsapp_text(to_phone: str, text_msg: str):
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        return {"sent": False, "reason": "No credentials"}
    
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
    
    return {"sent": r.status_code < 400, "whatsapp": r.json() if r.status_code < 400 else r.text}

async def upload_whatsapp_media(file_bytes: bytes, mime_type: str) -> str:
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID):
        return None

    url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/media"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    files = {"file": ("upload", file_bytes, mime_type)}
    data = {"messaging_product": "whatsapp", "type": mime_type}

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, headers=headers, data=data, files=files)
    
    if r.status_code >= 400:
        print(f"Media Upload Error: {r.text}")
        return None
    return r.json().get("id")

async def send_whatsapp_media_id(to_phone: str, media_type: str, media_id: str, caption: str = ""):
    if not (WHATSAPP_TOKEN and WHATSAPP_PHONE_NUMBER_ID): return {"sent": False}
    
    url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "to": to_phone,
        "type": media_type,
        media_type: {"id": media_id}
    }
    if caption: payload[media_type]["caption"] = caption
    
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, json=payload, headers=headers)
    return {"sent": r.status_code < 400}

# Webhook Verify
@router.get("/api/whatsapp/webhook")
async def whatsapp_verify(request: Request):
    qp = request.query_params
    if qp.get("hub.mode") == "subscribe" and qp.get("hub.verify_token") == VERIFY_TOKEN:
        return Response(content=qp.get("hub.challenge"), media_type="text/plain")
    raise HTTPException(403, "Verification failed")

# Webhook Receive
def _store_in_db(phone, direction, msg_type, text_msg, wamid=None, media_id=None):
    if not engine: return
    
    # Si tenemos WAMID, verificamos duplicados antes de nada
    if wamid:
        with engine.connect() as conn:
            exists = conn.execute(text("SELECT 1 FROM messages WHERE wamid = :id"), {"id": wamid}).first()
            if exists: return # Ya existe, ignorar

    with engine.begin() as conn:
        # Upsert conversation
        conn.execute(text("""
            INSERT INTO conversations (phone, takeover, updated_at) VALUES (:phone, FALSE, NOW())
            ON CONFLICT (phone) DO UPDATE SET updated_at = EXCLUDED.updated_at
        """), {"phone": phone})

        # Insert Message
        conn.execute(text("""
            INSERT INTO messages (phone, direction, msg_type, text, wamid, media_id, created_at)
            VALUES (:phone, :direction, :msg_type, :text, :wamid, :media_id, NOW())
        """), {
            "phone": phone, "direction": direction, "msg_type": msg_type, 
            "text": text_msg, "wamid": wamid, "media_id": media_id
        })

@router.post("/api/whatsapp/webhook")
async def whatsapp_receive(request: Request):
    try:
        data = await request.json()
    except:
        return {"ok": True}

    try:
        entry = (data.get("entry") or [])[0]
        changes = (entry.get("changes") or [])[0]
        value = changes.get("value") or {}
        messages = value.get("messages") or []

        if messages:
            m = messages[0]
            phone = m.get("from")
            wamid = m.get("id") # ID ÚNICO DEL MENSAJE
            msg_type = m.get("type")
            
            text_body = ""
            media_id = None

            if msg_type == "text":
                text_body = m.get("text", {}).get("body", "")
            elif msg_type in ["image", "video", "audio", "document"]:
                media = m.get(msg_type, {})
                media_id = media.get("id")
                text_body = media.get("caption", "") # Caption si existe
            
            _store_in_db(phone, "in", msg_type, text_body, wamid, media_id)
            
    except Exception as e:
        print(f"Webhook Error: {e}")
        pass

    return {"ok": True}

# Proxy para ver imágenes/videos en el frontend
from fastapi.responses import StreamingResponse

@router.get("/api/media/proxy/{media_id}")
async def proxy_media(media_id: str):
    if not WHATSAPP_TOKEN: raise HTTPException(500)
    
    url = f"https://graph.facebook.com/{WHATSAPP_GRAPH_VERSION}/{media_id}"
    headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
    
    async with httpx.AsyncClient() as client:
        # 1. Obtener URL de descarga
        r1 = await client.get(url, headers=headers)
        if r1.status_code >= 400: raise HTTPException(404)
        dl_url = r1.json().get("url")
        
        # 2. Descargar binario
        async with client.stream("GET", dl_url, headers=headers) as r2:
            return StreamingResponse(r2.aiter_bytes(), media_type=r1.json().get("mime_type"))