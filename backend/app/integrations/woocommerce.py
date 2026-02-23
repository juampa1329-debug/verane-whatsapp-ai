# app/integrations/woocommerce.py

import os
import re
import io
from typing import Optional, List, Tuple

import httpx
from fastapi import HTTPException
from PIL import Image

# =========================================================
# CONFIG
# =========================================================

WC_BASE_URL = os.getenv("WC_BASE_URL", "").rstrip("/")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY", "")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET", "")


def wc_enabled() -> bool:
    return bool(WC_BASE_URL and WC_CONSUMER_KEY and WC_CONSUMER_SECRET)


# =========================================================
# Text utils / heuristics
# =========================================================

def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9áéíóúñü\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _strip_html(s: str) -> str:
    return re.sub(r"<[^<]+?>", " ", (s or "")).strip()


def _shorten(s: str, max_chars: int = 260) -> str:
    s = re.sub(r"\s+", " ", (s or "").strip())
    if len(s) <= max_chars:
        return s
    cut = s[:max_chars].rsplit(" ", 1)[0].strip()
    return (cut + "…").strip()


def _looks_like_preference_query(q: str) -> bool:
    """
    Heurística: si el texto parece describir gustos/ocasión (no nombre exacto),
    usamos un fallback de búsqueda amplia para traer productos y rankear después.

    IMPORTANTE: NO usar "2+ palabras" como criterio (eso dispara falsos positivos).
    """
    t = _norm(q)
    if not t:
        return False

    # Si hay números/modelos típicos -> probablemente nombre
    if re.search(r"\b\d{2,4}\b", t):
        return False

    # Si contiene tokens de marcas comunes -> probablemente nombre
    brandish = [
        "dior", "versace", "armani", "azzaro", "carolina", "rabanne", "paco",
        "givenchy", "jean", "gaultier", "valentino", "gucci", "prada", "ysl",
        "tom ford", "hugo", "boss", "lacoste", "bvlgari", "bulgari",
    ]
    if any(b in t for b in brandish):
        return False

    # Palabras típicas de preferencias (dominio perfumes)
    prefs = [
        "maduro", "elegante", "serio", "juvenil", "seductor", "sofisticado",
        "oficina", "trabajo", "diario", "noche", "fiesta", "cita", "formal",
        "fresco", "dulce", "seco", "amader", "ambar", "vainill", "citr",
        "acuatic", "aromatic", "espec", "cuero", "almizcl", "iris", "floral",
        "gourmand", "proyeccion", "proyección", "duracion", "duración", "intenso", "suave",
        "verano", "invierno", "calor", "frio",
        "unisex", "hombre", "mujer", "mascul", "femen",
        "presupuesto", "hasta", "me alcanza", "barato", "economico", "económico",
    ]
    return any(p in t for p in prefs)


# =========================================================
# Woo API
# =========================================================

async def wc_get(path: str, params: dict | None = None):
    if not wc_enabled():
        raise HTTPException(status_code=500, detail="WooCommerce env vars not set")

    url = f"{WC_BASE_URL}/wp-json/wc/v3{path}"
    params = params or {}
    params["consumer_key"] = WC_CONSUMER_KEY
    params["consumer_secret"] = WC_CONSUMER_SECRET

    try:
        async with httpx.AsyncClient(timeout=20, headers={"User-Agent": "verane-bot/1.0"}) as client:
            r = await client.get(url, params=params)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"WooCommerce request error: {e}")

    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"WooCommerce error {r.status_code}: {r.text}")

    return r.json()


# =========================================================
# Product extractors
# =========================================================

def pick_first_image(product: dict) -> Optional[str]:
    imgs = product.get("images") or []
    if imgs and isinstance(imgs, list):
        src = (imgs[0] or {}).get("src")
        return src
    return None


