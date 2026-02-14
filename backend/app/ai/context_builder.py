from __future__ import annotations

import re
from typing import Any, Dict, List

from sqlalchemy import text

from app.db import engine


# =========================================================
# Utils
# =========================================================

def _clean_text(s: str) -> str:
    s = (s or "").strip()
    s = re.sub(r"\s+", " ", s)
    return s


def _keywords_from_text(user_text: str) -> List[str]:
    t = (user_text or "").lower()
    t = re.sub(r"[^a-z0-9áéíóúñü\s]+", " ", t, flags=re.IGNORECASE)
    parts = [p.strip() for p in t.split() if p.strip()]
    kws = [p for p in parts if len(p) >= 4]
    seen = set()
    out: List[str] = []
    for k in kws:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out[:12]


def _clip(s: str, max_chars: int) -> str:
    s = (s or "").strip()
    if max_chars <= 0 or len(s) <= max_chars:
        return s
    return (s[: max(0, max_chars - 20)] + " …(recortado)").strip()


# =========================================================
# DB accessors
# =========================================================

def _get_crm(phone: str) -> Dict[str, Any]:
    with engine.begin() as conn:
        r = conn.execute(text("""
            SELECT
                phone,
                COALESCE(first_name,'') AS first_name,
                COALESCE(last_name,'') AS last_name,
                COALESCE(city,'') AS city,
                COALESCE(customer_type,'') AS customer_type,
                COALESCE(interests,'') AS interests,
                COALESCE(tags,'') AS tags,
                COALESCE(notes,'') AS notes,
                COALESCE(ai_state,'') AS ai_state,
                COALESCE(takeover, FALSE) AS takeover
            FROM conversations
            WHERE phone = :phone
        """), {"phone": phone}).mappings().first()

    if not r:
        return {
            "first_name": "",
            "last_name": "",
            "city": "",
            "customer_type": "",
            "interests": "",
            "tags": "",
            "notes": "",
            "ai_state": "",
            "takeover": False,
        }
    return dict(r)


def _get_recent_messages(phone: str, limit: int = 14) -> List[Dict[str, Any]]:
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT direction, msg_type, text, created_at
            FROM messages
            WHERE phone = :phone
            ORDER BY created_at DESC
            LIMIT :limit
        """), {"phone": phone, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]


# =========================================================
# KB schema (best-effort + run-once)
# =========================================================

_KB_SCHEMA_READY = False

def _ensure_kb_schema_safe() -> None:
    """
    Best-effort: si el router KB ya creó tablas, OK.
    Si no, se crean. Si falla, KB simplemente no se usa.
    Run-once por proceso para evitar overhead en cada request.
    """
    global _KB_SCHEMA_READY
    if _KB_SCHEMA_READY:
        return

    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ai_knowledge_files (
                    id TEXT PRIMARY KEY,
                    file_name TEXT NOT NULL,
                    mime_type TEXT NOT NULL,
                    size_bytes INTEGER NOT NULL DEFAULT 0,
                    storage_path TEXT NOT NULL,
                    notes TEXT NOT NULL DEFAULT '',
                    is_active BOOLEAN NOT NULL DEFAULT TRUE,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS ai_knowledge_chunks (
                    id SERIAL PRIMARY KEY,
                    file_id TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL DEFAULT 0,
                    content TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    FOREIGN KEY (file_id) REFERENCES ai_knowledge_files(id) ON DELETE CASCADE
                )
            """))
        _KB_SCHEMA_READY = True
    except Exception:
        return


