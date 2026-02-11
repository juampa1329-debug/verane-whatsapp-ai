import os
import json
import re
from typing import Any, Optional

import httpx
from fastapi import FastAPI, Request

app = FastAPI()

BACKEND_BASE_URL = os.getenv("BACKEND_BASE_URL", "http://api:8000").rstrip("/")
AI_ENABLED = os.getenv("AI_ENABLED", "true").lower() == "true"
AI_ALLOWLIST = [x.strip() for x in os.getenv("AI_ALLOWLIST", "").split(",") if x.strip()]


def _allowed(phone: str) -> bool:
    if not AI_ALLOWLIST:
        return True
    return phone in AI_ALLOWLIST


async def _backend_get(path: str) -> Any:
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(f"{BACKEND_BASE_URL}{path}")
        r.raise_for_status()
        return r.json()


async def _backend_post(path: str, payload: dict) -> Any:
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(f"{BACKEND_BASE_URL}{path}", json=payload)
        r.raise_for_status()
        return r.json()


def _extract_text_from_whatsapp_webhook(data: dict) -> tuple[Optional[str], str]:
    """
    Devuelve (phone, text)
    Si no es texto, devuelve "[type]"
    """
    try:
        entry = (data.get("entry") or [])[0]
        change = (entry.get("changes") or [])[0]
        value = change.get("value") or {}
        messages = value.get("messages") or []
        if not messages:
            return None, ""
        m = messages[0]
        phone = m.get("from")
        msg_type = m.get("type", "text") or "text"
        if msg_type == "text":
            text = ((m.get("text") or {}).get("body") or "").strip()
            return phone, text
        return phone, f"[{msg_type}]"
    except Exception:
        return None, ""


def _is_handoff(text: str) -> bool:
    t = (text or "").lower()
    keywords = ["humano", "asesor", "persona", "llamar", "queja", "reclamo", "malo", "pésimo", "pesimo"]
    return any(k in t for k in keywords)


def _guess_query(text: str) -> str:
    # una limpieza simple para usarlo como búsqueda en WC
    t = (text or "").strip()
    t = re.sub(r"\s+", " ", t)
    return t[:60]


def _format_products(products: list[dict]) -> str:
    if not products:
        return "No encontré productos con ese nombre. ¿Me dices si es para Hombre, Mujer o Unisex y tu presupuesto aproximado?"

    lines = ["Te comparto algunas opciones:"]
    for p in products[:4]:
        name = (p.get("name") or "").strip()
        price = (p.get("price") or "").strip()
        pid = p.get("id")
        brand = (p.get("brand") or "").strip()
        extra = []
        if brand:
            extra.append(brand)
        if price:
            extra.append(f"${price}")
        extra_txt = " · ".join(extra)
        if extra_txt:
            lines.append(f"• ({pid}) {name} — {extra_txt}")
        else:
            lines.append(f"• ({pid}) {name}")

    lines.append("\nSi te interesa uno, respóndeme con el número entre paréntesis, por ejemplo: 123")
    return "\n".join(lines)


def _extract_product_id(text: str) -> Optional[int]:
    # detecta el primer número de 2-8 dígitos
    m = re.search(r"\b(\d{2,8})\b", text or "")
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


@app.get("/ai/health")
def health():
    return {"ok": True, "enabled": AI_ENABLED, "backend": BACKEND_BASE_URL}


@app.post("/ai/whatsapp-webhook-forward")
async def whatsapp_forward(request: Request):
    if not AI_ENABLED:
        return {"ok": True, "skipped": "disabled"}

    raw = await request.body()
    try:
        data = json.loads(raw.decode("utf-8") or "{}")
    except Exception:
        return {"ok": True}

    phone, text_in = _extract_text_from_whatsapp_webhook(data)
    if not phone:
        return {"ok": True}

    if not _allowed(phone):
        return {"ok": True, "skipped": "not in allowlist"}

    # 1) takeover check
    crm = await _backend_get(f"/api/crm/{phone}")
    takeover = bool((crm or {}).get("takeover")) if isinstance(crm, dict) else False
    if takeover:
        return {"ok": True, "skipped": "takeover"}

    # 2) handoff keywords -> activar takeover y no responder
    if _is_handoff(text_in):
        await _backend_post("/api/conversations/takeover", {"phone": phone, "takeover": True})
        await _backend_post("/api/messages/ingest", {
            "phone": phone,
            "direction": "out",
            "msg_type": "text",
            "text": "Perfecto 🙌 Te paso con un asesor humano para ayudarte mejor."
        })
        return {"ok": True, "handoff": True}

    # 3) si el cliente manda un ID, enviamos el producto como imagen real
    pid = _extract_product_id(text_in)
    if pid:
        # envía producto por WhatsApp como adjunto real (tu endpoint ya lo hace)
        await _backend_post("/api/wc/send-product", {"phone": phone, "product_id": pid, "caption": ""})
        return {"ok": True, "sent_product": pid}

    # 4) si no, asumimos que está buscando algo y mostramos opciones
    q = _guess_query(text_in)
    wc = await _backend_get(f"/api/wc/products?q={httpx.QueryParams({'q': q})['q']}")
    products = (wc or {}).get("products") or []
    reply = _format_products(products)

    await _backend_post("/api/messages/ingest", {
        "phone": phone,
        "direction": "out",
        "msg_type": "text",
        "text": reply
    })

    return {"ok": True}
