from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Dict, Any, Literal, List

import requests
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.ai.knowledge_router import router as knowledge_router
from app.ai.context_builder import build_ai_meta
from app.db import engine

router = APIRouter()

# KB endpoints quedan bajo /api/ai/knowledge/*
router.include_router(knowledge_router, prefix="/knowledge")

# Providers soportados
AIProvider = Literal["google", "groq", "mistral", "openrouter"]

# =========================================================
# Static catalog (safe defaults) - optional fallback
# =========================================================

MODEL_CATALOG: Dict[str, List[str]] = {
    "google": [
        "gemma-3-4b-it",
    ],
    "groq": [
        "llama-3.1-8b-instant",
        "llama-3.1-70b-versatile",
    ],
    "mistral": [
        "mistral-small-latest",
        "mistral-medium-latest",
    ],
    "openrouter": [
        "google/gemma-2-9b-it",
    ],
}


def _is_valid_provider(p: str) -> bool:
    return (p or "").strip().lower() in ("google", "groq", "mistral", "openrouter")


# =========================================================
# Live models helpers
# =========================================================

def _strip_google_model_prefix(name: str) -> str:
    # "models/gemini-2.5-flash" -> "gemini-2.5-flash"
    n = (name or "").strip()
    if n.startswith("models/"):
        return n.split("/", 1)[1]
    return n


def _fetch_google_models() -> List[Dict[str, Any]]:
    api_key = os.getenv("GOOGLE_AI_API_KEY") or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="Missing GOOGLE_AI_API_KEY (or GEMINI_API_KEY)")

    url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    r = requests.get(url, timeout=20)
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"google models error {r.status_code}: {r.text[:300]}")

    data = r.json() or {}
    models = data.get("models") or []
    out: List[Dict[str, Any]] = []
    for m in models:
        raw = (m.get("name") or "").strip()  # models/xxx
        mid = _strip_google_model_prefix(raw)  # xxx
        if not mid:
            continue
        out.append({
            "id": mid,
            "label": m.get("displayName") or mid,
            "raw": raw,
        })
    return out


def _fetch_openai_style_models(url: str, api_key: str, label_key: str = "id") -> List[Dict[str, Any]]:
    if not api_key:
        raise HTTPException(status_code=400, detail="Missing API key for provider")

    r = requests.get(url, headers={"Authorization": f"Bearer {api_key}"}, timeout=20)
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"models error {r.status_code}: {r.text[:300]}")

    data = r.json() or {}
    items = data.get("data") or []
    out: List[Dict[str, Any]] = []
    for it in items:
        mid = (it.get("id") or "").strip()
        if not mid:
            continue
        out.append({"id": mid, "label": it.get(label_key) or mid, "raw": mid})
    return out


def _fetch_groq_models() -> List[Dict[str, Any]]:
    api_key = os.getenv("GROQ_API_KEY")
    return _fetch_openai_style_models("https://api.groq.com/openai/v1/models", api_key)


def _fetch_mistral_models() -> List[Dict[str, Any]]:
    api_key = os.getenv("MISTRAL_API_KEY")
    return _fetch_openai_style_models("https://api.mistral.ai/v1/models", api_key)


def _fetch_openrouter_models() -> List[Dict[str, Any]]:
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="Missing OPENROUTER_API_KEY")

    r = requests.get(
        "https://openrouter.ai/api/v1/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=20,
    )
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"openrouter models error {r.status_code}: {r.text[:300]}")

    data = r.json() or {}
    items = data.get("data") or []
    out: List[Dict[str, Any]] = []
    for it in items:
        mid = (it.get("id") or "").strip()
        if not mid:
            continue
        name = (it.get("name") or "").strip()
        out.append({"id": mid, "label": name or mid, "raw": mid})
    return out


def _provider_supports_live(p: str) -> bool:
    return p in ("google", "groq", "mistral", "openrouter")


