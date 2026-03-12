from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import text

from app.db import engine
from app.crm.crm_writer import sync_ai_memory


_BRAND_HINTS = (
    "dior", "versace", "armani", "azzaro", "paco", "rabanne", "carolina", "herrera",
    "ysl", "chanel", "lattafa", "armaf", "tom ford", "valentino", "givenchy",
    "jean paul", "gaultier", "gucci", "prada", "lacoste", "hugo boss", "paquito",
)
_PERFUME_HINTS = (
    "sauvage", "eros", "invictus", "one million", "212", "bleu de chanel",
    "acqua di gio", "acqua de gio", "profondo", "profumo", "nitro red",
    "le male", "bad boy", "good girl", "spicebomb", "toy boy",
)
_PRODUCT_WORDS = (
    "perfume", "perfumes", "fragancia", "fragancias", "colonia", "colonias",
    "que me recomiendas", "que me recomienda", "qué me recomiendas", "qué me recomienda",
    "uno para", "algo para", "pa mi", "pa mi novio", "pa mi novia", "del bueno",
)
_PRICE_WORDS = (
    "precio", "cuanto", "cuánto", "vale", "cuesta", "valor", "stock", "disponible",
    "disponibilidad", "agotado", "hay", "tienen", "manejan",
)
_BUY_WORDS = (
    "comprar", "lo compro", "me lo llevo", "quiero comprar", "quiero ese",
    "me interesa ese", "pasame el link", "pásame el link", "link de pago",
    "checkout", "carrito", "como pago", "cómo pago", "quiero pagarlo",
)
_PAYMENT_WORDS = (
    "comprobante", "transferencia", "consignacion", "consignación", "pago",
    "ya pague", "ya pagué", "adjunto pago", "soporte de pago",
)
_PAYMENT_PROOF_STRONG_WORDS = (
    "comprobante", "transferencia", "consignacion", "consignación",
    "ya pague", "ya pagué", "adjunto pago", "soporte de pago",
)
_SUPPORT_WORDS = (
    "reclamo", "queja", "pedido mal", "mal pedido", "equivocado", "devolucion",
    "devolución", "cambio", "garantia", "garantía", "no me llego", "no me llegó",
    "me llego mal", "me llegó mal", "vino roto", "llego roto", "llegó roto",
    "se rego", "se regó", "me mandaron otro", "no era el que pedi", "no era el que pedí",
    "salio malo", "salió malo", "chimbo", "paila",
)
_PHOTO_WORDS = (
    "foto", "fotos", "imagen", "imagenes", "imágenes", "ver foto",
    "foto real", "muestrame", "muéstrame", "mandame", "mándame", "enviame", "envíame",
)
_GIFT_WORDS = (
    "regalo", "novio", "novia", "esposo", "esposa", "pareja", "cumpleaños", "cumpleanos",
)
_VARIANT_WORDS = (
    "50ml", "100ml", "200ml", "30ml", "grande", "pequeño", "pequeno", "mediano",
    "el de 50", "el de 100", "presentacion", "presentación", "tamaño", "tamano",
)
_TINY_ACKS = {
    "ok", "dale", "listo", "perfecto", "gracias", "si", "sí", "vale", "bien", "de una",
}
_GREETING_WORDS = (
    "hola", "buenas", "buenos dias", "buen día", "buen dia", "buenas tardes", "buenas noches",
    "como vas", "cómo vas", "como estas", "cómo estás", "que tal", "qué tal",
)
_ONBOARDING_WORDS = (
    "con quien tengo el gusto", "con quién tengo el gusto", "quien eres", "quién eres",
    "como te llamas", "cómo te llamas", "tu nombre", "me regalas tu nombre",
    "quien me atiende", "quién me atiende", "como va todo", "cómo va todo",
)
_COMMERCIAL_FOLLOWUP_WORDS = (
    "ese", "esa", "ese perfume", "esa fragancia", "el de", "la de", "mandamelo", "mándamelo",
    "pasame", "pásame", "precio", "stock", "disponible", "link", "comprar",
    "50ml", "100ml", "200ml", "foto", "imagen", "me interesa",
)
_CITY_HINTS = (
    "bogota", "bogotá", "medellin", "medellín", "cali", "barranquilla", "cartagena",
    "bucaramanga", "pereira", "manizales", "ibague", "ibagué", "cucuta", "cúcuta",
    "santa marta", "villavicencio", "pasto", "armenia",
)


