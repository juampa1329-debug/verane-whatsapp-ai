import json
import re
import time
from typing import Callable, Awaitable, Any, Optional

from app.integrations.woocommerce import wc_get, map_product_for_ui, wc_enabled


# =========================
# Normalización
# =========================

_STOPWORDS = {
    "y", "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "al", "a", "en", "por", "para", "con", "sin",
    "que", "qué", "cual", "cuál", "como", "cómo", "me", "te", "se",
    "tienes", "tienen", "hay", "manejan", "manejamos",
    "disponible", "disponibles",
    "precio", "vale", "cuanto", "cuánto", "cuesta", "valor",
    "hola", "buenas", "buenos", "dias", "días", "tardes", "noches",
    "quiero", "busco", "necesito", "dame",
}


def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = (
        s.replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokenize(s: str) -> list[str]:
    t = _norm(s)
    if not t:
        return []
    return [x for x in t.split() if x and x not in _STOPWORDS]


def _looks_like_product_intent(text: str) -> bool:
    t = _norm(text)
    if not t:
        return False

    if len(_tokenize(t)) == 0:
        return False

    if t in ("hola", "buenas", "gracias"):
        return False

    return True


def _score_match(query: str, name: str) -> int:
    q = _norm(query)
    n = _norm(name)

    if not q or not n:
        return 0

    if q == n:
        return 100

    if q in n:
        return 75

    q_tokens = set(q.split())
    n_tokens = set(n.split())

    common = len(q_tokens & n_tokens)

    return common * 15


def _parse_choice_number(text: str) -> Optional[int]:
    m = re.search(r"\b([1-9])\b", text)
    if m:
        try:
            return int(m.group(1))
        except Exception:
            return None
    return None


# =========================
# Woo Smart Search
# =========================

async def _wc_search_products(query: str) -> list[dict]:
    params = {
        "search": query,
        "per_page": 12,
        "status": "publish",
    }

    data = await wc_get("/products", params=params)
    results = []

    for p in (data or []):
        results.append(map_product_for_ui(p))

    scored = []
    for r in results:
        score = _score_match(query, r.get("name") or "")
        scored.append((score, r))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [x[1] for x in scored]


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

    # 🔹 Si no es texto, limpiar estado Woo y salir
    if msg_type != "text":
        clear_state(phone)
        return {"handled": False}

    text = (user_text or "").strip()
    if not text:
        return {"handled": False}

    state = get_state(phone) or ""

    # =========================
    # Si estamos esperando elección
    # =========================
    if state.startswith("wc_await:"):
        try:
            payload = json.loads(state[len("wc_await:"):])
            options = payload.get("options", [])
            ts = int(payload.get("ts") or 0)
        except Exception:
            clear_state(phone)
            return {"handled": False}

        # ✅ TTL: si el estado tiene más de 3 minutos, expirarlo
        if ts:
            now = int(time.time())
            if (now - ts) > 180:  # 180s = 3 min
                clear_state(phone)
                return {"handled": False}

        if not options:
            clear_state(phone)
            return {"handled": False}

        choice = _parse_choice_number(text)

        if choice and 1 <= choice <= len(options):
            product = options[choice - 1]
            clear_state(phone)
            return {
                "handled": True,
                "wc": True,
                "reason": "choice_send",
                "wa": await send_product_fn(phone, product["id"], "")
            }

        # Si escribe algo largo, salir del modo Woo
        if len(text.split()) > 8:
            clear_state(phone)
            return {"handled": False}

        await send_text_fn(phone, "Responde con el número de la opción 🙂")
        return {"handled": True, "wc": True}

    # =========================
    # Nueva búsqueda
    # =========================

    if not _looks_like_product_intent(text):
        return {"handled": False}

    try:
        items = await _wc_search_products(text)
    except Exception:
        return {"handled": False}

    if not items:
        await send_text_fn(phone, "No encontré ese perfume 😕 ¿Puedes confirmarme el nombre exacto?")
        return {"handled": True, "wc": True}

    top = items[:5]

    # Match fuerte → enviar directo
    if _score_match(text, top[0]["name"]) >= 80:
        clear_state(phone)
        return {
            "handled": True,
            "wc": True,
            "reason": "strong_match_send",
            "wa": await send_product_fn(phone, top[0]["id"], "")
        }

    # Varias opciones → preguntar
    lines = ["Encontré estas opciones: 👇"]

    opts = []
    for i, p in enumerate(top, start=1):
        name = p.get("name")
        price = p.get("price")
        stock = p.get("stock_status")
        stock_label = "✅ disponible" if stock == "instock" else "⛔ agotado"

        lines.append(f"{i}) {name} — ${price} ({stock_label})")
        opts.append({"id": p["id"], "name": name})

    lines.append("")
    lines.append("¿Cuál deseas? Responde con el número.")

    # ✅ Guardamos estado con timestamp para TTL
    set_state(phone, "wc_await:" + json.dumps({"options": opts, "ts": int(time.time())}))

    await send_text_fn(phone, "\n".join(lines))

    return {"handled": True, "wc": True}