from __future__ import annotations

import json
import time
import re
from datetime import datetime
from typing import Callable, Awaitable, Any, Optional

from sqlalchemy import text

from app.db import engine
from app.integrations.woocommerce import (
    wc_enabled,
    wc_search_products,
    looks_like_product_question,
    score_product_match,
    parse_choice_number,
)

# ============================================================
# Woo Advisor V2 (State machine + Slots + Scoring + Anti-stuck)
# + DB-backed options (plan B)
# ============================================================

STATE_PREFIX_V2 = "wc_state:"
STATE_PREFIX_V1 = "wc_await:"


# -------------------------
# DB helpers (Plan B)
# conversations.wc_last_options JSONB
# conversations.wc_last_options_at TIMESTAMP
# -------------------------

async def _db_save_recent_options(phone: str, options: list[dict]) -> None:
    """
    Guarda opciones recientes (1-5) en conversations para recuperar contexto si:
    - se pierde ai_state
    - restart / redeploy
    - webhook retry raro
    """
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO conversations (phone, wc_last_options, wc_last_options_at, updated_at)
                VALUES (:phone, :opts::jsonb, :ts, :ts)
                ON CONFLICT (phone)
                DO UPDATE SET
                    wc_last_options = EXCLUDED.wc_last_options,
                    wc_last_options_at = EXCLUDED.wc_last_options_at,
                    updated_at = EXCLUDED.updated_at
            """), {
                "phone": phone,
                "opts": json.dumps(options or [], ensure_ascii=False),
                "ts": datetime.utcnow(),
            })
    except Exception:
        return


async def _db_load_recent_options(phone: str, *, max_age_sec: int = 20 * 60) -> list[dict]:
    """
    Recupera opciones recientes (si no han expirado).
    """
    try:
        with engine.begin() as conn:
            r = conn.execute(text("""
                SELECT wc_last_options, wc_last_options_at
                FROM conversations
                WHERE phone = :phone
                LIMIT 1
            """), {"phone": phone}).mappings().first()

        if not r:
            return []

        ts = r.get("wc_last_options_at")
        if not ts:
            return []

        try:
            age = (datetime.utcnow() - ts).total_seconds()
            if age > max_age_sec:
                return []
        except Exception:
            pass

        data = r.get("wc_last_options")
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            # por si quedara mal guardado
            return []
        if isinstance(data, str):
            try:
                j = json.loads(data)
                return j if isinstance(j, list) else []
            except Exception:
                return []
        return []
    except Exception:
        return []


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


def _norm(s: str) -> str:
    s = _clean_text(s).lower()
    replacements = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    for a, b in replacements.items():
        s = s.replace(a, b)
    return s


def _is_tiny_ack(text: str) -> bool:
    t = _clean_text(text).lower()
    return t in {
        "ok", "listo", "dale", "gracias", "perfecto", "de una", "vale", "bien",
        "👍", "👌", "✅",
        "hola", "buenas", "buenos dias", "buenas tardes", "buenas noches",
        "okey", "oki", "okeyy"
    }


def _is_exit_command(text: str) -> bool:
    t = _norm(text)
    return any(x in t for x in [
        "cancelar", "salir", "detener", "para", "parar", "stop",
        "hablar con asesor", "asesor humano", "humano", "agente"
    ])


# -------------------------
# Intent: request photo/image (hard rules)
# -------------------------

_PHOTO_KEYWORDS = [
    "foto", "fotos", "imagen", "imagenes", "imágenes",
    "foto real", "ver foto", "ver la foto", "verlo", "verla",
    "muestrame", "muéstrame", "mandame", "mándame", "enviame", "envíame",
    "quiero ver", "tienes foto", "tiene foto",
]

_CONFIRM_WORDS = {
    "si", "sí", "dale", "ok", "okay", "listo", "de una", "enviala", "envíala",
    "manda", "mandala", "mándala", "hazlo", "listo entonces"
}


def _is_photo_request(text: str) -> bool:
    t = _norm(text)
    if not t:
        return False

    for kw in _PHOTO_KEYWORDS:
        if _norm(kw) in t:
            return True

    # confirmación corta SOLO con contexto (lo validamos donde se usa)
    if len(t) <= 12 and t in _CONFIRM_WORDS:
        return True

    return False


def _is_budget_mention(text: str) -> bool:
    t = _norm(text)
    return bool(re.search(r"(\$|\bpesos?\b|\bmil\b|\bk\b|\bmxn\b|\bcop\b|\bclp\b)", t)) or bool(
        re.search(r"\b\d{2,6}\b", t)
    )


def _extract_budget(text: str) -> Optional[int]:
    t = _norm(text)
    if not t:
        return None

    m = re.search(r"\b(\d{1,3})\s*(mil|k)\b", t)
    if m:
        base = _safe_int(m.group(1), 0)
        if base > 0:
            return base * 1000

    m2 = re.search(r"\b(\d{2,6})(?:[.,]\d{3})?\b", t)
    if m2:
        raw = m2.group(0).replace(".", "").replace(",", "")
        val = _safe_int(raw, 0)
        if val >= 10000:
            return val

    return None


def _looks_like_refinement(text: str) -> bool:
    t = _norm(text)
    if not t:
        return False

    if re.fullmatch(r"\d{1,2}", t):
        return False

    if _is_budget_mention(text):
        return True

    keywords = [
        "maduro", "elegante", "serio", "juvenil", "fresco", "dulce", "seco",
        "oficina", "trabajo", "diario", "noche", "fiesta", "cita", "formal",
        "verano", "invierno", "calor", "frio",
        "fuerte", "suave", "duracion", "duración", "proyeccion", "proyección", "intenso",
        "amader", "ambar", "vainill", "citr", "acuatic", "aromatic", "espec",
        "cuero", "almizcle", "musk", "iris", "floral", "oriental", "gourmand",
        "unisex", "hombre", "mujer", "mascul", "femen"
    ]
    if any(k in t for k in keywords):
        return True

    if any(x in t for x in ["mas ", "más ", "menos ", "no tan", "que sea", "para ", "tipo "]):
        if "para " in t and not any(k in t for k in [
            "para hombre", "para mujer", "para unisex",
            "para oficina", "para noche", "para diario", "para fiesta", "para cita"
        ]):
            return False
        return True

    return False


def _get_list_names(obj_list: Any) -> list[str]:
    out: list[str] = []
    if isinstance(obj_list, list):
        for x in obj_list:
            if isinstance(x, dict):
                name = (x.get("name") or "").strip()
                if name:
                    out.append(name)
            elif isinstance(x, str) and x.strip():
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
            "gender": None,
            "vibe": [],
            "occasion": [],
            "family": [],
            "sweetness": None,
            "intensity": None,
            "brand": None,
            "budget": None,
        },
        "candidates": [],
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

    # brand
    m = re.search(r"\bmarca\s+([a-z0-9]+)\b", t)
    if m:
        slots["brand"] = m.group(1)

    return slots


# -------------------------
# Product normalization + scoring
# -------------------------

def _product_text_blob(p: dict) -> str:
    name = (p.get("name") or "")
    short_desc = (p.get("short_description") or "")
    desc = (p.get("description") or "")
    cats = " ".join(_get_list_names(p.get("categories")))
    tags = " ".join(_get_list_names(p.get("tags")))
    return _norm(" ".join([name, short_desc, desc, cats, tags]))


def _score_with_slots(p: dict, slots: dict, user_text: str) -> int:
    score = 0
    name = (p.get("name") or "").strip()
    score += min(50, int(score_product_match(user_text, name) * 0.5))

    blob = _product_text_blob(p)

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

    stock = (p.get("stock_status") or "").strip()
    if stock == "instock":
        score += 10
    elif stock:
        score -= 15

    budget = slots.get("budget")
    if budget:
        price_raw = str(p.get("price") or "").strip()
        price = _safe_int(price_raw.replace(".", "").replace(",", ""), 0)
        if price > 0:
            if price <= budget:
                score += 6
            elif price <= int(budget * 1.15):
                score += 2
            else:
                score -= 10

    return score


def _pick_followup_question(slots: dict) -> str:
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
    top = items[:5]
    lines = ["Encontré estas opciones: 👇"]
    opts: list[dict] = []

    for i, p in enumerate(top, start=1):
        name = (p.get("name") or "").strip()
        price = str(p.get("price") or "").strip()
        stock = (p.get("stock_status") or "").strip()
        stock_label = "✅ disponible" if stock == "instock" else "⛔ agotado"

        short_desc = _shorten(p.get("short_description") or p.get("description") or "", 90)
        desc_part = f" — {short_desc}" if short_desc else ""

        price_part = f"${price}" if price else ""
        lines.append(f"{i}) {name} — {price_part} ({stock_label}){desc_part}")
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

    if msg_type != "text":
        clear_state(phone)
        return {"handled": False}

    text = _clean_text(user_text)
    if not text:
        return {"handled": False}

    if _is_exit_command(text):
        clear_state(phone)
        return {"handled": False, "reason": "exit_command"}

    if _is_tiny_ack(text):
        return {"handled": False}

    # Defaults DB-backed (Plan B) si no pasan funciones desde ingest_core
    if save_options_fn is None:
        save_options_fn = _db_save_recent_options
    if load_recent_options_fn is None:
        load_recent_options_fn = _db_load_recent_options

    raw_state = (get_state(phone) or "").strip()

    # -----------------------------------------
    # 0) Compatibilidad: state viejo V1
    # -----------------------------------------
    if raw_state.startswith(STATE_PREFIX_V1):
        try:
            options, ts = _state_v1_unpack(raw_state)
        except Exception:
            options, ts = [], 0

        if (not options) and load_recent_options_fn is not None:
            try:
                recovered = await load_recent_options_fn(phone)
                if isinstance(recovered, list) and recovered:
                    options = recovered
                    set_state(phone, _state_v1_pack(options))
                    ts = _now_ts()
            except Exception:
                pass

        if ts and (_now_ts() - ts) > 180:
            clear_state(phone)
            return {"handled": False}

        # Foto: SOLO si hay opciones/contexto
        if _is_photo_request(text) and options:
            if len(options) == 1:
                picked = options[0]
                clear_state(phone)
                return {
                    "handled": True,
                    "wc": True,
                    "reason": "photo_send_v1_single",
                    "slots": {},
                    "wa": await send_product_fn(phone, int(picked["id"]), ""),
                }
            await send_text_fn(phone, "📸 Claro. ¿De cuál opción quieres la foto? Responde con el número (1-5).")
            return {"handled": True, "wc": True, "reason": "photo_need_choice_v1", "slots": {}}

        if options:
            choice = parse_choice_number(text)
            if choice and 1 <= choice <= len(options):
                picked = options[choice - 1]
                clear_state(phone)
                return {
                    "handled": True,
                    "wc": True,
                    "reason": "choice_send_v1",
                    "slots": {},
                    "wa": await send_product_fn(phone, int(picked["id"]), ""),
                }

            clear_state(phone)
            return {"handled": False, "reason": "v1_no_number_release"}

        clear_state(phone)
        return {"handled": False}

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

    ts = _safe_int(wc_state.get("ts"), 0)
    if ts and (_now_ts() - ts) > 600:
        wc_state = _default_wc_state()

    stage = (wc_state.get("stage") or "discovery").strip()
    slots = wc_state.get("slots") or _default_wc_state()["slots"]
    candidates = wc_state.get("candidates") or []

    # -----------------------------------------
    # ✅ Foto: si hay candidatos => enviar la tarjeta del primero
    # -----------------------------------------
    if _is_photo_request(text):
        tnorm = _norm(text)
        is_short_confirm = (len(tnorm) <= 12 and tnorm in _CONFIRM_WORDS)

        if not candidates:
            recovered = []
            try:
                recovered = await load_recent_options_fn(phone) if load_recent_options_fn else []
            except Exception:
                recovered = []

            if recovered:
                candidates = recovered
                wc_state["candidates"] = candidates
                wc_state["stage"] = "await_choice"
                wc_state["ts"] = _now_ts()
                set_state(phone, _state_v2_pack(wc_state))

        if candidates:
            if is_short_confirm and len(candidates) > 1:
                await send_text_fn(phone, "📸 Perfecto. ¿De cuál opción quieres la foto? Responde con el número (1-5).")
                return {"handled": True, "wc": True, "reason": "photo_confirm_need_choice_v2", "slots": slots}

            picked = candidates[0]
            pid = _safe_int(picked.get("id"))
            if pid:
                wc_state["ts"] = _now_ts()
                set_state(phone, _state_v2_pack(wc_state))
                return {
                    "handled": True,
                    "wc": True,
                    "reason": "photo_send_from_state_v2",
                    "slots": slots,
                    "wa": await send_product_fn(phone, int(pid), ""),
                }

        await send_text_fn(
            phone,
            "📸 ¡Claro! ¿De cuál perfume quieres la foto?\n\n"
            "Dime el *nombre exacto* o dime si quieres que te muestre opciones para elegir."
        )
        return {"handled": True, "wc": True, "reason": "photo_need_product_v2", "slots": slots}

    # -----------------------------------------
    # 2) Woo aplica SIEMPRE que sea invocado por el router
    # Eliminamos el doble filtro (looks_like_product_question)
    # porque ingest_core ya validó la intención real.
    # -----------------------------------------
    # Esto soluciona que la IA responda "voy a consultar con mi compañero" 
    # cuando mandan el nombre exacto de un perfume extraído de una foto.

    # -----------------------------------------
    # 3) Update slots
    # -----------------------------------------
    slots = _extract_slots(text, slots)
    wc_state["slots"] = slots
    wc_state["ts"] = _now_ts()

    # -----------------------------------------
    # 4) Si espera elección y llega número -> enviar
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
                "slots": slots,
                "wa": await send_product_fn(phone, int(picked["id"]), ""),
            }

        stage = "shortlist"
        wc_state["stage"] = "shortlist"

    # -----------------------------------------
    # 5) Retrieval
    # -----------------------------------------
    query = text
    wc_state["last_query"] = query

    try:
        items = await wc_search_products(query, per_page=12)
    except Exception:
        return {"handled": False}

    if not items:
        wc_state["stage"] = "discovery"
        set_state(phone, _state_v2_pack(wc_state))
        await send_text_fn(phone, f"No encontré resultados exactos con eso 😕\n{_pick_followup_question(slots)}")
        return {"handled": True, "wc": True, "reason": "no_results_v2", "slots": slots}

    # -----------------------------------------
    # 6) Ranking
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

    wc_state["candidates"] = [{"id": _safe_int(p.get("id")), "name": (p.get("name") or "").strip()} for p in top]

    # -----------------------------------------
    # 7) UX
    # -----------------------------------------
    user_norm = _norm(text)
    wants_list = any(k in user_norm for k in ["opciones", "lista", "muestrame", "muéstrame", "ver opciones", "dame opciones"])

    top1 = top[0]
    top_name = (top1.get("name") or "").strip()
    strong_name_score = score_product_match(text, top_name)

    # Si el usuario pidió lista -> menú 1-5 + guardar en DB
    if wants_list and len(top) >= 2:
        menu_text, opts = _build_menu_lines(top)
        wc_state["stage"] = "await_choice"
        wc_state["candidates"] = opts
        set_state(phone, _state_v2_pack(wc_state))

        if save_options_fn is not None:
            try:
                await save_options_fn(phone, opts)
            except Exception:
                pass

        await send_text_fn(phone, menu_text)
        return {"handled": True, "wc": True, "reason": "menu_options_v2", "slots": slots}

    # Match fuerte -> enviar directo
    if strong_name_score >= 80:
        clear_state(phone)
        return {
            "handled": True,
            "wc": True,
            "reason": "strong_match_send_v2",
            "slots": slots,
            "wa": await send_product_fn(phone, int(top1["id"]), ""),
        }

    # Recomendación: enviar 2 tarjetas + texto resumen + guardar candidatos
    recs = top[:2]
    for p in recs:
        try:
            await send_product_fn(phone, int(p["id"]), "")
        except Exception:
            pass

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
    summary_lines.append("Si quieres, te muestro 5 opciones para que elijas con número.")
    summary_lines.append(_pick_followup_question(slots))

    wc_state["stage"] = "await_choice"
    set_state(phone, _state_v2_pack(wc_state))

    # Guardar top 5 en DB para recuperarlo aunque se pierda state
    if save_options_fn is not None:
        try:
            await save_options_fn(phone, wc_state["candidates"])
        except Exception:
            pass

    await send_text_fn(phone, "\n".join(summary_lines))
    return {"handled": True, "wc": True, "reason": "advisor_reco_v2", "slots": slots}