def _validate_model_flex(provider: str, model: str) -> None:
    """
    FLEX validation:
    - google: acepta gemini-* y gemma-* (y preview)
    - groq/mistral/openrouter: acepta cualquier string no vacío
    """
    p = (provider or "").strip().lower()
    m = (model or "").strip()

    if not p:
        raise HTTPException(status_code=400, detail="provider is required")
    if not m:
        raise HTTPException(status_code=400, detail="model is required")

    if p == "google":
        m2 = _strip_google_model_prefix(m)
        if not (m2.startswith("gemini-") or m2.startswith("gemma-")):
            raise HTTPException(status_code=400, detail=f"Invalid google model format: {m}")
        return

    if p in ("openrouter", "groq", "mistral"):
        return

    raise HTTPException(status_code=400, detail=f"Invalid provider: {provider}")


# =========================================================
# DB helpers
# =========================================================

def _get_settings_row(conn) -> Dict[str, Any]:
    """
    OJO: Estos campos (reply_chunk_chars, reply_delay_ms, typing_delay_ms)
    deben existir en la tabla ai_settings.
    Si aún no existen, agrégalos en main.ensure_schema():
      ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS reply_chunk_chars INTEGER;
      ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS reply_delay_ms INTEGER;
      ALTER TABLE ai_settings ADD COLUMN IF NOT EXISTS typing_delay_ms INTEGER;
    """
    r = conn.execute(text("""
        SELECT
            id,
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

            COALESCE(reply_chunk_chars, 480) AS reply_chunk_chars,
            COALESCE(reply_delay_ms, 900) AS reply_delay_ms,
            COALESCE(typing_delay_ms, 450) AS typing_delay_ms,

            created_at,
            updated_at
        FROM ai_settings
        ORDER BY id ASC
        LIMIT 1
    """)).mappings().first()

    if not r:
        raise HTTPException(status_code=500, detail="ai_settings row not found. ensure_schema() did not run?")
    return dict(r)


# =========================================================
# Schemas
# =========================================================

class AISettingsOut(BaseModel):
    id: int
    is_enabled: bool
    provider: str
    model: str
    system_prompt: str
    max_tokens: int
    temperature: float

    fallback_provider: str = ""
    fallback_model: str = ""
    timeout_sec: int = 25
    max_retries: int = 1

    # ✅ humanización
    reply_chunk_chars: int = 480         # tamaño por “párrafo”/chunk
    reply_delay_ms: int = 900            # delay entre chunks
    typing_delay_ms: int = 450           # delay inicial antes de enviar el primer chunk

    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class AISettingsUpdate(BaseModel):
    is_enabled: Optional[bool] = None
    provider: Optional[AIProvider] = None
    model: Optional[str] = None
    system_prompt: Optional[str] = None
    max_tokens: Optional[int] = Field(default=None, ge=32, le=8192)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)

    fallback_provider: Optional[AIProvider] = None
    fallback_model: Optional[str] = None
    timeout_sec: Optional[int] = Field(default=None, ge=5, le=120)
    max_retries: Optional[int] = Field(default=None, ge=0, le=3)

    # ✅ humanización (ajustable en frontend)
    reply_chunk_chars: Optional[int] = Field(default=None, ge=120, le=2000)
    reply_delay_ms: Optional[int] = Field(default=None, ge=0, le=6000)
    typing_delay_ms: Optional[int] = Field(default=None, ge=0, le=6000)


class AIProcessRequest(BaseModel):
    phone: str
    text: str = ""
    meta: Optional[Dict[str, Any]] = None


class AIProcessResponse(BaseModel):
    ok: bool
    provider: str
    model: str
    reply_text: str
    used_fallback: bool = False
    error: Optional[str] = None


# =========================================================
# Engine import
# =========================================================

from app.ai.engine import process_message


# =========================================================
# Routes
# =========================================================

@router.get("/settings", response_model=AISettingsOut)
def get_ai_settings():
    with engine.begin() as conn:
        row = _get_settings_row(conn)
    return AISettingsOut(**row)


