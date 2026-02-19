from __future__ import annotations

import os
import base64
from typing import Optional, Tuple, Dict, Any

import httpx


# =========================================================
# TTS Router
# =========================================================

def _tts_provider() -> str:
    return (os.getenv("TTS_PROVIDER", "google") or "google").strip().lower()


async def tts_synthesize(text: str, provider: Optional[str] = None) -> Tuple[bytes, str, str, Dict[str, Any]]:
    """
    Returns: (audio_bytes, mime_type, filename, meta)
    Providers: google | elevenlabs | piper
    """
    provider = (provider or _tts_provider()).strip().lower()
    text = (text or "").strip()

    if not text:
        return b"", "application/octet-stream", "empty.bin", {"ok": False, "reason": "empty text"}

    if provider == "google":
        return await _tts_google(text)

    if provider == "elevenlabs":
        return await _tts_elevenlabs(text)

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

    Default output: OGG_OPUS (good for WhatsApp audio messages)
    """
    api_key = (os.getenv("GOOGLE_CLOUD_TTS_API_KEY", "") or "").strip()
    if not api_key:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "reason": "GOOGLE_CLOUD_TTS_API_KEY missing"}

    lang = (os.getenv("GOOGLE_TTS_LANGUAGE_CODE", "es-US") or "es-US").strip()
    voice = (os.getenv("GOOGLE_TTS_VOICE_NAME", "") or "").strip()  # optional
    speaking_rate = float(os.getenv("GOOGLE_TTS_SPEAKING_RATE", "1.0") or 1.0)
    pitch = float(os.getenv("GOOGLE_TTS_PITCH", "0.0") or 0.0)

    # Encoding:
    # - OGG_OPUS works well for WhatsApp "audio"
    # - If you prefer MP3: set GOOGLE_TTS_AUDIO_ENCODING=MP3 and mime becomes audio/mpeg
    encoding = (os.getenv("GOOGLE_TTS_AUDIO_ENCODING", "OGG_OPUS") or "OGG_OPUS").strip().upper()

    url = f"https://texttospeech.googleapis.com/v1/text:synthesize?key={api_key}"

    payload: Dict[str, Any] = {
        "input": {"text": text},
        "voice": {
            "languageCode": lang,
        },
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
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "status": r.status_code, "body": r.text[:900]}

    j = r.json() or {}
    audio_b64 = j.get("audioContent") or ""
    if not audio_b64:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "reason": "no audioContent"}

    try:
        audio_bytes = base64.b64decode(audio_b64)
    except Exception:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "reason": "base64 decode failed"}

    if encoding == "MP3":
        return audio_bytes, "audio/mpeg", "tts.mp3", {"ok": True, "provider": "google", "encoding": encoding, "language": lang, "voice": voice or None}
    # default ogg/opus
    return audio_bytes, "audio/ogg", "tts.ogg", {"ok": True, "provider": "google", "encoding": encoding, "language": lang, "voice": voice or None}


# =========================================================
# Provider: ElevenLabs
# =========================================================

async def _tts_elevenlabs(text: str) -> Tuple[bytes, str, str, Dict[str, Any]]:
    """
    Env vars:
      ELEVENLABS_API_KEY
      ELEVENLABS_VOICE_ID
    """
    api_key = (os.getenv("ELEVENLABS_API_KEY", "") or "").strip()
    voice_id = (os.getenv("ELEVENLABS_VOICE_ID", "") or "").strip()

    if not api_key:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "reason": "ELEVENLABS_API_KEY missing"}
    if not voice_id:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "reason": "ELEVENLABS_VOICE_ID missing"}

    # Output format:
    # - MP3 is simplest and WhatsApp accepts audio/mpeg
    # If you want opus, we can later change to an opus endpoint variant.
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    model_id = (os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2") or "eleven_multilingual_v2").strip()

    payload: Dict[str, Any] = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": float(os.getenv("ELEVENLABS_STABILITY", "0.5") or 0.5),
            "similarity_boost": float(os.getenv("ELEVENLABS_SIMILARITY_BOOST", "0.75") or 0.75),
        }
    }

    headers = {
        "xi-api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "audio/mpeg",
    }

    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.post(url, json=payload, headers=headers)

    if r.status_code >= 400:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "status": r.status_code, "body": r.text[:900]}

    audio_bytes = r.content or b""
    if not audio_bytes:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "reason": "empty audio"}

    return audio_bytes, "audio/mpeg", "tts.mp3", {"ok": True, "provider": "elevenlabs", "voice_id": voice_id, "model_id": model_id}


# =========================================================
# Provider: Piper (prepared)
# =========================================================

async def _tts_piper(text: str) -> Tuple[bytes, str, str, Dict[str, Any]]:
    """
    Expects a local Piper TTS microservice later.
    Env:
      PIPER_BASE_URL (example: http://piper:8000)

    We keep this prepared. When you deploy piper, make sure it returns audio/ogg (opus)
    or audio/wav and we can convert.
    """
    base_url = (os.getenv("PIPER_BASE_URL", "") or "").strip()
    if not base_url:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "reason": "PIPER_BASE_URL missing"}

    # Example endpoint (we'll match whatever you deploy):
    # GET /tts?text=...
    url = f"{base_url.rstrip('/')}/tts"
    params = {"text": text}

    async with httpx.AsyncClient(timeout=45) as client:
        r = await client.get(url, params=params)

    if r.status_code >= 400:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "status": r.status_code, "body": r.text[:900]}

    ct = (r.headers.get("content-type") or "audio/ogg").split(";")[0].strip().lower()
    audio_bytes = r.content or b""
    if not audio_bytes:
        return b"", "application/octet-stream", "audio.bin", {"ok": False, "reason": "empty audio"}

    # Default guess
    if ct in ("audio/ogg", "audio/opus"):
        return audio_bytes, "audio/ogg", "tts.ogg", {"ok": True, "provider": "piper", "content_type": ct}
    if ct in ("audio/wav", "audio/x-wav"):
        return audio_bytes, "audio/wav", "tts.wav", {"ok": True, "provider": "piper", "content_type": ct}

    return audio_bytes, ct, "tts.bin", {"ok": True, "provider": "piper", "content_type": ct}
