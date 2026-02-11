import os
import re
from datetime import datetime
from typing import Optional
from app.routes.whatsapp import send_whatsapp_text
from fastapi import UploadFile, File, Form


import requests
from fastapi import FastAPI, Request, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text

# ✅ Router externo WhatsApp
from app.routes.whatsapp import router as whatsapp_router

# =========================================================
# APP
# =========================================================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(whatsapp_router)

# =========================================================
# DATABASE
# =========================================================

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)

LAST_PRODUCT_CACHE: dict[str, dict] = {}

def ensure_schema():
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations (
                phone TEXT PRIMARY KEY,
                takeover BOOLEAN NOT NULL DEFAULT FALSE,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
                first_name TEXT,
                last_name TEXT,
                city TEXT,
                customer_type TEXT,
                interests TEXT,
                tags TEXT,
                notes TEXT
            )
        """))

        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS messages (
                id SERIAL PRIMARY KEY,
                phone TEXT NOT NULL,
                direction TEXT NOT NULL,
                msg_type TEXT NOT NULL DEFAULT 'text',
                text TEXT NOT NULL DEFAULT '',
                media_url TEXT,
                media_caption TEXT,
                featured_image TEXT,
                real_image TEXT,
                permalink TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

ensure_schema()

# =========================================================
# MODELS
# =========================================================

class IngestMessage(BaseModel):
    phone: str
    direction: str
    msg_type: str = "text"  # text | image | video | document | product
    phone: str
    direction: str
    msg_type: str = "text"
    text: str = ""
    media_url: Optional[str] = None
    media_caption: Optional[str] = None
    featured_image: Optional[str] = None
    real_image: Optional[str] = None
    permalink: Optional[str] = None
    media_id: Optional[str] = None


    # texto normal (o caption / descripción del producto)
    text: str = ""

    # media (imagen / video / documento)
    media_url: Optional[str] = None
    media_caption: Optional[str] = None

    # producto (tarjeta como tu screenshot)
    featured_image: Optional[str] = None   # imagen bonita (catálogo)
    real_image: Optional[str] = None       # foto real (galería)
    permalink: Optional[str] = None        # link del producto


class BotReplyIn(BaseModel):
    phone: str
    text: str

class CRMIn(BaseModel):
    phone: str
    first_name: str = ""
    last_name: str = ""
    city: str = ""
    customer_type: str = ""
    interests: str = ""
    tags: str = ""
    notes: str = ""

class TakeoverPayload(BaseModel):
    phone: str
    takeover: bool

# =========================================================
# HELPERS
# =========================================================

def save_message(
    conn,
    phone: str,
    direction: str,
    text_msg: str = "",
    msg_type: str = "text",
    media_url: Optional[str] = None,
    media_caption: Optional[str] = None,
    featured_image: Optional[str] = None,
    real_image: Optional[str] = None,
    permalink: Optional[str] = None,
):
    conn.execute(text("""
        INSERT INTO messages (
            phone, direction, msg_type, text,
            media_url, media_caption,
            featured_image, real_image, permalink, created_at
        )
        VALUES (
            :phone, :direction, :msg_type, :text,
            :media_url, :media_caption,
            :featured_image, :real_image, :permalink, :created_at
        )
    """), {
        "phone": phone,
        "direction": direction,
        "msg_type": msg_type,
        "text": text_msg,
        "media_url": media_url,
        "media_caption": media_caption,
        "featured_image": featured_image,
        "real_image": real_image,
        "permalink": permalink,
        "created_at": datetime.utcnow(),
    })

    conn.execute(text("""
        INSERT INTO conversations (phone, updated_at)
        VALUES (:phone, :updated_at)
        ON CONFLICT (phone) DO UPDATE SET updated_at = EXCLUDED.updated_at
    """), {
        "phone": phone,
        "updated_at": datetime.utcnow()
    })


# =========================================================
# ENDPOINTS
# =========================================================

@app.get("/api/health")
def health():
    return {"ok": True}

@app.post("/api/media/upload")
async def upload_media(file: UploadFile = File(...), kind: str = Form("image")):
    """
    Recibe archivo desde el frontend (PC local), lo sube a WhatsApp y devuelve media_id.
    kind: image | video | audio | document
    """
    kind = (kind or "image").lower().strip()

    if kind not in ("image", "video", "audio", "document"):
        raise HTTPException(status_code=400, detail="Invalid kind")

    content = await file.read()
    mime = file.content_type or "application/octet-stream"

    from app.routes.whatsapp import upload_whatsapp_media
    media_id = await upload_whatsapp_media(content, mime)

    return {
        "ok": True,
        "media_id": media_id,
        "mime_type": mime,
        "filename": file.filename,
        "kind": kind
    }


@app.get("/api/conversations")
def get_conversations():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT phone, takeover, updated_at
            FROM conversations
            ORDER BY updated_at DESC
            LIMIT 200
        """)).mappings().all()
    return {"conversations": [dict(r) for r in rows]}

