# app/ai/intent_router.py
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class IntentResult:
    intent: str
    confidence: float
    payload: Dict[str, Any]


_PHOTO_PAT = re.compile(r"\b(foto|imagen|foto real|muestrame|muestrame la|envia(me)?|manda(me)?)(?:\s+la)?\s*(foto|imagen)?\b", re.I)
_BUY_PAT = re.compile(r"\b(comprar|carrito|pagar|pago|checkout|envio|domicilio|direccion)\b", re.I)
_PRICE_PAT = re.compile(r"\b(precio|cuanto\s+vale|cuesta|valor|stock|disponible|agotad[oa])\b", re.I)
_COMPARE_PAT = re.compile(r"\b(comparar|cual\s+es\s+mejor|entre\s+el\s+\d+\s+y\s+el\s+\d+|vs\b)\b", re.I)

# Preferencias (muy simple; el Woo Assistant hace el parse fino)
_PREF_PAT = re.compile(r"\b(dulce|vainilla|amaderad|citr|acuatic|aromatic|especiad|cuero|floral|noche|dia|oficina|cita|fiesta|verano|invierno|elegante|juvenil|seductor|deportivo)\b", re.I)

# Marcas comunes (puedes ampliar)
_BRAND_PAT = re.compile(r"\b(dior|versace|lattafa|armaf|paco\s+rabanne|carolina\s+herrera|tom\s+ford|chanel|givenchy|ysl|yves\s+saint\s+laurent)\b", re.I)

# Nombre de perfume en caja suele venir con 'pour homme', 'eau de parfum', etc.
_BOX_HINT_PAT = re.compile(r"\b(pour\s+homme|pour\s+femme|eau\s+de\s+parfum|eau\s+de\s+toilette|parfum)\b", re.I)


def _norm(s: str) -> str:
    s = (s or "").strip().lower()
    repl = {"á":"a","é":"e","í":"i","ó":"o","ú":"u","ñ":"n"}
    for a,b in repl.items():
        s = s.replace(a,b)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def detect_intent(
    *,
    user_text: str,
    msg_type: str = "text",
    state: str = "",
    extracted_text: str = "",
    crm_snapshot: Optional[Dict[str, Any]] = None,
) -> IntentResult:
    """
    Router de intención V3 (reglas determinísticas).
    Devuelve intent + confidence + payload (p.ej. query sugerida).
    """
    st = _norm(state)
    t = _norm(user_text)
    et = (extracted_text or "").strip()

    # 1) Choice si está esperando opciones
    if ("await_choice" in st or st.startswith("wc_await")) and t.isdigit():
        return IntentResult("CHOICE", 0.95, {"choice": int(t)})

    # 2) Handoff humano
    if re.search(r"\b(asesor|humano|persona|llamar|llamada)\b", t, re.I):
        return IntentResult("HUMAN_HANDOFF", 0.8, {})

    # 3) Photo request
    if _PHOTO_PAT.search(t):
        return IntentResult("PHOTO_REQUEST", 0.85, {})

    # 4) Buy / price / compare
    if _BUY_PAT.search(t):
        return IntentResult("BUY_FLOW", 0.8, {})
    if _PRICE_PAT.search(t):
        return IntentResult("PRICE_STOCK", 0.75, {})
    if _COMPARE_PAT.search(t):
        return IntentResult("COMPARE", 0.75, {})

    # 5) Imagen/documento con OCR/desc => probable búsqueda de producto
    mt = _norm(msg_type)
    if mt in ("image", "document") and et:
        # Si hay señales de caja o marca, intentamos búsqueda por nombre
        if _BOX_HINT_PAT.search(et) or _BRAND_PAT.search(et):
            # query sugerida: las primeras ~8 palabras útiles
            q = re.sub(r"[^\w\s\-]", " ", et)
            q = re.sub(r"\s+", " ", q).strip()
            q = " ".join(q.split()[:10])
            return IntentResult("PRODUCT_SEARCH", 0.7, {"query": q, "source": "extracted_text"})
        # Si no hay señales, igual puede ser preferencia/consulta
        return IntentResult("UNKNOWN", 0.45, {"source": "image_no_strong_signal"})

    # 6) Presupuesto -> preferencia
    if re.search(r"\b\d{2,3}\s*(k|mil)\b|\b\d{5,7}\b", t):
        return IntentResult("PREFERENCE_RECO", 0.65, {})

    # 7) Preferencias
    if _PREF_PAT.search(t) or _BRAND_PAT.search(t) or re.search(r"\b(perfume|colonia|fragancia)\b", t, re.I):
        # Si parece nombre exacto (muchas mayúsculas en original) se maneja luego en wc_assistant
        return IntentResult("PREFERENCE_RECO", 0.6, {})

    return IntentResult("UNKNOWN", 0.3, {})
