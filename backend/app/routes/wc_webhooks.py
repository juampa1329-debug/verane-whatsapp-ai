# app/routes/wc_webhooks.py

from __future__ import annotations

import os
import hmac
import hashlib
import base64
import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Request, HTTPException, Query

from app.integrations.woocommerce import wc_enabled, wc_get, map_product_for_ui
from app.catalog.cache_repo import (
    upsert_cached_product,
    get_cache_stats,
    list_cached_brands,
    list_cached_references,
)
from app.catalog.sync_service import (
    sync_all_products_once,
    sync_recent_products_once,
    get_sync_state,
    mark_sync_now,
)

router = APIRouter()

WC_WEBHOOK_SECRET = (os.getenv("WC_WEBHOOK_SECRET", "") or "").strip()
WC_SYNC_ADMIN_TOKEN = (os.getenv("WC_SYNC_ADMIN_TOKEN", "") or "").strip()


# =========================================================
# Helpers
# =========================================================

def _require_secret():
    if not WC_WEBHOOK_SECRET:
        raise HTTPException(status_code=500, detail="WC_WEBHOOK_SECRET not configured")


def _verify_woocommerce_signature(raw_body: bytes, signature_header: str | None) -> None:
    """
    Woo header: X-WC-Webhook-Signature
    = base64(hmac_sha256(raw_body, secret))
    """
    _require_secret()

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
    upsert_cached_product(mapped, updated_at_woo=None)
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
    upsert_cached_product(mapped, updated_at_woo=None)
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
    upsert_cached_product(tombstone, updated_at_woo=None)


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

    if pid > 0:
        mark_sync_now()

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

    if pid > 0:
        mark_sync_now()

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
    mark_sync_now()
    return {"ok": True, "event": "product-deleted", "product_id": pid}


# =========================================================
# Cache observability endpoints
# =========================================================

@router.get("/api/wc/cache/stats")
async def wc_cache_stats():
    return {
        "ok": True,
        "cache": get_cache_stats(),
        "sync": get_sync_state(),
    }


@router.get("/api/wc/cache/brands")
async def wc_cache_brands(
    q: str = Query("", description="Filtro de marca"),
    limit: int = Query(200, ge=1, le=1000),
):
    brands = list_cached_brands(q=q, limit=limit)
    return {"ok": True, "brands": brands, "total": len(brands)}


@router.get("/api/wc/cache/references")
async def wc_cache_references(
    q: str = Query("", description="Texto de búsqueda por nombre/SKU/slug"),
    brand: str = Query("", description="Marca"),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    instock_only: bool = Query(False),
):
    data = list_cached_references(
        q=q,
        brand=brand,
        page=page,
        per_page=per_page,
        instock_only=instock_only,
    )
    return {"ok": True, **data}


# =========================================================
# Admin sync endpoints (llenar DB desde 0)
# =========================================================

@router.post("/api/wc/cache/sync/full")
async def wc_cache_sync_full(request: Request):
    _admin_guard(request)

    result = await sync_all_products_once(per_page=100, max_pages=2000)
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=str(result.get("reason") or "sync_full_failed"))

    return {"ok": True, **result}


@router.post("/api/wc/cache/sync/recent")
async def wc_cache_sync_recent(request: Request):
    _admin_guard(request)

    result = await sync_recent_products_once(per_page=100, max_pages=30)
    if not result.get("ok"):
        raise HTTPException(status_code=500, detail=str(result.get("reason") or "sync_recent_failed"))

    return {"ok": True, **result}


@router.post("/api/wc/cache/sync/product/{product_id}")
async def wc_cache_sync_one(product_id: int, request: Request):
    _admin_guard(request)

    if not wc_enabled():
        raise HTTPException(status_code=500, detail="Woo env vars not set")

    pid = await _cache_one_product_by_id(int(product_id))
    if pid <= 0:
        raise HTTPException(status_code=502, detail="Woo returned invalid product")

    mark_sync_now()
    return {"ok": True, "product_id": pid}
