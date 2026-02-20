from __future__ import annotations

import os
import base64
from typing import Optional, Tuple, Dict, Any

import httpx


# =========================================================
# TTS Router (library)
# =========================================================

def _tts_provider_default() -> str:
    """
    Fallback global (ENV) si no se pasa provider desde DB/request.
    OJO: En tu flujo normal, el provider “real” viene de ai_settings.voice_tts_provider.
    """
    return (os.getenv("TTS_PROVIDER", "google") or "google").strip().lower()


async def tts_synthesize(
    text: str,
    provider: Optional[str] = None,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
) -> Tuple[bytes, str, str, Dict[str, Any]]:
    """
    Returns: (audio_bytes, mime_type, filename, meta)
    Providers: google | elevenlabs | piper

    - provider: si None, usa ENV TTS_PROVIDER (fallback).
    - voice_id/model_id: overrides (principalmente para elevenlabs). Si None, caen al ENV.
    """
    provider = (provider or _tts_provider_default()).strip().lower()
    text = (text or "").strip()

    if not text:
        return b"", "application/octet-stream", "empty.bin", {"ok": False, "reason": "empty text"}

    if provider == "google":
        return await _tts_google(text)

    if provider == "elevenlabs":
        return await _tts_elevenlabs(text, voice_id=voice_id, model_id=model_id)

    if provider == "piper":
        return await _tts_piper(text)

    return b"", "application/octet-stream", "audio.bin", {"ok": False, "reason": f"unsupported provider: {provider}"}


# =========================================================
# Provider: Google Cloud Text-to-Speech
# =========================================================

async def _tts_google(text: str) -> Tuple[bytes, str, str, Dict[str, Any]]:
    """
    Uses Google Cloud TTS API key:
      GOOGLE_CLOUD_TTS_API_KEY

    Defaults:
      - language: GOOGLE_TTS_LANGUAGE_CODE (es-US)
      - voice name: GOOGLE_TTS_VOICE_NAME (optional)
      - encoding: GOOGLE_TTS_AUDIO_ENCODING (OGG_OPUS)
      - speaking rate: GOOGLE_TTS_SPEAKING_RATE (1.0)
      - pitch: GOOGLE_TTS_PITCH (0.0)
    """
    api_key = (os.getenv("GOOGLE_CLOUD_TTS_API_KEY", "") or "").strip()
    if not api_key:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "reason": "GOOGLE_CLOUD_TTS_API_KEY missing"}

    lang = (os.getenv("GOOGLE_TTS_LANGUAGE_CODE", "es-US") or "es-US").strip()
    voice = (os.getenv("GOOGLE_TTS_VOICE_NAME", "") or "").strip()  # optional

    try:
        speaking_rate = float(os.getenv("GOOGLE_TTS_SPEAKING_RATE", "1.0") or 1.0)
    except Exception:
        speaking_rate = 1.0

    try:
        pitch = float(os.getenv("GOOGLE_TTS_PITCH", "0.0") or 0.0)
    except Exception:
        pitch = 0.0

    encoding = (os.getenv("GOOGLE_TTS_AUDIO_ENCODING", "OGG_OPUS") or "OGG_OPUS").strip().upper()

    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"

    payload: Dict[str, Any] = {
        "input": {"text": text},
        "voice": {"languageCode": lang},
        "audioConfig": {
            "audioEncoding": encoding,
            "speakingRate": speaking_rate,
            "pitch": pitch,
        },
    }

    if voice:
        payload["voice"]["name"] = voice

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(url, json=payload)

    if r.status_code >= 400:
        return b"", "application/octet-stream", "audio.bin", {
            "ok": False,
            "provider": "google",
            "status": r.status_code,
            "body": r.text[:900],
        }

    j = r.json() or {}
    audio_b64 = j.get("audioContent") or ""
    if not audio_b64:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "provider": "google", "reason": "no audioContent"}

    try:
        audio_bytes = base64.b64decode(audio_b64)
    except Exception:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "provider": "google", "reason": "base64 decode failed"}

    if encoding == "MP3":
        return audio_bytes, "audio/mpeg", "tts.mp3", {
            "ok": True,
            "provider": "google",
            "encoding": encoding,
            "language": lang,
            "voice": voice or None,
        }

    # default: ogg/opus (mejor para WhatsApp audio)
    return audio_bytes, "audio/ogg", "tts.ogg", {
        "ok": True,
        "provider": "google",
        "encoding": encoding,
        "language": lang,
        "voice": voice or None,
    }


# =========================================================
# Provider: ElevenLabs
# =========================================================

def _env_bool(name: str, default: bool = False) -> bool:
    v = (os.getenv(name, "") or "").strip().lower()
    if v == "":
        return default
    return v in ("1", "true", "yes", "y", "on")


def _env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)) or default)
    except Exception:
        return default