def extract_aromas(product: dict) -> List[str]:
    out: List[str] = []
    attrs = product.get("attributes") or []
    for a in attrs:
        if not isinstance(a, dict):
            continue
        name = (a.get("name") or "").strip().lower()
        if name == "aromas":
            opts = a.get("options") or []
            if isinstance(opts, list):
                out = [str(x).strip() for x in opts if str(x).strip()]
    return out


def extract_brand(product: dict) -> str:
    for md in (product.get("meta_data") or []):
        if not isinstance(md, dict):
            continue
        k = (md.get("key") or "").lower().strip()
        if k in ("brand", "_brand", "pa_brand", "product_brand", "yith_wcbm_brand"):
            v = md.get("value")
            if isinstance(v, str) and v.strip():
                return v.strip()

    for a in (product.get("attributes") or []):
        if not isinstance(a, dict):
            continue
        nm = (a.get("name") or "").lower().strip()
        if nm in ("brand", "marca"):
            opts = a.get("options") or []
            if isinstance(opts, list) and opts:
                return str(opts[0]).strip()

    tags = product.get("tags") or []
    if isinstance(tags, list) and tags:
        t0 = tags[0]
        if isinstance(t0, dict) and (t0.get("name") or "").strip():
            return (t0.get("name") or "").strip()

    return ""


def extract_gender(product: dict) -> str:
    cats = product.get("categories") or []
    names = []
    for c in cats:
        if isinstance(c, dict) and c.get("name"):
            names.append(str(c["name"]).lower())

    if any("hombre" in n for n in names):
        return "hombre"
    if any("mujer" in n for n in names):
        return "mujer"
    if any("unisex" in n for n in names):
        return "unisex"
    return ""


def extract_size(product: dict) -> str:
    """Extrae el tamaño o presentación (ej: 100ml) para diferenciar productos homónimos"""
    for a in (product.get("attributes") or []):
        if not isinstance(a, dict):
            continue
        nm = (a.get("name") or "").lower().strip()
        if nm in (
            "tamaño", "tamano", "size", "volumen", "mililitros", "ml",
            "capacidad", "presentacion", "presentación"
        ):
            opts = a.get("options") or []
            if isinstance(opts, list) and opts:
                return str(opts[0]).strip()
    return ""


def _safe_categories(product: dict) -> List[dict]:
    cats = product.get("categories") or []
    out: List[dict] = []
    if isinstance(cats, list):
        for c in cats:
            if isinstance(c, dict):
                nm = (c.get("name") or "").strip()
                if nm:
                    out.append({"name": nm})
    return out


def _safe_tags(product: dict) -> List[dict]:
    tags = product.get("tags") or []
    out: List[dict] = []
    if isinstance(tags, list):
        for t in tags:
            if isinstance(t, dict):
                nm = (t.get("name") or "").strip()
                if nm:
                    out.append({"name": nm})
    return out


def map_product_for_ui(product: dict) -> dict:
    """
    Mapea el producto a un dict amigable para IA/UI.

    - Incluye 'description' limpia.
    - Incluye 'categories' y 'tags' para ranking.
    """
    price = product.get("price") or product.get("regular_price") or ""
    size = extract_size(product)
    name = product.get("name") or ""

    if size and size.lower() not in name.lower():
        name = f"{name} ({size})"

    short_description_raw = (product.get("short_description") or "").strip()
    description_raw = (product.get("description") or "").strip()

    short_description_clean = _shorten(_strip_html(short_description_raw), 260)
    description_clean = _shorten(_strip_html(description_raw), 520)

    cats = _safe_categories(product)
    tags = _safe_tags(product)

    return {
        "id": product.get("id"),
        "name": name,
        "price": str(price),
        "permalink": product.get("permalink") or "",
        "featured_image": pick_first_image(product),

        "short_description": short_description_clean,
        "description": description_clean,

        "categories": cats,
        "tags": tags,

        "aromas": extract_aromas(product),
        "brand": extract_brand(product),
        "gender": extract_gender(product),
        "size": size,
        "stock_status": product.get("stock_status") or "",
    }


# =========================================================
# Search / matching
# =========================================================

