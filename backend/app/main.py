import os
import re
import json
from datetime import datetime
from typing import Optional
from fastapi import FastAPI, Request, HTTPException, Query, Body


import requests
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from fastapi import FastAPI
from app.routes.whatsapp import router as whatsapp_router

app = FastAPI()
app.include_router(whatsapp_router)


DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, pool_pre_ping=True)

# Cache simple en memoria (solo para local/dev)
LAST_PRODUCT_CACHE: dict[str, dict] = {}


def ensure_schema():
    # IMPORTANTE: DDL con AUTOCOMMIT para evitar "current transaction is aborted"
    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")

        # conversations base
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS conversations (
                phone TEXT PRIMARY KEY,
                takeover BOOLEAN NOT NULL DEFAULT FALSE,
                updated_at TIMESTAMP NOT NULL DEFAULT NOW()
            )
        """))

        # messages base (con todas las columnas nuevas desde el inicio)
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

        # columnas CRM en conversations (por si la tabla ya existía vieja)
        conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS first_name TEXT"))
        conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS last_name TEXT"))
        conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS city TEXT"))
        conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS customer_type TEXT"))
        conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS interests TEXT"))
        conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS tags TEXT"))
        conn.execute(text("ALTER TABLE conversations ADD COLUMN IF NOT EXISTS notes TEXT"))

        # columnas nuevas en messages (por si la tabla ya existía vieja)
        conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS msg_type TEXT"))
        conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS media_url TEXT"))
        conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS media_caption TEXT"))
        conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS featured_image TEXT"))
        conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS real_image TEXT"))
        conn.execute(text("ALTER TABLE messages ADD COLUMN IF NOT EXISTS permalink TEXT"))

        # defaults para filas viejas si msg_type quedó NULL
        conn.execute(text("UPDATE messages SET msg_type='text' WHERE msg_type IS NULL"))


ensure_schema()
def ensure_conversation(conn, phone: str):
    conn.execute(text("""
        INSERT INTO conversations (phone, takeover, updated_at)
        VALUES (:phone, FALSE, :updated_at)
        ON CONFLICT (phone) DO UPDATE SET updated_at = EXCLUDED.updated_at
    """), {"phone": phone, "updated_at": datetime.utcnow()})

def save_message(
    conn,
    phone: str,
    direction: str,
    text_msg: str,
    msg_type: str = "text",
    media_url: str | None = None,
    media_caption: str | None = None,
    featured_image: str | None = None,
    real_image: str | None = None,
    permalink: str | None = None,
):
    ensure_conversation(conn, phone)
    conn.execute(text("""
        INSERT INTO messages (
            phone, direction, msg_type, text,
            media_url, media_caption, featured_image, real_image, permalink,
            created_at
        )
        VALUES (
            :phone, :direction, :msg_type, :text,
            :media_url, :media_caption, :featured_image, :real_image, :permalink,
            :created_at
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
        UPDATE conversations SET updated_at = :updated_at WHERE phone = :phone
    """), {"phone": phone, "updated_at": datetime.utcnow()})


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class IngestMessage(BaseModel):
    phone: str
    direction: str  # "in" o "out"
    text: str


class BotReplyIn(BaseModel):
    phone: str
    text: str


def strip_html(s: str) -> str:
    if not s:
        return ""
    # Reemplazar <br> con saltos de línea
    s = s.replace("<br>", "\n").replace("<br/>", "\n").replace("<br />", "\n")
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def normalize_woo_query(user_text: str) -> str:
    """Limpia texto del usuario para búsqueda en WooCommerce."""
    t = (user_text or "").lower().strip()
    # Quitar signos
    t = re.sub(r"[\?\!\.,;:¡¿\(\)\[\]\{\}\"']", " ", t)
    t = re.sub(r"\s+", " ", t).strip()

    stop_prefixes = [
        "tienes ", "tienen ", "hay ", "me das ", "me puedes ", "quiero ",
        "busca ", "buscame ", "tendras ", "tendra ", "precio de ", "info de "
    ]
    for pref in stop_prefixes:
        if t.startswith(pref):
            t = t[len(pref):].strip()

    stopwords = {
        "tienes", "tienen", "hay", "un", "una", "el", "la", "los", "las",
        "de", "del", "por", "para", "me", "porfa", "favor", "quiero",
        "quisiera", "busco", "buscar", "precio", "disponible"
    }

    tokens = [w for w in t.split() if w not in stopwords]
    q = " ".join(tokens).strip()

    # Si borramos todo (ej: solo escribió "precio"), devolvemos el original
    return q if len(q) > 1 else t


def wants_real_photo(user_text: str) -> bool:
    t = (user_text or "").lower()
    return any(k in t for k in ["foto real", "imagen real", "foto del producto", "ver foto"])


def get_attr_options(p: dict, attr_name: str) -> list[str]:
    attrs = p.get("attributes") or []
    out = []
    for a in attrs:
        name = (a.get("name") or "").strip().lower()
        if attr_name.strip().lower() in name:  # Match parcial para "Aromas" o "Notas Olfativas"
            opts = a.get("options") or []
            out.extend([str(x) for x in opts if str(x).strip()])
    return out


def pick_images(p: dict) -> tuple[str, str]:
    featured = ""
    real = ""

    # Intentar sacar imagen principal
    images = p.get("images") or []
    if images and isinstance(images, list):
        if len(images) > 0:
            featured = images[0].get("src") or ""
        if len(images) > 1:
            real = images[1].get("src") or ""

    # Fallback si 'real' está vacío, usamos la featured
    return featured, (real or featured)


WC_BASE_URL = os.getenv("WC_BASE_URL", "").strip()
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY", "").strip()
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET", "").strip()


def wc_get(resource: str, params: dict):
    if not WC_BASE_URL:
        return []
    base = WC_BASE_URL.rstrip("/")
    url = f"{base}/wp-json/wc/v3/{resource.lstrip('/')}"
    p = dict(params or {})
    p["consumer_key"] = WC_CONSUMER_KEY
    p["consumer_secret"] = WC_CONSUMER_SECRET
    try:
        r = requests.get(url, params=p, timeout=20)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"Woo Error: {e}")
        return []


def build_product_reply(p: dict) -> dict:
    name = (p.get("name", "") or "").strip()
    price = p.get("price") or p.get("regular_price") or ""

    # Limpieza de descripción
    raw_desc = p.get("short_description") or ""
    short_desc = strip_html(raw_desc)

    aromas = get_attr_options(p, "Aromas")  # O "Notas"
    brand = p.get("brand") or ""  # Ajusta si usas marcas como taxonomía

    featured_img, real_img = pick_images(p)

    # Formato moneda
    try:
        price_fmt = f"${int(float(price)):,.0f}".replace(",", ".")
    except:
        price_fmt = f"${price}"

    aromas_txt = ", ".join(aromas[:5]) if aromas else ""

    # Construcción del mensaje tipo "Tarjeta"
    # Título y Precio
    text_msg = f"✨ *{name}*\n💰 *{price_fmt} COP*\n"

    if brand:
        text_msg += f"🏷️ {brand}\n"

    # Descripción corta (truncada si es muy larga)
    if short_desc:
        limit = 180
        desc_cut = (short_desc[:limit] + '...') if len(short_desc) > limit else short_desc
        text_msg += f"\n_{desc_cut}_\n"

    # Aromas destacados
    if aromas_txt:
        text_msg += f"\n🌸 *Notas:* {aromas_txt}"

    # Cierre con pregunta
    text_msg += f"\n\n🔗 {p.get('permalink', '')}\n\n¿Te gustaría ver una foto real o lo agregamos al pedido?"

    return {
        "name": name,
        "price": price,
        "text": text_msg.strip(),
        "featured_image": featured_img,
        "real_image": real_img,
        "permalink": p.get("permalink", ""),
        "aromas": aromas,
    }


def handle_bot_message(user_text: str) -> dict:
    q_raw = (user_text or "").strip()

    # 1. ¿Pide foto real?
    if wants_real_photo(q_raw):
        return {"intent": "real_photo"}

    # 2. Buscar producto
    q = normalize_woo_query(q_raw)
    if not q:
        return {"text": "¿Qué perfume estás buscando? 😊"}

    print(f"Buscando en Woo: '{q}'")
    products = wc_get("products", {"search": q, "per_page": 5, "status": "publish"}) or []

    if not products:
        # Intento de fallback (a veces la búsqueda fuzzy de Woo necesita ayuda)
        return {
            "text": f"No encontré '*{q}*' 😕. ¿Podrías intentar con el nombre de la marca o una palabra clave?",
            "products": [],
        }

    # Tomamos el primero
    best = products[0]

    # (Opcional) Refinar búsqueda si el usuario fue específico
    # for p in products: ...

    product_card = build_product_reply(best)
    return {"text": product_card["text"], "product": product_card}


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
    conn.execute(
        text(
            """
            INSERT INTO messages (
                phone, direction, msg_type, text, media_url, media_caption, 
                featured_image, real_image, permalink, created_at
            )
            VALUES (
                :phone, :direction, :msg_type, :text, :media_url, :media_caption, 
                :featured_image, :real_image, :permalink, :created_at
            )
            """
        ),
        {
            "phone": phone,
            "direction": direction,
            "msg_type": msg_type,
            "text": text_msg or "",
            "media_url": media_url,
            "media_caption": media_caption,
            "featured_image": featured_image,
            "real_image": real_image,
            "permalink": permalink,
            "created_at": datetime.utcnow(),
        },
    )


@app.get("/api/health")
def health():
    return {"ok": True}


@app.get("/api/conversations")
def get_conversations():
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
            SELECT phone, takeover, updated_at
            FROM conversations
            ORDER BY updated_at DESC
            LIMIT 200
            """
            )
        ).mappings().all()
    return {"conversations": [dict(r) for r in rows]}