async def _tts_elevenlabs(
    text: str,
    voice_id: Optional[str] = None,
    model_id: Optional[str] = None,
) -> Tuple[bytes, str, str, Dict[str, Any]]:
    """
    Env vars:
      ELEVENLABS_API_KEY
      ELEVENLABS_VOICE_ID           (fallback si no pasas voice_id)
      ELEVENLABS_MODEL_ID           (fallback si no pasas model_id) default: eleven_multilingual_v2

    Optional controls:
      ELEVENLABS_OUTPUT_FORMAT (default: mp3_44100_128)
      ELEVENLABS_APPLY_TEXT_NORMALIZATION (auto|on|off, default: auto)
      ELEVENLABS_ENABLE_LOGGING (true|false, default: true)
      ELEVENLABS_OPTIMIZE_STREAMING_LATENCY (0..4, optional)

      ELEVENLABS_STABILITY (0..1, default 0.5)
      ELEVENLABS_SIMILARITY_BOOST (0..1, default 0.75)
      ELEVENLABS_STYLE (0..1, optional)
      ELEVENLABS_USE_SPEAKER_BOOST (true|false, optional)

    Output:
      - Normalmente MP3. WhatsApp acepta audio/mpeg.
    """
    api_key = (os.getenv("ELEVENLABS_API_KEY", "") or "").strip()
    if not api_key:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "reason": "ELEVENLABS_API_KEY missing"}

    # ✅ override primero; si no, ENV
    voice_id = (voice_id or os.getenv("ELEVENLABS_VOICE_ID", "") or "").strip()
    if not voice_id:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "reason": "ELEVENLABS_VOICE_ID missing"}

    model_id = (model_id or os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2") or "eleven_multilingual_v2").strip()

    base_url = "https://api.elevenlabs.io"
    url = f"{base_url}/v1/text-to-speech/{voice_id}/stream"

    output_format = (os.getenv("ELEVENLABS_OUTPUT_FORMAT", "mp3_44100_128") or "mp3_44100_128").strip()

    apply_norm = (os.getenv("ELEVENLABS_APPLY_TEXT_NORMALIZATION", "auto") or "auto").strip().lower()
    if apply_norm not in ("auto", "on", "off"):
        apply_norm = "auto"

    enable_logging = _env_bool("ELEVENLABS_ENABLE_LOGGING", True)

    params: Dict[str, Any] = {
        "output_format": output_format,
        "enable_logging": "true" if enable_logging else "false",
        "apply_text_normalization": apply_norm,
    }

    opt_lat = (os.getenv("ELEVENLABS_OPTIMIZE_STREAMING_LATENCY", "") or "").strip()
    if opt_lat != "":
        params["optimize_streaming_latency"] = opt_lat

    voice_settings: Dict[str, Any] = {
        "stability": _env_float("ELEVENLABS_STABILITY", 0.5),
        "similarity_boost": _env_float("ELEVENLABS_SIMILARITY_BOOST", 0.75),
    }

    style = (os.getenv("ELEVENLABS_STYLE", "") or "").strip()
    if style != "":
        try:
            voice_settings["style"] = float(style)
        except Exception:
            pass

    use_speaker_boost = (os.getenv("ELEVENLABS_USE_SPEAKER_BOOST", "") or "").strip().lower()
    if use_speaker_boost in ("1", "true", "yes", "y", "on", "0", "false", "no", "n", "off"):
        voice_settings["use_speaker_boost"] = use_speaker_boost in ("1", "true", "yes", "y", "on")

    payload: Dict[str, Any] = {
        "text": text,
        "model_id": model_id,
        "voice_settings": voice_settings,
    }

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, params=params, json=payload, headers=headers)

    if r.status_code >= 400:
        return b"", "application/octet-stream", "audio.bin", {
            "ok": False,
            "status": r.status_code,
            "body": r.text[:900],
            "provider": "elevenlabs",
            "voice_id": voice_id,
            "model_id": model_id,
            "output_format": output_format,
            "apply_text_normalization": apply_norm,
        }

    audio_bytes = r.content or b""
    if not audio_bytes:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "provider": "elevenlabs", "reason": "empty audio"}

    # Por defecto: mp3
    mime = "audio/mpeg"
    filename = "tts.mp3"

    # (si luego soportas otros output_format, ajustamos mime/filename aquí)
    return audio_bytes, mime, filename, {
        "ok": True,
        "provider": "elevenlabs",
        "voice_id": voice_id,
        "model_id": model_id,
        "output_format": output_format,
        "apply_text_normalization": apply_norm,
        "enable_logging": enable_logging,
    }


# =========================================================
# Provider: Piper (prepared)
# =========================================================

async def _tts_piper(text: str) -> Tuple[bytes, str, str, Dict[str, Any]]:
    """
    Expects a local Piper TTS microservice later.
    Env:
      PIPER_BASE_URL (example: http://piper:8000)

    Expected endpoint example:
      GET /tts?text=...

    Return audio as:
      audio/ogg (opus) or audio/wav
    """
    base_url = (os.getenv("PIPER_BASE_URL", "") or "").strip()
    if not base_url:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "reason": "PIPER_BASE_URL missing"}

    url = f"{base_url.rstrip('/')}/tts"
    params = {"text": text}

    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.get(url, params=params)

    if r.status_code >= 400:
        return b"", "application/octet-stream", "audio.bin", {
            "ok": False,
            "provider": "piper",
            "status": r.status_code,
            "body": r.text[:900],
        }

    ct = (r.headers.get("content-type") or "audio/ogg").split(";")[0].strip().lower()
    audio_bytes = r.content or b""
    if not audio_bytes:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "provider": "piper", "reason": "empty audio"}

    if ct in ("audio/ogg", "audio/opus"):
        return audio_bytes, "audio/ogg", "tts.ogg", {"ok": True, "provider": "piper", "content_type": ct}

    if ct in ("audio/wav", "audio/x-wav"):
        return audio_bytes, "audio/wav", "tts.wav", {"ok": True, "provider": "piper", "content_type": ct}

    return audio_bytes, ct, "tts.bin", {"ok": True, "provider": "piper", "content_type": ct}