async def wc_search_products(query: str, per_page: int = 8) -> List[dict]:
    """
    Búsqueda Woo robusta:
    - intenta normal
    - fallback normalizaciones
    - fallback tokens
    - si el query parece SOLO preferencias: búsqueda amplia ("perfume")
    """
    q = (query or "").strip()
    if not q:
        return []

    is_pref = _looks_like_preference_query(q)
    base_q = "perfume" if is_pref else q

    effective_per_page = int(per_page)
    if is_pref:
        effective_per_page = max(effective_per_page, 24)

    async def _search_once(qx: str) -> List[dict]:
        params = {"search": qx, "page": 1, "per_page": int(effective_per_page), "status": "publish"}
        data = await wc_get("/products", params=params)
        items = [map_product_for_ui(p) for p in (data or [])]
        items.sort(key=lambda x: (0 if (x.get("stock_status") == "instock") else 1, (x.get("name") or "")))
        return items

    items = await _search_once(base_q)
    if items:
        return items

    if is_pref:
        return []

    q2 = _norm(q)
    q2 = q2.replace("aqua de gio", "acqua di gio")
    q2 = q2.replace("acqua de gio", "acqua di gio")
    q2 = q2.replace("aqua di gio", "acqua di gio")
    q2 = q2.replace("aqua", "acqua")
    q2 = q2.replace(" de ", " di ")

    if q2 and q2 != q:
        items = await _search_once(q2)
        if items:
            return items

    toks = [t for t in q2.split() if len(t) >= 2]
    if len(toks) >= 2:
        q3 = " ".join(toks[:3])
        if q3 and q3 not in (q, q2):
            items = await _search_once(q3)
            if items:
                return items

    return []


def looks_like_product_question(user_text: str) -> bool:
    """
    Detector de intención Woo (más estricto para evitar interceptar todo):
    - Se activa por señales claras: precio, stock, disponibilidad, buscar/recomendar, perfume/fragancia + verbo
    - Evita dispararse por "tienes/hay" solos
    """
    t = _norm(user_text)
    if not t:
        return False

    generic = {
        "ok", "listo", "dale", "gracias", "perfecto", "de una", "vale", "bien",
        "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
    }
    if t in generic:
        return False

    strong_signals = [
        "precio", "vale", "cuanto", "cuánto", "cost", "valor",
        "disponible", "disponibles", "stock", "hay stock", "agotado",
        "envio", "envío", "domicilio",
        "recomiend", "recomendar", "suger", "buscar", "encuentra", "muest", "muestr",
    ]
    if any(s in t for s in strong_signals):
        return True

    domain_words = ["perfume", "fragancia", "colonia"]
    has_domain = any(w in t for w in domain_words)

    generic_verbs = ["tienes", "tienen", "hay", "manej", "venden", "ofrecen"]
    has_generic_verb = any(v in t for v in generic_verbs)

    strong_tokens = (
        "gio", "armani", "dior", "versace", "azzaro", "carolina",
        "nitro", "212", "one million", "paco", "rabanne",
        "tom ford", "gucci", "prada", "ysl", "valentino", "gaultier",
    )
    has_brandish = any(tok in t for tok in strong_tokens)

    if has_generic_verb and (has_domain or has_brandish):
        return True

    if len(t.split()) <= 6 and len(t) >= 6:
        return has_brandish

    return False


def score_product_match(query: str, product_name: str) -> int:
    q = _norm(query)
    n = _norm(product_name)
    if not q or not n:
        return 0
    if n == q:
        return 100
    if q in n:
        cover = int(50 + min(40, (len(q) * 40) / max(1, len(n))))
        return cover
    qwords = [w for w in q.split() if len(w) >= 3]
    if not qwords:
        return 0
    hit = sum(1 for w in qwords if w in n)
    if hit == 0:
        return 0
    return 20 + hit * 10


