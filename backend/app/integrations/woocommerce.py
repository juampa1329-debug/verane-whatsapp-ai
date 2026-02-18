# app/integrations/woocommerce.py
import os
import re
import io
import json
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


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = re.sub(r"[^a-z0-9áéíóúñü\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


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


def map_product_for_ui(product: dict) -> dict:
    price = product.get("price") or product.get("regular_price") or ""
    return {
        "id": product.get("id"),
        "name": product.get("name") or "",
        "price": str(price),
        "permalink": product.get("permalink") or "",
        "featured_image": pick_first_image(product),
        "short_description": (product.get("short_description") or "").strip(),
        "aromas": extract_aromas(product),
        "brand": extract_brand(product),
        "gender": extract_gender(product),
        "stock_status": product.get("stock_status") or "",
    }


async def wc_search_products(query: str, per_page: int = 8) -> List[dict]:
    q = (query or "").strip()
    if not q:
        return []

    async def _search_once(qx: str) -> List[dict]:
        params = {"search": qx, "page": 1, "per_page": int(per_page), "status": "publish"}
        data = await wc_get("/products", params=params)
        items = [map_product_for_ui(p) for p in (data or [])]
        items.sort(key=lambda x: (0 if (x.get("stock_status") == "instock") else 1, (x.get("name") or "")))
        return items

    # 1) intento normal
    items = await _search_once(q)
    if items:
        return items

    # 2) fallback: normaliza variaciones comunes (aqua/acqua, gio/giò, di/de)
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

    # 3) fallback: intenta por tokens clave (2-3 palabras)
    toks = [t for t in q2.split() if len(t) >= 2]
    if len(toks) >= 2:
        q3 = " ".join(toks[:3])
        if q3 and q3 not in (q, q2):
            items = await _search_once(q3)
            if items:
                return items

    return []



def looks_like_product_question(user_text: str) -> bool:
    t = _norm(user_text)
    if not t:
        return False

    generic = {
        "ok", "listo", "dale", "gracias", "perfecto", "de una", "vale", "bien",
        "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
    }
    if t in generic:
        return False

    triggers = [
        "tienes", "tienen", "hay", "disponible", "disponibles",
        "precio", "vale", "cuanto", "cuánto",
        "perfume", "fragancia", "colonia",
    ]
    if any(w in t for w in triggers):
        return True

    # texto corto: solo si parece marca/línea
    if len(t.split()) <= 6 and len(t) >= 6:
        strong_tokens = (
            "gio", "armani", "dior", "versace", "azzaro", "carolina",
            "nitro", "212", "one million", "paco", "rabanne",
        )
        return any(tok in t for tok in strong_tokens)

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


async def wc_fetch_product(product_id: int) -> dict:
    if not wc_enabled():
        raise HTTPException(status_code=500, detail="WC env vars not configured")
    return await wc_get(f"/products/{int(product_id)}", params={})


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


def build_caption(product: dict, featured_image: str, real_image: str, custom_caption: str = "") -> str:
    name = product.get("name", "") or ""
    price = product.get("price") or product.get("regular_price") or ""
    short_description = re.sub('<[^<]+?>', '', product.get("short_description", "") or "").strip()
    permalink = product.get("permalink", "") or ""

    brand = extract_brand(product)
    gender = extract_gender(product)
    gender_label = "Hombre" if gender == "hombre" else "Mujer" if gender == "mujer" else "Unisex" if gender == "unisex" else ""

    aromas_list = extract_aromas(product)
    aromas = ", ".join(aromas_list) if aromas_list else ""

    caption_lines = [f"✨ {name}"]
    if gender_label:
        caption_lines.append(f"👤 Para: {gender_label}")
    if aromas:
        caption_lines.append(f"🌿 Aromas: {aromas}")
    if price:
        caption_lines.append(f"💰 Precio: ${price}")
    if short_description:
        caption_lines.append(f"\n{short_description}")
    if permalink:
        caption_lines.append(f"\n🛒 Ver producto: {permalink}")
    if real_image:
        caption_lines.append(f"📸 Ver foto real: {real_image}")

    caption = (custom_caption or "").strip() or "\n".join(caption_lines)
    return caption.strip()
