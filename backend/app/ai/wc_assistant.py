# app/ai/wc_assistant.py
import json
import re
from typing import Callable, Awaitable, Any

from fastapi import HTTPException

from app.integrations.woocommerce import wc_get, map_product_for_ui, wc_enabled


# =========================
# Normalización + heurísticas
# =========================

_STOPWORDS = {
    "y", "el", "la", "los", "las", "un", "una", "unos", "unas",
    "de", "del", "al", "a", "en", "por", "para", "con", "sin",
    "que", "qué", "cual", "cuál", "como", "cómo", "me", "te", "se", "mi", "tu", "su",
    "tienes", "tienen", "hay", "manejan", "manejamos",
    "disponible", "disponibles", "agotado", "agotados",
    "precio", "vale", "cuanto", "cuánto", "cuesta", "valor",
    "porfavor", "por", "fa", "pls", "plis",
    "hola", "buenas", "buenos", "dias", "días", "tardes", "noches",
    "quiero", "busco", "necesito", "dame", "envio", "envío", "ciudad",
    "informacion", "información",

    # ✅ NUEVO: intención de “foto/imagen”
    "muestrame", "muéstrame", "muestra", "mostrar", "ver", "adjunta", "mandame", "envia", "envía",
    "foto", "fotos", "imagen", "imagenes", "imágenes", "real",
}

_TRIGGERS = {
    "tienes", "tienen", "hay", "disponible", "disponibles",
    "precio", "vale", "cuanto", "cuánto", "cuesta", "valor",

    # ✅ NUEVO: intención de “foto/imagen”
    "foto", "imagen", "muestrame", "muestra", "mostrar", "ver", "adjunta", "real",

    "perfume", "perfumes", "fragancia", "fragancias", "colonia", "colonias",
    "referencia", "ref",
}