_NON_NAME_WORDS = {
    "hola", "buenas", "buenos", "dias", "tardes", "noches", "como", "que", "tal",
    "soy", "de", "en", "mi", "nombre", "es", "llamo", "llamas", "gusto",
    "hombre", "mujer", "unisex", "perfume", "fragancia", "colonia",
    "precio", "stock", "disponible", "comprar", "pago", "reclamo", "soporte",
    "foto", "imagen", "regalo", "oficina", "noche", "fiesta",
}


def _norm(text_value: str) -> str:
    text_value = (text_value or "").strip().lower()
    replacements = {"á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u", "ñ": "n"}
    for a, b in replacements.items():
        text_value = text_value.replace(a, b)
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value


def _clean_visible_text(text_value: str) -> str:
    text_value = (text_value or "").strip()
    text_value = re.sub(r"\s+", " ", text_value).strip()
    return text_value


def _normalize_product_aliases(text_value: str) -> str:
    out = _clean_visible_text(text_value)
    replacements = {
        "paquito": "paco rabanne",
        "agua de gio": "acqua di gio",
        "aqua di gio": "acqua di gio",
        "aqua de gio": "acqua di gio",
        "acqua de gio": "acqua di gio",
    }
    low = _norm(out)
    for src, dst in replacements.items():
        low = low.replace(_norm(src), _norm(dst))
    return re.sub(r"\s+", " ", low).strip()


def _latest_user_messages(messages: List[Dict[str, Any]]) -> List[str]:
    out: List[str] = []
    for row in messages:
        if (row.get("direction") or "").strip().lower() != "in":
            continue
        parts = [
            _clean_visible_text(row.get("text") or ""),
            _clean_visible_text(row.get("extracted_text") or ""),
        ]
        for part in parts:
            if part:
                out.append(part)
                break
    return out


def _is_plausible_name_token(raw_token: str) -> bool:
    token = _clean_visible_text(raw_token)
    n = _norm(token)
    if not n or len(n) < 2 or len(n) > 24:
        return False
    if re.search(r"\d", n):
        return False
    if n in _NON_NAME_WORDS:
        return False
    return re.fullmatch(r"[a-zA-ZÁÉÍÓÚáéíóúÑñÜü]+", token) is not None


def _extract_name_from_text(raw: str, low: str) -> tuple[str, str, bool]:
    if not raw or not low:
        return "", "", False

    m_name = re.search(
        r"\b(mi nombre es|me llamo)\s+([a-zA-ZÁÉÍÓÚáéíóúÑñÜü]+)(?:\s+([a-zA-ZÁÉÍÓÚáéíóúÑñÜü]+))?\b",
        raw,
        re.IGNORECASE,
    )
    if m_name:
        first = _clean_visible_text(m_name.group(2))
        last = _clean_visible_text(m_name.group(3) or "")
        if _is_plausible_name_token(first):
            if last and (not _is_plausible_name_token(last)):
                last = ""
            return first, last, True

    # Permitimos "soy juan" como mensaje corto, evitando "soy hombre".
    m_soy = re.search(
        r"^\s*soy\s+([a-zA-ZÁÉÍÓÚáéíóúÑñÜü]+)(?:\s+([a-zA-ZÁÉÍÓÚáéíóúÑñÜü]+))?\s*$",
        raw,
        re.IGNORECASE,
    )
    if m_soy:
        first = _clean_visible_text(m_soy.group(1))
        last = _clean_visible_text(m_soy.group(2) or "")
        if _is_plausible_name_token(first):
            if last and (not _is_plausible_name_token(last)):
                last = ""
            return first, last, True

    return "", "", False


def _extract_profile(messages: List[str]) -> Dict[str, Any]:
    profile: Dict[str, Any] = {"first_name": "", "last_name": "", "city": "", "name_confirmed": False}

    for msg in reversed(messages):
        raw = _clean_visible_text(msg)
        low = _norm(raw)
        if not low:
            continue

        if not profile["first_name"]:
            first, last, confirmed = _extract_name_from_text(raw, low)
            if first:
                profile["first_name"] = first
                profile["last_name"] = last
                profile["name_confirmed"] = bool(confirmed)

        for city in _CITY_HINTS:
            city_norm = _norm(city)
            if any(x in low for x in (f"soy de {city_norm}", f"estoy en {city_norm}", f"vivo en {city_norm}", city_norm)):
                profile["city"] = city.title()
                break

        if profile["first_name"] and profile["city"]:
            break

    return profile


