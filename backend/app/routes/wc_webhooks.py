# app/routes/wc_webhooks.py

from __future__ import annotations

import os
import hmac
import hashlib
import base64
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request, HTTPException

from app.integrations.woocommerce import wc_enabled, wc_get, map_product_for_ui
from app.catalog.cache_repo import upsert_cached_product

router = APIRouter()

WC_WEBHOOK_SECRET = (os.getenv("WC_WEBHOOK_SECRET", "") or "").strip()
WC_SYNC_ADMIN_TOKEN = (os.getenv("WC_SYNC_ADMIN_TOKEN", "") or "").strip()


# =========================================================
# Helpers
# =========================================================

def _require_secret() -> bool:
    # Si no hay secret, no bloqueamos (permite configurar Woo primero).
    # Recomendado: definir WC_WEBHOOK_SECRET en producción para validar firma.
    return bool(WC_WEBHOOK_SECRET)


def _verify_woocommerce_signature(raw_body: bytes, signature_header: str | None) -> None:
    """
    Woo header: X-WC-Webhook-Signature = base64(hmac_sha256(raw_body, secret))

    Si WC_WEBHOOK_SECRET no está configurado, se omite validación (modo setup).
    """
    if not _require_secret():
        return

    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing X-WC-Webhook-Signature")

    expected = hmac.new(
        WC_WEBHOOK_SECRET.encode("utf-8"),
        msg=raw_body,
        digestmod=hashlib.sha256,
    ).digest()

    expected_b64 = base64.b64encode(expected).decode("utf-8").strip()
    provided = (signature_header or "").strip()

    if not hmac.compare_digest(expected_b64, provided):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

        raise HTTPException(status_code=401, detail="Invalid webhook signature")


def _admin_guard(request: Request) -> None:
    if not WC_SYNC_ADMIN_TOKEN:
        raise HTTPException(status_code=403, detail="WC_SYNC_ADMIN_TOKEN not configured")

    tok = (request.headers.get("X-Admin-Token") or "").strip()
    if tok != WC_SYNC_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")


def _parse_json(raw: bytes) -> dict:
    try:
        j = json.loads(raw.decode("utf-8", errors="ignore") or "{}")
        return j if isinstance(j, dict) else {}
    except Exception:
        return {}


def _safe_int(x: Any) -> int:
    try:
        return int(x)
    except Exception:
        return 0


def _cache_one_product_from_payload(payload: dict) -> int:
    """
    Payload normalmente ya es el producto completo.
    Lo mapeamos y lo guardamos en cache.
    """
    pid = _safe_int(payload.get("id"))
    if pid <= 0:
        return 0

    mapped = map_product_for_ui(payload)
    upsert_cached_product(mapped, updated_at_woo=None, raw_json=payload, is_deleted=False)
    return pid


async def _cache_one_product_by_id(product_id: int) -> int:
    """
    Plan B: si el payload llega incompleto, pedimos el producto a Woo.
    OJO: esto usa wc_get (con breaker). Para sync full, usamos el endpoint admin.
    """
    pid = int(product_id)
    if pid <= 0:
        return 0

    data = await wc_get(f"/products/{pid}", params={})
    if not isinstance(data, dict) or not data.get("id"):
        return 0

    mapped = map_product_for_ui(data)
    upsert_cached_product(mapped, updated_at_woo=None, raw_json=data, is_deleted=False)
    return pid


def _cache_deleted(product_id: int) -> None:
    """
    Sin cambiar schema: lo marcamos como "deleted" para que el fallback no lo recomiende.
    """
    pid = int(product_id)
    if pid <= 0:
        return

    tombstone = {
        "id": pid,
        "name": f"DELETED #{pid}",
        "price": "",
        "permalink": "",
        "featured_image": "",
        "real_image": "",
        "short_description": "",
        "description": "",
        "categories": [],
        "tags": [],
        "aromas": [],
        "brand": "",
        "gender": "",
        "size": "",
        "stock_status": "deleted",
    }
    upsert_cached_product(tombstone, updated_at_woo=None, raw_json=tombstone, is_deleted=True)


# =========================================================
# Webhooks (Woo -> Backend)
# =========================================================

@router.post("/api/wc/webhook/product-created")
async def wc_webhook_product_created(request: Request):
    raw = await request.body()
    _verify_woocommerce_signature(raw, request.headers.get("X-WC-Webhook-Signature"))

    payload = _parse_json(raw)
    pid = _cache_one_product_from_payload(payload)

    # Si por alguna razón llega incompleto, intentamos por ID
    if pid <= 0:
        pid = _safe_int(payload.get("product_id"))
        if pid > 0:
            await _cache_one_product_by_id(pid)

    return {"ok": True, "event": "product-created", "product_id": pid}


@router.post("/api/wc/webhook/product-updated")
async def wc_webhook_product_updated(request: Request):
    raw = await request.body()
    _verify_woocommerce_signature(raw, request.headers.get("X-WC-Webhook-Signature"))

    payload = _parse_json(raw)
    pid = _cache_one_product_from_payload(payload)

    if pid <= 0:
        pid = _safe_int(payload.get("product_id"))
        if pid > 0:
            await _cache_one_product_by_id(pid)

    return {"ok": True, "event": "product-updated", "product_id": pid}


@router.post("/api/wc/webhook/product-deleted")
async def wc_webhook_product_deleted(request: Request):
    raw = await request.body()
    _verify_woocommerce_signature(raw, request.headers.get("X-WC-Webhook-Signature"))

    payload = _parse_json(raw)
    pid = _safe_int(payload.get("id") or payload.get("product_id"))
    if pid <= 0:
        raise HTTPException(status_code=400, detail="Missing product id")

    _cache_deleted(pid)
    return {"ok": True, "event": "product-deleted", "product_id": pid}


# =========================================================
# Admin sync endpoints (llenar DB desde 0)
# =========================================================

@router.post("/api/wc/cache/sync/full")
async def wc_cache_sync_full(request: Request):
    _admin_guard(request)

    if not wc_enabled():
        raise HTTPException(status_code=500, detail="Woo env vars not set")

    page = 1
    total = 0

    while True:
        data = await wc_get("/products", params={"page": page, "per_page": 100, "status": "publish"})
        if not data or not isinstance(data, list):
            break

        for p in data:
            if isinstance(p, dict) and p.get("id"):
                mapped = map_product_for_ui(p)
                upsert_cached_product(mapped, updated_at_woo=None, raw_json=payload, is_deleted=False)
                total += 1

        page += 1
        if page > 2000:
            break

    return {"ok": True, "synced": total}


@router.post("/api/wc/cache/sync/product/{product_id}")
async def wc_cache_sync_one(product_id: int, request: Request):
    _admin_guard(request)

    if not wc_enabled():
        raise HTTPException(status_code=500, detail="Woo env vars not set")

    pid = await _cache_one_product_by_id(int(product_id))
    if pid <= 0:
        raise HTTPException(status_code=502, detail="Woo returned invalid product")

    return {"ok": True, "product_id": pid}