@router.put("/settings", response_model=AISettingsOut)
def update_ai_settings(payload: AISettingsUpdate):
    with engine.begin() as conn:
        current = _get_settings_row(conn)
        sid = current["id"]

        provider = current["provider"] if payload.provider is None else payload.provider
        model = current["model"] if payload.model is None else (payload.model or "")
        system_prompt = current["system_prompt"] if payload.system_prompt is None else (payload.system_prompt or "")

        fallback_provider = current.get("fallback_provider", "") if payload.fallback_provider is None else (payload.fallback_provider or "")
        fallback_model = current.get("fallback_model", "") if payload.fallback_model is None else (payload.fallback_model or "")

        new_vals = {
            "is_enabled": current["is_enabled"] if payload.is_enabled is None else payload.is_enabled,
            "provider": (str(provider or "").strip().lower()),
            "model": (str(model or "").strip()),
            "system_prompt": str(system_prompt or ""),
            "max_tokens": current["max_tokens"] if payload.max_tokens is None else payload.max_tokens,
            "temperature": current["temperature"] if payload.temperature is None else payload.temperature,
            "fallback_provider": (str(fallback_provider or "").strip().lower()),
            "fallback_model": (str(fallback_model or "").strip()),
            "timeout_sec": current.get("timeout_sec", 25) if payload.timeout_sec is None else payload.timeout_sec,
            "max_retries": current.get("max_retries", 1) if payload.max_retries is None else payload.max_retries,

            # ✅ humanización
            "reply_chunk_chars": current.get("reply_chunk_chars", 480) if payload.reply_chunk_chars is None else payload.reply_chunk_chars,
            "reply_delay_ms": current.get("reply_delay_ms", 900) if payload.reply_delay_ms is None else payload.reply_delay_ms,
            "typing_delay_ms": current.get("typing_delay_ms", 450) if payload.typing_delay_ms is None else payload.typing_delay_ms,
        }

        # required
        if not new_vals["provider"]:
            raise HTTPException(status_code=400, detail="provider is required")
        if not new_vals["model"]:
            raise HTTPException(status_code=400, detail="model is required")

        if not _is_valid_provider(new_vals["provider"]):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider: {new_vals['provider']}. Allowed: ['google','groq','mistral','openrouter']",
            )

        # FLEX validation
        _validate_model_flex(new_vals["provider"], new_vals["model"])

        # normalize google "models/xxx" -> "xxx"
        if new_vals["provider"] == "google":
            new_vals["model"] = _strip_google_model_prefix(new_vals["model"])

        # fallback optional, validate too
        fb_p = (new_vals.get("fallback_provider") or "").strip().lower()
        fb_m = (new_vals.get("fallback_model") or "").strip()

        if fb_p:
            if not _is_valid_provider(fb_p):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid fallback_provider: {fb_p}. Allowed: ['google','groq','mistral','openrouter']",
                )
            if fb_m:
                _validate_model_flex(fb_p, fb_m)
                if fb_p == "google":
                    new_vals["fallback_model"] = _strip_google_model_prefix(fb_m)

        conn.execute(text("""
            UPDATE ai_settings
            SET
                is_enabled = :is_enabled,
                provider = :provider,
                model = :model,
                system_prompt = :system_prompt,
                max_tokens = :max_tokens,
                temperature = :temperature,
                fallback_provider = :fallback_provider,
                fallback_model = :fallback_model,
                timeout_sec = :timeout_sec,
                max_retries = :max_retries,

                reply_chunk_chars = :reply_chunk_chars,
                reply_delay_ms = :reply_delay_ms,
                typing_delay_ms = :typing_delay_ms,

                updated_at = NOW()
            WHERE id = :id
        """), {**new_vals, "id": sid})

        row = _get_settings_row(conn)

    return AISettingsOut(**row)


