from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import text
from app.db import engine


# =========================================================
# Auto schema (seguridad deploy)
# =========================================================

def _ensure_schema() -> None:
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS wc_products_cache (
                    product_id BIGINT PRIMARY KEY,
                    data JSONB NOT NULL,
                    name TEXT,
                    price TEXT,
                    permalink TEXT,
                    featured_image TEXT,
                    real_image TEXT,
                    stock_status TEXT,
                    updated_at_woo TIMESTAMP NULL,
                    synced_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    search_blob TEXT
                )
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_wc_cache_stock
                ON wc_products_cache (stock_status)
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_wc_cache_search
                ON wc_products_cache USING GIN (to_tsvector('simple', search_blob))
            """))
    except Exception:
        pass


_ensure_schema()


# =========================================================
# Utils
# =========================================================

def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9áéíóúñü\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def build_search_blob(p: dict) -> str:
    parts = []
    for k in ("name", "short_description", "description", "brand", "gender", "size"):
        parts.append(str(p.get(k) or ""))

    cats = p.get("categories") or []
    tags = p.get("tags") or []
    aromas = p.get("aromas") or []

    parts.append(" ".join([str(x.get("name") or "") for x in cats if isinstance(x, dict)]))
    parts.append(" ".join([str(x.get("name") or "") for x in tags if isinstance(x, dict)]))
    parts.append(" ".join([str(x) for x in aromas if x]))

    return _norm(" ".join(parts))


# =========================================================
# UPSERT
# =========================================================

def upsert_cached_product(product: dict, *, updated_at_woo: Optional[datetime] = None) -> None:
    if not isinstance(product, dict):
        return

    try:
        pid = int(product.get("id"))
    except Exception:
        return

    if pid <= 0:
        return

    now = datetime.utcnow()
    search_blob = build_search_blob(product)

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO wc_products_cache (
                product_id,
                data,
                name,
                price,
                permalink,
                featured_image,
                real_image,
                stock_status,
                updated_at_woo,
                synced_at,
                search_blob
            )
            VALUES (
                :product_id,
                :data::jsonb,
                :name,
                :price,
                :permalink,
                :featured_image,
                :real_image,
                :stock_status,
                :updated_at_woo,
                :synced_at,
                :search_blob
            )
            ON CONFLICT (product_id) DO UPDATE SET
                data = EXCLUDED.data,
                name = EXCLUDED.name,
                price = EXCLUDED.price,
                permalink = EXCLUDED.permalink,
                featured_image = EXCLUDED.featured_image,
                real_image = EXCLUDED.real_image,
                stock_status = EXCLUDED.stock_status,
                updated_at_woo = COALESCE(EXCLUDED.updated_at_woo, wc_products_cache.updated_at_woo),
                synced_at = EXCLUDED.synced_at,
                search_blob = EXCLUDED.search_blob
        """), {
            "product_id": pid,
            "data": json.dumps(product, ensure_ascii=False),
            "name": (product.get("name") or "")[:300],
            "price": str(product.get("price") or "")[:60],
            "permalink": (product.get("permalink") or "")[:900],
            "featured_image": (product.get("featured_image") or "")[:900],
            "real_image": (product.get("real_image") or "")[:900],
            "stock_status": (product.get("stock_status") or "")[:60],
            "updated_at_woo": updated_at_woo,
            "synced_at": now,
            "search_blob": search_blob[:5000],
        })


# =========================================================
# GET
# =========================================================

def get_cached_product(product_id: int) -> Optional[dict]:
    try:
        pid = int(product_id)
    except Exception:
        return None

    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT data
            FROM wc_products_cache
            WHERE product_id = :pid
            LIMIT 1
        """), {"pid": pid}).mappings().first()

    if not row:
        return None

    data = row.get("data")

    if isinstance(data, dict):
        return data

    try:
        return json.loads(data) if isinstance(data, str) else None
    except Exception:
        return None


# =========================================================
# SEARCH (ranking simple)
# =========================================================

def search_cached_products(query: str, *, limit: int = 24) -> list[dict]:
    q = _norm(query)
    if not q:
        return []

    tokens = [t for t in q.split() if len(t) >= 2]
    if not tokens:
        return []

    clauses = []
    params: dict[str, Any] = {"limit": int(max(1, min(limit, 60)))}

    for i, tok in enumerate(tokens[:8]):
        k = f"t{i}"
        params[k] = f"%{tok}%"
        clauses.append(f"(CASE WHEN search_blob LIKE :{k} THEN 1 ELSE 0 END)")

    score_sql = " + ".join(clauses) if clauses else "0"

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT data, stock_status, ({score_sql}) AS score
            FROM wc_products_cache
            WHERE ({score_sql}) > 0
            ORDER BY
                CASE WHEN stock_status = 'instock' THEN 0 ELSE 1 END,
                score DESC,
                product_id DESC
            LIMIT :limit
        """), params).mappings().all()

    out = []
    for r in rows:
        data = r.get("data")
        if isinstance(data, dict):
            out.append(data)
        else:
            try:
                out.append(json.loads(data) if isinstance(data, str) else {})
            except Exception:
                pass

    return [x for x in out if isinstance(x, dict) and x.get("id")]


# =========================================================
# DELETE (cuando Woo elimina producto)
# =========================================================

def delete_cached_product(product_id: int) -> None:
    try:
        pid = int(product_id)
    except Exception:
        return

    with engine.begin() as conn:
        conn.execute(text("""
            DELETE FROM wc_products_cache
            WHERE product_id = :pid
        """), {"pid": pid})


# =========================================================
# MAINTENANCE
# =========================================================

def clear_cache() -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM wc_products_cache"))


def get_cache_stats() -> dict:
    with engine.begin() as conn:
        row = conn.execute(text("""
            SELECT COUNT(*) AS total
            FROM wc_products_cache
        """)).mappings().first()

    return {
        "total_products": int((row or {}).get("total") or 0)
    }