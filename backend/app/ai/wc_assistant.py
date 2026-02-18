# app/ai/wc_assistant.py
import json
from typing import Any, Dict, Optional, Tuple

from fastapi import HTTPException

from app.integrations.woocommerce import (
    wc_enabled,
    looks_like_product_question,
    wc_search_products,
    score_product_match,
    parse_choice_number,
)

# Estas 3 funciones las vas a pasar desde main.py (inyección simple):
# - get_state(phone) -> str
# - set_state(phone, state) -> None
# - clear_state(phone) -> None


async def handle_wc_if_applicable(
    phone: str,
    user_text: str,
    msg_type: str,
    get_state,
    set_state,
    clear_state,
    send_product_fn,          # async (phone, product_id, caption="") -> dict
    send_text_fn,             # async (phone, text) -> dict  (tu sender “humanizado”)
) -> Dict[str, Any]:
    """
    Retorna:
      {"handled": True, ...} si Woo respondió o preguntó.
      {"handled": False} si NO aplicó (para que siga al flujo IA normal).
    """

    if not wc_enabled():
        return {"handled": False}

    if msg_type != "text":
        return {"handled": False}

    text = (user_text or "").strip()
    if not text:
        return {"handled": False}

    # 1) si venimos esperando elección del cliente
    st = (get_state(phone) or "").strip()
    if st.startswith("wc_await:"):
        try:
            payload = json.loads(st[len("wc_await:"):].strip() or "{}")
        except Exception:
            payload = {}

        options = payload.get("options") or []
        if isinstance(options, list) and options:
            n = parse_choice_number(text)
            chosen = None

            if n is not None and 1 <= n <= len(options):
                chosen = options[n - 1]
            else:
                # match por texto
                best = None
                best_score = 0
                for opt in options:
                    name = str((opt or {}).get("name") or "")
                    sc = score_product_match(text, name)
                    if sc > best_score:
                        best_score = sc
                        best = opt
                if best and best_score >= 30:
                    chosen = best

            if chosen and chosen.get("id"):
                clear_state(phone)
                wa = await send_product_fn(phone=phone, product_id=int(chosen["id"]), caption="")
                return {"handled": True, "wc": True, "reason": "choice_send", "wa": wa}

            # no entendimos
            await send_text_fn(phone, "¿Cuál opción deseas? Responde con el número (1, 2, 3...) o el nombre exacto 🙂")
            return {"handled": True, "wc": True, "reason": "awaiting_choice"}

        # si el state estaba roto, lo limpiamos y seguimos normal
        clear_state(phone)
        return {"handled": False}

    # 2) detectar si es pregunta de producto
    if not looks_like_product_question(text):
        return {"handled": False}

    try:
        items = await wc_search_products(text, per_page=8)
    except HTTPException:
        # si Woo falla, no tumbamos el chat
        return {"handled": False}
    except Exception:
        return {"handled": False}

    if not items:
        # no handled -> dejamos que IA responda normal (o si quieres, aquí podríamos decir “no encontré”)
        return {"handled": False}

    # score
    scored = []
    for it in items:
        sc = score_product_match(text, it.get("name") or "")
        scored.append((sc, it))
    scored.sort(key=lambda x: x[0], reverse=True)

    best_score, best_item = scored[0]
    second_score = scored[1][0] if len(scored) > 1 else 0

    # ✅ enviar directo SOLO si score alto y hay brecha clara (para evitar Acqua di Giò y similares)
    strong = best_score >= 70 and (best_score - second_score) >= 18

    if strong and best_item.get("id"):
        wa = await send_product_fn(phone=phone, product_id=int(best_item["id"]), caption="")
        return {"handled": True, "wc": True, "reason": "strong_match_send", "wa": wa}

    # si hay varias, preguntamos
    top = [x[1] for x in scored[:5]]
    lines = ["Encontré estas opciones: 👇"]
    opts = []

    for i, it in enumerate(top, start=1):
        name = str(it.get("name") or "")
        price = str(it.get("price") or "")
        stock = str(it.get("stock_status") or "")
        stock_label = "✅ disponible" if stock == "instock" else "⛔ agotado"
        price_label = f" — ${price}" if price else ""
        lines.append(f"{i}) {name}{price_label} ({stock_label})")
        opts.append({"id": it.get("id"), "name": name})

    lines.append("")
    lines.append("¿Cuál deseas? Responde con el número (1,2,3...) o el nombre exacto.")
    msg_out = "\n".join(lines).strip()

    set_state(phone, "wc_await:" + json.dumps({"options": opts}, ensure_ascii=False))
    await send_text_fn(phone, msg_out)

    return {"handled": True, "wc": True, "reason": "multiple_options"}
