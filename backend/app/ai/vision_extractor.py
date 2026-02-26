# app/ai/vision_extractor.py
from __future__ import annotations

import os
import json
import base64
import re
import asyncio
from typing import Any, Dict, Tuple

import httpx


def _get_gemini_key() -> str:
    return (os.getenv("GOOGLE_AI_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip())


def _clean_mime(m: str) -> str:
    return (m or "application/octet-stream").split(";")[0].strip().lower()


def _model() -> str:
    return (os.getenv("GEMINI_MM_MODEL", "").strip() or "gemini-2.5-flash").strip()


def _timeout_sec() -> float:
    try:
        return float(os.getenv("GEMINI_MM_TIMEOUT_SEC", "75").strip() or "75")
    except Exception:
        return 75.0


def _extract_json_loose(text: str) -> Dict[str, Any]:
    """
    Intenta parsear JSON aunque venga con basura alrededor.
    """
    if not text:
        return {}
    t = text.strip()

    # si viene en ```json ... ```
    t = re.sub(r"^```(?:json)?\s*", "", t, flags=re.IGNORECASE).strip()
    t = re.sub(r"\s*```$", "", t).strip()

    # buscar primer { ... último }
    if "{" in t and "}" in t:
        i = t.find("{")
        j = t.rfind("}")
        if i >= 0 and j > i:
            t = t[i:j+1].strip()

    try:
        obj = json.loads(t)
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _build_prompt() -> str:
    # ✅ PROMPT ESTRICTO (lo que tú pediste)
    return (
        "Eres un extractor de datos para ventas por WhatsApp.\n"
        "Tu tarea NO es describir: es IDENTIFICAR y EXTRAER.\n\n"
        "Debes devolver SOLO un JSON válido (sin texto adicional, sin markdown).\n\n"
        "Detecta el tipo:\n"
        "1) PERFUME: si ves un perfume (frasco/caja), identifica el nombre comercial, marca y variante.\n"
        "2) COMPROBANTE: si es comprobante/pago/transferencia, extrae monto, moneda, referencia, fecha, banco, titular.\n"
        "3) OTHER: si no aplica.\n\n"
        "Reglas:\n"
        "- NO inventes. Si no se ve claro, pon null o lista vacía.\n"
        "- Para PERFUME entrega 3 a 5 candidatos (más probable primero).\n"
        "- Crea 'search_text' corto para buscar en Woo (marca + nombre + variante si aplica).\n\n"
        "Formato exacto:\n"
        "{\n"
        '  "type": "perfume|receipt|other",\n'
        '  "confidence": 0.0,\n'
        '  "search_text": "",\n'
        '  "product_candidates": [\n'
        '     {"name": "", "brand": "", "variant": "", "size": "", "confidence": 0.0}\n'
        "  ],\n"
        '  "receipt": {\n'
        '     "amount": null,\n'
        '     "currency": null,\n'
        '     "reference": null,\n'
        '     "date": null,\n'
        '     "bank": null,\n'
        '     "payer_name": null\n'
        "  },\n"
        '  "notes": ""\n'
        "}\n"
    )


async def extract_structured_from_media(
    *,
    media_bytes: bytes,
    mime_type: str,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    api_key = _get_gemini_key()
    if not api_key:
        return {}, {"ok": False, "reason": "GOOGLE_AI_API_KEY missing"}

    mime_clean = _clean_mime(mime_type)
    model = _model()
    timeout = _timeout_sec()

    b64 = base64.b64encode(media_bytes or b"").decode("utf-8")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": _build_prompt()},
                {"inline_data": {"mime_type": mime_clean, "data": b64}},
            ],
        }],
        "generationConfig": {"temperature": 0.0, "maxOutputTokens": 512},
    }

    t0 = asyncio.get_event_loop().time()
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.post(url, json=body)
    except Exception as e:
        return {}, {"ok": False, "stage": "http", "error": str(e)[:900], "model": model}

    latency_ms = int((asyncio.get_event_loop().time() - t0) * 1000)

    if r.status_code >= 400:
        return {}, {
            "ok": False,
            "stage": "gemini",
            "status": int(r.status_code),
            "body": (r.text or "")[:1200],
            "model": model,
            "mime_type": mime_clean,
            "latency_ms": latency_ms,
        }

    j = r.json() or {}
    out_text = ""
    try:
        parts = (((j.get("candidates") or [])[0] or {}).get("content") or {}).get("parts") or []
        texts = []
        for p in parts:
            tx = (p or {}).get("text")
            if tx:
                texts.append(str(tx))
        out_text = "\n".join(texts).strip()
    except Exception:
        out_text = ""

    obj = _extract_json_loose(out_text)

    # Normalización mínima
    if not isinstance(obj, dict):
        obj = {}

    if obj.get("type") not in ("perfume", "receipt", "other"):
        obj["type"] = "other"

    try:
        obj["confidence"] = float(obj.get("confidence") or 0.0)
    except Exception:
        obj["confidence"] = 0.0

    if not isinstance(obj.get("product_candidates"), list):
        obj["product_candidates"] = []

    if not isinstance(obj.get("receipt"), dict):
        obj["receipt"] = {}

    obj["search_text"] = str(obj.get("search_text") or "").strip()
    obj["notes"] = str(obj.get("notes") or "").strip()

    meta = {"ok": True, "stage": "gemini", "status": int(r.status_code), "model": model, "latency_ms": latency_ms}
    return obj, meta