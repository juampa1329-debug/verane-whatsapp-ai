from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict, Any, Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import text

from app.ai.knowledge_router import router as knowledge_router
from app.ai.context_builder import build_ai_meta
from app.db import engine

router = APIRouter()

# KB endpoints quedan bajo /api/ai/knowledge/*
router.include_router(knowledge_router, prefix="/knowledge")

# Providers que vamos a soportar desde ya (Fase 1)
AIProvider = Literal["google", "groq", "mistral", "openrouter"]

# =========================================================
# Model catalog (whitelist) - backend source of truth
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
    return (p or "").strip().lower() in MODEL_CATALOG

def _is_valid_model(provider: str, model: str) -> bool:
    p = (provider or "").strip().lower()
    m = (model or "").strip()
    return bool(p in MODEL_CATALOG and m in MODEL_CATALOG[p])



# =========================================================
# DB helpers (solo lectura/escritura; el schema lo crea main.ensure_schema)
# =========================================================

def _get_settings_row(conn) -> Dict[str, Any]:
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
        }

        if not new_vals["provider"]:
            raise HTTPException(status_code=400, detail="provider is required")
        if not new_vals["model"]:
            raise HTTPException(status_code=400, detail="model is required")
        
                # ✅ Validación fuerte provider/model (evita strings inválidos)
        if not _is_valid_provider(new_vals["provider"]):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid provider: {new_vals['provider']}. Allowed: {list(MODEL_CATALOG.keys())}"
            )

        if not _is_valid_model(new_vals["provider"], new_vals["model"]):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid model '{new_vals['model']}' for provider '{new_vals['provider']}'"
            )

        # fallback opcional pero recomendado: si viene, validarlo también
        fb_p = (new_vals.get("fallback_provider") or "").strip().lower()
        fb_m = (new_vals.get("fallback_model") or "").strip()

        if fb_p:
            if not _is_valid_provider(fb_p):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid fallback_provider: {fb_p}. Allowed: {list(MODEL_CATALOG.keys())}"
                )
            if fb_m and not _is_valid_model(fb_p, fb_m):
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid fallback_model '{fb_m}' for fallback_provider '{fb_p}'"
                )


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
                updated_at = NOW()
            WHERE id = :id
        """), {**new_vals, "id": sid})

        row = _get_settings_row(conn)

    return AISettingsOut(**row)


@router.post("/process-message", response_model=AIProcessResponse)
async def process_ai_message(payload: AIProcessRequest):
    """
    Endpoint de prueba/manual QA.
    NOTA: el disparo automático real ocurre desde /api/messages/ingest cuando takeover=true.
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
        # Si no pasan meta manual, usamos el mismo helper que usa el pipeline real
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
    """
    Catálogo (whitelist) de providers/modelos permitidos para el frontend.
    Esto evita que el frontend mande cualquier string y te rompa el engine.
    """
    return {
        "providers": {
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
        },
        "defaults": {
            "provider": "google",
            "model": "gemma-3-4b-it",
            "fallback_provider": "groq",
            "fallback_model": "llama-3.1-8b-instant",
        },
    }

@router.get("/debug/prompt")
def debug_prompt(
    phone: str = Query(..., description="Teléfono del chat"),
    text: str = Query("", description="Texto del usuario (último mensaje)"),
):
    """
    Dry-run: construye el meta (CRM + historial + KB), lee settings (system_prompt, etc.)
    y devuelve el payload final que se mandaría al LLM. NO llama a ningún provider.
    """
    phone = (phone or "").strip()
    user_text = (text or "").strip()

    if not phone:
        raise HTTPException(status_code=400, detail="phone is required")

    # 1) leer settings desde DB
    with engine.begin() as conn:
        s = _get_settings_row(conn)

    system_prompt = str(s.get("system_prompt") or "").strip()

    # 2) armar meta igual que en el pipeline real (CRM + history + KB)
    meta = build_ai_meta(phone, user_text)

    # 3) armar messages EXACTAMENTE como el engine (sin duplicar RAG aquí)
    #    - system_prompt viene de DB
    #    - meta["context"] viene del context_builder (ya incluye KB)
    messages = []
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
        },
        "system_prompt": system_prompt,
        "meta": meta,
        "messages": messages,
    }
