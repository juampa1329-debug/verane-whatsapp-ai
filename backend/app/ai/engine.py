from __future__ import annotations

import os
import re
import asyncio
from typing import Any, Dict, Optional, Tuple, List

import requests
from sqlalchemy import text

from app.db import engine as db_engine


# =========================================================
# Settings
# =========================================================

def _get_settings() -> Dict[str, Any]:
    with db_engine.begin() as conn:
        r = conn.execute(text("""
            SELECT
                is_enabled,
                provider,
                model,
                system_prompt,
                max_tokens,
                temperature,
                COALESCE(fallback_provider, '') AS fallback_provider,
                COALESCE(fallback_model, '') AS fallback_model,
                COALESCE(timeout_sec, 25) AS timeout_sec,
                COALESCE(max_retries, 1) AS max_retries
            FROM ai_settings
            ORDER BY id ASC
            LIMIT 1
        """)).mappings().first()

    if not r:
        return {
            "is_enabled": True,
            "provider": "google",
            "model": "gemma-3-4b-it",
            "system_prompt": "",
            "max_tokens": 512,
            "temperature": 0.7,
            "fallback_provider": "groq",
            "fallback_model": "llama-3.1-8b-instant",
            "timeout_sec": 25,
            "max_retries": 1,
        }

    d = dict(r)
    d["system_prompt"] = (d.get("system_prompt") or "").strip()
    d["provider"] = (d.get("provider") or "").strip().lower()
    d["model"] = (d.get("model") or "").strip()
    d["fallback_provider"] = (d.get("fallback_provider") or "").strip().lower()
    d["fallback_model"] = (d.get("fallback_model") or "").strip()
    return d


# =========================================================
# Knowledge Base (RAG - light)
# =========================================================

def _ensure_knowledge_schema_safe() -> None:
    try:
        with db_engine.begin() as conn:
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
    except Exception:
        return


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


def _build_context_from_kb(user_text: str, max_chunks: int = 6, max_chars: int = 4000) -> str:
    _ensure_knowledge_schema_safe()

    kws = _keywords_from_text(user_text)
    rows: List[Dict[str, Any]] = []

    with db_engine.begin() as conn:
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
                    kc.file_id,
                    kc.chunk_index,
                    kf.mime_type,
                    kf.notes,
                    kf.updated_at
                FROM ai_knowledge_chunks kc
                JOIN ai_knowledge_files kf ON kf.id = kc.file_id
                WHERE kf.is_active = TRUE
                  AND ({where_sql})
                ORDER BY kf.updated_at DESC, kc.chunk_index ASC
                LIMIT :limit
            """), params).mappings().all()
            rows = [dict(r) for r in rows]

        if not rows:
            rows2 = conn.execute(text("""
                SELECT
                    kc.content,
                    kf.file_name,
                    kc.file_id,
                    kc.chunk_index,
                    kf.mime_type,
                    kf.notes,
                    kf.updated_at
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

        content = (r.get("content") or "").strip()
        if not content:
            continue

        fname = (r.get("file_name") or "").strip()
        notes = (r.get("notes") or "").strip()

        header = f"[Fuente: {fname}]"
        if notes:
            header += f" ({notes})"

        block = f"{header}\n{content}".strip()
        if not block:
            continue

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
# Public API
# =========================================================

