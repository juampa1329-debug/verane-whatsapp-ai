# app/crm/crm_writer.py

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import re
import json

from sqlalchemy import text

from app.db import engine


def _clean(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def ensure_conversation_row(phone: str) -> None:
    """
    Asegura que exista una fila en conversations para ese phone.
    Si no existe, la crea (sin pisar campos).
    """
    phone = (phone or "").strip()
    if not phone:
        return

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                INSERT INTO conversations (phone, updated_at)
                VALUES (:phone, :updated_at)
                ON CONFLICT (phone) DO UPDATE
                SET updated_at = EXCLUDED.updated_at
            """), {"phone": phone, "updated_at": datetime.utcnow()})
    except Exception:
        return


def _merge_tags(existing: str, add: List[str]) -> str:
    """
    Tags separados por coma.
    - normaliza a lower
    - evita duplicados
    """
    base = []
    if existing:
        for t in existing.split(","):
            tt = _clean(t).lower()
            if tt:
                base.append(tt)

    seen = set(base)
    for t in (add or []):
        tt = _clean(str(t)).lower()
        if not tt:
            continue
        if tt not in seen:
            base.append(tt)
            seen.add(tt)

    return ",".join(base)


def update_crm_fields(
    phone: str,
    *,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    city: Optional[str] = None,
    customer_type: Optional[str] = None,
    interests: Optional[str] = None,
    tags_add: Optional[List[str]] = None,
    notes_append: Optional[str] = None,
) -> None:
    """
    Actualiza CRM sin borrar lo previo:
    - tags_add se agrega a tags existente (sin duplicar)
    - notes_append se concatena al final
    - campos (first_name, city, etc) solo se actualizan si vienen no-vacíos
    """
    phone = (phone or "").strip()
    if not phone:
        return

    ensure_conversation_row(phone)

    try:
        with engine.begin() as conn:
            row = conn.execute(text("""
                SELECT
                    COALESCE(first_name,'') AS first_name,
                    COALESCE(last_name,'') AS last_name,
                    COALESCE(city,'') AS city,
                    COALESCE(customer_type,'') AS customer_type,
                    COALESCE(interests,'') AS interests,
                    COALESCE(tags,'') AS tags,
                    COALESCE(notes,'') AS notes
                FROM conversations
                WHERE phone = :phone
                LIMIT 1
            """), {"phone": phone}).mappings().first()

            if not row:
                existing = {"tags": "", "notes": ""}
            else:
                existing = dict(row)

            new_tags = existing.get("tags", "") or ""
            if tags_add:
                new_tags = _merge_tags(new_tags, tags_add)

            new_notes = existing.get("notes", "") or ""
            if notes_append:
                na = _clean(notes_append)
                if na:
                    if new_notes:
                        new_notes = (new_notes + "\n" + na).strip()
                    else:
                        new_notes = na

            def pick(old_val: str, new_val: Optional[str]) -> str:
                nv = _clean(new_val or "")
                if nv:
                    return nv
                return _clean(old_val or "")

            upd = {
                "phone": phone,
                "updated_at": datetime.utcnow(),
                "first_name": pick(existing.get("first_name", ""), first_name),
                "last_name": pick(existing.get("last_name", ""), last_name),
                "city": pick(existing.get("city", ""), city),
                "customer_type": pick(existing.get("customer_type", ""), customer_type),
                "interests": pick(existing.get("interests", ""), interests),
                "tags": new_tags,
                "notes": new_notes,
            }

            conn.execute(text("""
                UPDATE conversations
                SET
                    updated_at = :updated_at,
                    first_name = :first_name,
                    last_name = :last_name,
                    city = :city,
                    customer_type = :customer_type,
                    interests = :interests,
                    tags = :tags,
                    notes = :notes
                WHERE phone = :phone
            """), upd)

    except Exception:
        return


def apply_wc_slots_to_crm(phone: str, slots: Dict[str, Any]) -> None:
    """
    Convierte slots del Woo Assistant a tags/intereses/notes en CRM.

    Ejemplos de tags que guarda:
      - pref:gender:hombre
      - pref:vibe:elegante
      - pref:family:amaderado
      - pref:sweetness:dulce
      - pref:intensity:fuerte
      - pref:budget:150000
    """
    phone = (phone or "").strip()
    if not phone or not isinstance(slots, dict):
        return

    tags: List[str] = []

    gender = (slots.get("gender") or "").strip()
    if gender:
        tags.append(f"pref:gender:{gender}")

    for v in (slots.get("vibe") or []):
        vv = _clean(str(v))
        if vv:
            tags.append(f"pref:vibe:{vv}")

    for o in (slots.get("occasion") or []):
        oo = _clean(str(o))
        if oo:
            tags.append(f"pref:occasion:{oo}")

    for f in (slots.get("family") or []):
        ff = _clean(str(f))
        if ff:
            tags.append(f"pref:family:{ff}")

    sweetness = (slots.get("sweetness") or "").strip()
    if sweetness:
        tags.append(f"pref:sweetness:{sweetness}")

    intensity = (slots.get("intensity") or "").strip()
    if intensity:
        tags.append(f"pref:intensity:{intensity}")

    budget = slots.get("budget")
    if budget:
        try:
            b = int(budget)
            if b > 0:
                tags.append(f"pref:budget:{b}")
        except Exception:
            pass

    brand = (slots.get("brand") or "").strip()
    if brand:
        tags.append(f"pref:brand:{brand}")

    if tags:
        update_crm_fields(phone, tags_add=tags)


# =========================================================
# ✅ NUEVO: Memoria del último producto enviado
# (para "envíame la foto", "mándame la imagen", etc.)
# =========================================================

def remember_last_product_sent(
    phone: str,
    *,
    product_id: int,
    featured_image: str = "",
    real_image: str = "",
    permalink: str = "",
) -> None:
    """
    Guarda "memoria" del último producto enviado en conversations.notes.

    No asume cambios de DB (porque no sabemos si hay columnas extras).
    Es robusto y funciona aunque solo exista la columna notes.

    Formato (línea única):
      last_product_id=123|featured=...|real=...|permalink=...|ts=2026-02-23T...
    """
    phone = (phone or "").strip()
    if not phone:
        return

    ensure_conversation_row(phone)

    try:
        pid = int(product_id)
        if pid <= 0:
            return
    except Exception:
        return

    line = (
        f"last_product_id={pid}"
        f"|featured={(featured_image or '').strip()}"
        f"|real={(real_image or '').strip()}"
        f"|permalink={(permalink or '').strip()}"
        f"|ts={datetime.utcnow().isoformat(timespec='seconds')}Z"
    ).strip()

    # Guardamos al FINAL (append). Si ya existe otra línea last_product_id, la dejamos:
    # al leer tomaremos la ÚLTIMA.
    try:
        update_last_products(phone, last_product_id=pid)
    except Exception:
        pass
    update_crm_fields(phone, notes_append=line)


def get_last_product_sent(phone: str) -> dict:
    """
    Recupera el último producto enviado desde conversations.notes.
    Devuelve:
      {"ok": True, "product_id": int, "featured_image": str, "real_image": str, "permalink": str, "raw": str}
    o:
      {"ok": False, "reason": "..."}
    """
    phone = (phone or "").strip()
    if not phone:
        return {"ok": False, "reason": "missing_phone"}

    try:
        with engine.begin() as conn:
            row = conn.execute(text("""
                SELECT COALESCE(notes,'') AS notes
                FROM conversations
                WHERE phone = :phone
                LIMIT 1
            """), {"phone": phone}).mappings().first()
        notes = (row or {}).get("notes") or ""
    except Exception:
        return {"ok": False, "reason": "db_error"}

    notes = str(notes or "")
    if not notes.strip():
        return {"ok": False, "reason": "no_notes"}

    # buscamos la última línea que contenga last_product_id=
    last_line = ""
    for ln in [x.strip() for x in notes.split("\n") if x.strip()]:
        if "last_product_id=" in ln:
            last_line = ln

    if not last_line:
        return {"ok": False, "reason": "no_last_product"}

    # parse
    try:
        parts = last_line.split("|")
        kv = {}
        for p in parts:
            if "=" in p:
                k, v = p.split("=", 1)
                kv[_clean(k).lower()] = (v or "").strip()

        pid = int(kv.get("last_product_id") or "0")
        if pid <= 0:
            return {"ok": False, "reason": "invalid_product_id", "raw": last_line}

        return {
            "ok": True,
            "product_id": pid,
            "featured_image": kv.get("featured", ""),
            "real_image": kv.get("real", ""),
            "permalink": kv.get("permalink", ""),
            "raw": last_line,
        }
    except Exception:
        return {"ok": False, "reason": "parse_error", "raw": last_line}

# =========================================================
# ✅ NUEVO: CRM Intelligence Layer (campos estructurados)
# =========================================================

def update_intent(
    phone: str,
    *,
    intent_current: str,
    intent_confidence: float = 0.0,
) -> None:
    """Guarda intención actual (si existen columnas). Fallback: tags."""
    phone = (phone or "").strip()
    if not phone:
        return

    ensure_conversation_row(phone)

    ic = _clean(intent_current).lower()
    try:
        conf = float(intent_confidence or 0.0)
    except Exception:
        conf = 0.0

    # Intent como tag (fallback / histórico)
    tags_add = []
    if ic:
        tags_add.append(f"intent:{ic}")

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE conversations
                SET
                    updated_at = :updated_at,
                    intent_current = :intent_current,
                    intent_confidence = :intent_confidence
                WHERE phone = :phone
            """), {
                "phone": phone,
                "updated_at": datetime.utcnow(),
                "intent_current": ic,
                "intent_confidence": conf,
            })
    except Exception:
        # Si no existen columnas, guardamos en tags
        if tags_add:
            update_crm_fields(phone, tags_add=tags_add)