def _extract_perfumes_asked(messages: List[str], vision_obj: Dict[str, Any] | None) -> List[str]:
    found: List[str] = []

    if isinstance(vision_obj, dict) and vision_obj.get("type") == "perfume":
        q = _clean_visible_text(vision_obj.get("search_text") or "")
        if q:
            found.append(q)

    for msg in messages:
        raw = _clean_visible_text(msg)
        low = _norm(raw)
        if not raw or _is_tiny_ack(raw):
            continue

        if not (
            _contains_any(raw, _BRAND_HINTS)
            or _contains_any(raw, _PERFUME_HINTS)
            or any(x in low for x in ("perfume", "fragancia", "colonia", "paquito"))
        ):
            continue

        candidate = _normalize_product_aliases(raw)
        candidate = re.sub(
            r"\b(quiero|busco|tienen|tiene|que me recomiendas|qué me recomiendas|que me recomienda|qué me recomienda|me interesa|muestrame|muéstrame|mandame|mándame|enviame|envíame|uno para|algo para|pa mi|pa mi novio|pa mi novia|para regalo)\b",
            " ",
            candidate,
            flags=re.IGNORECASE,
        )
        candidate = re.sub(r"\s+", " ", candidate).strip()
        if candidate:
            found.append(" ".join(candidate.split()[:8]))

    deduped: List[str] = []
    seen = set()
    for item in found:
        key = _norm(item)
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
        if len(deduped) >= 6:
            break
    return deduped


def _contains_any(text_value: str, words: tuple[str, ...]) -> bool:
    t = _norm(text_value)
    return any(_norm(word) in t for word in words)


def _is_tiny_ack(text_value: str) -> bool:
    return _norm(text_value) in _TINY_ACKS


def _is_greeting_or_onboarding(text_value: str) -> bool:
    t = _norm(text_value)
    if not t:
        return False
    return _contains_any(t, _GREETING_WORDS) or _contains_any(t, _ONBOARDING_WORDS)


def _has_commercial_signal(text_value: str) -> bool:
    t = _norm(text_value)
    if not t:
        return False
    return any(
        _contains_any(t, group)
        for group in (
            _BRAND_HINTS,
            _PERFUME_HINTS,
            _PRODUCT_WORDS,
            _PRICE_WORDS,
            _BUY_WORDS,
            _PAYMENT_WORDS,
            _SUPPORT_WORDS,
            _PHOTO_WORDS,
            _VARIANT_WORDS,
            _COMMERCIAL_FOLLOWUP_WORDS,
        )
    )


def _should_reuse_previous_query(current_text: str, messages: List[str]) -> bool:
    latest = _clean_visible_text(current_text) or (messages[-1] if messages else "")
    if not latest:
        return False
    if _is_greeting_or_onboarding(latest):
        return False
    if _is_tiny_ack(latest):
        return True
    return _has_commercial_signal(latest)


def _extract_budget(text_value: str) -> int | None:
    t = _norm(text_value)
    if not t:
        return None

    m = re.search(r"\b(\d{1,3})\s*(mil|k)\b", t)
    if m:
        try:
            return int(m.group(1)) * 1000
        except Exception:
            return None

    m = re.search(r"\b(\d{5,7})\b", t)
    if not m:
        return None

    try:
        return int(m.group(1))
    except Exception:
        return None


def _extract_preferences(messages: List[str]) -> Dict[str, Any]:
    joined = " ".join(_norm(x) for x in messages if x)
    prefs: Dict[str, Any] = {
        "gender": None,
        "occasion": [],
        "family": [],
        "budget": None,
        "gift": False,
    }

    if any(x in joined for x in ("hombre", "masculino", "novio", "esposo")):
        prefs["gender"] = "hombre"
    elif any(x in joined for x in ("mujer", "femenino", "novia", "esposa")):
        prefs["gender"] = "mujer"
    elif "unisex" in joined:
        prefs["gender"] = "unisex"

    occasions = []
    for key in ("oficina", "trabajo", "diario", "noche", "fiesta", "cita", "regalo"):
        if key in joined:
            occasions.append(key)
    prefs["occasion"] = occasions

    families = []
    for key in ("dulce", "fresco", "amaderado", "ambarado", "citrico", "cítrico", "acuatico", "floral", "vainilla"):
        if _norm(key) in joined:
            families.append(_norm(key))
    prefs["family"] = families

    for msg in reversed(messages):
        budget = _extract_budget(msg)
        if budget:
            prefs["budget"] = budget
            break

    prefs["gift"] = any(_contains_any(msg, _GIFT_WORDS) for msg in messages)
    return prefs


