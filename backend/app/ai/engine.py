from __future__ import annotations

import os
import re
import asyncio
from typing import Any, Dict, Optional, Tuple, List

import httpx
from sqlalchemy import text

from app.db import engine as db_engine
from app.integrations.woocommerce import wc_enabled, looks_like_product_question


# =========================================================
# Model name mapping (UI label -> API model id)
# =========================================================

MODEL_MAP_GOOGLE: Dict[str, str] = {
    "Gemini 2.5 Flash": "gemini-2.5-flash",
    "Gemini 2.5 Pro": "gemini-2.5-pro",
    "Gemini 2.5 Flash Preview TTS": "gemini-2.5-flash-preview-tts",
    "Gemini 2.5 Pro Preview TTS": "gemini-2.5-pro-preview-tts",

    # Compatibilidad si ya están guardados en DB/UI
    "Gemini 2.0 Flash": "gemini-2.0-flash",
    "Gemini 2.0 Flash 001": "gemini-2.0-flash-001",
    "Gemini 2.0 Flash-Lite": "gemini-2.0-flash-lite",
    "Gemini 2.0 Flash-Lite 001": "gemini-2.0-flash-lite-001",
    "Gemini 2.0 Flash (Image Generation) Experimental": "gemini-2.0-flash-exp",

    "Gemma 3 1B": "gemma-3-1b-it",
    "Gemma 3 4B": "gemma-3-4b-it",
    "Gemma 3 12B": "gemma-3-12b-it",
    "Gemma 3 27B": "gemma-3-27b-it",
    "Gemma 3n E4B": "gemma-3n-e4b",
    "Gemma 3n E2B": "gemma-3n-e2b",
}


def _default_google_chat_model() -> str:
    return (os.getenv("GOOGLE_DEFAULT_MODEL", "").strip() or "gemini-2.5-flash").strip().lower()


def _fallback_google_chat_model() -> str:
    return (os.getenv("GOOGLE_FALLBACK_MODEL", "").strip() or "gemini-2.5-flash-lite").strip().lower()


def _resolve_google_model(model: str) -> str:
    m = (model or "").strip()
    if not m:
        return _default_google_chat_model()

    low = m.lower().strip()
    if low.startswith(("gemini-", "gemma-")):
        return low

    return MODEL_MAP_GOOGLE.get(m, m)


# =========================================================
# Voice prompt builder
# =========================================================

def _clamp_int(v: Any, lo: int, hi: int, default: int) -> int:
    try:
        n = int(v)
    except Exception:
        return default
    return max(lo, min(hi, n))


def _truthy(v: Any) -> bool:
    if isinstance(v, bool):
        return v
    s = str(v or "").strip().lower()
    return s in ("1", "true", "yes", "y", "on", "si", "sí")


def _build_voice_style_block(s: Dict[str, Any]) -> str:
    enabled = _truthy(s.get("voice_enabled", False))
    if not enabled:
        return ""

    gender = (s.get("voice_gender") or "neutral").strip().lower()
    lang = (s.get("voice_language") or "es-CO").strip()
    accent = (s.get("voice_accent") or "colombiano").strip()
    speaking_rate = float(s.get("voice_speaking_rate") or 1.0)
    speaking_rate = max(0.6, min(1.4, speaking_rate))

    max_voice_notes = _clamp_int(s.get("voice_max_notes_per_reply", 1), 0, 5, 1)
    prefer_voice = _truthy(s.get("voice_prefer_voice", False))

    style_prompt = (s.get("voice_style_prompt") or "").strip()

    lines = [
        "VOICE_STYLE (guía para que el texto suene como nota de voz):",
        f"- Idioma: {lang}",
        f"- Acento/registro: {accent}",
        f"- Género de la voz (referencial): {gender}",
        f"- Ritmo objetivo (referencial): {speaking_rate}",
        "- Escribe frases naturales, como habladas por WhatsApp.",
        "- Evita textos demasiado largos; usa pausas naturales y párrafos cortos.",
        "- No uses lenguaje robótico. No repitas el mensaje del usuario.",
        f"- Máximo sugerido de segmentos de voz por respuesta: {max_voice_notes}",
        f"- Preferir voz sobre texto: {'sí' if prefer_voice else 'no'}",
    ]

    if style_prompt:
        lines.append("- Instrucciones personalizadas del admin (Voice Prompt):")
        lines.append(style_prompt)

    return "\n".join(lines).strip()