def update_preferences_structured(phone: str, slots: Dict[str, Any]) -> None:
    """Escribe pref_gender y pref_budget si hay columnas; si no, usa tags."""
    phone = (phone or "").strip()
    if not phone or not isinstance(slots, dict):
        return

    gender = _clean(str(slots.get("gender") or "")).lower()
    budget_val = slots.get("budget")

    pref_budget = None
    if budget_val is not None:
        try:
            pref_budget = int(budget_val)
            if pref_budget <= 0:
                pref_budget = None
        except Exception:
            pref_budget = None

    # Fallback tags
    tags_add = []
    if gender:
        tags_add.append(f"pref_gender:{gender}")
    if pref_budget:
        tags_add.append(f"pref_budget:{pref_budget}")

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE conversations
                SET
                    updated_at = :updated_at,
                    pref_gender = COALESCE(NULLIF(:pref_gender,''), pref_gender),
                    pref_budget = COALESCE(:pref_budget, pref_budget)
                WHERE phone = :phone
            """), {
                "phone": phone,
                "updated_at": datetime.utcnow(),
                "pref_gender": gender,
                "pref_budget": pref_budget,
            })
    except Exception:
        if tags_add:
            update_crm_fields(phone, tags_add=tags_add)


def update_summary_auto(phone: str, summary: str) -> None:
    """Guarda un resumen corto (<=500 chars) en summary_auto o notes."""
    phone = (phone or "").strip()
    if not phone:
        return

    s = _clean(summary)
    if not s:
        return
    s = s[:500]

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE conversations
                SET
                    updated_at = :updated_at,
                    summary_auto = :summary_auto
                WHERE phone = :phone
            """), {
                "phone": phone,
                "updated_at": datetime.utcnow(),
                "summary_auto": s,
            })
    except Exception:
        update_crm_fields(phone, notes_append=f"summary_auto: {s}")


