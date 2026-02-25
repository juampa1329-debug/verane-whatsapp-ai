import os
import re
import json
import base64
import tempfile
import subprocess
import asyncio
from typing import Tuple, Dict, Any, Optional

import httpx


def _get_gemini_key() -> str:
    return (os.getenv("GOOGLE_AI_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip())


def _clean_mime(m: str) -> str:
    return (m or "application/octet-stream").split(";")[0].strip().lower()


def _default_gemini_mm_model() -> str:
    """
    Modelo principal para multimodal (VISION/OCR/DOC).
    ✅ Cambiado a Gemini 2.5 por defecto.
    """
    return (os.getenv("GEMINI_MM_MODEL", "").strip() or "gemini-2.5-flash").strip()


def _fallback_gemini_mm_model() -> str:
    """
    Modelo fallback si el principal falla (404 deprecado/no disponible, etc.)
    """
    return (os.getenv("GEMINI_MM_FALLBACK_MODEL", "").strip() or "gemini-2.5-flash-lite").strip()


def _gemini_timeout_sec() -> float:
    try:
        return float(os.getenv("GEMINI_MM_TIMEOUT_SEC", "75").strip() or "75")
    except Exception:
        return 75.0


def _gemini_max_retries() -> int:
    try:
        # retries extra ante 429/5xx (no cuenta el primer intento)
        v = int(os.getenv("GEMINI_MM_MAX_RETRIES", "2").strip() or "2")
        return max(0, min(v, 8))
    except Exception:
        return 2


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


def _extract_retry_after_seconds(headers: httpx.Headers, body_text: str) -> Optional[float]:
    """
    Intenta obtener retry_after desde:
    - Header Retry-After
    - Mensaje tipo: "Please retry in 16.86s"
    """
    try:
        ra = (headers.get("retry-after") or headers.get("Retry-After") or "").strip()
        if ra:
            # Puede ser segundos (int) o fecha HTTP; tomamos segundos si es numérico
            try:
                return float(ra)
            except Exception:
                pass
    except Exception:
        pass

    # Parsear texto del body
    try:
        m = re.search(r"retry in\s+([0-9]+(?:\.[0-9]+)?)s", body_text or "", re.IGNORECASE)
        if m:
            return float(m.group(1))
    except Exception:
        pass

    return None


def _is_model_not_found_404(body_text: str) -> bool:
    """
    Detecta el caso típico:
    - NOT_FOUND
    - "model ... is no longer available"
    """
    t = (body_text or "").lower()
    if "not_found" in t or "\"status\": \"not_found\"" in t:
        return True
    if "no longer available" in t:
        return True
    if "model models/" in t and "not found" in t:
        return True
    return False


def _build_prompt(kind: str) -> str:
    if kind == "audio":
        return (
            "Transcribe exactamente el audio en español. "
            "No inventes nada. "
            "Devuelve SOLO el texto transcrito, sin explicaciones."
        )

    # document / image: OCR + clasificación (perfume vs pago)
    # Importante: el modelo debe devolver SOLO JSON válido (sin Markdown)
    return (
        "Eres un asistente de ventas por WhatsApp para una tienda de perfumes. "
        "Analiza la imagen/documento y devuelve SOLO un JSON válido (sin texto extra, sin Markdown). "
        "1) OCR: transcribe TODO el texto visible tal cual (si no hay, ocr_text=''). "
        "2) Clasifica type en: 'PERFUME', 'PAYMENT' o 'OTHER'. "
        "3) Si es PERFUME, intenta identificar brand/nombre exacto. Si NO hay texto visible, infiere por rasgos distintivos (forma del frasco/colores) y devuelve guesses (máx 3) con confianza. Si no es exacto, llena keywords útiles de búsqueda. "
        "4) Si es PAYMENT (comprobante/recibo), extrae monto, moneda, referencia, fecha, banco, pagador y beneficiario si aparecen. "
        "Devuelve exactamente este formato JSON (rellena con '' si no aplica): "
        "{"
        "\"type\":\"PERFUME|PAYMENT|OTHER\","
        "\"ocr_text\":\"\","
        "\"perfume\":{\"brand\":\"\",\"name\":\"\",\"variant\":\"\",\"gender_hint\":\"hombre|mujer|unisex|\",\"keywords\":[\"\"]},"
        "\"payment\":{\"amount\":\"\",\"currency\":\"\",\"reference\":\"\",\"date\":\"\",\"bank\":\"\",\"payer\":\"\",\"payee\":\"\"},"
        "\"notes\":\"\""
        "}"
    )


async def _gemini_generate_with_model(
    *,
    model: str,
    kind: str,
    media_bytes: bytes,
    mime_type: str,
    timeout_sec: float,
) -> Tuple[str, Dict[str, Any]]:
    api_key = _get_gemini_key()
    if not api_key:
        return "", {"ok": False, "reason": "GOOGLE_AI_API_KEY missing"}

    mime_clean = _clean_mime(mime_type)
    prompt = _build_prompt(kind)

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

    t0 = asyncio.get_event_loop().time()
    try:
        async with httpx.AsyncClient(timeout=timeout_sec) as client:
            r = await client.post(url, json=body)
    except Exception as e:
        return "", {
            "ok": False,
            "stage": "http",
            "error": str(e)[:900],
            "model": model,
            "mime_type": mime_clean,
        }

    latency_ms = int((asyncio.get_event_loop().time() - t0) * 1000)

    if r.status_code >= 400:
        body_text = ""
        try:
            body_text = r.text or ""
        except Exception:
            body_text = ""

        retry_after = _extract_retry_after_seconds(r.headers, body_text)
        return "", {
            "ok": False,
            "stage": "generate",
            "status": int(r.status_code),
            "body": (body_text[:1200] if body_text else ""),
            "model": model,
            "mime_type": mime_clean,
            "latency_ms": latency_ms,
            "retry_after_s": retry_after,
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

    parsed_json = None
    if out_text:
        try:
            parsed_json = json.loads(out_text)
            if not isinstance(parsed_json, dict):
                parsed_json = None
        except Exception:
            parsed_json = None

    return out_text, {
        "ok": True,
        "stage": "generate",
        "status": int(r.status_code),
        "model": model,
        "mime_type": mime_clean,
        "latency_ms": latency_ms,
        "parsed_json": parsed_json,
    }


async def gemini_generate_text_inline(kind: str, media_bytes: bytes, mime_type: str) -> Tuple[str, Dict[str, Any]]:
    """
    Wrapper robusto:
    - Usa modelo principal (Gemini 2.5 por defecto)
    - Si 404 (modelo no disponible) -> intenta fallback model 1 vez
    - Si 429/5xx -> retries con backoff (respeta retry_after si existe)
    """
    api_key = _get_gemini_key()
    if not api_key:
        return "", {"ok": False, "reason": "GOOGLE_AI_API_KEY missing"}

    primary_model = _default_gemini_mm_model()
    fallback_model = _fallback_gemini_mm_model()
    timeout_sec = _gemini_timeout_sec()
    max_retries = _gemini_max_retries()

    tried_models = []
    attempts = 0

    async def _attempt(model_name: str) -> Tuple[str, Dict[str, Any]]:
        nonlocal attempts
        attempts += 1
        tried_models.append(model_name)
        return await _gemini_generate_with_model(
            model=model_name,
            kind=kind,
            media_bytes=media_bytes,
            mime_type=mime_type,
            timeout_sec=timeout_sec,
        )

    # 1) Intento con primary (con retries si 429/5xx)
    last_meta: Dict[str, Any] = {}
    last_text: str = ""

    for i in range(max_retries + 1):
        txt, meta = await _attempt(primary_model)
        last_text, last_meta = txt, meta

        if meta.get("ok") is True:
            meta.update({
                "attempts": attempts,
                "tried_models": tried_models,
                "primary_model": primary_model,
                "fallback_model": fallback_model,
            })
            return (txt or "").strip(), meta

        status = int(meta.get("status") or 0)
        body_text = str(meta.get("body") or "")

        # 404 -> no hacemos retries: pasamos a fallback model
        if status == 404 and _is_model_not_found_404(body_text):
            break

        # 429 o 5xx -> backoff y reintentar
        if status == 429 or (500 <= status <= 599):
            retry_after = meta.get("retry_after_s")
            if retry_after is None:
                # Backoff simple
                retry_after = min(2.0 * (2 ** i), 20.0)
            try:
                await asyncio.sleep(float(retry_after))
            except Exception:
                pass
            continue

        # otros 4xx -> no reintentar
        break

    # 2) Intento con fallback model (1 vez; y retries si 429/5xx)
    if fallback_model and fallback_model != primary_model:
        for i in range(max_retries + 1):
            txt, meta = await _attempt(fallback_model)
            last_text, last_meta = txt, meta

            if meta.get("ok") is True:
                meta.update({
                    "attempts": attempts,
                    "tried_models": tried_models,
                    "primary_model": primary_model,
                    "fallback_model": fallback_model,
                    "used_fallback": True,
                })
                return (txt or "").strip(), meta

            status = int(meta.get("status") or 0)
            # 429 o 5xx -> reintentar con backoff
            if status == 429 or (500 <= status <= 599):
                retry_after = meta.get("retry_after_s")
                if retry_after is None:
                    retry_after = min(2.0 * (2 ** i), 20.0)
                try:
                    await asyncio.sleep(float(retry_after))
                except Exception:
                    pass
                continue
            break

    # Falló todo
    if isinstance(last_meta, dict):
        last_meta.update({
            "attempts": attempts,
            "tried_models": tried_models,
            "primary_model": primary_model,
            "fallback_model": fallback_model,
        })
    return "", (last_meta or {"ok": False, "reason": "gemini_failed"})


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

    # Try to parse JSON for image/document (prompt requests JSON)
    parsed = None
    if kind in ("image", "document") and text_out:
        try:
            parsed = json.loads(text_out)
        except Exception:
            parsed = None

    if isinstance(parsed, dict):
        meta["parsed"] = parsed
        meta["parsed_ok"] = True

        ptype = (parsed.get("type") or "").strip().upper()
        ocr_text = (parsed.get("ocr_text") or "").strip()

        # PERFUME: build a compact query for Woo search (brand+name+variant+keywords)
        if ptype == "PERFUME":
            perf = parsed.get("perfume") or {}
            brand = (perf.get("brand") or "").strip()
            name = (perf.get("name") or "").strip()
            variant = (perf.get("variant") or "").strip()
            kw = perf.get("keywords") or []
            if not isinstance(kw, list):
                kw = []
            kw = [str(x).strip() for x in kw if str(x).strip()]
            # fallback guesses (si el modelo los mandó)
            guesses = parsed.get("guesses") or []
            if (not name) and isinstance(guesses, list) and guesses:
                g0 = guesses[0] if isinstance(guesses[0], dict) else {}
                name = (g0.get("name") or "").strip() or name
                brand = (g0.get("brand") or "").strip() or brand

            query = " ".join([x for x in [brand, name, variant] if x]).strip()
            if not query and ocr_text:
                query = ocr_text[:180].strip()
            if kw and len(query) < 6:
                query = (query + " " + " ".join(kw[:6])).strip()
            # Return query as extracted_text so downstream can search
            text_out = query or ocr_text or ""

        # PAYMENT: return ocr_text as extracted_text for CRM notes
        elif ptype == "PAYMENT":
            text_out = ocr_text or ""

        else:
            # OTHER: keep OCR if any
            text_out = ocr_text or text_out

    else:
        meta["parsed_ok"] = False

    meta["ok"] = bool(text_out)
    meta["extracted_len"] = int(len(text_out))
    meta["mime_used"] = use_mime

    return text_out, meta