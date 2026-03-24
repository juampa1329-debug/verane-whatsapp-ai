from __future__ import annotations

import json
import re
import unicodedata
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

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_wc_cache_brand_lower
                ON wc_products_cache ((LOWER(COALESCE(data->>'brand', ''))))
            """))

            conn.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_wc_cache_sku_lower
                ON wc_products_cache ((LOWER(COALESCE(data->>'sku', ''))))
            """))
    except Exception:
        pass


_ensure_schema()


# =========================================================
# Utils
# =========================================================

def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def build_search_blob(p: dict) -> str:
    parts = []
    for k in ("name", "short_description", "description", "brand", "gender", "size", "sku", "slug"):
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

    stopwords = {
        "de", "del", "la", "las", "el", "los", "un", "una", "unos", "unas",
        "que", "para", "por", "con", "sin", "y", "o", "me", "mi", "tu",
        "favor", "porfa", "hola", "buenas", "gracias",
        "quiero", "busco", "tienes", "tienen", "hay", "dame", "muestrame",
        "enviame", "mandame", "precio", "stock", "disponible", "opciones",
        "perfume", "perfumes", "fragancia", "fragancias", "colonia", "colonias",
        "hombre", "mujer", "unisex",
    }
    tokens = [t for t in q.split() if len(t) >= 2 and t not in stopwords]
    if not tokens:
        tokens = [t for t in q.split() if len(t) >= 2]
    if not tokens:
        return []

    score_parts = []
    params: dict[str, Any] = {"limit": int(max(1, min(limit, 60)))}
    params["q_phrase"] = f"%{q}%"
    params["q_exact"] = q

    score_parts.append("(CASE WHEN LOWER(COALESCE(name, '')) LIKE :q_phrase THEN 120 ELSE 0 END)")
    score_parts.append("(CASE WHEN LOWER(COALESCE(search_blob, '')) LIKE :q_phrase THEN 35 ELSE 0 END)")
    score_parts.append("(CASE WHEN LOWER(COALESCE(data->>'sku', '')) = :q_exact THEN 160 ELSE 0 END)")

    for i, tok in enumerate(tokens[:8]):
        k = f"t{i}"
        params[k] = f"%{tok}%"
        score_parts.append(f"(CASE WHEN LOWER(COALESCE(name, '')) LIKE :{k} THEN 18 ELSE 0 END)")
        score_parts.append(f"(CASE WHEN LOWER(COALESCE(data->>'brand', '')) LIKE :{k} THEN 14 ELSE 0 END)")
        score_parts.append(f"(CASE WHEN LOWER(COALESCE(data->>'sku', '')) LIKE :{k} THEN 24 ELSE 0 END)")
        score_parts.append(f"(CASE WHEN LOWER(COALESCE(data->>'slug', '')) LIKE :{k} THEN 20 ELSE 0 END)")
        score_parts.append(f"(CASE WHEN LOWER(COALESCE(search_blob, '')) LIKE :{k} THEN 5 ELSE 0 END)")

    score_sql = " + ".join(score_parts) if score_parts else "0"

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
            SELECT
                COUNT(*) AS total,
                COUNT(*) FILTER (WHERE stock_status = 'instock') AS total_instock,
                COUNT(DISTINCT NULLIF(LOWER(TRIM(COALESCE(data->>'brand', ''))), '')) AS total_brands,
                COUNT(*) FILTER (WHERE NULLIF(TRIM(COALESCE(data->>'sku', '')), '') IS NOT NULL) AS total_with_sku,
                MAX(synced_at) AS last_synced_at
            FROM wc_products_cache
        """)).mappings().first()

    return {
        "total_products": int((row or {}).get("total") or 0),
        "total_instock": int((row or {}).get("total_instock") or 0),
        "total_brands": int((row or {}).get("total_brands") or 0),
        "total_with_sku": int((row or {}).get("total_with_sku") or 0),
        "last_synced_at": (
            row.get("last_synced_at").isoformat()
            if isinstance((row or {}).get("last_synced_at"), datetime)
            else None
        ),
    }


def list_cached_brands(*, q: str = "", limit: int = 200) -> list[str]:
    q_norm = _norm(q or "")
    params: dict[str, Any] = {"limit": int(max(1, min(limit, 1000)))}
    where_sql = ""
    if q_norm:
        params["q"] = f"%{q_norm}%"
        where_sql = """
            WHERE LOWER(TRIM(COALESCE(data->>'brand', ''))) LIKE :q
        """

    with engine.begin() as conn:
        rows = conn.execute(text(f"""
            SELECT DISTINCT TRIM(COALESCE(data->>'brand', '')) AS brand
            FROM wc_products_cache
            {where_sql}
            ORDER BY brand ASC
            LIMIT :limit
        """), params).mappings().all()

    out: list[str] = []
    for row in rows:
        value = str((row or {}).get("brand") or "").strip()
        if value:
            out.append(value)
    return out


def list_cached_references(
    *,
    q: str = "",
    brand: str = "",
    page: int = 1,
    per_page: int = 50,
    instock_only: bool = False,
) -> dict:
    safe_page = int(max(1, page))
    safe_per_page = int(max(1, min(per_page, 200)))
    offset = (safe_page - 1) * safe_per_page

    q_norm = _norm(q or "")
    brand_norm = _norm(brand or "")

    conds: list[str] = []
    params: dict[str, Any] = {
        "limit": safe_per_page,
        "offset": offset,
    }

    if q_norm:
        params["q"] = f"%{q_norm}%"
        conds.append("""
            (
                LOWER(COALESCE(name, '')) LIKE :q
                OR LOWER(COALESCE(data->>'sku', '')) LIKE :q
                OR LOWER(COALESCE(data->>'slug', '')) LIKE :q
            )
        """)

    if brand_norm:
        params["brand"] = f"%{brand_norm}%"
        conds.append("LOWER(COALESCE(data->>'brand', '')) LIKE :brand")

    if instock_only:
        conds.append("LOWER(COALESCE(stock_status, '')) = 'instock'")

    where_sql = ("WHERE " + " AND ".join(conds)) if conds else ""

    with engine.begin() as conn:
        total_row = conn.execute(text(f"""
            SELECT COUNT(*) AS total
            FROM wc_products_cache
            {where_sql}
        """), params).mappings().first()

        rows = conn.execute(text(f"""
            SELECT
                product_id,
                name,
                price,
                permalink,
                stock_status,
                synced_at,
                COALESCE(data->>'brand', '') AS brand,
                COALESCE(data->>'sku', '') AS sku,
                COALESCE(data->>'slug', '') AS slug
            FROM wc_products_cache
            {where_sql}
            ORDER BY
                CASE WHEN stock_status = 'instock' THEN 0 ELSE 1 END,
                synced_at DESC,
                product_id DESC
            LIMIT :limit OFFSET :offset
        """), params).mappings().all()

    items: list[dict] = []
    for row in rows:
        synced_at = row.get("synced_at")
        items.append({
            "product_id": int((row or {}).get("product_id") or 0),
            "name": str((row or {}).get("name") or ""),
            "brand": str((row or {}).get("brand") or ""),
            "sku": str((row or {}).get("sku") or ""),
            "slug": str((row or {}).get("slug") or ""),
            "price": str((row or {}).get("price") or ""),
            "stock_status": str((row or {}).get("stock_status") or ""),
            "permalink": str((row or {}).get("permalink") or ""),
            "synced_at": synced_at.isoformat() if isinstance(synced_at, datetime) else None,
        })

    total = int((total_row or {}).get("total") or 0)
    return {
        "items": items,
        "page": safe_page,
        "per_page": safe_per_page,
        "total": total,
    }