def update_last_products(
    phone: str,
    *,
    last_product_id: int | None = None,
    last_products_seen: list[int] | None = None,
    last_stage: str | None = None,
    last_followup_question: str | None = None,
) -> None:
    """Actualiza campos de estado de venta (si existen); fallback a notes."""
    phone = (phone or "").strip()
    if not phone:
        return

    ensure_conversation_row(phone)

    pid = None
    if last_product_id is not None:
        try:
            pid = int(last_product_id)
        except Exception:
            pid = None

    lps = None
    if last_products_seen is not None:
        out = []
        for x in last_products_seen:
            try:
                out.append(int(x))
            except Exception:
                continue
        lps = out

    ls = _clean(last_stage or "")
    lf = _clean(last_followup_question or "")
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                UPDATE conversations
                SET
                    updated_at = :updated_at,
                    last_product_id = COALESCE(:last_product_id, last_product_id),
                    last_products_seen = COALESCE(:last_products_seen, last_products_seen),
                    last_stage = COALESCE(NULLIF(:last_stage,''), last_stage),
                    last_followup_question = COALESCE(NULLIF(:last_followup_question,''), last_followup_question)
                WHERE phone = :phone
            """), {
                "phone": phone,
                "updated_at": datetime.utcnow(),
                "last_product_id": pid,
                "last_products_seen": json.dumps(lps) if lps is not None else None,
                "last_stage": ls,
                "last_followup_question": lf,
            })
    except Exception:
        note = f"last_product_id={pid}|last_stage={ls}|followup={lf}".strip()
        update_crm_fields(phone, notes_append=note)
