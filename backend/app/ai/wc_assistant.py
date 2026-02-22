import json
import time
from typing import Callable, Awaitable, Any, Optional

from app.integrations.woocommerce import (
    wc_enabled,
    wc_search_products,
    looks_like_product_question,
    score_product_match,
    parse_choice_number,
)


# =========================
# Helpers
# =========================

def _now_ts() -> int:
    try:
        return int(time.time())
    except Exception:
        return 0


def _shorten(s: str, max_chars: int = 80) -> str:
    s = (s or "").strip()
    s = " ".join(s.split())
    if not s:
        return ""
    if len(s) <= max_chars:
        return s
    cut = s[:max_chars].rsplit(" ", 1)[0].strip()
    return (cut + "…").strip()


def _is_tiny_ack(text: str) -> bool:
    t = (text or "").strip().lower()
    return t in {
        "ok", "listo", "dale", "gracias", "perfecto", "de una", "vale", "bien",
        "👍", "👌", "✅",
        "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
    }


def _state_pack(options: list[dict]) -> str:
    return "wc_await:" + json.dumps({"options": options, "ts": _now_ts()}, ensure_ascii=False)


def _state_unpack(state: str) -> tuple[list[dict], int]:
    """
    returns (options, ts)
    """
    raw = state[len("wc_await:"):]
    payload = json.loads(raw)
    opts = payload.get("options", [])
    ts = int(payload.get("ts") or 0)
    if not isinstance(opts, list):
        opts = []
    return opts, ts


# =========================
# MAIN
# =========================

async def handle_wc_if_applicable(
    phone: str,
    user_text: str,
    msg_type: str,

    get_state: Callable[[str], str],
    set_state: Callable[[str, str], None],
    clear_state: Callable[[str], None],

    send_product_fn: Callable[[str, int, str], Awaitable[dict]],
    send_text_fn: Callable[[str, str], Awaitable[dict]],

    save_options_fn: Optional[Callable[[str, list[dict]], Awaitable[None]]] = None,
    load_recent_options_fn: Optional[Callable[[str], Awaitable[list[dict]]]] = None,

    **kwargs: Any,
) -> dict[str, Any]:

    if not wc_enabled():
        return {"handled": False}

    # Si no es texto, limpiamos estado Woo y dejamos que IA normal resuelva.
    if msg_type != "text":
        clear_state(phone)
        return {"handled": False}

    text = (user_text or "").strip()
    if not text:
        return {"handled": False}

    # Evitar que "ok/gracias/hola" dispare búsquedas o bloquee el await
    if _is_tiny_ack(text):
        return {"handled": False}

    state = (get_state(phone) or "").strip()

    # =========================================================
    # 1) Si estamos esperando elección (wc_await)
    # =========================================================
    if state.startswith("wc_await:"):

        options: list[dict] = []
        ts: int = 0

        # 1.1) Parse state normal
        try:
            options, ts = _state_unpack(state)
        except Exception:
            options, ts = [], 0

        # 1.2) Si state está dañado o vacío, intentamos rescatar desde DB cache
        if (not options) and load_recent_options_fn is not None:
            try:
                recovered = await load_recent_options_fn(phone)
                if isinstance(recovered, list) and recovered:
                    options = recovered
                    # si recuperamos, reescribimos el state con TTL nuevo
                    set_state(phone, _state_pack(options))
                    ts = _now_ts()
            except Exception:
                pass

        # 1.3) TTL: 3 minutos
        if ts:
            if (_now_ts() - ts) > 180:
                clear_state(phone)
                return {"handled": False}

        if not options:
            clear_state(phone)
            return {"handled": False}

        # 1.4) Si manda número, resolvemos elección
        choice = parse_choice_number(text)
        if choice and 1 <= choice <= len(options):
            picked = options[choice - 1]
            clear_state(phone)
            return {
                "handled": True,
                "wc": True,
                "reason": "choice_send",
                "wa": await send_product_fn(phone, int(picked["id"]), ""),
            }

        # 1.5) Si NO manda número, pero el texto parece una NUEVA búsqueda,
        # rompemos el await y hacemos búsqueda nueva (evita “pegado”)
        if looks_like_product_question(text) or len(text.split()) >= 2:
            clear_state(phone)
            # caemos al flujo de búsqueda nueva abajo
        else:
            await send_text_fn(phone, "Responde con el número de la opción 🙂 (o dime el nombre del perfume)")
            return {"handled": True, "wc": True, "reason": "await_number"}

    # =========================================================
    # 2) Nueva búsqueda (o re-búsqueda después de romper await)
    # =========================================================
    if not looks_like_product_question(text):
        return {"handled": False}

    try:
        items = await wc_search_products(text, per_page=10)
    except Exception:
        # si falla Woo, no bloqueamos: dejamos IA normal seguir
        return {"handled": False}

    if not items:
        await send_text_fn(
            phone,
            "No encontré ese perfume 😕\n\n"
            "¿Me confirmas el nombre exacto o la marca? (ej: Dior Sauvage, Versace Eros, 212 VIP)"
        )
        return {"handled": True, "wc": True, "reason": "no_results"}

    # Priorizamos top 5
    top = items[:5]

    # 2.1) Match fuerte -> enviar directo
    top_score = score_product_match(text, top[0].get("name") or "")
    if top_score >= 80:
        clear_state(phone)
        return {
            "handled": True,
            "wc": True,
            "reason": "strong_match_send",
            "wa": await send_product_fn(phone, int(top[0]["id"]), ""),
        }

    # 2.2) Varias opciones -> menú (con mini descripción)
    lines = ["Encontré estas opciones: 👇"]
    opts: list[dict] = []

    for i, p in enumerate(top, start=1):
        name = (p.get("name") or "").strip()
        price = (p.get("price") or "").strip()
        stock = (p.get("stock_status") or "").strip()
        stock_label = "✅ disponible" if stock == "instock" else "⛔ agotado"

        short_desc = _shorten(p.get("short_description") or "", 70)
        desc_part = f" — {short_desc}" if short_desc else ""

        price_part = f"${price}" if price else ""
        price_sep = " — " if price_part else " — "

        lines.append(f"{i}) {name}{price_sep}{price_part} ({stock_label}){desc_part}")
        opts.append({
            "id": int(p["id"]),
            "name": name,
        })

    lines.append("")
    lines.append("¿Cuál deseas? Responde con el número (1-5) o escribe el nombre exacto.")

    # Guardar estado + (opcional) cache en DB
    set_state(phone, _state_pack(opts))
    if save_options_fn is not None:
        try:
            await save_options_fn(phone, opts)
        except Exception:
            pass

    await send_text_fn(phone, "\n".join(lines))
    return {"handled": True, "wc": True, "reason": "menu_options"}