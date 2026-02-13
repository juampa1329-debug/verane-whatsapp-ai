import os
import re
import requests
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text

# ✅ Router externo WhatsApp
from app.routes.whatsapp import router as whatsapp_router
from app.routes.whatsapp import send_whatsapp_text, send_whatsapp_media_id

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

from fastapi.responses import JSONResponse
from starlette.requests import Request as StarletteRequest

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: StarletteRequest, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={
            "ok": False,
            "error": str(exc),
            "path": str(request.url.path),
        },
    )

app.include_router(whatsapp_router)

# =========================================================
# DATABASE
# =========================================================

from app.db import engine

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

        # ✅ Media extra
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS media_id TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS mime_type TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS file_name TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS file_size INTEGER"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS duration_sec INTEGER"""))

        # ✅ Estados WhatsApp (checkmarks)
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_message_id TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_status TEXT"""))  # sent|delivered|read|failed
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_error TEXT"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_ts_sent TIMESTAMP"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_ts_delivered TIMESTAMP"""))
        conn.execute(text("""ALTER TABLE messages ADD COLUMN IF NOT EXISTS wa_ts_read TIMESTAMP"""))

ensure_schema()

# =========================================================
# MODELS
# =========================================================

class IngestMessage(BaseModel):
    model_config = {"extra": "allow"}

    phone: str
    direction: str
    msg_type: str = "text"  # text | image | video | audio | document | product

    text: str = ""

    media_url: Optional[str] = None
    media_caption: Optional[str] = None
    media_id: Optional[str] = None
    mime_type: Optional[str] = None
    file_name: Optional[str] = None
    file_size: Optional[int] = None
    duration_sec: Optional[int] = None

    featured_image: Optional[str] = None
    real_image: Optional[str] = None
    permalink: Optional[str] = None

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
    media_id: Optional[str] = None,
    mime_type: Optional[str] = None,
    file_name: Optional[str] = None,
    file_size: Optional[int] = None,
    duration_sec: Optional[int] = None,

    featured_image: Optional[str] = None,
    real_image: Optional[str] = None,
    permalink: Optional[str] = None,
) -> int:
    r = conn.execute(text("""
        INSERT INTO messages (
            phone, direction, msg_type, text,
            media_url, media_caption, media_id, mime_type, file_name, file_size, duration_sec,
            featured_image, real_image, permalink, created_at,
            wa_status, wa_ts_sent
        )
        VALUES (
            :phone, :direction, :msg_type, :text,
            :media_url, :media_caption, :media_id, :mime_type, :file_name, :file_size, :duration_sec,
            :featured_image, :real_image, :permalink, :created_at,
            :wa_status, :wa_ts_sent
        )
        RETURNING id
    """), {
        "phone": phone,
        "direction": direction,
        "msg_type": msg_type,
        "text": text_msg,
        "media_url": media_url,
        "media_caption": media_caption,
        "media_id": media_id,
        "mime_type": mime_type,
        "file_name": file_name,
        "file_size": file_size,
        "duration_sec": duration_sec,
        "featured_image": featured_image,
        "real_image": real_image,
        "permalink": permalink,
        "created_at": datetime.utcnow(),

        # ✅ si es OUT, el estado inicial visual será "sent" (en realidad: "queued local")
        # luego el webhook lo sube a delivered/read cuando WhatsApp lo notifica.
        "wa_status": "sent" if direction == "out" else None,
        "wa_ts_sent": datetime.utcnow() if direction == "out" else None,
    })

    message_id = int(r.scalar())

    conn.execute(text("""
        INSERT INTO conversations (phone, updated_at)
        VALUES (:phone, :updated_at)
        ON CONFLICT (phone) DO UPDATE SET updated_at = EXCLUDED.updated_at
    """), {"phone": phone, "updated_at": datetime.utcnow()})

    return message_id

