# app/pipeline/wc_sender.py

from __future__ import annotations

from fastapi import HTTPException

from app.db import engine
from app.pipeline.reply_sender import save_message, set_wa_send_result

from app.routes.whatsapp import (
    upload_whatsapp_media,
    send_whatsapp_media_id,
    send_whatsapp_interactive_cta_url,
)

from app.integrations.woocommerce import (
    wc_fetch_product,
    build_caption,
    download_image_bytes,
    ensure_whatsapp_image_compat,
    WC_BASE_URL,
    WC_CONSUMER_KEY,
    WC_CONSUMER_SECRET,
)

# NOTE: the helper lives in reply_sender (used by both text and card senders)
from app.pipeline.reply_sender import remember_last_product_sent


async def wc_send_product(phone: str, product_id: int, custom_caption: str = "") -> dict:
    """
    Envía una tarjeta de producto por WhatsApp:

    ✅ Prioridad:
    1) Interactive CTA URL (como la tarjeta 2) si hay real_image o permalink
    2) Fallback: image + caption

    Además guarda memoria del último producto enviado para “envíame la foto”.
    """

    # Pillow AVIF (opcional)
    try:
        import pillow_avif  # noqa: F401
    except Exception:
        pass

    phone = (phone or "").strip()
    if not phone or not product_id:
        raise HTTPException(status_code=400, detail="phone and product_id required")

    if not (WC_BASE_URL and WC_CONSUMER_KEY and WC_CONSUMER_SECRET):
        raise HTTPException(status_code=500, detail="WC env vars not configured")

    # 1) Traer producto
    product = await wc_fetch_product(int(product_id))

    images = product.get("images") or []
    if not images:
        raise HTTPException(status_code=400, detail="Product has no image")

    featured_image = (images[0] or {}).get("src") or ""
    real_image = (images[1] or {}).get("src") if len(images) > 1 else ""

    if not featured_image:
        raise HTTPException(status_code=400, detail="Product image src missing")

    permalink = (product.get("permalink") or "").strip()

    # 2) Descargar imagen + normalizar a formato WhatsApp
    img_bytes, content_type = await download_image_bytes(featured_image)
    if not img_bytes:
        raise HTTPException(status_code=502, detail="Image download returned empty content")

    img_bytes, mime_type = ensure_whatsapp_image_compat(img_bytes, content_type, featured_image)

    # 3) Subir media a WhatsApp
    media_id = await upload_whatsapp_media(img_bytes, mime_type)
    if not media_id:
        raise HTTPException(status_code=502, detail="WhatsApp media upload failed (no media_id)")

    # 4) Caption (texto del cuerpo)
    caption = build_caption(
        product=product,
        featured_image=featured_image,
        real_image=real_image,
        custom_caption=(custom_caption or ""),
    )

    # 5) Guardar en DB el OUT como product
    with engine.begin() as conn:
        local_id = save_message(
            conn,
            phone=phone,
            direction="out",
            msg_type="product",
            text_msg=caption,
            media_id=media_id,
            mime_type=mime_type,
            file_name="product_image",
            file_size=len(img_bytes) if img_bytes else None,
            featured_image=featured_image,
            real_image=real_image or None,
            permalink=permalink,
        )

    # ✅ 5.1) Memoria del último producto enviado
    remember_last_product_sent(
        phone,
        product_id=int(product_id),
        featured_image=featured_image,
        real_image=real_image,
        permalink=permalink,
    )

    # 6) Enviar (preferimos TARJETA con botón)
    wa_resp = None

    cta_url = (real_image or "").strip() or (permalink or "").strip()
    cta_text = "Ver foto real" if (real_image or "").strip() else "Ver producto"

    if cta_url:
        try:
            wa_resp = await send_whatsapp_interactive_cta_url(
                to_phone=phone,
                body_text=caption,
                button_text=cta_text,
                url_to_open=cta_url,
                header_image_media_id=media_id,
            )
        except Exception as e:
            wa_resp = {"sent": False, "reason": "interactive_exception", "error": str(e)[:900]}

    # Fallback: si interactive falla
    if not (isinstance(wa_resp, dict) and wa_resp.get("sent") is True):
        wa_resp = await send_whatsapp_media_id(
            to_phone=phone,
            media_type="image",
            media_id=media_id,
            caption=caption,
        )

    # 7) Persistir resultado WA
    wa_message_id = wa_resp.get("wa_message_id") if isinstance(wa_resp, dict) else None

    with engine.begin() as conn:
        if isinstance(wa_resp, dict) and wa_resp.get("sent") is True and wa_message_id:
            set_wa_send_result(conn, local_id, wa_message_id, True, "")
        else:
            err = (
                (wa_resp.get("whatsapp_body") if isinstance(wa_resp, dict) else "")
                or (wa_resp.get("reason") if isinstance(wa_resp, dict) else "")
                or (wa_resp.get("error") if isinstance(wa_resp, dict) else "")
                or "WhatsApp send failed"
            )
            set_wa_send_result(conn, local_id, None, False, str(err)[:900])

    out = wa_resp if isinstance(wa_resp, dict) else {"sent": False, "reason": "invalid wa_resp"}
    out["local_message_id"] = local_id
    out["media_id"] = media_id
    out["mime_type"] = mime_type
    out["product_id"] = int(product_id)
    out["card_mode"] = "interactive_cta" if cta_url else "image_caption"
    out["cta_url"] = cta_url
    return out