@app.get("/api/conversations/{phone}/messages")
def get_messages(phone: str):
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT id, phone, direction, msg_type, text,
                   featured_image, real_image, permalink, created_at
            FROM messages
            WHERE phone = :phone
            ORDER BY created_at ASC
            LIMIT 500
        """), {"phone": phone}).mappings().all()
    return {"messages": [dict(r) for r in rows]}

@app.post("/api/messages/ingest")
async def ingest(msg: IngestMessage):
    direction = msg.direction if msg.direction in ("in", "out") else "in"
    msg_type = (msg.msg_type or "text").strip().lower()

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, takeover, updated_at)
            VALUES (:phone, FALSE, :updated_at)
            ON CONFLICT (phone) DO UPDATE SET updated_at = EXCLUDED.updated_at
        """), {"phone": msg.phone, "updated_at": datetime.utcnow()})

        save_message(
            conn,
            phone=msg.phone,
            direction=direction,
            msg_type=msg_type,
            text_msg=msg.text or "",
            media_url=msg.media_url,
            media_caption=msg.media_caption,
            featured_image=msg.featured_image,
            real_image=msg.real_image,
            permalink=msg.permalink,
        )

    # --- ENVIAR A WHATSAPP SOLO SI ES OUT ---
    if direction == "out":
        # ✅ Adjuntos reales (imagen/video/audio/document) usando media_id
        if msg_type in ("image", "video", "audio", "document"):
            if not msg.media_id:
                return {"saved": True, "sent": False, "reason": "media_id is required for media messages"}

            from app.routes.whatsapp import send_whatsapp_media_id
            return await send_whatsapp_media_id(
                to_phone=msg.phone,
                media_type=msg_type,
                media_id=msg.media_id,
                caption=msg.media_caption or msg.text or ""
            )

        # ✅ Producto (por ahora texto con links; luego lo mejoramos a imagen adjunta + texto)
        if msg_type == "product":
            body = (msg.text or "").strip()

            extra_lines = []
            if msg.permalink:
                extra_lines.append(f"🛒 Ver producto: {msg.permalink}")
            if msg.real_image:
                extra_lines.append(f"📸 Ver foto real: {msg.real_image}")

            if extra_lines:
                body = (body + "\n\n" + "\n".join(extra_lines)).strip()

            return await send_whatsapp_text(msg.phone, body)

        # ✅ Texto normal
        return await send_whatsapp_text(msg.phone, msg.text or "")

    return {"saved": True}





@app.post("/api/conversations/takeover")
def set_takeover(payload: TakeoverPayload):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, takeover, updated_at)
            VALUES (:phone, :takeover, :updated_at)
            ON CONFLICT (phone)
            DO UPDATE SET takeover = EXCLUDED.takeover,
                          updated_at = EXCLUDED.updated_at
        """), {
            "phone": payload.phone,
            "takeover": payload.takeover,
            "updated_at": datetime.utcnow()
        })
    return {"ok": True}

@app.post("/api/crm")
def save_crm(payload: CRMIn):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (
                phone, updated_at, first_name, last_name,
                city, customer_type, interests, tags, notes
            )
            VALUES (
                :phone, :updated_at, :first_name, :last_name,
                :city, :customer_type, :interests, :tags, :notes
            )
            ON CONFLICT (phone) DO UPDATE SET
              updated_at = EXCLUDED.updated_at,
              first_name = EXCLUDED.first_name,
              last_name = EXCLUDED.last_name,
              city = EXCLUDED.city,
              customer_type = EXCLUDED.customer_type,
              interests = EXCLUDED.interests,
              tags = EXCLUDED.tags,
              notes = EXCLUDED.notes
        """), {
            "phone": payload.phone,
            "updated_at": datetime.utcnow(),
            "first_name": payload.first_name,
            "last_name": payload.last_name,
            "city": payload.city,
            "customer_type": payload.customer_type,
            "interests": payload.interests,
            "tags": payload.tags,
            "notes": payload.notes,
        })
    return {"ok": True}

