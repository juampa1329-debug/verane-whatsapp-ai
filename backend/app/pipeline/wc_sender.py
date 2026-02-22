# app/pipeline/wc_sender.py

from __future__ import annotations

from typing import Optional
from fastapi import HTTPException

from app.db import engine
from app.pipeline.reply_sender import save_message, set_wa_send_result
from app.routes.whatsapp import upload_whatsapp_media, send_whatsapp_media_id

from app.integrations.woocommerce import (
    wc_fetch_product,
    build_caption,
    download_image_bytes,
    ensure_whatsapp_image_compat,
    WC_BASE_URL,
    WC_CONSUMER_KEY,
    WC_CONSUMER_SECRET,
)


async def wc_send_product(phone: str, product_id: int, custom_caption: str = "") -> dict:
    """
    Envía una "tarjeta" de producto por WhatsApp:
    - baja imagen del producto
    - la sube a WhatsApp (media_id)
    - manda imagen + caption
    - guarda en DB como msg_type='product'
    """

    try:
        import pillow_avif  # noqa: F401
    except Exception:
        pass

    if not phone or not product_id:
        raise HTTPException(status_code=400, detail="phone and product_id required")

    if not (WC_BASE_URL and WC_CONSUMER_KEY and WC_CONSUMER_SECRET):
        raise HTTPException(status_code=500, detail="WC env vars not configured")

    product = await wc_fetch_product(int(product_id))

    images = product.get("images") or []
    if not images:
        raise HTTPException(status_code=400, detail="Product has no image")

    featured_image = (images[0] or {}).get("src") or ""
    real_image = (images[1] or {}).get("src") if len(images) > 1 else ""

    img_bytes, content_type = await download_image_bytes(featured_image)
    img_bytes, mime_type = ensure_whatsapp_image_compat(img_bytes, content_type, featured_image)

    media_id = await upload_whatsapp_media(img_bytes, mime_type)

    caption = build_caption(
        product=product,
        featured_image=featured_image,
        real_image=real_image,
        custom_caption=(custom_caption or "")
    )

    permalink = product.get("permalink", "") or ""

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
        if isinstance(wa_resp, dict) and wa_resp.get("sent") is True and wa_message_id:
            set_wa_send_result(conn, local_id, wa_message_id, True, "")
        else:
            err = (wa_resp.get("whatsapp_body") if isinstance(wa_resp, dict) else "") or (wa_resp.get("reason") if isinstance(wa_resp, dict) else "") or "WhatsApp send failed"
            set_wa_send_result(conn, local_id, None, False, str(err)[:900])

    return wa_resp if isinstance(wa_resp, dict) else {"sent": False, "reason": "invalid wa_resp"}