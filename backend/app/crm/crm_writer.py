# app/crm/crm_writer.py

from __future__ import annotations

from typing import Any, Dict, List, Optional
from datetime import datetime
import re

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