@app.get("/api/crm/{phone}")
def get_crm(phone: str):
    with engine.begin() as conn:
        r = conn.execute(text("""
            SELECT phone, first_name, last_name, city,
                   customer_type, interests, tags, notes
            FROM conversations
            WHERE phone = :phone
        """), {"phone": phone}).mappings().first()
    return dict(r) if r else {"phone": phone}

@app.post("/api/messages/send")
def send_message(phone: str = Query(...), text_msg: str = Query(...)):
    with engine.begin() as conn:
        save_message(conn, phone, "out", text_msg)
    return {"ok": True}



# =========================================================
# WOOCOMMERCE (CATÁLOGO + ENVÍO COMO ADJUNTO REAL)
# =========================================================

WC_BASE_URL = os.getenv("WC_BASE_URL", "").rstrip("/")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY", "")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET", "")

def _wc_enabled() -> bool:
    return bool(WC_BASE_URL and WC_CONSUMER_KEY and WC_CONSUMER_SECRET)

def _wc_get(path: str, params: dict | None = None):
    """
    WooCommerce REST API v3 helper.
    Usa query auth (ck/cs) por simplicidad.
    """
    if not _wc_enabled():
        raise HTTPException(status_code=500, detail="WooCommerce env vars not set")

    url = f"{WC_BASE_URL}/wp-json/wc/v3{path}"
    params = params or {}
    params["consumer_key"] = WC_CONSUMER_KEY
    params["consumer_secret"] = WC_CONSUMER_SECRET

    try:
        r = requests.get(url, params=params, timeout=20)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"WooCommerce request error: {e}")

    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"WooCommerce error {r.status_code}: {r.text}")

    return r.json()

def _pick_first_image(product: dict) -> str | None:
    # WC v3 trae lista `images`
    imgs = product.get("images") or []
    if imgs and isinstance(imgs, list):
        src = (imgs[0] or {}).get("src")
        return src
    return None

def _extract_aromas(product: dict) -> list[str]:
    """
    En tu JSON ejemplo, Aromas está en attributes name="Aromas" con options.
    En WC real, suele venir en product["attributes"] con name y options.
    """
    out: list[str] = []
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

def _extract_brand(product: dict) -> str:
    """
    Marca puede venir como:
    - metadata / brands plugin
    - attributes
    - tags
    Como no tenemos el JSON real de WC v3 de tu tienda aquí,
    usamos una estrategia conservadora:
    1) meta_data con keys comunes
    2) atributo llamado "brand" o "marca"
    3) tags (si manejas marca como tag)
    """
    # 1) meta_data
    for md in (product.get("meta_data") or []):
        if not isinstance(md, dict):
            continue
        k = (md.get("key") or "").lower().strip()
        if k in ("brand", "_brand", "pa_brand", "product_brand", "yith_wcbm_brand"):
            v = md.get("value")
            if isinstance(v, str) and v.strip():
                return v.strip()

    # 2) attributes
    for a in (product.get("attributes") or []):
        if not isinstance(a, dict):
            continue
        nm = (a.get("name") or "").lower().strip()
        if nm in ("brand", "marca"):
            opts = a.get("options") or []
            if isinstance(opts, list) and opts:
                return str(opts[0]).strip()

    # 3) tags
    tags = product.get("tags") or []
    if isinstance(tags, list) and tags:
        # si tags trae objetos {name}
        t0 = tags[0]
        if isinstance(t0, dict) and (t0.get("name") or "").strip():
            return (t0.get("name") or "").strip()

    return ""

