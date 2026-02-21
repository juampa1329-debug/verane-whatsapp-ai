import os
import re
import json
import base64
import tempfile
import subprocess
from typing import Tuple, Dict, Any, Optional

import httpx


def _get_gemini_key() -> str:
    return (os.getenv("GOOGLE_AI_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip())


def _clean_mime(m: str) -> str:
    return (m or "application/octet-stream").split(";")[0].strip().lower()


def _default_gemini_mm_model() -> str:
    return (os.getenv("GEMINI_MM_MODEL", "").strip() or "gemini-2.0-flash").strip()


def is_effectively_empty_text(text_value: str) -> bool:
    t = (text_value or "").strip().lower()
    if not t:
        return True

    placeholders = {
        "[audio]", "[voice]", "[nota de voz]", "audio",
        "[image]", "[imagen]", "[photo]", "[foto]", "image", "imagen", "foto",
        "[video]", "[document]", "[archivo]", "video", "documento", "archivo",
        "[sticker]", "[gif]", "sticker", "gif",
    }
    t2 = re.sub(r"\s+", " ", t)
    if t in placeholders or t2 in placeholders:
        return True

    if re.fullmatch(r"\[[a-záéíóúñ0-9\s]+\]", t2) is not None:
        return True

    return False


def _gemini_media_kind(msg_type: str, mime_type: str) -> str:
    mime = (mime_type or "").lower()
    if msg_type == "audio" or mime.startswith("audio/"):
        return "audio"
    if msg_type == "image" or mime.startswith("image/"):
        return "image"
    if msg_type == "document" or mime.startswith("application/pdf") or "pdf" in mime:
        return "document"
    if mime.startswith("image/"):
        return "image"
    return "document"


def _ffmpeg_convert_to_wav_16k_mono(in_bytes: bytes, in_mime: str) -> Tuple[bytes, str, Dict[str, Any]]:
    """
    Convierte audio (ogg/opus/webm/mp3/etc) a WAV PCM 16k mono.
    Retorna (wav_bytes, 'audio/wav', meta)
    """
    meta: Dict[str, Any] = {"ok": False, "in_mime": _clean_mime(in_mime or "")}

    if not in_bytes:
        meta["reason"] = "empty_input_bytes"
        return b"", "audio/wav", meta

    try:
        with tempfile.TemporaryDirectory() as tmp:
            in_path = os.path.join(tmp, "in.bin")
            out_path = os.path.join(tmp, "out.wav")

            with open(in_path, "wb") as f:
                f.write(in_bytes)

            cmd = [
                "ffmpeg", "-y",
                "-i", in_path,
                "-ac", "1",
                "-ar", "16000",
                "-c:a", "pcm_s16le",
                out_path
            ]
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if p.returncode != 0:
                err = p.stderr.decode("utf-8", errors="ignore")
                meta["reason"] = "ffmpeg_failed"
                meta["ffmpeg_err"] = err[:1200]
                return b"", "audio/wav", meta

            with open(out_path, "rb") as f:
                wav_bytes = f.read()

        meta["ok"] = bool(wav_bytes)
        meta["out_len"] = int(len(wav_bytes) if wav_bytes else 0)
        return wav_bytes or b"", "audio/wav", meta

    except Exception as e:
        meta["reason"] = "ffmpeg_exception"
        meta["error"] = str(e)[:900]
        return b"", "audio/wav", meta


async def gemini_generate_text_inline(kind: str, media_bytes: bytes, mime_type: str) -> Tuple[str, Dict[str, Any]]:
    api_key = _get_gemini_key()
    if not api_key:
        return "", {"ok": False, "reason": "GOOGLE_AI_API_KEY missing"}

    model = _default_gemini_mm_model()
    mime_clean = _clean_mime(mime_type)

    if kind == "audio":
        prompt = (
            "Transcribe exactamente el audio en español. "
            "No inventes nada. "
            "Devuelve SOLO el texto transcrito, sin explicaciones."
        )
    elif kind == "document":
        prompt = (
            "Extrae o resume el contenido del documento. "
            "Si tiene texto legible, transcríbelo. "
            "Si es una imagen o foto dentro del documento, descríbela. "
            "Devuelve SOLO el texto útil, sin explicaciones."
        )
    else:
        prompt = (
            "Describe la imagen con detalle útil para un asesor comercial. "
            "Si hay texto visible (nombre del producto, etiqueta, precio, caja), extráelo. "
            "Devuelve SOLO: (1) descripción corta. (2) texto visible si existe."
        )

    b64 = base64.b64encode(media_bytes).decode("utf-8")

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    body = {
        "contents": [{
            "role": "user",
            "parts": [
                {"text": prompt},
                {"inline_data": {"mime_type": mime_clean, "data": b64}},
            ],
        }],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 512},
    }

    try:
        async with httpx.AsyncClient(timeout=75) as client:
            r = await client.post(url, json=body)
    except Exception as e:
        return "", {"ok": False, "stage": "http", "error": str(e)[:900], "model": model, "mime_type": mime_clean}

    if r.status_code >= 400:
        return "", {
            "ok": False,
            "stage": "generate",
            "status": r.status_code,
            "body": r.text[:1200],
            "model": model,
            "mime_type": mime_clean,
        }

    j = r.json() or {}
    out_text = ""
    try:
        parts = (((j.get("candidates") or [])[0] or {}).get("content") or {}).get("parts") or []
        texts = []
        for p in parts:
            tx = (p or {}).get("text")
            if tx:
                texts.append(str(tx))
        out_text = "\n".join(texts).strip()
    except Exception:
        out_text = ""

    return out_text, {"ok": True, "stage": "generate", "model": model, "mime_type": mime_clean}


async def extract_text_from_media(
    msg_type: str,
    media_bytes: bytes,
    mime_type: str,
) -> Tuple[str, Dict[str, Any]]:
    """
    Punto único para:
    - audio -> convierte a wav 16k mono si viene ogg/opus/webm y transcribe
    - image/document -> manda tal cual
    """
    mime_clean = _clean_mime(mime_type)
    kind = _gemini_media_kind(msg_type, mime_clean)

    meta: Dict[str, Any] = {
        "ok": False,
        "kind": kind,
        "msg_type": msg_type,
        "mime_in": mime_clean,
        "stages": {}
    }

    use_bytes = media_bytes
    use_mime = mime_clean

    if kind == "audio":
        # WhatsApp casi siempre llega en audio/ogg (OPUS). Convertimos SIEMPRE para robustez.
        wav_bytes, wav_mime, conv_meta = _ffmpeg_convert_to_wav_16k_mono(media_bytes, mime_clean)
        meta["stages"]["audio_convert"] = conv_meta

        if conv_meta.get("ok") is True and wav_bytes:
            use_bytes = wav_bytes
            use_mime = wav_mime
        else:
            # si no pudimos convertir, intentamos igual con el original (por si acaso)
            meta["stages"]["audio_convert_fallback"] = {"ok": False, "reason": "conversion_failed_using_original"}

    text_out, gen_meta = await gemini_generate_text_inline(kind=kind, media_bytes=use_bytes, mime_type=use_mime)
    meta["stages"]["gemini"] = gen_meta
    text_out = (text_out or "").strip()

    meta["ok"] = bool(text_out)
    meta["extracted_len"] = int(len(text_out))
    meta["mime_used"] = use_mime

    return text_out, meta