def set_wa_send_result(conn, local_message_id: int, wa_message_id: Optional[str], sent_ok: bool, wa_error: str = ""):
    # Si no hay wa_message_id, marcamos failed para que lo veas en UI
    if not wa_message_id or not sent_ok:
        conn.execute(text("""
            UPDATE messages
            SET wa_status = 'failed',
                wa_error = :wa_error
            WHERE id = :id
        """), {"id": local_message_id, "wa_error": wa_error or "WhatsApp send failed"})
        return

    conn.execute(text("""
        UPDATE messages
        SET wa_message_id = :wa_message_id,
            wa_status = 'sent',
            wa_error = NULL,
            wa_ts_sent = COALESCE(wa_ts_sent, NOW())
        WHERE id = :id
    """), {"id": local_message_id, "wa_message_id": wa_message_id})

# =========================================================
# ENDPOINTS
# =========================================================

@app.get("/api/health")
def health():
    return {"ok": True, "build": "2026-02-12-1"}

@app.post("/api/media/upload")
async def upload_media(file: UploadFile = File(...), kind: str = Form("image")):
    import tempfile
    import subprocess

    kind = (kind or "image").lower().strip()
    if kind not in ("image", "video", "audio", "document"):
        raise HTTPException(status_code=400, detail="Invalid kind")

    content = await file.read()
    mime = (file.content_type or "application/octet-stream").split(";")[0].strip().lower()
    filename = file.filename or "upload"

    # ✅ Audio webm -> ogg/opus
    if kind == "audio" and mime == "audio/webm":
        with tempfile.TemporaryDirectory() as tmp:
            in_path = os.path.join(tmp, "in.webm")
            out_path = os.path.join(tmp, "out.ogg")

            with open(in_path, "wb") as f:
                f.write(content)

            cmd = ["ffmpeg", "-y", "-i", in_path, "-c:a", "libopus", "-b:a", "24k", "-vn", out_path]
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if p.returncode != 0:
                err = p.stderr.decode("utf-8", errors="ignore")
                raise HTTPException(status_code=500, detail=f"ffmpeg convert failed: {err[:900]}")

            with open(out_path, "rb") as f:
                content = f.read()

        mime = "audio/ogg"
        filename = "audio.ogg"

    from app.routes.whatsapp import upload_whatsapp_media
    media_id = await upload_whatsapp_media(content, mime)

    return {"ok": True, "media_id": media_id, "mime_type": mime, "filename": filename, "kind": kind}

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
            SELECT
                id, phone, direction, msg_type, text,
                media_url, media_caption, media_id, mime_type, file_name, file_size, duration_sec,
                featured_image, real_image, permalink, created_at,
                wa_message_id, wa_status, wa_error, wa_ts_sent, wa_ts_delivered, wa_ts_read
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

    # 1) Guardar en DB
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO conversations (phone, takeover, updated_at)
                VALUES (:phone, FALSE, :updated_at)
                ON CONFLICT (phone) DO UPDATE SET updated_at = EXCLUDED.updated_at
            """), {"phone": msg.phone, "updated_at": datetime.utcnow()})

            local_id = save_message(
                conn,
                phone=msg.phone,
                direction=direction,
                msg_type=msg_type,
                text_msg=msg.text or "",
                media_url=msg.media_url,
                media_caption=msg.media_caption,
                media_id=msg.media_id,
                mime_type=msg.mime_type,
                file_name=msg.file_name,
                file_size=msg.file_size,
                duration_sec=msg.duration_sec,
                featured_image=msg.featured_image,
                real_image=msg.real_image,
                permalink=msg.permalink,
            )
    except Exception as e:
        return {"saved": False, "sent": False, "stage": "db", "error": str(e)}

    # 2) Enviar a WhatsApp si es OUT + guardar wa_message_id
    if direction == "out":
        try:
            wa_resp = None

            if msg_type in ("image", "video", "audio", "document"):
                if not msg.media_id:
                    with engine.begin() as conn:
                        set_wa_send_result(conn, local_id, None, False, "media_id is required")
                    return {"saved": True, "sent": False, "reason": "media_id is required for media messages"}

                wa_resp = await send_whatsapp_media_id(
                    to_phone=msg.phone,
                    media_type=msg_type,
                    media_id=msg.media_id,
                    caption=msg.media_caption or msg.text or ""
                )

            elif msg_type == "product":
                body = (msg.text or "").strip()
                extra_lines = []
                if msg.permalink:
                    extra_lines.append(f"🛒 Ver producto: {msg.permalink}")
                if msg.real_image:
                    extra_lines.append(f"📸 Ver foto real: {msg.real_image}")
                if extra_lines:
                    body = (body + "\n\n" + "\n".join(extra_lines)).strip()

                wa_resp = await send_whatsapp_text(msg.phone, body)

            else:
                wa_resp = await send_whatsapp_text(msg.phone, msg.text or "")

            # ✅ Persistir resultado de envío
            wa_message_id = None
            if isinstance(wa_resp, dict) and wa_resp.get("sent") is True:
                wa_message_id = wa_resp.get("wa_message_id")

            with engine.begin() as conn:
                if wa_resp.get("sent") is True and wa_message_id:
                    set_wa_send_result(conn, local_id, wa_message_id, True, "")
                else:
                    # guardar error de WhatsApp si vino
                    err = wa_resp.get("whatsapp_body") or wa_resp.get("reason") or wa_resp.get("error") or "WhatsApp send failed"
                    set_wa_send_result(conn, local_id, None, False, str(err)[:900])

            return {"saved": True, "sent": bool(wa_resp.get("sent")), "wa": wa_resp}

        except Exception as e:
            with engine.begin() as conn:
                set_wa_send_result(conn, local_id, None, False, str(e)[:900])
            return {"saved": True, "sent": False, "stage": "whatsapp", "error": str(e)}

    return {"saved": True, "sent": False}

@app.post("/api/conversations/takeover")
def set_takeover(payload: TakeoverPayload):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, takeover, updated_at)
            VALUES (:phone, :takeover, :updated_at)
            ON CONFLICT (phone)
            DO UPDATE SET takeover = EXCLUDED.takeover,
                          updated_at = EXCLUDED.updated_at
        """), {"phone": payload.phone, "takeover": payload.takeover, "updated_at": datetime.utcnow()})
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
    try:
        with engine.begin() as conn:
            r = conn.execute(text("""
                SELECT
                    phone,
                    takeover,
                    first_name,
                    last_name,
                    city,
                    customer_type,
                    interests,
                    tags,
                    notes
                FROM conversations
                WHERE phone = :phone
            """), {"phone": phone}).mappings().first()

        if not r:
            return {
                "phone": phone,
                "takeover": False,
                "first_name": "",
                "last_name": "",
                "city": "",
                "customer_type": "",
                "interests": "",
                "tags": "",
                "notes": "",
            }

        return dict(r)

    except Exception as e:
        return {"ok": False, "error": str(e), "phone": phone}