def _merge_system_prompt(system_prompt: str, voice_block: str) -> str:
    sys = (system_prompt or "").strip()
    vb = (voice_block or "").strip()
    if not vb:
        return sys
    if not sys:
        return vb
    return (sys + "\n\n" + vb).strip()


def _norm_tts_provider(p: Any) -> str:
    raw = str(p or "").strip().lower()
    raw = raw.replace("_", "").replace("-", "").replace(" ", "")
    if raw in ("", "default", "auto"):
        return ""
    if raw in ("elevenlabs", "11labs", "eleven", "xi"):
        return "elevenlabs"
    if raw in ("google", "gcp", "googletts", "cloudtts", "texttospeech"):
        return "google"
    if raw in ("piper", "pipertts"):
        return "piper"
    return raw


# =========================================================
# Settings
# =========================================================

def _get_settings() -> Dict[str, Any]:
    try:
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
                    COALESCE(max_retries, 1) AS max_retries,

                    COALESCE(voice_enabled, FALSE) AS voice_enabled,
                    COALESCE(voice_gender, 'neutral') AS voice_gender,
                    COALESCE(voice_language, 'es-CO') AS voice_language,
                    COALESCE(voice_accent, 'colombiano') AS voice_accent,
                    COALESCE(voice_style_prompt, '') AS voice_style_prompt,
                    COALESCE(voice_max_notes_per_reply, 1) AS voice_max_notes_per_reply,
                    COALESCE(voice_prefer_voice, FALSE) AS voice_prefer_voice,
                    COALESCE(voice_speaking_rate, 1.0) AS voice_speaking_rate,

                    COALESCE(voice_tts_provider, 'google') AS voice_tts_provider,
                    COALESCE(voice_tts_voice_id, '') AS voice_tts_voice_id,
                    COALESCE(voice_tts_model_id, '') AS voice_tts_model_id
                FROM ai_settings
                ORDER BY id ASC
                LIMIT 1
            """)).mappings().first()
    except Exception:
        r = None

    if not r:
        return {
            "is_enabled": True,
            "provider": "google",
            "model": _default_google_chat_model(),
            "system_prompt": "",
            "max_tokens": 512,
            "temperature": 0.7,
            "fallback_provider": "groq",
            "fallback_model": "llama-3.1-8b-instant",
            "timeout_sec": 25,
            "max_retries": 1,

            "voice_enabled": False,
            "voice_gender": "neutral",
            "voice_language": "es-CO",
            "voice_accent": "colombiano",
            "voice_style_prompt": "",
            "voice_max_notes_per_reply": 1,
            "voice_prefer_voice": False,
            "voice_speaking_rate": 1.0,

            "voice_tts_provider": "google",
            "voice_tts_voice_id": "",
            "voice_tts_model_id": "",
        }

    d = dict(r)

    d["system_prompt"] = (d.get("system_prompt") or "").strip()
    d["provider"] = (d.get("provider") or "").strip().lower()
    d["model"] = (d.get("model") or "").strip() or _default_google_chat_model()
    d["fallback_provider"] = (d.get("fallback_provider") or "").strip().lower()
    d["fallback_model"] = (d.get("fallback_model") or "").strip()

    d["timeout_sec"] = int(d.get("timeout_sec") or 25)
    d["max_retries"] = int(d.get("max_retries") or 1)
    d["max_tokens"] = int(d.get("max_tokens") or 512)
    d["temperature"] = float(d.get("temperature") or 0.7)

    d["voice_enabled"] = _truthy(d.get("voice_enabled", False))
    d["voice_gender"] = (d.get("voice_gender") or "neutral").strip().lower()
    d["voice_language"] = (d.get("voice_language") or "es-CO").strip()
    d["voice_accent"] = (d.get("voice_accent") or "colombiano").strip()
    d["voice_style_prompt"] = (d.get("voice_style_prompt") or "").strip()
    d["voice_max_notes_per_reply"] = _clamp_int(d.get("voice_max_notes_per_reply", 1), 0, 5, 1)
    d["voice_prefer_voice"] = _truthy(d.get("voice_prefer_voice", False))
    try:
        d["voice_speaking_rate"] = float(d.get("voice_speaking_rate") or 1.0)
    except Exception:
        d["voice_speaking_rate"] = 1.0
    d["voice_speaking_rate"] = max(0.6, min(1.4, float(d["voice_speaking_rate"])))


    d["voice_tts_provider"] = _norm_tts_provider(d.get("voice_tts_provider") or "google") or "google"
    d["voice_tts_voice_id"] = (d.get("voice_tts_voice_id") or "").strip()
    d["voice_tts_model_id"] = (d.get("voice_tts_model_id") or "").strip()

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
# Extra system block: ventas/catálogo (solo guía)
# =========================================================

def _sales_assistant_block(user_text: str) -> str:
    """
    NO ejecuta Woo.
    Solo le da reglas al LLM para responder como asesor de perfumes.
    """
    t = (user_text or "").strip()
    if not t:
        return ""

    if not wc_enabled():
        return ""

    if not looks_like_product_question(t):
        return ""

    return (
        "MODO ASESOR PERFUMES (reglas):\n"
        "- Actúa como asesor de perfumes de Perfumes Verané.\n"
        "- Si el usuario pregunta por precio/stock/si hay X perfume: pide 1 dato faltante si es necesario (tamaño, para hombre/mujer/unisex, rango de precio).\n"
        "- Si el usuario describe gustos (fresco/dulce/amaderado, ocasión, edad): recomienda 2 a 4 opciones concretas.\n"
        "- Mantén respuestas cortas, con bullets y 1 pregunta de cierre.\n"
        "- Si no tienes certeza de disponibilidad exacta, dilo y ofrece buscar.\n"
    ).strip()


# =========================================================
# Public API
# =========================================================

async def process_message(phone: str, text: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    s = _get_settings()
    if not bool(s.get("is_enabled", True)):
        return {
            "ok": False,
            "provider": str(s.get("provider", "")),
            "model": str(s.get("model", "")),
            "reply_text": "",
            "reply_chunks": [],
            "used_fallback": False,
            "error": "AI disabled",
            "voice": {"enabled": bool(s.get("voice_enabled", False))},
        }

    meta = meta or {}
    user_text = (text or "").strip()

    existing_ctx = (meta.get("context") or "").strip() if isinstance(meta, dict) else ""
    if not existing_ctx and user_text:
        kb_ctx = _build_context_from_kb(user_text=user_text, max_chunks=6, max_chars=4000)
        if kb_ctx:
            meta["context"] = kb_ctx

    voice_block = _build_voice_style_block(s)

    # ✅ extra block de ventas/catálogo (solo guía)
    sales_block = _sales_assistant_block(user_text)

    merged_system = _merge_system_prompt(str(s.get("system_prompt") or ""), voice_block)
    if sales_block:
        merged_system = _merge_system_prompt(merged_system, sales_block)

    messages = _build_messages(
        system_prompt=merged_system,
        user_text=user_text,
        meta=meta,
    )

    provider = str(s.get("provider") or "").strip().lower()
    model = str(s.get("model") or "").strip() or _default_google_chat_model()
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

    def _voice_payload() -> Dict[str, Any]:
        return {
            "enabled": bool(s.get("voice_enabled", False)),
            "gender": s.get("voice_gender", "neutral"),
            "language": s.get("voice_language", "es-CO"),
            "accent": s.get("voice_accent", "colombiano"),
            "style_prompt": s.get("voice_style_prompt", ""),
            "max_notes_per_reply": int(s.get("voice_max_notes_per_reply") or 1),
            "prefer_voice": bool(s.get("voice_prefer_voice", False)),
            "speaking_rate": float(s.get("voice_speaking_rate") or 1.0),

            "tts_provider": s.get("voice_tts_provider", "google"),
            "tts_voice_id": s.get("voice_tts_voice_id", ""),
            "tts_model_id": s.get("voice_tts_model_id", ""),
        }

    if ok and reply:
        return {
            "ok": True,
            "provider": provider,
            "model": model,
            "reply_text": reply,
            "reply_chunks": [],
            "used_fallback": False,
            "error": None,
            "voice": _voice_payload(),
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
                "ok": True,
                "provider": fb_provider,
                "model": fb_model,
                "reply_text": reply2,
                "reply_chunks": [],
                "used_fallback": True,
                "error": None,
                "voice": _voice_payload(),
            }

        return {
            "ok": False,
            "provider": fb_provider or provider,
            "model": fb_model or model,
            "reply_text": "",
            "reply_chunks": [],
            "used_fallback": True,
            "error": (err2 or err or "AI call failed")[:900],
            "voice": {"enabled": bool(s.get("voice_enabled", False))},
        }

    return {
        "ok": False,
        "provider": provider,
        "model": model,
        "reply_text": "",
        "reply_chunks": [],
        "used_fallback": False,
        "error": (err or "AI call failed")[:900],
        "voice": {"enabled": bool(s.get("voice_enabled", False))},
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
        resolved = _resolve_google_model(model)
        return await _call_google_gemma(resolved, messages, max_tokens, temperature, timeout_sec)

    if provider == "groq":
        return await _call_groq(model, messages, max_tokens, temperature, timeout_sec)

    if provider == "openrouter":
        return await _call_openrouter(model, messages, max_tokens, temperature, timeout_sec)

    if provider == "mistral":
        return await _call_mistral(model, messages, max_tokens, temperature, timeout_sec)

    raise RuntimeError(f"Unsupported provider: {provider}")


# =========================================================
# Provider implementations (HTTP) - async httpx
# =========================================================

def _system_text(messages: list[Dict[str, str]]) -> str:
    for m in messages:
        if m.get("role") == "system":
            return str(m.get("content", "") or "")
    return ""


def _all_user_text(messages: list[Dict[str, str]]) -> str:
    parts: List[str] = []
    for m in messages:
        if m.get("role") == "user":
            c = str(m.get("content", "") or "").strip()
            if c:
                parts.append(c)
    return "\n\n".join(parts).strip()


def _extract_retry_after_seconds(headers: Dict[str, Any], body_text: str) -> Optional[float]:
    try:
        ra = (headers.get("Retry-After") or headers.get("retry-after") or "").strip()
        if ra:
            try:
                return float(ra)
            except Exception:
                pass
    except Exception:
        pass

    try:
        m = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", body_text or "", re.IGNORECASE)
        if m:
            return float(m.group(1))
    except Exception:
        pass

    return None


def _looks_like_model_not_found(body_text: str) -> bool:
    t = (body_text or "").lower()
    if "not_found" in t or "\"status\": \"not_found\"" in t:
        return True
    if "no longer available" in t:
        return True
    if "not available" in t and "model" in t:
        return True
    return False


def _timeout(timeout_sec: int) -> httpx.Timeout:
    sec = max(3, int(timeout_sec or 25))
    return httpx.Timeout(connect=min(10, sec), read=sec, write=sec, pool=min(10, sec))


async def _call_google_gemma(model: str, messages: list[Dict[str, str]], max_tokens: int, temperature: float, timeout_sec: int) -> str:
    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GOOGLE_AI_API_KEY is not set")

    model = (model or _default_google_chat_model()).strip().lower()
    fallback_model = _fallback_google_chat_model()

    url_tpl = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    sys = _system_text(messages)
    user_all = _all_user_text(messages)

    payload: Dict[str, Any] = {
        "contents": [{"role": "user", "parts": [{"text": user_all or "Hola"}]}],
        "generationConfig": {
            "temperature": float(temperature),
            "maxOutputTokens": int(max_tokens),
        },
    }
    if sys:
        payload["systemInstruction"] = {"parts": [{"text": sys}]}

    # Retries específicos para Google (además del engine)
    try:
        override = os.getenv("GOOGLE_MAX_RETRIES_OVERRIDE", "").strip()
        google_retries = int(override) if override else 2
    except Exception:
        google_retries = 2
    google_retries = max(0, min(google_retries, 8))

    async def _do_call(model_name: str) -> str:
        url = url_tpl.format(model=model_name, api_key=api_key)
        attempts = google_retries + 1
        last_err = ""

        async with httpx.AsyncClient(timeout=_timeout(timeout_sec)) as client:
            for i in range(attempts):
                r = await client.post(url, json=payload)
                if r.status_code < 400:
                    data = r.json() if r.content else {}
                    cands = data.get("candidates") or []
                    if not cands:
                        return ""
                    content = (cands[0] or {}).get("content") or {}
                    parts = content.get("parts") or []
                    if parts and isinstance(parts, list):
                        out = []
                        for p in parts:
                            if isinstance(p, dict) and p.get("text"):
                                out.append(str(p.get("text") or ""))
                        return "".join(out).strip()
                    return ""

                body = (r.text or "")[:900]
                last_err = f"google error {r.status_code}: {body}"

                # 404 => modelo no existe/no disponible
                if r.status_code == 404:
                    raise RuntimeError(last_err)

                # 429 / 5xx => backoff
                if r.status_code == 429 or (500 <= r.status_code <= 599):
                    ra = _extract_retry_after_seconds(dict(r.headers), r.text or "")
                    if ra is None:
                        ra = min(0.8 * (2 ** i), 12.0)
                    await asyncio.sleep(float(ra))
                    continue

                # otros 4xx => parar
                raise RuntimeError(last_err)

        raise RuntimeError(last_err)

    # 1) modelo principal
    try:
        return await _do_call(model)
    except Exception as e:
        err = str(e)[:900]

        # 2) fallback si es 404 / modelo no disponible
        if "google error 404" in err.lower() and fallback_model and fallback_model != model:
            if _looks_like_model_not_found(err):
                return await _do_call(fallback_model)

        raise RuntimeError(err)


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
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=_timeout(timeout_sec)) as client:
        r = await client.post(url, headers=headers, json=payload)

    if r.status_code >= 400:
        raise RuntimeError(f"groq error {r.status_code}: {(r.text or '')[:600]}")

    data = r.json() if r.content else {}
    ch = (data.get("choices") or [{}])[0]
    msg = (ch.get("message") or {})
    return str(msg.get("content") or "")


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

    async with httpx.AsyncClient(timeout=_timeout(timeout_sec)) as client:
        r = await client.post(url, headers=headers, json=payload)

    if r.status_code >= 400:
        raise RuntimeError(f"openrouter error {r.status_code}: {(r.text or '')[:600]}")

    data = r.json() if r.content else {}
    ch = (data.get("choices") or [{}])[0]
    msg = (ch.get("message") or {})
    return str(msg.get("content") or "")


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
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    async with httpx.AsyncClient(timeout=_timeout(timeout_sec)) as client:
        r = await client.post(url, headers=headers, json=payload)

    if r.status_code >= 400:
        raise RuntimeError(f"mistral error {r.status_code}: {(r.text or '')[:600]}")

    data = r.json() if r.content else {}
    ch = (data.get("choices") or [{}])[0]
    msg = (ch.get("message") or {})
    return str(msg.get("content") or "")