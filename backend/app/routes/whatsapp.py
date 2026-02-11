import os
import json
import asyncio
import httpx
from datetime import datetime

from fastapi import APIRouter, Request, Response, HTTPException
from sqlalchemy import create_engine, text

router = APIRouter()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
FORWARD_URL = os.getenv("WHATSAPP_FORWARD_URL", "")
FORWARD_ENABLED = os.getenv("WHATSAPP_FORWARD_ENABLED", "true").lower() == "true"
FORWARD_TIMEOUT = float(os.getenv("WHATSAPP_FORWARD_TIMEOUT", "4"))

DATABASE_URL = os.getenv("DATABASE_URL", "")
engine = create_engine(DATABASE_URL, pool_pre_ping=True) if DATABASE_URL else None


@router.get("/api/whatsapp/webhook")
async def whatsapp_verify(request: Request):
    qp = request.query_params
    mode = qp.get("hub.mode")
    token = qp.get("hub.verify_token")
    challenge = qp.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN and challenge is not None:
        return Response(content=str(challenge), media_type="text/plain")

    raise HTTPException(status_code=403, detail="Verification failed")


async def _forward_to_sellerchat(raw_body: bytes):
    if not (FORWARD_ENABLED and FORWARD_URL):
        return
    headers = {"Content-Type": "application/json", "X-Verane-Forwarded": "1"}
    async with httpx.AsyncClient(timeout=FORWARD_TIMEOUT) as client:
        await client.post(FORWARD_URL, content=raw_body, headers=headers)


def _store_in_db(phone: str, direction: str, msg_type: str, text_msg: str):
    if not (engine and phone):
        return
    with engine.begin() as conn:
        # upsert conversation
        conn.execute(text("""
            INSERT INTO conversations (phone, takeover, updated_at)
            VALUES (:phone, FALSE, :updated_at)
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
        })


@router.post("/api/whatsapp/webhook")
async def whatsapp_receive(request: Request):
    raw = await request.body()

    # 1) ACK rápido + forward en background
    asyncio.create_task(_forward_to_sellerchat(raw))

    # 2) Parse + store (sin romper si cambia el payload)
    try:
        data = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        return {"ok": True}

    try:
        entry = (data.get("entry") or [])[0]
        change = (entry.get("changes") or [])[0]
        value = change.get("value") or {}

        # WhatsApp messages
        messages = value.get("messages") or []
        if messages:
            m = messages[0]
            phone = m.get("from")
            msg_type = m.get("type", "text") or "text"

            text_msg = ""
            if msg_type == "text":
                text_msg = (m.get("text") or {}).get("body", "") or ""
            else:
                # para pruebas, guardamos algo genérico
                text_msg = f"[{msg_type}]"

            _store_in_db(phone=phone, direction="in", msg_type=msg_type, text_msg=text_msg)

    except Exception:
        # no rompemos el webhook por payloads raros (statuses, etc.)
        pass

    return {"ok": True}
