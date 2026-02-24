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
            try:
                conn.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm"))
            except Exception:
                pass

            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS wc_products_cache (
                    product_id BIGINT PRIMARY KEY,

                    data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    name TEXT NOT NULL DEFAULT '',
                    price TEXT NOT NULL DEFAULT '',
                    permalink TEXT NOT NULL DEFAULT '',
                    featured_image TEXT NOT NULL DEFAULT '',
                    real_image TEXT NOT NULL DEFAULT '',
                    short_description TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',

                    categories JSONB NOT NULL DEFAULT '[]'::jsonb,
                    tags JSONB NOT NULL DEFAULT '[]'::jsonb,

                    brand TEXT NOT NULL DEFAULT '',
                    gender TEXT NOT NULL DEFAULT '',
                    size TEXT NOT NULL DEFAULT '',
                    stock_status TEXT NOT NULL DEFAULT '',

                    search_blob TEXT NOT NULL DEFAULT '',

                    raw_json JSONB NOT NULL DEFAULT '{}'::jsonb,
                    is_deleted BOOLEAN NOT NULL DEFAULT FALSE,

                    updated_at_woo TIMESTAMP NULL,
                    synced_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))

            # best-effort migrations for older schemas
            try:
                conn.execute(text("ALTER TABLE wc_products_cache ADD COLUMN IF NOT EXISTS data_json JSONB NOT NULL DEFAULT '{}'::jsonb"))
                conn.execute(text("ALTER TABLE wc_products_cache ADD COLUMN IF NOT EXISTS short_description TEXT NOT NULL DEFAULT ''"))
                conn.execute(text("ALTER TABLE wc_products_cache ADD COLUMN IF NOT EXISTS description TEXT NOT NULL DEFAULT ''"))
                conn.execute(text("ALTER TABLE wc_products_cache ADD COLUMN IF NOT EXISTS categories JSONB NOT NULL DEFAULT '[]'::jsonb"))
                conn.execute(text("ALTER TABLE wc_products_cache ADD COLUMN IF NOT EXISTS tags JSONB NOT NULL DEFAULT '[]'::jsonb"))
                conn.execute(text("ALTER TABLE wc_products_cache ADD COLUMN IF NOT EXISTS brand TEXT NOT NULL DEFAULT ''"))
                conn.execute(text("ALTER TABLE wc_products_cache ADD COLUMN IF NOT EXISTS gender TEXT NOT NULL DEFAULT ''"))
                conn.execute(text("ALTER TABLE wc_products_cache ADD COLUMN IF NOT EXISTS size TEXT NOT NULL DEFAULT ''"))
                conn.execute(text("ALTER TABLE wc_products_cache ADD COLUMN IF NOT EXISTS raw_json JSONB NOT NULL DEFAULT '{}'::jsonb"))
                conn.execute(text("ALTER TABLE wc_products_cache ADD COLUMN IF NOT EXISTS is_deleted BOOLEAN NOT NULL DEFAULT FALSE"))
                conn.execute(text("ALTER TABLE wc_products_cache ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP NOT NULL DEFAULT NOW()"))
            except Exception:
                pass

            # backfill from legacy column `data` if present
            try:
                conn.execute(text("UPDATE wc_products_cache SET data_json = COALESCE(data_json, data) WHERE data_json = '{}'::jsonb"))
            except Exception:
                pass

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_wc_cache_stock
                ON wc_products_cache (stock_status)
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_wc_cache_search_blob
                ON wc_products_cache USING gin (search_blob gin_trgm_ops)
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

def upsert_cached_product(product: dict, *, updated_at_woo: Optional[datetime] = None, raw_json: Optional[dict] = None, is_deleted: bool = False) -> None:
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
                data_json,
                name,
                price,
                permalink,
                featured_image,
                real_image,
                short_description,
                description,
                categories,
                tags,
                brand,
                gender,
                size,
                stock_status,
                raw_json,
                is_deleted,
                updated_at_woo,
                synced_at,
                updated_at,
                search_blob
            )
            VALUES (
                :product_id,
                :data_json::jsonb,
                :name,
                :price,
                :permalink,
                :featured_image,
                :real_image,
                :short_description,
                :description,
                :categories::jsonb,
                :tags::jsonb,
                :brand,
                :gender,
                :size,
                :stock_status,
                :raw_json::jsonb,
                :is_deleted,
                :updated_at_woo,
                :synced_at,
                :updated_at,
                :search_blob
            )
            ON CONFLICT (product_id) DO UPDATE SET
                data_json = EXCLUDED.data_json,
                name = EXCLUDED.name,
                price = EXCLUDED.price,
                permalink = EXCLUDED.permalink,
                featured_image = EXCLUDED.featured_image,
                real_image = EXCLUDED.real_image,
                short_description = EXCLUDED.short_description,
                description = EXCLUDED.description,
                categories = EXCLUDED.categories,
                tags = EXCLUDED.tags,
                brand = EXCLUDED.brand,
                gender = EXCLUDED.gender,
                size = EXCLUDED.size,
                stock_status = EXCLUDED.stock_status,
                raw_json = EXCLUDED.raw_json,
                is_deleted = EXCLUDED.is_deleted,
                updated_at_woo = COALESCE(EXCLUDED.updated_at_woo, wc_products_cache.updated_at_woo),
                synced_at = EXCLUDED.synced_at,
                updated_at = EXCLUDED.updated_at,
                search_blob = EXCLUDED.search_blob
        """), {
            "product_id": pid,
            "data_json": json.dumps(product, ensure_ascii=False),
            "name": (product.get("name") or "")[:300],
            "price": str(product.get("price") or "")[:60],
            "permalink": (product.get("permalink") or "")[:900],
            "featured_image": (product.get("featured_image") or "")[:900],
            "real_image": (product.get("real_image") or "")[:900],
            "short_description": (product.get("short_description") or "")[:2000],
            "description": (product.get("description") or "")[:5000],
            "categories": json.dumps(product.get("categories") or [], ensure_ascii=False),
            "tags": json.dumps(product.get("tags") or [], ensure_ascii=False),
            "brand": (product.get("brand") or "")[:200],
            "gender": (product.get("gender") or "")[:40],
            "size": (product.get("size") or "")[:60],
            "stock_status": (product.get("stock_status") or "")[:60],
            "raw_json": json.dumps(raw_json if isinstance(raw_json, dict) else product, ensure_ascii=False),
            "is_deleted": bool(is_deleted),
            "updated_at_woo": updated_at_woo,
            "synced_at": now,
            "updated_at": now,
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
            SELECT data_json
            FROM wc_products_cache
            WHERE product_id = :pid AND is_deleted = FALSE
            LIMIT 1
        """), {"pid": pid}).mappings().first()

    if not row:
        return None

    data = row.get("data_json")

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
            SELECT data_json, stock_status, ({score_sql}) AS score
            FROM wc_products_cache
            WHERE is_deleted = FALSE AND ({score_sql}) > 0
            ORDER BY
                CASE WHEN stock_status = 'instock' THEN 0 ELSE 1 END,
                score DESC,
                product_id DESC
            LIMIT :limit
        """), params).mappings().all()

    out = []
    for r in rows:
        data = r.get("data_json")
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
            UPDATE wc_products_cache
            SET is_deleted = TRUE, updated_at = NOW(), stock_status = 'deleted'
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