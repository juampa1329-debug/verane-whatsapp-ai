# app/catalog/sync_service.py

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from app.db import engine
from app.integrations.woocommerce import wc_get, map_product_for_ui, wc_enabled
from app.catalog.cache_repo import upsert_cached_product


def _ensure_sync_state_schema() -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS wc_sync_state (
                id INTEGER PRIMARY KEY,
                last_sync_at TIMESTAMP NULL,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))
        conn.execute(text("""
            INSERT INTO wc_sync_state (id, last_sync_at, updated_at)
            VALUES (1, NULL, NOW())
            ON CONFLICT (id) DO NOTHING
        """))


def _get_last_sync_ts() -> Optional[datetime]:
    _ensure_sync_state_schema()
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT last_sync_at
            FROM wc_sync_state
            WHERE id = 1
        """)).mappings().first()
    ts = (row or {}).get("last_sync_at")
    return ts if isinstance(ts, datetime) else None


def get_sync_state() -> dict:
    last_sync_at = _get_last_sync_ts()
    return {
        "last_sync_at": (
            last_sync_at.isoformat() if isinstance(last_sync_at, datetime) else None
        )
    }


def _set_last_sync_ts(ts: datetime) -> None:
    _ensure_sync_state_schema()
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO wc_sync_state (id, last_sync_at, updated_at)
            VALUES (1, :ts, :now)
            ON CONFLICT (id) DO UPDATE SET
                last_sync_at = EXCLUDED.last_sync_at,
                updated_at = EXCLUDED.updated_at
        """), {"ts": ts, "now": datetime.utcnow()})


def mark_sync_now() -> None:
    _set_last_sync_ts(datetime.utcnow())


def _parse_woo_modified_ts(product: dict) -> Optional[datetime]:
    if not isinstance(product, dict):
        return None
    raw = (
        product.get("date_modified_gmt")
        or product.get("date_modified")
        or product.get("date_created_gmt")
        or product.get("date_created")
        or ""
    )
    value = str(raw or "").strip()
    if not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


def _upsert_from_woo_product(product: dict) -> None:
    mapped = map_product_for_ui(product)
    upsert_cached_product(mapped, updated_at_woo=_parse_woo_modified_ts(product))


async def sync_all_products_once(per_page: int = 100, max_pages: int = 50) -> dict:
    """
    Sync completo (paginado). Útil para primera carga.
    """
    if not wc_enabled():
        return {"ok": False, "reason": "wc_not_enabled"}

    saved = 0
    page = 1
    while page <= max_pages:
        data = await wc_get("/products", params={
            "page": page,
            "per_page": int(per_page),
            "status": "publish",
        })
        items = data or []
        if not items:
            break

        for p in items:
            _upsert_from_woo_product(p)
            saved += 1

        page += 1

    _set_last_sync_ts(datetime.utcnow())
    return {"ok": True, "mode": "full", "saved": saved, "pages": page - 1}


async def sync_recent_products_once(per_page: int = 100, max_pages: int = 20) -> dict:
    """
    Sync incremental “mejor esfuerzo”:
    Woo v3 products soporta "modified_after" en algunas instalaciones,
    pero como puede variar, hacemos:
    - traer últimas páginas recientes (por fecha desc si Woo responde así),
    - upsert (idempotente).
    Es robusto sin depender de filtros raros.
    """
    if not wc_enabled():
        return {"ok": False, "reason": "wc_not_enabled"}

    saved = 0
    page = 1
    while page <= max_pages:
        data = await wc_get("/products", params={
            "page": page,
            "per_page": int(per_page),
            "status": "publish",
            "orderby": "date",
            "order": "desc",
        })
        items = data or []
        if not items:
            break

        for p in items:
            _upsert_from_woo_product(p)
            saved += 1

        page += 1

    _set_last_sync_ts(datetime.utcnow())
    return {"ok": True, "mode": "recent", "saved": saved, "pages": page - 1}


async def start_periodic_sync(interval_sec: int = 300) -> None:
    """
    Loop infinito. Llamar en startup con create_task().
    """
    interval_sec = int(max(30, min(interval_sec, 3600)))
    # primer sync “soft”
    try:
        await sync_recent_products_once()
    except Exception:
        pass

    while True:
        try:
            await sync_recent_products_once()
        except Exception:
            pass
        await asyncio.sleep(interval_sec)