def _extract_product_query(
    messages: List[str],
    vision_obj: Dict[str, Any] | None,
    current_text: str = "",
) -> str:
    if isinstance(vision_obj, dict) and (vision_obj.get("type") == "perfume"):
        search_text = _clean_visible_text(vision_obj.get("search_text") or "")
        if search_text:
            return _normalize_product_aliases(search_text)

        cands = vision_obj.get("product_candidates") or []
        if isinstance(cands, list) and cands:
            top = cands[0] or {}
            parts = [
                _clean_visible_text(top.get("brand") or ""),
                _clean_visible_text(top.get("name") or ""),
                _clean_visible_text(top.get("variant") or ""),
                _clean_visible_text(top.get("size") or ""),
            ]
            query = " ".join([p for p in parts if p]).strip()
            if query:
                return _normalize_product_aliases(query)

    latest = _clean_visible_text(current_text) or (messages[-1] if messages else "")
    allow_history = _should_reuse_previous_query(latest, messages)

    for idx, msg in enumerate(reversed(messages)):
        if idx > 0 and not allow_history:
            break

        raw = _clean_visible_text(msg)
        low = _norm(raw)
        if not raw or _is_tiny_ack(raw):
            continue

        explicit_product = (
            _contains_any(raw, _PRODUCT_WORDS)
            or _contains_any(raw, _BRAND_HINTS)
            or _contains_any(raw, _PERFUME_HINTS)
            or re.search(r"\b\d{2,3}\s*ml\b", low) is not None
        )
        if not explicit_product:
            continue

        cleaned = re.sub(
            r"\b(quiero|busco|tienen|tiene|tendran|tendrán|me muestras|muestrame|muéstrame|me interesa|mandame|mándame|enviame|envíame|pasame|pásame|quiero ver|quiero comprar|tienes algo para|para regalo|para mi novio|para mi novia)\b",
            " ",
            raw,
            flags=re.IGNORECASE,
        )
        cleaned = re.sub(r"[?¡!.,;:]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if cleaned:
            return _normalize_product_aliases(" ".join(cleaned.split()[:8]).strip())

    return ""


def _infer_intent(
    *,
    current_text: str,
    msg_type: str,
    messages: List[str],
    product_query: str,
    prefs: Dict[str, Any],
    last_product_id: int,
    vision_obj: Dict[str, Any] | None,
) -> tuple[str, float, str]:
    latest_text = _clean_visible_text(current_text) or (messages[-1] if messages else "")
    joined_recent = " || ".join(_norm(x) for x in messages[-6:])
    current_has_commerce = _has_commercial_signal(latest_text) or _contains_any(latest_text, _COMMERCIAL_FOLLOWUP_WORDS)

    # Si el mensaje actual es saludo/social, priorizamos modo asesor conversacional
    # para no arrastrar intencion comercial vieja de mensajes anteriores.
    if _is_greeting_or_onboarding(latest_text) and not current_has_commerce:
        return "ONBOARDING", 0.92, "discovery"

    if isinstance(vision_obj, dict) and vision_obj.get("type") == "receipt":
        return "PAYMENT_PROOF", 0.99, "awaiting_payment_validation"

    if msg_type in ("image", "document") and _contains_any(latest_text, _PAYMENT_WORDS):
        return "PAYMENT_PROOF", 0.85, "awaiting_payment_validation"

    if _contains_any(joined_recent, _PAYMENT_PROOF_STRONG_WORDS):
        return "PAYMENT_PROOF", 0.82, "awaiting_receipt"

    if _contains_any(joined_recent, _SUPPORT_WORDS):
        return "SUPPORT", 0.82, "support"

    if _contains_any(latest_text, _PHOTO_WORDS) and (last_product_id > 0 or product_query):
        return "PHOTO_REQUEST", 0.9, "negotiating"

    if _contains_any(joined_recent, _BUY_WORDS) and (last_product_id > 0 or product_query):
        return "BUY_FLOW", 0.92, "buying"

    if _contains_any(joined_recent, _VARIANT_WORDS):
        return "VARIANT_SELECTION", 0.8, "searching_product"

    if _contains_any(joined_recent, _PRICE_WORDS) and (product_query or last_product_id > 0):
        return "PRICE_STOCK", 0.8, "searching_product"

    if product_query:
        return "PRODUCT_SEARCH", 0.78, "searching_product"

    has_preferences = bool(
        prefs.get("gender")
        or prefs.get("occasion")
        or prefs.get("family")
        or prefs.get("budget")
        or prefs.get("gift")
    )
    if has_preferences:
        return "PREFERENCE_RECO", 0.72, "discovery"

    return "GENERAL", 0.35, "general"


def _load_recent_context(phone: str, limit: int) -> Dict[str, Any]:
    with engine.begin() as conn:
        conv = conn.execute(text("""
            SELECT
                COALESCE(last_product_id, 0) AS last_product_id,
                COALESCE(intent_product_query, '') AS intent_product_query,
                COALESCE(intent_product_candidates, '[]'::jsonb) AS intent_product_candidates,
                COALESCE(wc_last_options, '[]'::jsonb) AS wc_last_options
            FROM conversations
            WHERE phone = :phone
            LIMIT 1
        """), {"phone": phone}).mappings().first()

        rows = conn.execute(text("""
            SELECT direction, msg_type, text, extracted_text, created_at
            FROM messages
            WHERE phone = :phone
            ORDER BY created_at DESC
            LIMIT :limit
        """), {"phone": phone, "limit": limit}).mappings().all()

    return {
        "conversation": dict(conv or {}),
        "messages": [dict(r) for r in reversed(rows)],
    }


def _persist_state(phone: str, state: Dict[str, Any]) -> None:
    if not phone:
        return

    payload = {
        "phone": phone,
        "updated_at": datetime.utcnow(),
        "intent_current": str(state.get("intent_current") or "GENERAL").strip(),
        "intent_confidence": float(state.get("intent_confidence") or 0.0),
        "intent_stage": str(state.get("intent_stage") or "general").strip(),
        "intent_product_query": str(state.get("intent_product_query") or "").strip(),
        "intent_product_candidates": json.dumps(state.get("intent_product_candidates") or [], ensure_ascii=False),
        "intent_preferences": json.dumps(state.get("intent_preferences") or {}, ensure_ascii=False),
        "payment_status": str(state.get("payment_status") or "").strip(),
        "payment_reference": str(state.get("payment_reference") or "").strip(),
        "payment_amount": str(state.get("payment_amount") or "").strip(),
        "payment_currency": str(state.get("payment_currency") or "").strip(),
        "last_reconstructed_at": datetime.utcnow(),
    }

    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO conversations (
                phone,
                updated_at,
                intent_current,
                intent_confidence,
                intent_stage,
                intent_product_query,
                intent_product_candidates,
                intent_preferences,
                payment_status,
                payment_reference,
                payment_amount,
                payment_currency,
                last_reconstructed_at
            )
            VALUES (
                :phone,
                :updated_at,
                :intent_current,
                :intent_confidence,
                :intent_stage,
                :intent_product_query,
                CAST(:intent_product_candidates AS jsonb),
                CAST(:intent_preferences AS jsonb),
                :payment_status,
                :payment_reference,
                :payment_amount,
                :payment_currency,
                :last_reconstructed_at
            )
            ON CONFLICT (phone)
            DO UPDATE SET
                updated_at = EXCLUDED.updated_at,
                intent_current = EXCLUDED.intent_current,
                intent_confidence = EXCLUDED.intent_confidence,
                intent_stage = EXCLUDED.intent_stage,
                intent_product_query = EXCLUDED.intent_product_query,
                intent_product_candidates = EXCLUDED.intent_product_candidates,
                intent_preferences = EXCLUDED.intent_preferences,
                payment_status = CASE
                    WHEN COALESCE(EXCLUDED.payment_status, '') <> '' THEN EXCLUDED.payment_status
                    ELSE conversations.payment_status
                END,
                payment_reference = CASE
                    WHEN COALESCE(EXCLUDED.payment_reference, '') <> '' THEN EXCLUDED.payment_reference
                    ELSE conversations.payment_reference
                END,
                payment_amount = CASE
                    WHEN COALESCE(EXCLUDED.payment_amount, '') <> '' THEN EXCLUDED.payment_amount
                    ELSE conversations.payment_amount
                END,
                payment_currency = CASE
                    WHEN COALESCE(EXCLUDED.payment_currency, '') <> '' THEN EXCLUDED.payment_currency
                    ELSE conversations.payment_currency
                END,
                last_reconstructed_at = EXCLUDED.last_reconstructed_at
        """), payload)


def reconstruct_conversation_state(
    *,
    phone: str,
    current_text: str = "",
    msg_type: str = "text",
    vision_obj: Dict[str, Any] | None = None,
    limit: int = 30,
) -> Dict[str, Any]:
    phone = (phone or "").strip()
    if not phone:
        return {
            "intent_current": "GENERAL",
            "intent_confidence": 0.0,
            "intent_stage": "general",
            "intent_product_query": "",
            "intent_product_candidates": [],
            "intent_preferences": {},
            "payment_status": "",
            "payment_reference": "",
            "payment_amount": "",
            "payment_currency": "",
            "force_woo": False,
        }

    ctx = _load_recent_context(phone, max(10, min(int(limit or 30), 60)))
    conv = ctx.get("conversation") or {}
    recent_messages = ctx.get("messages") or []
    user_messages = _latest_user_messages(recent_messages)

    current_clean = _clean_visible_text(current_text)
    if current_clean:
        user_messages.append(current_clean)

    prefs = _extract_preferences(user_messages)
    profile = _extract_profile(user_messages)
    perfumes_asked = _extract_perfumes_asked(user_messages, vision_obj)
    product_query = _extract_product_query(user_messages, vision_obj, current_clean)
    if (not product_query) and _should_reuse_previous_query(current_clean, user_messages):
        product_query = _clean_visible_text(conv.get("intent_product_query") or "")
    if product_query and product_query not in perfumes_asked:
        perfumes_asked.insert(0, product_query)
        perfumes_asked = perfumes_asked[:6]

    last_product_id = 0
    try:
        last_product_id = int(conv.get("last_product_id") or 0)
    except Exception:
        last_product_id = 0

    intent_current, intent_confidence, intent_stage = _infer_intent(
        current_text=current_clean,
        msg_type=(msg_type or "text").strip().lower(),
        messages=user_messages,
        product_query=product_query,
        prefs=prefs,
        last_product_id=last_product_id,
        vision_obj=vision_obj,
    )

    product_candidates = conv.get("wc_last_options") or conv.get("intent_product_candidates") or []
    if not isinstance(product_candidates, list):
        product_candidates = []

    payment_status = ""
    payment_reference = ""
    payment_amount = ""
    payment_currency = ""
    if isinstance(vision_obj, dict) and vision_obj.get("type") == "receipt":
        receipt = vision_obj.get("receipt") or {}
        payment_status = "received_unverified"
        payment_reference = _clean_visible_text(receipt.get("reference") or "")
        payment_amount = _clean_visible_text(str(receipt.get("amount") or ""))
        payment_currency = _clean_visible_text(receipt.get("currency") or "")
    elif intent_current == "PAYMENT_PROOF":
        payment_status = "awaiting_receipt"

    support_status = "reclamo_activo" if intent_current == "SUPPORT" else ""

    state = {
        "intent_current": intent_current,
        "intent_confidence": float(intent_confidence),
        "intent_stage": intent_stage,
        "intent_product_query": product_query,
        "intent_product_candidates": product_candidates[:5],
        "intent_preferences": prefs,
        "payment_status": payment_status,
        "payment_reference": payment_reference,
        "payment_amount": payment_amount,
        "payment_currency": payment_currency,
        "support_status": support_status,
        "perfumes_asked": perfumes_asked,
        "first_name": profile.get("first_name") or "",
        "last_name": profile.get("last_name") or "",
        "city": profile.get("city") or "",
        "name_confirmed": bool(profile.get("name_confirmed") or False),
        "force_woo": intent_current in {
            "PHOTO_REQUEST",
            "BUY_FLOW",
            "VARIANT_SELECTION",
            "PRICE_STOCK",
            "PRODUCT_SEARCH",
        },
        "last_product_id": last_product_id,
    }

    _persist_state(phone, state)
    sync_ai_memory(
        phone,
        {
            "first_name": state.get("first_name") or "",
            "last_name": state.get("last_name") or "",
            "city": state.get("city") or "",
            "name_confirmed": bool(state.get("name_confirmed") or False),
            "intent_current": state.get("intent_current") or "",
            "intent_stage": state.get("intent_stage") or "",
            "product_query": state.get("intent_product_query") or "",
            "perfumes_asked": state.get("perfumes_asked") or [],
            "preferences": state.get("intent_preferences") or {},
            "payment_status": state.get("payment_status") or "",
            "payment_reference": state.get("payment_reference") or "",
            "payment_amount": state.get("payment_amount") or "",
            "payment_currency": state.get("payment_currency") or "",
            "support_status": state.get("support_status") or "",
        },
    )
    return state