def _extract_gender(product: dict) -> str:
    """
    Si manejas Hombre/Mujer como categories:
    product["categories"] -> [{name: "Hombre"}]
    """
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

def _map_product_for_ui(product: dict) -> dict:
    price = product.get("price") or product.get("regular_price") or ""
    return {
        "id": product.get("id"),
        "name": product.get("name") or "",
        "price": str(price),
        "permalink": product.get("permalink") or "",
        "featured_image": _pick_first_image(product),
        "short_description": (product.get("short_description") or "").strip(),
        "aromas": _extract_aromas(product),
        "brand": _extract_brand(product),
        "gender": _extract_gender(product),
        "stock_status": product.get("stock_status") or "",
    }

@app.get("/api/wc/products")
def wc_products(
    q: str = Query("", description="texto de búsqueda"),
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=50),
):
    """
    Para el modal del frontend y para la IA.
    """
    params = {
        "search": q or "",
        "page": page,
        "per_page": per_page,
        "status": "publish",
    }
    data = _wc_get("/products", params=params)
    items = [_map_product_for_ui(p) for p in (data or [])]
    return {"products": items}

class SendWCProductIn(BaseModel):
    phone: str
    product_id: int
    caption: str = ""  # opcional: si viene vacío, armamos uno

@app.post("/api/wc/send-product")
async def send_wc_product(payload: dict):
    """
    Envía un producto WooCommerce como imagen adjunta real + caption.
    """
    phone = payload.get("phone")
    product_id = payload.get("product_id")
    custom_caption = payload.get("caption", "")

    if not phone or not product_id:
        raise HTTPException(status_code=400, detail="phone and product_id required")

    # --- Woo credentials ---
    WC_BASE_URL = os.getenv("WC_BASE_URL")
    WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
    WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

    if not WC_BASE_URL:
        raise HTTPException(status_code=500, detail="WC_BASE_URL not configured")

    # --- Obtener producto desde Woo ---
    url = f"{WC_BASE_URL}/wp-json/wc/v3/products/{product_id}"
    params = {
        "consumer_key": WC_CONSUMER_KEY,
        "consumer_secret": WC_CONSUMER_SECRET
    }

    r = requests.get(url, params=params)
    if r.status_code != 200:
        raise HTTPException(status_code=500, detail="WooCommerce product fetch failed")

    product = r.json()

    # --- Imagen destacada ---
    images = product.get("images") or []
    if not images:
        raise HTTPException(status_code=400, detail="Product has no image")

    featured_image = images[0].get("src")

    # --- Descargar imagen ---
    img_response = requests.get(featured_image)
    if img_response.status_code != 200:
        raise HTTPException(status_code=500, detail="Image download failed")

    image_bytes = img_response.content
    mime_type = img_response.headers.get("Content-Type", "image/jpeg")

    # --- Subir a WhatsApp ---
    from app.routes.whatsapp import upload_whatsapp_media, send_whatsapp_media_id

    media_id = await upload_whatsapp_media(image_bytes, mime_type)

    # --- Construir caption ---
    name = product.get("name", "")
    price = product.get("price", "")
    short_description = re.sub('<[^<]+?>', '', product.get("short_description", "") or "")
    permalink = product.get("permalink", "")

    caption_lines = [f"✨ {name}"]
    if price:
        caption_lines.append(f"💰 Precio: ${price}")
    if short_description:
        caption_lines.append(f"\n{short_description}")
    if permalink:
        caption_lines.append(f"\n🛒 Ver producto: {permalink}")

    caption = custom_caption if custom_caption else "\n".join(caption_lines)

    # --- Guardar en DB ---
    with engine.begin() as conn:
        save_message(
            conn,
            phone=phone,
            direction="out",
            msg_type="product",
            text_msg=caption,
            featured_image=featured_image,
            permalink=permalink
        )

    # --- Enviar imagen real ---
    return await send_whatsapp_media_id(
        to_phone=phone,
        media_type="image",
        media_id=media_id,
        caption=caption
    )