# normaliza para scoring
def _norm(s: str) -> str:
    s = (s or "").lower().strip()
    s = s.replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n")
    s = re.sub(r"[^a-z0-9\s]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _tokenize(s: str) -> list[str]:
    t = _norm(s)
    if not t:
        return []
    toks = [x for x in t.split() if x and x not in _STOPWORDS and len(x) >= 2]
    return toks


def _looks_like_product_intent(user_text: str) -> bool:
    t = _norm(user_text)
    if not t:
        return False

    # saludos “puros”
    if t in ("hola", "buenas", "buenos dias", "buenas tardes", "buenas noches"):
        return False

    # pregunta por ciudad/envío sin producto => no dispares woo
    if any(x in t for x in ("para que ciudad", "para qué ciudad", "ciudad seria", "ciudad sería", "envio a", "envío a")) and len(_tokenize(t)) <= 2:
        return False

    # si hay triggers, casi seguro es catálogo
    if any(w in t.split() for w in _TRIGGERS):
        return True

    # si el mensaje es corto, normalmente es nombre/consulta de referencia
    toks = _tokenize(t)
    if 1 <= len(toks) <= 6 and len(t) >= 5:
        return True

    return False


def _extract_product_query(user_text: str) -> str:
    """
    Saca una query “limpia” para Woo:
    - quita stopwords
    - corrige variantes comunes (aqua/acqua, gio, etc.)
    """
    raw = _norm(user_text)

    # normaliza variantes típicas de “acqua di gio”
    raw = raw.replace("aqua de gio", "acqua di gio")
    raw = raw.replace("acqua de gio", "acqua di gio")
    raw = raw.replace("aqua di gio", "acqua di gio")
    raw = raw.replace("aqua", "acqua")  # ayuda en tu caso

    toks = _tokenize(raw)

    # si queda vacío, usa el raw
    if not toks:
        return raw.strip()

    # intenta armar query corta de 2-5 tokens (los más informativos)
    toks = toks[:5]
    return " ".join(toks).strip()


def _score_match(query: str, name: str) -> int:
    """
    Score simple:
    - exact match alto
    - substring alto
    - overlap por tokens
    """
    q = _norm(query)
    n = _norm(name)
    if not q or not n:
        return 0
    if q == n:
        return 100
    if q in n:
        # cubrimiento
        cover = int(60 + min(35, (len(q) * 35) / max(1, len(n))))
        return cover

    q_toks = [x for x in q.split() if x not in _STOPWORDS and len(x) >= 2]
    n_toks = set([x for x in n.split() if x not in _STOPWORDS and len(x) >= 2])
    if not q_toks:
        return 0

    hit = sum(1 for w in q_toks if w in n_toks)
    if hit == 0:
        return 0

    # base + hits
    return 30 + hit * 12


def _parse_choice_number(user_text: str) -> int | None:
    m = re.search(r"\b([1-9])\b", (user_text or "").strip())
    if not m:
        return None
    try:
        return int(m.group(1))
    except Exception:
        return None


async def _wc_search_products_smart(user_text: str, per_page: int = 12) -> list[dict]:
    """
    3 intentos:
    1) query limpio
    2) query original (norm)
    3) query por tokens claves (2-3)
    Dedupe por id, luego rank por score.
    """
    q_clean = _extract_product_query(user_text)
    q_raw = _norm(user_text)

    queries = []
    if q_clean and len(q_clean) >= 3:
        queries.append(q_clean)
    if q_raw and q_raw not in queries and len(q_raw) >= 3:
        queries.append(q_raw)

    toks = _tokenize(user_text)
    if len(toks) >= 2:
        q2 = " ".join(toks[:3])
        if q2 not in queries and len(q2) >= 3:
            queries.append(q2)

    results_by_id: dict[int, dict] = {}

    for q in queries[:3]:
        params = {"search": q, "page": 1, "per_page": int(per_page), "status": "publish"}
        data = await wc_get("/products", params=params)
        for p in (data or []):
            ui = map_product_for_ui(p)
            pid = ui.get("id")
            if isinstance(pid, int) and pid not in results_by_id:
                results_by_id[pid] = ui

    items = list(results_by_id.values())

    # prioriza instock + score
    scored = []
    for it in items:
        sc = _score_match(q_clean or user_text, it.get("name") or "")
        stock = it.get("stock_status") or ""
        stock_boost = 8 if stock == "instock" else 0
        scored.append((sc + stock_boost, it))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [x[1] for x in scored]


# =========================
# API principal del módulo
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
) -> dict[str, Any]:
    """
    Devuelve:
      {"handled": True, ...} si ya resolvió Woo
      {"handled": False} si NO aplica
    """

    if not wc_enabled():
        return {"handled": False}

    if msg_type != "text":
        return {"handled": False}

    text_in = (user_text or "").strip()
    if not text_in:
        return {"handled": False}

    # 1) si estamos esperando elección
    st = get_state(phone) or ""
    if st.startswith("wc_await:"):
        try:
            payload = json.loads(st[len("wc_await:"):].strip() or "{}")
        except Exception:
            payload = {}

        options = payload.get("options") or []
        if not isinstance(options, list) or not options:
            clear_state(phone)
            return {"handled": False}

        n = _parse_choice_number(text_in)
        chosen = None

        if n is not None and 1 <= n <= len(options):
            chosen = options[n - 1]
        else:
            # match por texto
            ut = _extract_product_query(text_in)
            best = None
            best_score = 0
            for opt in options:
                name = str((opt or {}).get("name") or "")
                sc = _score_match(ut, name)
                if sc > best_score:
                    best_score = sc
                    best = opt
            if best and best_score >= 35:
                chosen = best

        if chosen and chosen.get("id"):
            clear_state(phone)
            wa = await send_product_fn(phone, int(chosen["id"]), "")
            return {"handled": True, "wc": True, "reason": "choice_send", "wa": wa}

        await send_text_fn(phone, "¿Cuál opción deseas? Responde con el número (1, 2, 3...) o el nombre exacto 🙂")
        return {"handled": True, "wc": True, "reason": "awaiting_choice"}

    # 2) intención
    if not _looks_like_product_intent(text_in):
        return {"handled": False}

    # 3) búsqueda smart
    try:
        items = await _wc_search_products_smart(text_in, per_page=12)
    except HTTPException:
        return {"handled": False}
    except Exception:
        return {"handled": False}

    if not items:
        # no manejamos “no stock por cantidad”; pero sí podemos decir que no encontramos
        await send_text_fn(phone, "No la encontré con ese nombre 😕 ¿Me confirmas la referencia exacta o una foto?")
        return {"handled": True, "wc": True, "reason": "no_results"}

    # 4) decidir envío directo vs opciones
    # rank ya viene ordenado
    top = items[:5]

    # fuerte si el #1 le saca ventaja al #2 o score alto
    q_clean = _extract_product_query(text_in)
    s1 = _score_match(q_clean, top[0].get("name") or "")
    s2 = _score_match(q_clean, top[1].get("name") or "") if len(top) > 1 else 0

    strong = (s1 >= 70) or (s1 >= 60 and (s1 - s2) >= 15)

    if strong and top[0].get("id"):
        wa = await send_product_fn(phone, int(top[0]["id"]), "")
        return {"handled": True, "wc": True, "reason": "strong_match_send", "wa": wa}

    # 5) múltiples opciones -> preguntar
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
