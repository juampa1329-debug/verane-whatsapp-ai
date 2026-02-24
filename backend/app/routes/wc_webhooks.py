# app/routes/wc_webhooks.py

from __future__ import annotations

import os
import hmac
import hashlib
import base64
import json
from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import text

from app.db import engine
from app.integrations.woocommerce import wc_get_live  # fuerza Woo (sin cache)

router = APIRouter()

WC_WEBHOOK_SECRET = (os.getenv("WC_WEBHOOK_SECRET", "") or "").strip()

# Cache admin sync (opcional, recomendado)
WC_SYNC_ADMIN_TOKEN = (os.getenv("WC_SYNC_ADMIN_TOKEN", "") or "").strip()


# =========================================================
# Helpers
# =========================================================

def _require_secret():
    if not WC_WEBHOOK_SECRET:
        # Sin secret NO validamos firma -> inseguro
        raise HTTPException(status_code=500, detail="WC_WEBHOOK_SECRET not configured")


def _verify_woocommerce_signature(raw_body: bytes, signature_header: str | None) -> None:
    """
    Woo envía header: X-WC-Webhook-Signature
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

    # constant-time compare
    if not hmac.compare_digest(expected_b64, provided):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")


def _now() -> datetime:
    return datetime.utcnow()


def _upsert_product_raw(product: dict) -> None:
    """
    Guarda producto “raw” (JSON completo de Woo) para fallback en PostgreSQL.
    Mantiene catálogo espejo.
    """
    if not isinstance(product, dict):
        return

    pid = product.get("id")
    if not pid:
        return

    name = (product.get("name") or "").strip()
    permalink = (product.get("permalink") or "").strip()
    stock_status = (product.get("stock_status") or "").strip()

    images = product.get("images") or []
    featured_image = ""
    real_image = ""
    if isinstance(images, list) and images:
        featured_image = ((images[0] or {}).get("src") or "").strip()
        if len(images) > 1:
            real_image = ((images[1] or {}).get("src") or "").strip()

    raw_json = json.dumps(product, ensure_ascii=False)

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO wc_products_cache (
                product_id,
                name,
                permalink,
                stock_status,
                featured_image,
                real_image,
                raw_json,
                is_deleted,
                updated_at,
                synced_at
            )
            VALUES (
                :product_id,
                :name,
                :permalink,
                :stock_status,
                :featured_image,
                :real_image,
                CAST(:raw_json AS JSONB),
                FALSE,
                :updated_at,
                :synced_at
            )
            ON CONFLICT (product_id) DO UPDATE SET
                name = EXCLUDED.name,
                permalink = EXCLUDED.permalink,
                stock_status = EXCLUDED.stock_status,
                featured_image = EXCLUDED.featured_image,
                real_image = EXCLUDED.real_image,
                raw_json = EXCLUDED.raw_json,
                is_deleted = FALSE,
                updated_at = EXCLUDED.updated_at,
                synced_at = EXCLUDED.synced_at
        """), {
            "product_id": int(pid),
            "name": name,
            "permalink": permalink,
            "stock_status": stock_status,
            "featured_image": featured_image,
            "real_image": real_image,
            "raw_json": raw_json,
            "updated_at": _now(),
            "synced_at": _now(),
        })


def _mark_deleted(product_id: int) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO wc_products_cache (
                product_id, name, raw_json, is_deleted, updated_at, synced_at
            )
            VALUES (:product_id, '', '{}'::jsonb, TRUE, :updated_at, :synced_at)
            ON CONFLICT (product_id) DO UPDATE SET
                is_deleted = TRUE,
                updated_at = EXCLUDED.updated_at,
                synced_at = EXCLUDED.synced_at
        """), {
            "product_id": int(product_id),
            "updated_at": _now(),
            "synced_at": _now(),
        })


def _admin_guard(request: Request) -> None:
    """
    Protección simple para endpoints de sync.
    """
    if not WC_SYNC_ADMIN_TOKEN:
        # Si no configuras token, NO dejamos sync abierto.
        raise HTTPException(status_code=403, detail="WC_SYNC_ADMIN_TOKEN not configured")

    tok = (request.headers.get("X-Admin-Token") or "").strip()
    if not tok or tok != WC_SYNC_ADMIN_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid admin token")


# =========================================================
# Webhooks (Woo -> Backend)
# =========================================================

@router.post("/api/wc/webhook/product-created")
async def wc_webhook_product_created(request: Request):
    raw = await request.body()
    _verify_woocommerce_signature(raw, request.headers.get("X-WC-Webhook-Signature"))

    try:
        payload = json.loads(raw.decode("utf-8", errors="ignore") or "{}")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    _upsert_product_raw(payload)
    return {"ok": True, "event": "product-created", "product_id": payload.get("id")}


@router.post("/api/wc/webhook/product-updated")
async def wc_webhook_product_updated(request: Request):
    raw = await request.body()
    _verify_woocommerce_signature(raw, request.headers.get("X-WC-Webhook-Signature"))

    try:
        payload = json.loads(raw.decode("utf-8", errors="ignore") or "{}")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    _upsert_product_raw(payload)
    return {"ok": True, "event": "product-updated", "product_id": payload.get("id")}


@router.post("/api/wc/webhook/product-deleted")
async def wc_webhook_product_deleted(request: Request):
    raw = await request.body()
    _verify_woocommerce_signature(raw, request.headers.get("X-WC-Webhook-Signature"))

    try:
        payload = json.loads(raw.decode("utf-8", errors="ignore") or "{}")
    except Exception:
        payload = {}

    # Woo a veces manda { "id": 123 } o manda un producto con status=trash
    pid = payload.get("id") or payload.get("product_id")
    if not pid:
        raise HTTPException(status_code=400, detail="Missing product id")

    _mark_deleted(int(pid))
    return {"ok": True, "event": "product-deleted", "product_id": int(pid)}


# =========================================================
# Admin sync endpoints (para llenar DB desde 0)
# =========================================================

@router.post("/api/wc/cache/sync/full")
async def wc_cache_sync_full(request: Request):
    _admin_guard(request)

    # paginamos Woo: per_page=100
    page = 1
    total = 0

    while True:
        data = await wc_get_live("/products", params={"page": page, "per_page": 100, "status": "publish"})
        if not data:
            break

        for p in data:
            if isinstance(p, dict):
                _upsert_product_raw(p)
                total += 1

        page += 1
        if page > 2000:
            break

    return {"ok": True, "synced": total}


@router.post("/api/wc/cache/sync/product/{product_id}")
async def wc_cache_sync_one(product_id: int, request: Request):
    _admin_guard(request)

    p = await wc_get_live(f"/products/{int(product_id)}", params={})
    if not isinstance(p, dict):
        raise HTTPException(status_code=502, detail="Woo returned invalid product")

    _upsert_product_raw(p)
    return {"ok": True, "product_id": int(product_id)}