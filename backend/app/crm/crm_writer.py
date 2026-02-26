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
            conn.execute(
                text(
                    """
                INSERT INTO conversations (phone, updated_at)
                VALUES (:phone, :updated_at)
                ON CONFLICT (phone) DO UPDATE
                SET updated_at = EXCLUDED.updated_at
            """
                ),
                {"phone": phone, "updated_at": datetime.utcnow()},
            )
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
            row = (
                conn.execute(
                    text(
                        """
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
            """
                    ),
                    {"phone": phone},
                )
                .mappings()
                .first()
            )

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

            conn.execute(
                text(
                    """
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
            """
                ),
                upd,
            )

    except Exception:
        return


def apply_wc_slots_to_crm(phone: str, slots: Dict[str, Any]) -> None:
    """
    Guarda en CRM SOLO info útil para humanos:
    - Interests: resumen corto (familias/aromas/intención)
    - Tags: estado del cliente (no preferencias)
    - Notes: bullets con preferencias y lo que está pidiendo
    """
    phone = (phone or "").strip()
    if not phone or not isinstance(slots, dict):
        return

    # --- Tags (estado) ---
    tags: List[str] = []
    stage = (slots.get("stage") or "").strip()  # opcional si lo produce el modelo
    if stage:
        tags.append(f"estado:{_clean(stage)}")

    # --- Interests (texto corto) ---
    pieces: List[str] = []
    gender = (slots.get("gender") or "").strip()
    if gender:
        pieces.append(gender)

    fam = [_clean(str(x)) for x in (slots.get("family") or []) if _clean(str(x))]
    if fam:
        pieces.append(" / ".join(fam[:4]))

    vibe = [_clean(str(x)) for x in (slots.get("vibe") or []) if _clean(str(x))]
    if vibe:
        pieces.append(" ".join(vibe[:3]))

    interests = ". ".join([p for p in pieces if p]).strip() or None

    # --- Notes (bullets útiles) ---
    bullets: List[str] = []

    if gender:
        bullets.append(f"Preferencia: {gender}")

    occasion = [_clean(str(x)) for x in (slots.get("occasion") or []) if _clean(str(x))]
    if occasion:
        bullets.append(f"Ocasión: {', '.join(occasion[:3])}")

    sweetness = (slots.get("sweetness") or "").strip()
    if sweetness:
        bullets.append(f"Dulzor: {sweetness}")

    intensity = (slots.get("intensity") or "").strip()
    if intensity:
        bullets.append(f"Intensidad: {intensity}")

    budget = slots.get("budget")
    if budget:
        bullets.append(f"Presupuesto: {budget}")

    asked = (slots.get("asked") or "").strip()  # opcional: 'precio', 'foto', etc.
    if asked:
        bullets.append(f"Pregunta: {asked}")

    note = None
    if bullets:
        note = "• " + "\n• ".join(bullets)

    # ✅ FIX: update_crm_fields usa tags_add y notes_append
    update_crm_fields(
        phone,
        tags_add=tags or None,
        interests=interests,
        notes_append=note,
    )


def get_last_product_sent(phone: str) -> Dict[str, Any]:
    """
    Devuelve el último producto "enviado" al usuario, para poder reenviar la tarjeta
    cuando el cliente dice "envíame la foto".

    Como la estructura exacta puede variar según tu tabla `messages`,
    hacemos una búsqueda robusta y tratamos de inferir product_id desde:
      - texto (patterns como product_id=123, product_id: 123)
      - permalink (patterns /product/123, ?p=123, post=123)
    """
    phone = (phone or "").strip()
    if not phone:
        return {"ok": False, "reason": "missing_phone"}

    def _extract_product_id_from_any(text_val: str) -> int:
        t = (text_val or "").strip()
        if not t:
            return 0

        # product_id=123 / product_id: 123
        m = re.search(r"(?:product[_\s-]?id)\s*[:=]\s*(\d+)", t, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass

        # /product/123
        m = re.search(r"/product/(\d+)", t, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass

        # ?p=123 / post=123
        m = re.search(r"(?:\?|&)(?:p|post|product_id)=(\d+)", t, re.IGNORECASE)
        if m:
            try:
                return int(m.group(1))
            except Exception:
                pass

        return 0

    try:
        with engine.begin() as conn:
            # Tomamos el último outbound con señales típicas de producto (permalink o imagen),
            # sin asumir columnas nuevas.
            row = (
                conn.execute(
                    text(
                        """
                SELECT
                    id,
                    COALESCE(text,'') AS text,
                    COALESCE(permalink,'') AS permalink,
                    COALESCE(featured_image,'') AS featured_image,
                    COALESCE(real_image,'') AS real_image,
                    created_at
                FROM messages
                WHERE phone = :phone
                  AND direction = 'out'
                  AND (
                        COALESCE(permalink,'') <> ''
                     OR COALESCE(featured_image,'') <> ''
                     OR COALESCE(real_image,'') <> ''
                     OR COALESCE(text,'') ILIKE '%product%'
                  )
                ORDER BY created_at DESC
                LIMIT 1
            """
                    ),
                    {"phone": phone},
                )
                .mappings()
                .first()
            )

        if not row:
            return {"ok": False, "reason": "no_previous_product_like_message"}

        raw_text = (row.get("text") or "").strip()
        permalink = (row.get("permalink") or "").strip()
        featured_image = (row.get("featured_image") or "").strip()
        real_image = (row.get("real_image") or "").strip()

        pid = 0
        pid = pid or _extract_product_id_from_any(raw_text)
        pid = pid or _extract_product_id_from_any(permalink)

        if pid <= 0:
            return {
                "ok": False,
                "reason": "could_not_extract_product_id",
                "raw": raw_text or permalink or "",
                "message_id": int(row.get("id") or 0),
                "permalink": permalink,
                "featured_image": featured_image,
                "real_image": real_image,
            }

        return {
            "ok": True,
            "product_id": int(pid),
            "raw": raw_text or permalink or "",
            "message_id": int(row.get("id") or 0),
            "permalink": permalink,
            "featured_image": featured_image,
            "real_image": real_image,
        }

    except Exception as e:
        return {"ok": False, "reason": "db_error", "error": str(e)[:900]}