@app.get("/api/conversations/{phone}/messages")
def get_messages(phone: str):
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
            SELECT id, phone, direction, msg_type, text, media_url, media_caption, featured_image, real_image, permalink, created_at
            FROM messages
            WHERE phone = :phone
            ORDER BY created_at ASC
            LIMIT 500
            """
            ),
            {"phone": phone},
        ).mappings().all()
    return {"messages": [dict(r) for r in rows]}


@app.post("/api/messages/ingest")
def ingest(msg: IngestMessage):
    with engine.begin() as conn:
        conn.execute(
            text(
                """
            INSERT INTO conversations (phone, takeover, updated_at)
            VALUES (:phone, FALSE, :updated_at)
            ON CONFLICT (phone) DO UPDATE SET updated_at = EXCLUDED.updated_at
            """
            ),
            {"phone": msg.phone, "updated_at": datetime.utcnow()},
        )

        direction = msg.direction if msg.direction in ("in", "out") else "in"

        save_message(
            conn,
            msg.phone,
            msg.direction,
            text_msg=msg.text,
        )

    return {"saved": True}


@app.post("/api/bot/reply")
def bot_reply(payload: BotReplyIn):
    with engine.begin() as conn:
        # 1. Verificar Takeover
        row = conn.execute(text("SELECT takeover FROM conversations WHERE phone=:p"), {"p": payload.phone}).first()
        takeover = row[0] if row else False

        # Guardar mensaje del usuario
        save_message(conn, payload.phone, "in", payload.text)

        if takeover:
            return {"takeover": True}

        # 2. Generar respuesta
        result = handle_bot_message(payload.text)

        # 3. Manejar caso de Foto Real
        if result.get("intent") == "real_photo":
            prod = LAST_PRODUCT_CACHE.get(payload.phone)
            if prod:
                real_url = prod.get("real_image") or prod.get("featured_image")
                caption = f"📸 Foto real de *{prod.get('name', '')}*"
                save_message(
                    conn, payload.phone, "out", caption,
                    msg_type="product", featured_image=real_url, real_image=real_url,
                    permalink=prod.get("permalink"), media_caption=caption,
                )
                return {"text": caption, "reply": {"text": caption, "image": real_url}}

            # Si no hay producto previo en contexto
            out_text = "Claro, pero ¿de cuál producto te gustaría ver la foto?"
            save_message(conn, payload.phone, "out", out_text)
            return {"text": out_text}

        # 4. Manejar respuesta de Producto o Texto normal
        out_text = result.get("text", "")
        product = result.get("product")

        if product:
            LAST_PRODUCT_CACHE[payload.phone] = product
            # Guardar como mensaje tipo 'product' para que el frontend pinte la imagen
            save_message(
                conn, payload.phone, "out", out_text,
                msg_type="product",
                featured_image=product.get("featured_image"),
                real_image=product.get("real_image"),
                permalink=product.get("permalink"),
                media_caption=out_text,
            )
            return {"reply": product}

        # Texto normal (No encontrado o saludo)
        save_message(conn, payload.phone, "out", out_text)
        return {"text": out_text}



@app.get("/api/woo/products")
def woo_products(q: str = "", per_page: int = 20):
    data = wc_get("products", {"search": q, "per_page": per_page, "status": "publish"})
    products = []
    for p in data or []:
        featured_img, real_img = pick_images(p)
        aromas = get_attr_options(p, "Aromas")
        products.append({
            "id": p.get("id"),
            "name": p.get("name"),
            "price": p.get("price") or "",
            "image": featured_img,
            "short_description": strip_html(p.get("short_description") or ""),
            "aromas": ", ".join(aromas)
        })
    return {"products": products}

class CRMIn(BaseModel):
    phone: str
    first_name: str = ""
    last_name: str = ""
    city: str = ""
    customer_type: str = ""
    interests: str = ""
    tags: str = ""
    notes: str = ""

@app.post("/api/crm")
def save_crm(payload: CRMIn):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, updated_at, first_name, last_name, city, customer_type, interests, tags, notes)
            VALUES (:phone, :updated_at, :first_name, :last_name, :city, :customer_type, :interests, :tags, :notes)
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
            SELECT phone, first_name, last_name, city, customer_type, interests, tags, notes
            FROM conversations
            WHERE phone = :phone
        """), {"phone": phone}).mappings().first()
    return dict(r) if r else {"phone": phone}


@app.post("/api/messages/send")
def send_message(phone: str = Query(...), text_msg: str = Query(...)):
    with engine.begin() as conn:
        save_message(conn, phone, "out", text_msg, msg_type="text")
    return {"ok": True}

class TakeoverPayload(BaseModel):
    phone: str
    takeover: bool


@app.post("/api/conversations/takeover")
def set_takeover(payload: TakeoverPayload):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, takeover, updated_at)
            VALUES (:phone, :takeover, :updated_at)
            ON CONFLICT (phone)
            DO UPDATE SET takeover = EXCLUDED.takeover, updated_at = EXCLUDED.updated_at
        """), {
            "phone": payload.phone,
            "takeover": payload.takeover,
            "updated_at": datetime.utcnow()
        })
    return {"ok": True, "phone": payload.phone, "takeover": payload.takeover}