def parse_choice_number(user_text: str) -> Optional[int]:
    m = re.search(r"\b([1-9])\b", (user_text or "").strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


# =========================================================
# Fetch product
# =========================================================

async def wc_fetch_product(product_id: int) -> dict:
    if not wc_enabled():
        raise HTTPException(status_code=500, detail="WC env vars not configured")
    return await wc_get(f"/products/{int(product_id)}", params={})


# =========================================================
# Image helpers for WhatsApp
# =========================================================

async def download_image_bytes(url: str) -> Tuple[bytes, str]:
    if not url:
        raise HTTPException(status_code=400, detail="Image url missing")

    try:
        async with httpx.AsyncClient(timeout=25) as client:
            r = await client.get(url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Image download failed: {e}")

    if r.status_code != 200 or not r.content:
        raise HTTPException(status_code=502, detail=f"Image download failed: {r.status_code}")

    content_type = (r.headers.get("Content-Type") or "").lower()
    return r.content, content_type


def _to_jpeg_bytes(src_bytes: bytes) -> bytes:
    im = Image.open(io.BytesIO(src_bytes))
    im = im.convert("RGB")
    out = io.BytesIO()
    im.save(out, format="JPEG", quality=88, optimize=True)
    return out.getvalue()


def ensure_whatsapp_image_compat(image_bytes: bytes, content_type: str, image_url: str) -> Tuple[bytes, str]:
    """
    WhatsApp: mejor JPEG/PNG. Convertimos AVIF/WEBP u otros raros a JPEG.
    """
    lower_url = (image_url or "").lower()
    needs_convert = (
        ("image/avif" in (content_type or "")) or ("image/webp" in (content_type or "")) or
        lower_url.endswith(".avif") or lower_url.endswith(".webp")
    )

    try:
        if needs_convert:
            return _to_jpeg_bytes(image_bytes), "image/jpeg"

        mime_type = content_type if (content_type or "").startswith("image/") else "image/jpeg"
        if mime_type not in ("image/jpeg", "image/png"):
            return _to_jpeg_bytes(image_bytes), "image/jpeg"

        return image_bytes, mime_type
    except Exception as e:
        try:
            return _to_jpeg_bytes(image_bytes), "image/jpeg"
        except Exception:
            raise HTTPException(status_code=500, detail=f"Image decode/convert failed: {e}")


# =========================================================
# Caption builder
# =========================================================

def build_caption(product: dict, featured_image: str, real_image: str, custom_caption: str = "") -> str:
    """
    Caption para WhatsApp "tarjeta" + texto.
    """
    name = (product.get("name", "") or "").strip()
    price = product.get("price") or product.get("regular_price") or ""
    permalink = (product.get("permalink", "") or "").strip()

    brand = extract_brand(product)
    gender = extract_gender(product)
    gender_label = "Hombre" if gender == "hombre" else "Mujer" if gender == "mujer" else "Unisex" if gender == "unisex" else ""

    aromas_list = extract_aromas(product)
    aromas = ", ".join(aromas_list) if aromas_list else ""

    size = (product.get("size") or "").strip() or extract_size(product)

    short_description_raw = product.get("short_description", "") or ""
    short_description = _shorten(_strip_html(short_description_raw), 260)

    caption_lines = []
    if name:
        caption_lines.append(f"✨ {name}")
    if size:
        caption_lines.append(f"📏 Tamaño: {size}")
    if brand:
        caption_lines.append(f"🏷️ Marca: {brand}")
    if gender_label:
        caption_lines.append(f"👤 Para: {gender_label}")
    if aromas:
        caption_lines.append(f"🌿 Aromas: {aromas}")
    if price:
        caption_lines.append(f"💰 Precio: ${price}")
    if short_description:
        caption_lines.append(f"\n📝 {short_description}")
    if permalink:
        caption_lines.append(f"\n🛒 Ver producto: {permalink}")
    if real_image:
        caption_lines.append(f"📸 Ver foto real: {real_image}")

    caption = (custom_caption or "").strip() or "\n".join(caption_lines)
    return caption.strip()