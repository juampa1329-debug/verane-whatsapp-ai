import os
import asyncio
import httpx
from fastapi import APIRouter, Request, Response, HTTPException

router = APIRouter()

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
FORWARD_URL = os.getenv("WHATSAPP_FORWARD_URL", "")
FORWARD_ENABLED = os.getenv("WHATSAPP_FORWARD_ENABLED", "true").lower() == "true"
FORWARD_TIMEOUT = float(os.getenv("WHATSAPP_FORWARD_TIMEOUT", "4"))

@router.get("/api/whatsapp/webhook")
async def whatsapp_verify(request: Request):
    qp = request.query_params
    mode = qp.get("hub.mode")
    token = qp.get("hub.verify_token")
    challenge = qp.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN and challenge is not None:
        return Response(content=str(challenge), media_type="text/plain")

    raise HTTPException(status_code=403, detail="Verification failed")

async def _forward(raw_body: bytes):
    if not (FORWARD_ENABLED and FORWARD_URL):
        return
    headers = {
        "Content-Type": "application/json",
        "X-Verane-Forwarded": "1",  # evita loops si algún día reenvías de vuelta
    }
    async with httpx.AsyncClient(timeout=FORWARD_TIMEOUT) as client:
        await client.post(FORWARD_URL, content=raw_body, headers=headers)

@router.post("/api/whatsapp/webhook")
async def whatsapp_receive(request: Request):
    raw = await request.body()

    # ACK rápido a Meta y reenvío en background a Sellerchat
    asyncio.create_task(_forward(raw))

    return {"ok": True}
