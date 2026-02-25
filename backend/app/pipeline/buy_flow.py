# app/pipeline/buy_flow.py
from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any

from sqlalchemy import text

from app.db import engine
from app.pipeline.wc_sender import wc_send_product
from app.integrations.woocommerce import wc_get, map_product_for_ui


BUY_KEYWORDS = ("comprar", "lo compro", "quiero comprar", "pagar", "pago", "carrito", "checkout", "link de pago")
SHIP_KEYWORDS = ("envío", "envio", "domicilio", "cuanto vale el envio", "cuánto vale el envío", "costo de envio", "costo de envío")


def _get_conv(phone: str) -> Dict[str, Any]:
    with engine.begin() as conn:
        r = conn.execute(text("""
            SELECT phone, last_product_id, city, pref_budget, pref_gender, intent_current
            FROM conversations
            WHERE phone = :phone
        """), {"phone": phone}).mappings().first()
    return dict(r) if r else {"phone": phone}


def _append_internal_note(phone: str, line: str) -> None:
    line = (line or "").strip()
    if not line:
        return
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, notes, updated_at)
            VALUES (:phone, :notes, :ts)
            ON CONFLICT (phone)
            DO UPDATE SET
              notes = COALESCE(conversations.notes,'') || CASE WHEN COALESCE(conversations.notes,'') = '' THEN '' ELSE E'\n' END || :notes,
              updated_at = :ts
        """), {"phone": phone, "notes": line[:800], "ts": datetime.utcnow()})


def _set_tag(phone: str, tag: str) -> None:
    tag = (tag or "").strip().lower()
    if not tag:
        return
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, tags, updated_at)
            VALUES (:phone, :tags, :ts)
            ON CONFLICT (phone)
            DO UPDATE SET
              tags = CASE
                WHEN LOWER(COALESCE(conversations.tags,'')) LIKE '%' || :tag || '%' THEN conversations.tags
                WHEN COALESCE(conversations.tags,'') = '' THEN :tag
                ELSE conversations.tags || ',' || :tag
              END,
              updated_at = :ts
        """), {"phone": phone, "tags": tag, "tag": tag, "ts": datetime.utcnow()})


def _set_intent(phone: str, intent: str, confidence: float = 0.9) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (phone, intent_current, intent_confidence, updated_at)
            VALUES (:phone, :intent, :conf, :ts)
            ON CONFLICT (phone)
            DO UPDATE SET
              intent_current = EXCLUDED.intent_current,
              intent_confidence = EXCLUDED.intent_confidence,
              updated_at = EXCLUDED.updated_at
        """), {"phone": phone, "intent": intent, "conf": float(confidence or 0.0), "ts": datetime.utcnow()})


def is_buy_intent(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(k in t for k in BUY_KEYWORDS)


def is_shipping_intent(text: str) -> bool:
    t = (text or "").strip().lower()
    return any(k in t for k in SHIP_KEYWORDS)


async def handle_buy_or_shipping(phone: str, text_in: str) -> Optional[Dict[str, Any]]:
    """
    Manejo básico, sin inventar:
    - Si hay last_product_id => manda tarjeta del producto + pregunta unidades/dirección
    - Si preguntan por envío => pide ciudad/barrio y deja nota interna
    Retorna dict con "handled": True/False y opcional "reply_sent": bool
    """
    t = (text_in or "").strip().lower()
    if not t:
        return None

    buy = is_buy_intent(t)
    ship = is_shipping_intent(t)
    if not buy and not ship:
        return None

    conv = _get_conv(phone)
    last_pid = conv.get("last_product_id")

    if ship:
        _set_intent(phone, "SHIPPING_COST", 0.9)
        _set_tag(phone, "pendiente_envio")
        _append_internal_note(phone, "[AI] Cliente preguntó por envío. Falta ciudad/barrio y dirección.")
        # Respuesta corta (sin Woo)
        return {
            "handled": True,
            "reply": "Perfecto 😊 ¿A qué ciudad y barrio sería el envío? Con eso te confirmo el costo y el tiempo de entrega."
        }

    if buy:
        _set_intent(phone, "BUY_FLOW", 0.95)
        _set_tag(phone, "compra_inminente")

        if not last_pid:
            _append_internal_note(phone, "[AI] Cliente quiere comprar, pero no hay last_product_id. Pedir cuál perfume.")
            return {
                "handled": True,
                "reply": "¡Listo! 😊 ¿Cuál perfume deseas comprar? Escríbeme el nombre o envíame la foto del producto y te envío el link."
            }

        # Enviar tarjeta del producto para cerrar con datos reales
        try:
            await wc_send_product(phone=phone, product_id=int(last_pid), custom_caption="")
        except Exception:
            # si falla el envío de tarjeta, seguimos con texto
            pass

        _append_internal_note(phone, f"[AI] Cliente quiere comprar. last_product_id={last_pid}. Falta unidades y dirección.")
        return {
            "handled": True,
            "reply": "¡Genial! 😊 Para finalizar tu pedido, confírmame:
1) ¿Cuántas unidades?
2) Nombre completo
3) Dirección y ciudad
4) Método de pago (transferencia o link)

Con eso te lo dejo listo."
        }

    return None
