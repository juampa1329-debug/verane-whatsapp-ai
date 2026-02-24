# app/catalog/sync_service.py

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Optional

from sqlalchemy import text
from app.db import engine
from app.integrations.woocommerce import wc_get, map_product_for_ui, wc_enabled
from app.catalog.cache_repo import upsert_cached_product


def _get_last_sync_ts() -> Optional[datetime]:
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT last_sync_at
            FROM wc_sync_state
            WHERE id = 1
        """)).mappings().first()
    ts = (row or {}).get("last_sync_at")
    return ts if isinstance(ts, datetime) else None


def _set_last_sync_ts(ts: datetime) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO wc_sync_state (id, last_sync_at, updated_at)
            VALUES (1, :ts, :now)
            ON CONFLICT (id) DO UPDATE SET
                last_sync_at = EXCLUDED.last_sync_at,
                updated_at = EXCLUDED.updated_at
        """), {"ts": ts, "now": datetime.utcnow()})


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
            mapped = map_product_for_ui(p)
            upsert_cached_product(mapped, updated_at_woo=None)
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
            mapped = map_product_for_ui(p)
            upsert_cached_product(mapped, updated_at_woo=None)
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