# =========================================================
# WOOCOMMERCE (CATÁLOGO + ENVÍO COMO ADJUNTO REAL)
# =========================================================

WC_BASE_URL = os.getenv("WC_BASE_URL", "").rstrip("/")
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY", "")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET", "")

def _wc_enabled() -> bool:
    return bool(WC_BASE_URL and WC_CONSUMER_KEY and WC_CONSUMER_SECRET)

def _wc_get(path: str, params: dict | None = None):
    if not (WC_BASE_URL and WC_CONSUMER_KEY and WC_CONSUMER_SECRET):
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
    imgs = product.get("images") or []
    if imgs and isinstance(imgs, list):
        src = (imgs[0] or {}).get("src")
        return src
    return None

def _extract_aromas(product: dict) -> list[str]:
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

def _extract_gender(product: dict) -> str:
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
    params = {"search": q or "", "page": page, "per_page": per_page, "status": "publish"}
    data = _wc_get("/products", params=params)
    items = [_map_product_for_ui(p) for p in (data or [])]
    return {"products": items}

@app.post("/api/wc/send-product")
async def send_wc_product(payload: dict):
    import io
    from PIL import Image
    import pillow_avif  # noqa: F401

    phone = payload.get("phone")
    product_id = payload.get("product_id")
    custom_caption = payload.get("caption", "")

    if not phone or not product_id:
        raise HTTPException(status_code=400, detail="phone and product_id required")

    if not (WC_BASE_URL and WC_CONSUMER_KEY and WC_CONSUMER_SECRET):
        raise HTTPException(status_code=500, detail="WC env vars not configured")

    url = f"{WC_BASE_URL}/wp-json/wc/v3/products/{product_id}"
    params = {"consumer_key": WC_CONSUMER_KEY, "consumer_secret": WC_CONSUMER_SECRET}

    r = requests.get(url, params=params, timeout=25)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"WooCommerce product fetch failed: {r.status_code} {r.text}")

    product = r.json()

    images = product.get("images") or []
    if not images:
        raise HTTPException(status_code=400, detail="Product has no image")

    featured_image = (images[0] or {}).get("src") or ""
    real_image = (images[1] or {}).get("src") if len(images) > 1 else ""

    img_response = requests.get(featured_image, timeout=25)
    if img_response.status_code != 200 or not img_response.content:
        raise HTTPException(status_code=502, detail=f"Image download failed: {img_response.status_code}")

    image_bytes = img_response.content
    content_type = (img_response.headers.get("Content-Type") or "").lower()

    def _to_jpeg_bytes(src_bytes: bytes) -> bytes:
        im = Image.open(io.BytesIO(src_bytes))
        im = im.convert("RGB")
        out = io.BytesIO()
        im.save(out, format="JPEG", quality=88, optimize=True)
        return out.getvalue()

    lower_url = featured_image.lower()
    needs_convert = (
        ("image/avif" in content_type) or ("image/webp" in content_type) or
        lower_url.endswith(".avif") or lower_url.endswith(".webp")
    )

    try:
        if needs_convert:
            image_bytes = _to_jpeg_bytes(image_bytes)
            mime_type = "image/jpeg"
        else:
            mime_type = content_type if content_type.startswith("image/") else "image/jpeg"
            if mime_type not in ("image/jpeg", "image/png"):
                image_bytes = _to_jpeg_bytes(image_bytes)
                mime_type = "image/jpeg"
    except Exception as e:
        try:
            image_bytes = _to_jpeg_bytes(image_bytes)
            mime_type = "image/jpeg"
        except Exception:
            raise HTTPException(status_code=500, detail=f"Image decode/convert failed: {e}")

    from app.routes.whatsapp import upload_whatsapp_media
    media_id = await upload_whatsapp_media(image_bytes, mime_type)

    name = product.get("name", "") or ""
    price = product.get("price") or product.get("regular_price") or ""
    short_description = re.sub('<[^<]+?>', '', product.get("short_description", "") or "").strip()
    permalink = product.get("permalink", "") or ""

    brand = _extract_brand(product)
    gender = _extract_gender(product)
    gender_label = "Hombre" if gender == "hombre" else "Mujer" if gender == "mujer" else "Unisex" if gender == "unisex" else ""

    aromas_list = _extract_aromas(product)
    aromas = ", ".join(aromas_list) if aromas_list else ""

    caption_lines = [f"✨ {name}"]
    if gender_label:
        caption_lines.append(f"👤 Para: {gender_label}")
    if brand:
        caption_lines.append(f"🏷️ Marca: {brand}")
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

    # Guardar en DB (OUT) + luego enviar por WhatsApp (imagen real)
    with engine.begin() as conn:
        local_id = save_message(
            conn,
            phone=phone,
            direction="out",
            msg_type="product",
            text_msg=caption,
            featured_image=featured_image,
            real_image=real_image or None,
            permalink=permalink,
        )

    wa_resp = await send_whatsapp_media_id(
        to_phone=phone,
        media_type="image",
        media_id=media_id,
        caption=caption
    )

    wa_message_id = wa_resp.get("wa_message_id") if isinstance(wa_resp, dict) else None
    with engine.begin() as conn:
        if wa_resp.get("sent") is True and wa_message_id:
            set_wa_send_result(conn, local_id, wa_message_id, True, "")
        else:
            err = wa_resp.get("whatsapp_body") or wa_resp.get("reason") or "WhatsApp send failed"
            set_wa_send_result(conn, local_id, None, False, str(err)[:900])

    return wa_resp