async def process_message(phone: str, text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    s = _get_settings()
    if not bool(s.get("is_enabled", True)):
        return {
            "provider": str(s.get("provider", "")),
            "model": str(s.get("model", "")),
            "reply_text": "",
            "used_fallback": False,
            "error": "AI disabled",
        }

    meta = meta or {}
    user_text = (text or "").strip()

    # ✅ NO DUPLICAR RAG:
    # Si build_ai_meta ya envió meta["context"] (CRM + historial + KB), NO volvemos a meter KB.
    existing_ctx = (meta.get("context") or "").strip() if isinstance(meta, dict) else ""
    if not existing_ctx:
        kb_ctx = _build_context_from_kb(user_text=user_text, max_chunks=6, max_chars=4000)
        if kb_ctx:
            meta["context"] = kb_ctx

    messages = _build_messages(
        system_prompt=str(s.get("system_prompt") or ""),
        user_text=user_text,
        meta=meta,
    )

    provider = str(s.get("provider") or "").strip().lower()
    model = str(s.get("model") or "").strip()
    timeout_sec = int(s.get("timeout_sec") or 25)
    max_retries = int(s.get("max_retries") or 1)

    ok, reply, err = await _call_with_retries(
        provider=provider,
        model=model,
        messages=messages,
        max_tokens=int(s.get("max_tokens") or 512),
        temperature=float(s.get("temperature") or 0.7),
        timeout_sec=timeout_sec,
        max_retries=max_retries,
    )
    if ok and reply:
        return {
            "provider": provider,
            "model": model,
            "reply_text": reply,
            "used_fallback": False,
            "error": None,
        }

    fb_provider = (s.get("fallback_provider") or "").strip().lower()
    fb_model = (s.get("fallback_model") or "").strip()

    if fb_provider and fb_model and (fb_provider != provider or fb_model != model):
        ok2, reply2, err2 = await _call_with_retries(
            provider=fb_provider,
            model=fb_model,
            messages=messages,
            max_tokens=int(s.get("max_tokens") or 512),
            temperature=float(s.get("temperature") or 0.7),
            timeout_sec=timeout_sec,
            max_retries=max_retries,
        )
        if ok2 and reply2:
            return {
                "provider": fb_provider,
                "model": fb_model,
                "reply_text": reply2,
                "used_fallback": True,
                "error": None,
            }
        return {
            "provider": fb_provider or provider,
            "model": fb_model or model,
            "reply_text": "",
            "used_fallback": True,
            "error": (err2 or err or "AI call failed")[:900],
        }

    return {
        "provider": provider,
        "model": model,
        "reply_text": "",
        "used_fallback": False,
        "error": (err or "AI call failed")[:900],
    }


# =========================================================
# Prompt building
# =========================================================

def _build_messages(system_prompt: str, user_text: str, meta: Dict[str, Any]) -> list[Dict[str, str]]:
    msgs: list[Dict[str, str]] = []

    sys = (system_prompt or "").strip()
    if sys:
        msgs.append({"role": "system", "content": sys})

    ctx = (meta.get("context") or "").strip() if isinstance(meta, dict) else ""
    if ctx:
        msgs.append({
            "role": "user",
            "content": (
                "Contexto adicional (usa esto como referencia; si no aplica, ignóralo):\n"
                f"{ctx}"
            )
        })

    msgs.append({"role": "user", "content": user_text or "Hola"})
    return msgs


# =========================================================
# Retry + timeout wrapper
# =========================================================

async def _call_with_retries(
    provider: str,
    model: str,
    messages: list[Dict[str, str]],
    max_tokens: int,
    temperature: float,
    timeout_sec: int,
    max_retries: int,
) -> Tuple[bool, str, str]:
    last_err = ""
    attempts = max(1, max_retries + 1)

    for i in range(attempts):
        try:
            reply = await asyncio.wait_for(
                _call_provider(provider, model, messages, max_tokens, temperature, timeout_sec),
                timeout=timeout_sec + 5,
            )
            reply = (reply or "").strip()
            if reply:
                return True, reply, ""
            last_err = "Empty reply"
        except Exception as e:
            last_err = str(e)

        if i < attempts - 1:
            await asyncio.sleep(0.4 + (0.2 * i))

    return False, "", last_err[:900]


async def _call_provider(
    provider: str,
    model: str,
    messages: list[Dict[str, str]],
    max_tokens: int,
    temperature: float,
    timeout_sec: int,
) -> str:
    provider = (provider or "").strip().lower()

    if provider == "google":
        return await _call_google_gemma(model, messages, max_tokens, temperature, timeout_sec)

    if provider == "groq":
        return await _call_groq(model, messages, max_tokens, temperature, timeout_sec)

    if provider == "openrouter":
        return await _call_openrouter(model, messages, max_tokens, temperature, timeout_sec)

    if provider == "mistral":
        return await _call_mistral(model, messages, max_tokens, temperature, timeout_sec)

    raise RuntimeError(f"Unsupported provider: {provider}")


# =========================================================
# Provider implementations (HTTP)
# =========================================================

def _last_user_text(messages: list[Dict[str, str]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return str(m.get("content", "") or "")
    return ""


def _system_text(messages: list[Dict[str, str]]) -> str:
    for m in messages:
        if m.get("role") == "system":
            return str(m.get("content", "") or "")
    return ""


async def _call_google_gemma(model: str, messages: list[Dict[str, str]], max_tokens: int, temperature: float, timeout_sec: int) -> str:
    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_AI_API_KEY is not set")

    model = (model or "gemma-3-4b-it").strip()
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    sys = _system_text(messages)
    user = _last_user_text(messages)

    payload: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": user or "Hola"}]}],
        "generationConfig": {
            "temperature": float(temperature),
            "maxOutputTokens": int(max_tokens),
        },
    }

    if sys:
        payload["systemInstruction"] = {"parts": [{"text": sys}]}

    def _do() -> str:
        r = requests.post(url, json=payload, timeout=timeout_sec)
        if r.status_code >= 400:
            raise RuntimeError(f"google error {r.status_code}: {r.text[:600]}")
        data = r.json() or {}
        cands = data.get("candidates") or []
        if not cands:
            return ""
        content = (cands[0] or {}).get("content") or {}
        parts = content.get("parts") or []
        if parts and isinstance(parts, list):
            t = (parts[0] or {}).get("text")
            return str(t or "")
        return ""

    return await asyncio.to_thread(_do)


async def _call_groq(model: str, messages: list[Dict[str, str]], max_tokens: int, temperature: float, timeout_sec: int) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set")

    url = "https://api.groq.com/openai/v1/chat/completions"
    model = (model or "llama-3.1-8b-instant").strip()

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": int(max_tokens),
        "temperature": float(temperature),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    def _do() -> str:
        r = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
        if r.status_code >= 400:
            raise RuntimeError(f"groq error {r.status_code}: {r.text[:600]}")
        data = r.json() or {}
        ch = (data.get("choices") or [{}])[0]
        msg = (ch.get("message") or {})
        return str(msg.get("content") or "")

    return await asyncio.to_thread(_do)


async def _call_openrouter(model: str, messages: list[Dict[str, str]], max_tokens: int, temperature: float, timeout_sec: int) -> str:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not set")

    url = "https://openrouter.ai/api/v1/chat/completions"
    model = (model or "google/gemma-2-9b-it").strip()

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": int(max_tokens),
        "temperature": float(temperature),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": os.getenv("OPENROUTER_SITE", "http://localhost"),
        "X-Title": os.getenv("OPENROUTER_APP_NAME", "verane-whatsapp-ai"),
    }

    def _do() -> str:
        r = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
        if r.status_code >= 400:
            raise RuntimeError(f"openrouter error {r.status_code}: {r.text[:600]}")
        data = r.json() or {}
        ch = (data.get("choices") or [{}])[0]
        msg = (ch.get("message") or {})
        return str(msg.get("content") or "")

    return await asyncio.to_thread(_do)


async def _call_mistral(model: str, messages: list[Dict[str, str]], max_tokens: int, temperature: float, timeout_sec: int) -> str:
    api_key = os.getenv("MISTRAL_API_KEY")
    if not api_key:
        raise RuntimeError("MISTRAL_API_KEY is not set")

    url = "https://api.mistral.ai/v1/chat/completions"
    model = (model or "mistral-small-latest").strip()

    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": int(max_tokens),
        "temperature": float(temperature),
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    def _do() -> str:
        r = requests.post(url, headers=headers, json=payload, timeout=timeout_sec)
        if r.status_code >= 400:
            raise RuntimeError(f"mistral error {r.status_code}: {r.text[:600]}")
        data = r.json() or {}
        ch = (data.get("choices") or [{}])[0]
        msg = (ch.get("message") or {})
        return str(msg.get("content") or "")

    return await asyncio.to_thread(_do)