@router.post("/process-message", response_model=AIProcessResponse)
async def process_ai_message(payload: AIProcessRequest):
    """
    Endpoint de prueba/manual QA.
    NOTA: el disparo automático real ocurre desde /api/messages/ingest (o webhook real).
    """
    with engine.begin() as conn:
        s = _get_settings_row(conn)

    if not bool(s.get("is_enabled", True)):
        return AIProcessResponse(
            ok=True,
            provider=str(s.get("provider", "")),
            model=str(s.get("model", "")),
            reply_text="",
            used_fallback=False,
            error="AI disabled",
        )

    try:
        meta = payload.meta if payload.meta is not None else build_ai_meta(payload.phone, payload.text or "")

        result = await process_message(
            phone=payload.phone,
            text=payload.text or "",
            meta=meta or {},
        )

        return AIProcessResponse(
            ok=True,
            provider=str(result.get("provider", s.get("provider", ""))),
            model=str(result.get("model", s.get("model", ""))),
            reply_text=str(result.get("reply_text", "")),
            used_fallback=bool(result.get("used_fallback", False)),
            error=result.get("error"),
        )

    except Exception as e:
        return AIProcessResponse(
            ok=False,
            provider=str(s.get("provider", "")),
            model=str(s.get("model", "")),
            reply_text="",
            used_fallback=False,
            error=str(e)[:900],
        )


@router.get("/models")
def list_ai_models():
    return {
        "providers": MODEL_CATALOG,
        "defaults": {
            "provider": "google",
            "model": "gemma-3-4b-it",
            "fallback_provider": "groq",
            "fallback_model": "llama-3.1-8b-instant",
            "reply_chunk_chars": 480,
            "reply_delay_ms": 900,
            "typing_delay_ms": 450,
        },
    }


@router.get("/models/live")
def list_ai_models_live(
    provider: str = Query(..., description="google|groq|mistral|openrouter"),
):
    p = (provider or "").strip().lower()

    if not _is_valid_provider(p):
        raise HTTPException(status_code=400, detail="Invalid provider")

    if not _provider_supports_live(p):
        raise HTTPException(status_code=400, detail="Provider does not support live listing")

    if p == "google":
        models = _fetch_google_models()
    elif p == "groq":
        models = _fetch_groq_models()
    elif p == "mistral":
        models = _fetch_mistral_models()
    elif p == "openrouter":
        models = _fetch_openrouter_models()
    else:
        models = []

    return {"provider": p, "models": models}


@router.get("/debug/prompt")
def debug_prompt(
    phone: str = Query(..., description="Teléfono del chat"),
    text: str = Query("", description="Texto del usuario (último mensaje)"),
):
    """
    Dry-run: construye meta (CRM + historial + KB), lee settings y
    devuelve el payload final que se mandaría al LLM. NO llama provider.
    """
    phone = (phone or "").strip()
    user_text = (text or "").strip()

    if not phone:
        raise HTTPException(status_code=400, detail="phone is required")

    with engine.begin() as conn:
        s = _get_settings_row(conn)

    system_prompt = str(s.get("system_prompt") or "").strip()

    meta = build_ai_meta(phone, user_text)

    messages: List[Dict[str, str]] = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    ctx = (meta.get("context") or "").strip() if isinstance(meta, dict) else ""
    if ctx:
        messages.append({
            "role": "user",
            "content": (
                "Contexto adicional (usa esto como referencia; si no aplica, ignóralo):\n"
                f"{ctx}"
            )
        })

    messages.append({"role": "user", "content": user_text or "Hola"})

    return {
        "ok": True,
        "settings": {
            "is_enabled": bool(s.get("is_enabled", True)),
            "provider": str(s.get("provider") or ""),
            "model": str(s.get("model") or ""),
            "fallback_provider": str(s.get("fallback_provider") or ""),
            "fallback_model": str(s.get("fallback_model") or ""),
            "max_tokens": int(s.get("max_tokens") or 512),
            "temperature": float(s.get("temperature") or 0.7),
            "timeout_sec": int(s.get("timeout_sec") or 25),
            "max_retries": int(s.get("max_retries") or 1),

            "reply_chunk_chars": int(s.get("reply_chunk_chars") or 480),
            "reply_delay_ms": int(s.get("reply_delay_ms") or 900),
            "typing_delay_ms": int(s.get("typing_delay_ms") or 450),
        },
        "system_prompt": system_prompt,
        "meta": meta,
        "messages": messages,
    }
