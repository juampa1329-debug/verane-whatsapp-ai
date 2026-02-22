import json
import time
import re
from typing import Callable, Awaitable, Any, Optional

from app.integrations.woocommerce import (
    wc_enabled,
    wc_search_products,
    looks_like_product_question,
    score_product_match,
    parse_choice_number,
)

# ============================================================
# Woo Advisor V2 (State machine + Slots + Scoring + Anti-stuck)
# ============================================================

STATE_PREFIX_V2 = "wc_state:"
STATE_PREFIX_V1 = "wc_await:"


# -------------------------
# Helpers
# -------------------------

def _now_ts() -> int:
    try:
        return int(time.time())
    except Exception:
        return 0


def _safe_int(x: Any, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default


def _clean_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _shorten(s: str, max_chars: int = 120) -> str:
    s = _clean_text(re.sub(r"<[^>]+>", " ", (s or "")))
    if not s:
        return ""
    if len(s) <= max_chars:
        return s
    cut = s[:max_chars].rsplit(" ", 1)[0].strip()
    return (cut + "…").strip()


def _is_tiny_ack(text: str) -> bool:
    t = _clean_text(text).lower()
    return t in {
        "ok", "listo", "dale", "gracias", "perfecto", "de una", "vale", "bien",
        "👍", "👌", "✅",
        "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
        "okey", "oki", "okeyy"
    }


def _looks_like_refinement(text: str) -> bool:
    """
    Detecta si el texto parece refinamiento de preferencia, no una selección numérica.
    """
    t = _clean_text(text).lower()
    if not t:
        return False

    # Si es un número: NO es refinamiento
    if re.fullmatch(r"\d{1,2}", t):
        return False

    # Palabras típicas de preferencias
    keywords = [
        "maduro", "elegante", "serio", "juvenil", "fresco", "dulce", "seco",
        "oficina", "trabajo", "diario", "noche", "fiesta", "cita", "formal",
        "verano", "invierno", "calor", "frio",
        "fuerte", "suave", "duracion", "proyeccion", "intenso",
        "amader", "ambar", "vainill", "citr", "acuatic", "aromatic", "espec",
        "cuero", "almizcle", "iris", "floral", "oriental", "gourmand"
    ]
    if any(k in t for k in keywords):
        return True

    # Frases comunes
    if any(x in t for x in ["más ", "menos ", "no tan", "que sea", "para ", "tipo "]):
        return True

    # 2+ palabras suele ser refinamiento útil
    if len(t.split()) >= 2:
        return True

    return False


def _is_budget_mention(text: str) -> bool:
    t = _clean_text(text).lower()
    return bool(re.search(r"(\$|\bpesos?\b|\bmil\b|\bm\b|\bmxn\b|\bcop\b|\bclp\b)", t)) or bool(
        re.search(r"\b\d{2,6}\b", t)
    )


def _extract_budget(text: str) -> Optional[int]:
    """
    Extrae presupuesto aproximado como entero.
    Ej: "hasta 150k", "150000", "$120.000", "200 mil"
    """
    t = _clean_text(text).lower()
    if not t:
        return None

    # 200 mil
    m = re.search(r"\b(\d{1,3})\s*(mil|k)\b", t)
    if m:
        base = _safe_int(m.group(1), 0)
        if base > 0:
            return base * 1000

    # 120000 / 120.000 / 120,000
    m2 = re.search(r"\b(\d{2,6})(?:[.,]\d{3})?\b", t)
    if m2:
        raw = m2.group(0)
        raw = raw.replace(".", "").replace(",", "")
        val = _safe_int(raw, 0)
        if val >= 10000:
            return val

    return None


def _norm(s: str) -> str:
    s = _clean_text(s).lower()
    # quitar tildes simple
    replacements = {
        "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n",
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    return s


def _get_list_names(obj_list: Any) -> list[str]:
    """
    Woo suele traer categories/tags como lista de dicts con 'name'.
    """
    out: list[str] = []
    if isinstance(obj_list, list):
        for x in obj_list:
            if isinstance(x, dict):
                name = (x.get("name") or "").strip()
                if name:
                    out.append(name)
            elif isinstance(x, str):
                if x.strip():
                    out.append(x.strip())
    return out


# -------------------------
# State V2
# -------------------------

def _state_v2_pack(payload: dict) -> str:
    payload = payload or {}
    payload.setdefault("ts", _now_ts())
    return STATE_PREFIX_V2 + json.dumps(payload, ensure_ascii=False)


def _state_v2_unpack(state: str) -> dict:
    raw = state[len(STATE_PREFIX_V2):]
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        return {}
    return payload


def _state_v1_unpack(state: str) -> tuple[list[dict], int]:
    raw = state[len(STATE_PREFIX_V1):]
    payload = json.loads(raw)
    opts = payload.get("options", [])
    ts = int(payload.get("ts") or 0)
    if not isinstance(opts, list):
        opts = []
    return opts, ts


def _state_v1_pack(options: list[dict]) -> str:
    return STATE_PREFIX_V1 + json.dumps({"options": options, "ts": _now_ts()}, ensure_ascii=False)


def _default_wc_state() -> dict:
    return {
        "mode": "wc",
        "stage": "discovery",  # discovery | shortlist | await_choice | post_reco
        "slots": {
            "gender": None,          # hombre | mujer | unisex
            "vibe": [],              # maduro/elegante/juvenil/etc
            "occasion": [],          # oficina/noche/diario/cita/fiesta/formal
            "family": [],            # amaderado/cítrico/acuático/ambarado/etc
            "sweetness": None,       # dulce | medio | seco
            "intensity": None,       # suave | media | fuerte
            "brand": None,
            "budget": None,          # int
        },
        "candidates": [],           # lista de productos (mini payload)
        "last_query": None,
        "ts": _now_ts(),
    }


def _merge_unique(base: list[str], add: list[str]) -> list[str]:
    seen = set(_norm(x) for x in base if x)
    out = list(base)
    for x in add:
        if not x:
            continue
        nx = _norm(x)
        if nx not in seen:
            out.append(x)
            seen.add(nx)
    return out


def _extract_slots(text: str, prev_slots: dict) -> dict:
    """
    Extracción liviana por reglas (rápida, sin LLM).
    Si en tu engine también usas LLM, esto igual suma como baseline.
    """
    t = _norm(text)
    slots = dict(prev_slots or {})

    # gender
    if any(w in t for w in ["para hombre", "hombre", "masculino", "man"]):
        slots["gender"] = "hombre"
    if any(w in t for w in ["para mujer", "mujer", "femenino", "woman"]):
        slots["gender"] = "mujer"
    if "unisex" in t:
        slots["gender"] = "unisex"

    # vibe
    vibe_map = {
        "maduro": ["maduro", "serio", "adulto"],
        "elegante": ["elegante", "formal", "sofisticado"],
        "juvenil": ["juvenil", "joven", "fresco"],
        "seductor": ["seductor", "sensual", "sexy"],
        "deportivo": ["deportivo", "sport", "casual"],
    }
    vib_add: list[str] = []
    for vibe, keys in vibe_map.items():
        if any(k in t for k in keys):
            vib_add.append(vibe)
    slots["vibe"] = _merge_unique(slots.get("vibe") or [], vib_add)

    # occasion
    occ_map = {
        "oficina": ["oficina", "trabajo", "laboral"],
        "diario": ["diario", "dia a dia", "todos los dias"],
        "noche": ["noche"],
        "cita": ["cita", "date"],
        "fiesta": ["fiesta", "rumba", "party"],
        "formal": ["formal", "evento", "boda", "graduacion"],
        "verano": ["verano", "calor", "tropical"],
        "invierno": ["invierno", "frio"],
    }
    occ_add: list[str] = []
    for occ, keys in occ_map.items():
        if any(k in t for k in keys):
            occ_add.append(occ)
    slots["occasion"] = _merge_unique(slots.get("occasion") or [], occ_add)

    # sweetness
    if any(k in t for k in ["dulce", "azucar", "vainilla", "gourmand"]):
        slots["sweetness"] = "dulce"
    if any(k in t for k in ["seco", "amargo", "no tan dulce", "no dulce"]):
        slots["sweetness"] = "seco"
    if any(k in t for k in ["balanceado", "medio"]):
        slots["sweetness"] = "medio"

    # intensity
    if any(k in t for k in ["fuerte", "intenso", "potente", "proyeccion alta"]):
        slots["intensity"] = "fuerte"
    if any(k in t for k in ["suave", "ligero", "discreto"]):
        slots["intensity"] = "suave"
    if any(k in t for k in ["media", "moderado"]):
        slots["intensity"] = "media"

    # family / notes keywords
    fam_keywords = {
        "amaderado": ["amader", "madera", "cedro", "vetiver", "sandal"],
        "ambarado": ["ambar", "oriental", "resina"],
        "citrico": ["citr", "limon", "bergamota", "naranja"],
        "acuatico": ["acuatic", "marino", "oceano"],
        "aromatico": ["aromatic", "lavanda", "hierbas"],
        "especiado": ["espec", "pimienta", "canela", "cardamomo"],
        "almizclado": ["almizcle", "musk"],
        "cuero": ["cuero", "leather"],
        "floral": ["floral", "rosa", "jazmin"],
        "iris": ["iris"],
        "vainilla": ["vainilla", "vanilla"],
    }
    fam_add: list[str] = []
    for fam, keys in fam_keywords.items():
        if any(k in t for k in keys):
            fam_add.append(fam)
    slots["family"] = _merge_unique(slots.get("family") or [], fam_add)

    # budget
    if _is_budget_mention(text):
        b = _extract_budget(text)
        if b:
            slots["budget"] = b

    # brand (simple heurística: "marca X", "de X")
    m = re.search(r"\bmarca\s+([a-z0-9]+)\b", t)
    if m:
        slots["brand"] = m.group(1)

    return slots


# -------------------------
# Product normalization + scoring
# -------------------------

def _product_text_blob(p: dict) -> str:
    """
    Construye un texto grande para hacer scoring por keywords/slots.
    """
    name = (p.get("name") or "")
    short_desc = (p.get("short_description") or "")
    desc = (p.get("description") or "")
    cats = " ".join(_get_list_names(p.get("categories")))
    tags = " ".join(_get_list_names(p.get("tags")))
    return _norm(" ".join([name, short_desc, desc, cats, tags]))


def _score_with_slots(p: dict, slots: dict, user_text: str) -> int:
    """
    Score simple y robusto:
    - match nombre (0-50)
    - match preferencias (0-50)
    - stock bonus (+10) / agotado (-15)
    - budget (si está)
    """
    score = 0
    name = (p.get("name") or "").strip()
    score += min(50, int(score_product_match(user_text, name) * 0.5))  # escala a 0-50

    blob = _product_text_blob(p)

    # slot match
    slot_score = 0
    gender = slots.get("gender")
    if gender:
        if gender == "hombre" and any(x in blob for x in ["hombre", "men", "mascul"]):
            slot_score += 8
        if gender == "mujer" and any(x in blob for x in ["mujer", "women", "femen"]):
            slot_score += 8
        if gender == "unisex" and "unisex" in blob:
            slot_score += 8

    for v in (slots.get("vibe") or []):
        if _norm(v) in blob:
            slot_score += 6

    for o in (slots.get("occasion") or []):
        # ojo: "oficina" rara vez está en el texto del producto,
        # pero a veces sí en tags/categorías; igual suma si aparece
        if _norm(o) in blob:
            slot_score += 4

    for f in (slots.get("family") or []):
        if _norm(f) in blob:
            slot_score += 6

    sweetness = slots.get("sweetness")
    if sweetness == "dulce" and any(k in blob for k in ["vainilla", "dulce", "gourmand"]):
        slot_score += 6
    if sweetness == "seco" and any(k in blob for k in ["amaderado", "seco", "cuero", "vetiver"]):
        slot_score += 6

    intensity = slots.get("intensity")
    if intensity == "fuerte" and any(k in blob for k in ["intenso", "fuerte", "proyeccion", "duracion"]):
        slot_score += 4
    if intensity == "suave" and any(k in blob for k in ["suave", "ligero", "fresco"]):
        slot_score += 4

    slot_score = min(50, slot_score)
    score += slot_score

    # stock
    stock = (p.get("stock_status") or "").strip()
    if stock == "instock":
        score += 10
    elif stock:
        score -= 15

    # budget (si hay precio)
    budget = slots.get("budget")
    if budget:
        price_raw = str(p.get("price") or "").strip()
        price = _safe_int(price_raw.replace(".", "").replace(",", ""), 0)
        if price > 0:
            # penaliza si excede mucho el presupuesto
            if price <= budget:
                score += 6
            elif price <= int(budget * 1.15):
                score += 2
            else:
                score -= 10

    return score


def _pick_followup_question(slots: dict) -> str:
    """
    1 sola pregunta clave para avanzar como asesor humano.
    """
    if not slots.get("gender"):
        return "¿Lo buscas para hombre, mujer o unisex?"
    if not slots.get("occasion"):
        return "¿Lo quieres más para oficina/diario o para noche/fiesta?"
    if not slots.get("sweetness"):
        return "¿Prefieres algo más dulce o más seco?"
    if not slots.get("intensity"):
        return "¿Lo prefieres suave (discreto) o más fuerte (que se note)?"
    if not slots.get("budget"):
        return "¿Tienes un presupuesto aproximado?"
    return "¿Quieres que sea más fresco o más amaderado/intenso?"


def _build_menu_lines(items: list[dict]) -> tuple[str, list[dict]]:
    """
    Menú (1-5) con mini-descripción.
    """
    top = items[:5]
    lines = ["Encontré estas opciones: 👇"]
    opts: list[dict] = []

    for i, p in enumerate(top, start=1):
        name = (p.get("name") or "").strip()
        price = (p.get("price") or "").strip()
        stock = (p.get("stock_status") or "").strip()
        stock_label = "✅ disponible" if stock == "instock" else "⛔ agotado"

        short_desc = _shorten(p.get("short_description") or p.get("description") or "", 90)
        desc_part = f" — {short_desc}" if short_desc else ""

        price_part = f"${price}" if price else ""
        price_sep = " — " if (price_part or True) else " "

        lines.append(f"{i}) {name}{price_sep}{price_part} ({stock_label}){desc_part}")
        opts.append({"id": _safe_int(p.get("id")), "name": name})

    lines.append("")
    lines.append("Responde con el número (1-5) o dime tus preferencias (ej: “más dulce y para oficina”).")
    return "\n".join(lines), opts


# -------------------------
# MAIN
# -------------------------

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

    text = _clean_text(user_text)
    if not text:
        return {"handled": False}

    # Evitar que "ok/gracias/hola" dispare búsquedas o bloquee
    if _is_tiny_ack(text):
        return {"handled": False}

    raw_state = (get_state(phone) or "").strip()

    # -----------------------------------------
    # 0) Compatibilidad: si llega un state viejo
    # -----------------------------------------
    if raw_state.startswith(STATE_PREFIX_V1):
        # Mantengo tu comportamiento anterior, pero con anti-stuck mejorado:
        try:
            options, ts = _state_v1_unpack(raw_state)
        except Exception:
            options, ts = [], 0

        # rescate cache
        if (not options) and load_recent_options_fn is not None:
            try:
                recovered = await load_recent_options_fn(phone)
                if isinstance(recovered, list) and recovered:
                    options = recovered
                    set_state(phone, _state_v1_pack(options))
                    ts = _now_ts()
            except Exception:
                pass

        # TTL 3 min
        if ts and (_now_ts() - ts) > 180:
            clear_state(phone)
            return {"handled": False}

        if options:
            choice = parse_choice_number(text)
            if choice and 1 <= choice <= len(options):
                picked = options[choice - 1]
                clear_state(phone)
                return {
                    "handled": True,
                    "wc": True,
                    "reason": "choice_send_v1",
                    "wa": await send_product_fn(phone, int(picked["id"]), ""),
                }

            # Anti-stuck: si no hay número y parece refinamiento, rompemos el await
            if _looks_like_refinement(text) or looks_like_product_question(text) or len(text.split()) >= 2:
                clear_state(phone)
            else:
                await send_text_fn(phone, "Responde con el número de la opción 🙂 (o dime tus preferencias)")
                return {"handled": True, "wc": True, "reason": "await_number_v1"}

        clear_state(phone)

    # -----------------------------------------
    # 1) State V2
    # -----------------------------------------
    wc_state = None
    if raw_state.startswith(STATE_PREFIX_V2):
        try:
            wc_state = _state_v2_unpack(raw_state)
        except Exception:
            wc_state = None

    if not isinstance(wc_state, dict) or not wc_state:
        wc_state = _default_wc_state()

    # TTL: 10 minutos (asesoría puede durar más)
    ts = _safe_int(wc_state.get("ts"), 0)
    if ts and (_now_ts() - ts) > 600:
        wc_state = _default_wc_state()

    stage = (wc_state.get("stage") or "discovery").strip()
    slots = wc_state.get("slots") or _default_wc_state()["slots"]
    candidates = wc_state.get("candidates") or []

    # -----------------------------------------
    # 2) Detectar si Woo aplica
    # - aplica si: pregunta de producto O refinamiento claro (preferencias)
    # -----------------------------------------
    wc_applicable = looks_like_product_question(text) or _looks_like_refinement(text)
    if not wc_applicable:
        # si no aplica, liberamos el control a IA normal
        return {"handled": False}

    # -----------------------------------------
    # 3) Actualizar slots con el mensaje actual
    # -----------------------------------------
    slots = _extract_slots(text, slots)
    wc_state["slots"] = slots
    wc_state["ts"] = _now_ts()

    # -----------------------------------------
    # 4) Si estamos en await_choice y llega número -> enviar producto
    # -----------------------------------------
    if stage == "await_choice" and candidates:
        choice = parse_choice_number(text)
        if choice and 1 <= choice <= len(candidates):
            picked = candidates[choice - 1]
            clear_state(phone)
            return {
                "handled": True,
                "wc": True,
                "reason": "choice_send_v2",
                "wa": await send_product_fn(phone, int(picked["id"]), ""),
            }

        # Anti-stuck: si no es número, lo tratamos como refinamiento y recalculamos (NO insistir)
        stage = "shortlist"
        wc_state["stage"] = "shortlist"

    # -----------------------------------------
    # 5) Retrieval
    # - si el usuario escribió un nombre concreto: usarlo como query
    # - si escribió solo preferencias: usar query más general (o el texto mismo)
    # -----------------------------------------
    query = text
    # si es puras preferencias y no pregunta de "buscar", igual intentamos con el texto.
    # (Luego, cuando vea woocommerce.py, puedo mejorar con búsquedas por marca/familia)
    wc_state["last_query"] = query

    try:
        items = await wc_search_products(query, per_page=12)
    except Exception:
        return {"handled": False}

    if not items:
        # No resultados: pregunta clave y deja slots guardados para siguiente mensaje
        wc_state["stage"] = "discovery"
        set_state(phone, _state_v2_pack(wc_state))
        await send_text_fn(phone, f"No encontré resultados con eso 😕\n{_pick_followup_question(slots)}")
        return {"handled": True, "wc": True, "reason": "no_results_v2"}

    # -----------------------------------------
    # 6) Ranking / scoring con slots + texto del producto (incluye description)
    # -----------------------------------------
    scored = []
    for p in items:
        try:
            s = _score_with_slots(p, slots, text)
        except Exception:
            s = 0
        scored.append((s, p))
    scored.sort(key=lambda x: x[0], reverse=True)

    ranked = [p for _, p in scored]
    top = ranked[:5]

    # guardamos candidates (los top) para selección por número si el usuario lo desea
    wc_state["candidates"] = [{"id": _safe_int(p.get("id")), "name": (p.get("name") or "").strip()} for p in top]

    # -----------------------------------------
    # 7) Comportamiento “humano”
    # - Si hay match fuerte: enviar 1 producto directo
    # - Si no, recomendar 2 (tarjetas) + una pregunta de refinamiento
    # - Si usuario pidió "opciones", mostramos menú numérico
    # -----------------------------------------
    user_norm = _norm(text)
    wants_list = any(k in user_norm for k in ["opciones", "lista", "muestrame", "muéstrame", "ver opciones", "dame opciones"])

    # match fuerte con el top 1 por nombre (si el usuario escribió nombre)
    top1 = top[0]
    top_name = (top1.get("name") or "").strip()
    strong_name_score = score_product_match(text, top_name)

    # Si pidió lista explícita -> menú
    if wants_list and len(top) >= 2:
        menu_text, opts = _build_menu_lines(top)
        # Guardamos como await_choice para que número funcione
        wc_state["stage"] = "await_choice"
        wc_state["candidates"] = opts
        set_state(phone, _state_v2_pack(wc_state))
        if save_options_fn is not None:
            try:
                await save_options_fn(phone, opts)
            except Exception:
                pass
        await send_text_fn(phone, menu_text)
        return {"handled": True, "wc": True, "reason": "menu_options_v2"}

    # Si match fuerte -> 1 producto directo
    if strong_name_score >= 80:
        clear_state(phone)
        return {
            "handled": True,
            "wc": True,
            "reason": "strong_match_send_v2",
            "wa": await send_product_fn(phone, int(top1["id"]), ""),
        }

    # Recomendación consultiva: 1-2 tarjetas
    # Enviamos dos si hay, para replicar asesor humano
    recs = top[:2]
    for p in recs:
        try:
            await send_product_fn(phone, int(p["id"]), "")
        except Exception:
            # Si falla la tarjeta, al menos seguimos con texto
            pass

    # Texto de asesor (resumen usando description/short_description)
    # (Ojo: aquí NO mandamos la descripción completa: hacemos un resumen corto)
    def _one_liner(p: dict) -> str:
        name = (p.get("name") or "").strip()
        desc = _shorten(p.get("short_description") or p.get("description") or "", 120)
        price = str(p.get("price") or "").strip()
        price_part = f" — ${price}" if price else ""
        if desc:
            return f"• {name}{price_part}\n  {desc}"
        return f"• {name}{price_part}"

    summary_lines = ["Te recomendaría estos según lo que me dices: 👇", ""]
    for p in recs:
        summary_lines.append(_one_liner(p))

    summary_lines.append("")
    summary_lines.append(_pick_followup_question(slots))

    # Si hay varios candidatos, guardamos await_choice por si el usuario responde con número
    wc_state["stage"] = "await_choice"
    set_state(phone, _state_v2_pack(wc_state))

    await send_text_fn(phone, "\n".join(summary_lines))
    return {"handled": True, "wc": True, "reason": "advisor_reco_v2"}