def _kb_retrieve(user_text: str, max_chunks: int = 6, max_chars: int = 3500) -> str:
    _ensure_kb_schema_safe()

    kws = _keywords_from_text(user_text)
    rows: List[Dict[str, Any]] = []

    with engine.begin() as conn:
        if kws:
            clauses = []
            params: Dict[str, Any] = {"limit": max_chunks * 3}
            for i, k in enumerate(kws):
                key = f"kw{i}"
                params[key] = f"%{k}%"
                clauses.append(f"LOWER(kc.content) LIKE :{key}")

            where_sql = " OR ".join(clauses) if clauses else "FALSE"

            rows = conn.execute(text(f"""
                SELECT
                    kc.content,
                    kf.file_name,
                    kf.notes,
                    kf.updated_at,
                    kc.chunk_index
                FROM ai_knowledge_chunks kc
                JOIN ai_knowledge_files kf ON kf.id = kc.file_id
                WHERE kf.is_active = TRUE
                  AND ({where_sql})
                ORDER BY kf.updated_at DESC, kc.chunk_index ASC
                LIMIT :limit
            """), params).mappings().all()
            rows = [dict(r) for r in rows]

        # fallback: últimos chunks de KB
        if not rows:
            rows2 = conn.execute(text("""
                SELECT
                    kc.content,
                    kf.file_name,
                    kf.notes,
                    kf.updated_at,
                    kc.chunk_index
                FROM ai_knowledge_chunks kc
                JOIN ai_knowledge_files kf ON kf.id = kc.file_id
                WHERE kf.is_active = TRUE
                ORDER BY kf.updated_at DESC, kc.chunk_index ASC
                LIMIT :limit
            """), {"limit": max_chunks}).mappings().all()
            rows = [dict(r) for r in rows2]

    if not rows:
        return ""

    picked: List[str] = []
    total = 0
    used = 0

    for r in rows:
        if used >= max_chunks:
            break

        content = _clean_text(r.get("content") or "")
        if not content:
            continue

        fname = _clean_text(r.get("file_name") or "")
        notes = _clean_text(r.get("notes") or "")

        header = f"[Fuente: {fname}]"
        if notes:
            header += f" ({notes})"

        block = f"{header}\n{content}".strip()

        if total + len(block) + 2 > max_chars:
            remaining = max_chars - total - 2
            if remaining <= 50:
                break
            block = block[:remaining].rstrip() + "…"

        picked.append(block)
        total += len(block) + 2
        used += 1

        if total >= max_chars:
            break

    return "\n\n".join(picked).strip()


# =========================================================
# Public helper
# =========================================================

def build_ai_meta(
    phone: str,
    user_text: str,
    *,
    history_limit: int = 14,
    history_max_chars: int = 2200,
    kb_max_chars: int = 3500,
) -> Dict[str, Any]:
    """
    Construye meta para engine.process_message:
    - meta["context"]: mezcla CRM + ai_state + historial + KB (PDF chunks)
    - meta["crm"]: objeto estructurado (para tools futuro)
    """
    phone = (phone or "").strip()
    user_text = (user_text or "").strip()

    crm = _get_crm(phone) if phone else {
        "first_name": "", "last_name": "", "city": "", "customer_type": "",
        "interests": "", "tags": "", "notes": "", "ai_state": "", "takeover": False,
    }

    recent = _get_recent_messages(phone, limit=history_limit) if phone else []

    # Historial (limpio, compacto)
    history_lines: List[str] = []
    for r in reversed(recent):  # viejo -> nuevo
        d = (r.get("direction") or "").strip().lower()
        txt = _clean_text(r.get("text") or "")
        if not txt:
            continue
        if d == "in":
            history_lines.append(f"CLIENTE: {txt}")
        else:
            history_lines.append(f"AGENTE: {txt}")

    history_block = _clip("\n".join(history_lines).strip(), history_max_chars)

    # CRM block (estructurado, corto)
    crm_lines: List[str] = []
    fn = _clean_text(crm.get("first_name") or "")
    ln = _clean_text(crm.get("last_name") or "")
    if fn or ln:
        crm_lines.append(f"Nombre: {fn} {ln}".strip())
    city = _clean_text(crm.get("city") or "")
    if city:
        crm_lines.append(f"Ciudad: {city}")
    ct = _clean_text(crm.get("customer_type") or "")
    if ct:
        crm_lines.append(f"Tipo cliente: {ct}")
    interests = _clean_text(crm.get("interests") or "")
    if interests:
        crm_lines.append(f"Intereses: {interests}")
    tags = _clean_text(crm.get("tags") or "")
    if tags:
        crm_lines.append(f"Tags: {tags}")
    notes = _clean_text(crm.get("notes") or "")
    if notes:
        crm_lines.append(f"Notas: {notes}")
    ai_state = _clean_text(crm.get("ai_state") or "")
    if ai_state:
        crm_lines.append(f"AI_STATE: {ai_state}")

    # KB context
    kb_ctx = _kb_retrieve(user_text=user_text, max_chunks=6, max_chars=kb_max_chars)

    blocks: List[str] = []
    if crm_lines:
        blocks.append("CRM:\n" + "\n".join(crm_lines))
    if history_block:
        blocks.append("Historial reciente:\n" + history_block)
    if kb_ctx:
        blocks.append("Knowledge Base (referencia):\n" + kb_ctx)

    context = "\n\n".join(blocks).strip()

    # Si no hay contexto, no ensuciamos el meta
    meta: Dict[str, Any] = {"crm": crm}
    if context:
        meta["context"] = context

    return meta
