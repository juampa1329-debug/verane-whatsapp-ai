from __future__ import annotations

import asyncio
import json
import os
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple
from zoneinfo import ZoneInfo

from sqlalchemy import text

from app.ai.context_builder import build_ai_meta
from app.ai.engine import process_message
from app.crm.crm_writer import ensure_conversation_row, update_crm_fields
from app.db import engine
from app.integrations.social_channels import send_channel_media, send_channel_text
from app.pipeline.reply_sender import (
    _get_voice_settings,
    send_ai_reply_as_voice,
    send_ai_reply_in_chunks,
)
from app.routes.whatsapp import send_whatsapp_text


def get_trigger_catalog() -> Dict[str, Any]:
    return {
        "trigger_types": [
            {"key": "none", "label": "Ninguna"},
            {"key": "tag_changed", "label": "Etiqueta cambiada"},
            {"key": "logic", "label": "Logica"},
            {"key": "message_flow", "label": "Flujo de mensajes"},
            {"key": "time", "label": "Tiempo"},
        ],
        "flow_events": [
            {"key": "received", "label": "Recibido"},
            {"key": "sent", "label": "Enviado"},
            {"key": "both", "label": "Envian y reciben"},
        ],
        "assistant_message_types": [
            {"key": "auto", "label": "Auto"},
            {"key": "text", "label": "Texto"},
            {"key": "audio", "label": "Audio"},
        ],
        "condition_types": [
            {"key": "last_message_sent", "label": "Ultimo mensaje enviado"},
            {"key": "sent_count", "label": "Cantidad de mensajes enviado"},
            {"key": "check_words", "label": "Comprobar palabras"},
            {"key": "template_sent_status", "label": "Comprobar plantilla si/no enviada"},
            {"key": "current_tag", "label": "Etiqueta actual"},
            {"key": "schedule", "label": "Comprobar horario"},
        ],
        "action_types": [
            {"key": "send_template", "label": "Enviar plantilla de mensaje"},
            {"key": "change_tag", "label": "Cambiar etiqueta"},
            {"key": "configure_conversation", "label": "Configurar conversacion"},
            {"key": "change_contact_status", "label": "Cambiar estado contacto"},
            {"key": "notify_admins", "label": "Enviar notificacion Administradores"},
            {"key": "extract_conversation_info", "label": "Extraer informacion conversacion"},
            {"key": "schedule_message", "label": "Programar mensaje"},
        ],
    }


def _safe_json_dict(val: Any) -> Dict[str, Any]:
    if isinstance(val, dict):
        return val
    return {}


def _safe_json_list(val: Any) -> List[Any]:
    if isinstance(val, list):
        return val
    return []


def _norm_text(raw: str) -> str:
    s = (raw or "").strip().lower()
    repl = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "ñ": "n",
    }
    for a, b in repl.items():
        s = s.replace(a, b)
    s = re.sub(r"\s+", " ", s)
    return s.strip()


def _split_tags(raw: str) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in str(raw or "").split(","):
        t = _norm_text(item)
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def _join_tags(tags: List[str]) -> str:
    seen = set()
    out: List[str] = []
    for item in tags:
        t = _norm_text(item)
        if not t or t in seen:
            continue
        seen.add(t)
        out.append(t)
    return ",".join(out)


def _compare_numbers(left: float, op: str, right: float) -> bool:
    opv = (op or "gte").strip().lower()
    if opv in ("=", "eq"):
        return left == right
    if opv in ("!=", "ne"):
        return left != right
    if opv in ("<", "lt"):
        return left < right
    if opv in ("<=", "lte"):
        return left <= right
    if opv in (">", "gt"):
        return left > right
    return left >= right


def _render_template(text_value: str, variables: Dict[str, Any]) -> str:
    out = text_value or ""
    for key, value in (variables or {}).items():
        k = str(key or "").strip()
        if not k:
            continue
        out = out.replace(f"{{{{{k}}}}}", str(value if value is not None else ""))
    return out.strip()


def _normalize_template_blocks(raw_blocks: Any, body_fallback: str = "") -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    items = raw_blocks if isinstance(raw_blocks, list) else []

    for item in items:
        if not isinstance(item, dict):
            continue

        kind = str(item.get("kind") or item.get("type") or "text").strip().lower()
        try:
            delay_ms = int(item.get("delay_ms") or 0)
        except Exception:
            delay_ms = 0
        delay_ms = max(0, min(delay_ms, 60000))

        if kind in ("image", "video", "audio"):
            media_id = str(item.get("media_id") or "").strip()
            media_url = str(
                item.get(f"{kind}_url")
                or item.get("media_url")
                or item.get("url")
                or ""
            ).strip()
            caption = str(item.get("caption") or item.get("text") or "").strip() if kind in ("image", "video") else ""
            if not media_id and not media_url:
                continue
            block = {
                "kind": kind,
                "media_id": media_id,
                "delay_ms": delay_ms,
            }
            if kind == "image":
                block["image_url"] = media_url
            elif kind == "video":
                block["video_url"] = media_url
            else:
                block["audio_url"] = media_url
            if kind in ("image", "video"):
                block["caption"] = caption
            out.append(block)
            continue

        txt = str(item.get("text") or item.get("content") or item.get("body") or "").strip()
        if not txt:
            continue
        out.append({"kind": "text", "text": txt, "delay_ms": delay_ms})

    if out:
        return out

    fallback = str(body_fallback or "").strip()
    if fallback:
        return [{"kind": "text", "text": fallback, "delay_ms": 0}]
    return []


def _recipient_variables(phone: str) -> Dict[str, Any]:
    ensure_conversation_row(phone)
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    c.phone,
                    c.first_name,
                    c.last_name,
                    c.city,
                    c.customer_type,
                    c.interests,
                    c.tags,
                    c.payment_status,
                    COALESCE(c.crm_meta->>'country', 'CO') AS customer_country,
                    (
                        SELECT MIN(m0.created_at)
                        FROM messages m0
                        WHERE m0.phone = c.phone
                    ) AS first_message_date,
                    (
                        SELECT MAX(m1.created_at)
                        FROM messages m1
                        WHERE m1.phone = c.phone
                    ) AS last_message_date
                FROM conversations c
                WHERE c.phone = :phone
                LIMIT 1
                """
            ),
            {"phone": phone},
        ).mappings().first()

    data = dict(row or {})
    first_name = str(data.get("first_name") or "").strip()
    last_name = str(data.get("last_name") or "").strip()
    full_name = f"{first_name} {last_name}".strip()

    return {
        "nombre": full_name or phone,
        "first_name": first_name,
        "last_name": last_name,
        "city": str(data.get("city") or "").strip(),
        "customer_type": str(data.get("customer_type") or "").strip(),
        "interests": str(data.get("interests") or "").strip(),
        "tags": str(data.get("tags") or "").strip(),
        "payment_status": str(data.get("payment_status") or "").strip(),
        "phone": phone,
        "business_name": str(os.getenv("BUSINESS_NAME", "Verane")).strip(),
        "business_phone": str(os.getenv("BUSINESS_PHONE", "")).strip(),
        "business_email": str(os.getenv("BUSINESS_EMAIL", "")).strip(),
        "assistant_name": str(os.getenv("ASSISTANT_NAME", "Asistente Verane")).strip(),
        "assistant_phone": str(os.getenv("ASSISTANT_PHONE", "")).strip(),
        "customer_name": full_name or phone,
        "customer_phone": phone,
        "customer_tag": str(data.get("tags") or "").strip(),
        "customer_country": str(data.get("customer_country") or "CO").strip(),
        "first_message_date": str(data.get("first_message_date") or "").strip(),
        "last_message_date": str(data.get("last_message_date") or "").strip(),
    }


def _load_template_row(template_id: int = 0, template_name: str = "", channel: str = "whatsapp") -> Dict[str, Any]:
    template_id = int(template_id or 0)
    tname = str(template_name or "").strip()
    ch = str(channel or "whatsapp").strip().lower()
    use_channel_filter = ch not in ("", "all")

    with engine.begin() as conn:
        if template_id > 0:
            if use_channel_filter:
                row = conn.execute(
                    text(
                        """
                        SELECT id, name, body, blocks_json, params_json, variables_json, status, channel
                        FROM message_templates
                        WHERE id = :template_id
                          AND LOWER(COALESCE(channel, 'whatsapp')) = :channel
                        LIMIT 1
                        """
                    ),
                    {"template_id": template_id, "channel": ch},
                ).mappings().first()
            else:
                row = conn.execute(
                    text(
                        """
                        SELECT id, name, body, blocks_json, params_json, variables_json, status, channel
                        FROM message_templates
                        WHERE id = :template_id
                        LIMIT 1
                        """
                    ),
                    {"template_id": template_id},
                ).mappings().first()
            if row:
                return dict(row)

        if tname:
            if use_channel_filter:
                row = conn.execute(
                    text(
                        """
                        SELECT id, name, body, blocks_json, params_json, variables_json, status, channel
                        FROM message_templates
                        WHERE LOWER(name) = :name
                          AND LOWER(COALESCE(channel, 'whatsapp')) = :channel
                        ORDER BY id DESC
                        LIMIT 1
                        """
                    ),
                    {"name": tname.lower(), "channel": ch},
                ).mappings().first()
            else:
                row = conn.execute(
                    text(
                        """
                        SELECT id, name, body, blocks_json, params_json, variables_json, status, channel
                        FROM message_templates
                        WHERE LOWER(name) = :name
                        ORDER BY id DESC
                        LIMIT 1
                        """
                    ),
                    {"name": tname.lower()},
                ).mappings().first()
            if row:
                return dict(row)

    return {}


def _render_template_blocks(template_row: Dict[str, Any], variables: Dict[str, Any]) -> List[Dict[str, Any]]:
    body = str(template_row.get("body") or "")
    blocks = _normalize_template_blocks(template_row.get("blocks_json"), body_fallback=body)
    if not blocks:
        return []

    rendered: List[Dict[str, Any]] = []
    for block in blocks:
        kind = str(block.get("kind") or "text").strip().lower()
        delay_ms = int(block.get("delay_ms") or 0)

        if kind in ("image", "video", "audio"):
            media_url_key = "image_url" if kind == "image" else ("video_url" if kind == "video" else "audio_url")
            media_url = str(block.get(media_url_key) or block.get("media_url") or block.get("url") or "").strip()
            out_block = {
                "kind": kind,
                "media_id": str(block.get("media_id") or "").strip(),
                media_url_key: media_url,
                "delay_ms": delay_ms,
            }
            if kind in ("image", "video"):
                out_block["caption"] = _render_template(str(block.get("caption") or ""), variables)
            rendered.append(out_block)
            continue

        rendered.append(
            {
                "kind": "text",
                "text": _render_template(str(block.get("text") or ""), variables),
                "delay_ms": delay_ms,
            }
        )

    return rendered


def _save_out_message(
    *,
    phone: str,
    channel: str,
    msg_type: str,
    text_msg: str,
    media_id: str,
    media_caption: str,
    sent_ok: bool,
    wa_message_id: str,
    wa_error: str,
    ai_meta: Dict[str, Any],
) -> int:
    now = datetime.utcnow()
    with engine.begin() as conn:
        message_id = conn.execute(
            text(
                """
                INSERT INTO messages (
                    phone,
                    channel,
                    direction,
                    msg_type,
                    text,
                    media_id,
                    media_caption,
                    wa_status,
                    wa_message_id,
                    wa_error,
                    wa_ts_sent,
                    ai_meta,
                    created_at
                )
                VALUES (
                    :phone,
                    :channel,
                    'out',
                    :msg_type,
                    :text,
                    :media_id,
                    :media_caption,
                    :wa_status,
                    :wa_message_id,
                    :wa_error,
                    :wa_ts_sent,
                    CAST(:ai_meta AS jsonb),
                    :created_at
                )
                RETURNING id
                """
            ),
            {
                "phone": phone,
                "channel": (channel or "whatsapp").strip().lower() or "whatsapp",
                "msg_type": str(msg_type or "text").strip().lower(),
                "text": text_msg,
                "media_id": media_id or None,
                "media_caption": media_caption or None,
                "wa_status": "sent" if sent_ok else "failed",
                "wa_message_id": wa_message_id or None,
                "wa_error": wa_error or None,
                "wa_ts_sent": now if sent_ok else None,
                "ai_meta": json.dumps(_safe_json_dict(ai_meta), ensure_ascii=False),
                "created_at": now,
            },
        ).scalar()

        conn.execute(
            text(
                """
                INSERT INTO conversations (phone, updated_at)
                VALUES (:phone, :updated_at)
                ON CONFLICT (phone)
                DO UPDATE SET updated_at = EXCLUDED.updated_at
                """
            ),
            {"phone": phone, "updated_at": now},
        )

    try:
        return int(message_id)
    except Exception:
        return 0


async def _send_template_blocks(
    *,
    phone: str,
    channel: str,
    blocks: List[Dict[str, Any]],
    ai_meta_base: Dict[str, Any],
) -> Dict[str, Any]:
    sent_messages = 0
    failed_messages = 0
    local_message_ids: List[int] = []
    wa_message_ids: List[str] = []
    errors: List[str] = []

    for idx, block in enumerate(blocks):
        kind = str(block.get("kind") or "text").strip().lower()
        delay_ms = int(block.get("delay_ms") or 0)
        msg_type = kind if kind in ("image", "video", "audio") else "text"

        block_text = ""
        media_id = ""
        media_caption = ""
        media_url = ""

        try:
            if kind in ("image", "video", "audio"):
                media_id = str(block.get("media_id") or "").strip()
                media_url = str(
                    block.get(f"{kind}_url")
                    or block.get("media_url")
                    or block.get("url")
                    or ""
                ).strip()
                media_caption = str(block.get("caption") or "").strip() if kind in ("image", "video") else ""
                if not media_id and not media_url:
                    raise RuntimeError(f"{kind} block without media_id/media_url")
                wa = await send_channel_media(
                    channel=channel,
                    to=phone,
                    media_type=kind,
                    media_id=media_id,
                    media_url=media_url,
                    caption=media_caption,
                )
                block_text = media_caption or f"[{kind}]"
            else:
                block_text = str(block.get("text") or "").strip()
                if not block_text:
                    raise RuntimeError("text block empty")
                wa = await send_channel_text(channel, phone, block_text)
        except Exception as e:
            err = str(e)[:900]
            failed_messages += 1
            errors.append(err)
            message_id = _save_out_message(
                phone=phone,
                channel=channel,
                msg_type=msg_type,
                text_msg=block_text,
                media_id=media_id,
                media_caption=media_caption,
                sent_ok=False,
                wa_message_id="",
                wa_error=err,
                ai_meta={**ai_meta_base, "block_index": idx},
            )
            if message_id > 0:
                local_message_ids.append(message_id)
            continue

        ok = bool((wa or {}).get("sent"))
        wa_id = str(
            (wa or {}).get("wa_message_id")
            or (wa or {}).get("provider_message_id")
            or ""
        ).strip()
        wa_err = str((wa or {}).get("reason") or (wa or {}).get("whatsapp_body") or "")[:900]

        message_id = _save_out_message(
            phone=phone,
            channel=channel,
            msg_type=msg_type,
            text_msg=block_text,
            media_id=media_id,
            media_caption=media_caption,
            sent_ok=ok,
            wa_message_id=wa_id,
            wa_error=wa_err,
            ai_meta={**ai_meta_base, "block_index": idx},
        )

        if message_id > 0:
            local_message_ids.append(message_id)
        if wa_id:
            wa_message_ids.append(wa_id)

        if ok:
            sent_messages += 1
        else:
            failed_messages += 1
            if wa_err:
                errors.append(wa_err)

        if idx < len(blocks) - 1 and delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)

    return {
        "sent_messages": sent_messages,
        "failed_messages": failed_messages,
        "local_message_ids": local_message_ids,
        "wa_message_ids": wa_message_ids,
        "errors": errors,
    }


async def send_template_to_phone(
    *,
    phone: str,
    template_id: int = 0,
    template_name: str = "",
    trigger_id: int = 0,
    source: str = "trigger",
    channel: str = "whatsapp",
    overrides: Dict[str, Any] | None = None,
    extra_meta: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    p = str(phone or "").strip()
    if not p:
        return {"ok": False, "error": "phone_required", "sent_messages": 0}

    tpl = _load_template_row(template_id=template_id, template_name=template_name, channel=channel)
    if not tpl:
        return {"ok": False, "error": "template_not_found", "sent_messages": 0}

    vars_map = _recipient_variables(p)

    defaults = _safe_json_dict(tpl.get("params_json"))
    for key, value in defaults.items():
        k = str(key or "").strip()
        if not k:
            continue
        if k not in vars_map or str(vars_map.get(k) or "").strip() == "":
            vars_map[k] = value

    for key, value in _safe_json_dict(overrides).items():
        k = str(key or "").strip()
        if not k:
            continue
        vars_map[k] = value

    rendered_blocks = _render_template_blocks(tpl, vars_map)
    if not rendered_blocks:
        return {"ok": False, "error": "template_empty", "sent_messages": 0}

    ai_meta_base = {
        "source": str(source or "trigger"),
        "trigger_id": int(trigger_id or 0) if int(trigger_id or 0) > 0 else None,
        "template_id": int(tpl.get("id") or 0),
        "template_name": str(tpl.get("name") or "").strip(),
        "channel": str(tpl.get("channel") or channel or "whatsapp").strip().lower(),
    }
    ai_meta_base.update(_safe_json_dict(extra_meta))

    send_result = await _send_template_blocks(
        phone=p,
        channel=channel,
        blocks=rendered_blocks,
        ai_meta_base=ai_meta_base,
    )
    ok = int(send_result.get("sent_messages") or 0) > 0 and int(send_result.get("failed_messages") or 0) == 0

    return {
        "ok": ok,
        "template_id": int(tpl.get("id") or 0),
        "template_name": str(tpl.get("name") or "").strip(),
        **send_result,
    }


def _current_conversation(phone: str) -> Dict[str, Any]:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT
                    phone,
                    takeover,
                    ai_state,
                    tags,
                    customer_type,
                    payment_status,
                    crm_meta
                FROM conversations
                WHERE phone = :phone
                LIMIT 1
                """
            ),
            {"phone": phone},
        ).mappings().first()
    return dict(row or {})


def _resolve_template_id(template_id: int, template_name: str, channel: str = "whatsapp") -> int:
    tid = int(template_id or 0)
    if tid > 0:
        return tid
    row = _load_template_row(template_id=0, template_name=template_name, channel=channel)
    try:
        return int(row.get("id") or 0)
    except Exception:
        return 0


def _condition_check_words(user_text: str, cond: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    words_raw = cond.get("words")
    if not isinstance(words_raw, list):
        words_raw = []

    if not words_raw:
        single = str(cond.get("word") or cond.get("contains") or "").strip()
        if single:
            words_raw = [single]

    words = [_norm_text(str(x)) for x in words_raw if str(x or "").strip()]
    words = [w for w in words if w]
    if not words:
        return False, {"reason": "empty_words"}

    text_norm = _norm_text(user_text)
    hits = [w for w in words if w in text_norm]

    mode = str(cond.get("mode") or "any").strip().lower()
    if mode == "all":
        ok = all(w in text_norm for w in words)
    else:
        ok = len(hits) > 0

    return ok, {"hits": hits, "mode": mode, "words": words}


def _condition_template_sent_status(phone: str, cond: Dict[str, Any], channel: str = "whatsapp") -> Tuple[bool, Dict[str, Any]]:
    ch = str(channel or "whatsapp").strip().lower()
    template_id = _resolve_template_id(int(cond.get("template_id") or 0), str(cond.get("template_name") or ""), channel=ch)
    template_name = str(cond.get("template_name") or "").strip().lower()

    state = str(cond.get("state") or cond.get("sent_state") or "not_sent").strip().lower()
    if state in ("no enviado", "no_enviado", "not-sent"):
        state = "not_sent"
    if state in ("enviado",):
        state = "sent"

    try:
        window_days = int(cond.get("window_days") or 365)
    except Exception:
        window_days = 365
    window_days = max(1, min(window_days, 3650))
    since = datetime.utcnow() - timedelta(days=window_days)

    message_exists = False
    campaign_exists = False

    with engine.begin() as conn:
        if template_id > 0:
            row = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM messages
                    WHERE phone = :phone
                      AND LOWER(COALESCE(channel, 'whatsapp')) = :channel
                      AND direction = 'out'
                      AND created_at >= :since
                      AND (
                            COALESCE(ai_meta->>'template_id', '') = :template_id_txt
                            OR LOWER(COALESCE(ai_meta->>'template_name', '')) = :template_name
                      )
                    LIMIT 1
                    """
                ),
                {
                    "phone": phone,
                    "channel": ch,
                    "since": since,
                    "template_id_txt": str(template_id),
                    "template_name": template_name,
                },
            ).first()
            message_exists = bool(row)

            crow = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM campaign_recipients cr
                    JOIN campaigns c ON c.id = cr.campaign_id
                    WHERE cr.phone = :phone
                      AND LOWER(COALESCE(c.channel, 'whatsapp')) = :channel
                      AND c.template_id = :template_id
                      AND LOWER(COALESCE(cr.status, '')) IN ('sent', 'delivered', 'read', 'replied')
                      AND COALESCE(cr.sent_at, cr.created_at) >= :since
                    LIMIT 1
                    """
                ),
                {
                    "phone": phone,
                    "channel": ch,
                    "template_id": template_id,
                    "since": since,
                },
            ).first()
            campaign_exists = bool(crow)
        elif template_name:
            row = conn.execute(
                text(
                    """
                    SELECT 1
                    FROM messages
                    WHERE phone = :phone
                      AND LOWER(COALESCE(channel, 'whatsapp')) = :channel
                      AND direction = 'out'
                      AND created_at >= :since
                      AND LOWER(COALESCE(ai_meta->>'template_name', '')) = :template_name
                    LIMIT 1
                    """
                ),
                {
                    "phone": phone,
                    "channel": ch,
                    "since": since,
                    "template_name": template_name,
                },
            ).first()
            message_exists = bool(row)

    sent_exists = bool(message_exists or campaign_exists)
    ok = sent_exists if state == "sent" else (not sent_exists)

    return ok, {
        "sent_exists": sent_exists,
        "state": state,
        "template_id": template_id,
        "template_name": template_name,
    }


def _condition_current_tag(phone: str, cond: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    tag = _norm_text(str(cond.get("tag") or ""))
    if not tag:
        return False, {"reason": "empty_tag"}

    state = str(cond.get("state") or "has").strip().lower()
    if state in ("no", "not", "without", "not_has"):
        state = "not_has"
    else:
        state = "has"

    conv = _current_conversation(phone)
    tags = _split_tags(str(conv.get("tags") or ""))
    has = tag in tags

    return (has if state == "has" else not has), {"has": has, "state": state, "tag": tag}


def _condition_last_message_sent(phone: str, cond: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    try:
        value = float(cond.get("value") or cond.get("minutes") or 0)
    except Exception:
        value = 0.0
    value = max(0.0, min(value, 525600.0))
    op = str(cond.get("op") or "gte").strip().lower()

    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT MAX(created_at) AS last_out
                FROM messages
                WHERE phone = :phone
                  AND direction = 'out'
                """
            ),
            {"phone": phone},
        ).mappings().first()

    last_out = (row or {}).get("last_out")
    if isinstance(last_out, datetime):
        minutes_since = max(0.0, (datetime.utcnow() - last_out).total_seconds() / 60.0)
    else:
        minutes_since = 999999.0

    ok = _compare_numbers(minutes_since, op, value)
    return ok, {"minutes_since": minutes_since, "op": op, "value": value}


def _condition_sent_count(phone: str, cond: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    try:
        value = float(cond.get("value") or cond.get("count") or 0)
    except Exception:
        value = 0.0
    value = max(0.0, min(value, 100000.0))
    op = str(cond.get("op") or "gte").strip().lower()

    try:
        window_hours = int(cond.get("window_hours") or 24)
    except Exception:
        window_hours = 24
    window_hours = max(1, min(window_hours, 24 * 180))

    since = datetime.utcnow() - timedelta(hours=window_hours)
    with engine.begin() as conn:
        count = conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM messages
                WHERE phone = :phone
                  AND direction = 'out'
                  AND created_at >= :since
                """
            ),
            {"phone": phone, "since": since},
        ).scalar()

    current = float(count or 0)
    ok = _compare_numbers(current, op, value)
    return ok, {"count": current, "op": op, "value": value, "window_hours": window_hours}


def _parse_hhmm_to_minutes(raw: str, default_minutes: int) -> int:
    txt = str(raw or "").strip()
    if not txt:
        return default_minutes
    m = re.match(r"^(\d{1,2}):(\d{2})$", txt)
    if not m:
        return default_minutes
    try:
        hh = int(m.group(1))
        mm = int(m.group(2))
    except Exception:
        return default_minutes
    if hh < 0 or hh > 23 or mm < 0 or mm > 59:
        return default_minutes
    return hh * 60 + mm


def _condition_schedule(cond: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
    tz_name = str(cond.get("timezone") or os.getenv("TZ") or "America/Bogota").strip()
    try:
        tz = ZoneInfo(tz_name)
    except Exception:
        tz = ZoneInfo("America/Bogota")
        tz_name = "America/Bogota"

    now_local = datetime.now(tz)

    days = cond.get("days")
    day_tokens: List[str] = []
    if isinstance(days, list):
        day_tokens = [str(x or "").strip().lower()[:3] for x in days if str(x or "").strip()]

    if not day_tokens:
        day_str = str(cond.get("day") or "").strip().lower()
        if day_str:
            day_tokens = [d.strip().lower()[:3] for d in day_str.split(",") if d.strip()]

    week_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
    current_day = week_days[now_local.weekday()]

    if day_tokens and current_day not in day_tokens:
        return False, {"reason": "day_not_allowed", "current_day": current_day, "days": day_tokens, "timezone": tz_name}

    start_minutes = _parse_hhmm_to_minutes(str(cond.get("start_time") or ""), int(cond.get("start_hour") or 0) * 60)
    end_minutes = _parse_hhmm_to_minutes(str(cond.get("end_time") or ""), int(cond.get("end_hour") or 23) * 60 + 59)
    now_minutes = now_local.hour * 60 + now_local.minute

    if start_minutes <= end_minutes:
        in_window = start_minutes <= now_minutes <= end_minutes
    else:
        in_window = now_minutes >= start_minutes or now_minutes <= end_minutes

    return in_window, {
        "timezone": tz_name,
        "current_day": current_day,
        "days": day_tokens,
        "start_minutes": start_minutes,
        "end_minutes": end_minutes,
        "now_minutes": now_minutes,
    }


def _normalize_conditions_payload(conditions_json: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    root = _safe_json_dict(conditions_json)
    mode = str(root.get("match") or root.get("mode") or "all").strip().lower()
    if mode not in ("all", "any"):
        mode = "all"

    conditions = _safe_json_list(root.get("conditions"))
    if not conditions:
        maybe_all = root.get("all")
        if isinstance(maybe_all, list):
            conditions = maybe_all

    if not conditions:
        if "contains" in root:
            conditions = [{"type": "check_words", "words": [str(root.get("contains") or "")]}]
        elif "template_id" in root and "state" in root:
            conditions = [{"type": "template_sent_status", **root}]

    out = [c for c in conditions if isinstance(c, dict)]
    return mode, out


def _normalize_actions_payload(action_json: Dict[str, Any]) -> List[Dict[str, Any]]:
    root = _safe_json_dict(action_json)
    actions = _safe_json_list(root.get("actions"))
    if not actions:
        maybe_list = root.get("list")
        if isinstance(maybe_list, list):
            actions = maybe_list

    if not actions and root.get("type"):
        actions = [root]

    return [a for a in actions if isinstance(a, dict)]


def _evaluate_conditions(
    phone: str,
    user_text: str,
    conditions_json: Dict[str, Any],
    *,
    channel: str = "whatsapp",
) -> Tuple[bool, List[Dict[str, Any]]]:
    mode, conditions = _normalize_conditions_payload(conditions_json)
    if not conditions:
        return True, []

    evals: List[Dict[str, Any]] = []

    for cond in conditions:
        ctype = str(cond.get("type") or "").strip().lower()
        ok = False
        info: Dict[str, Any] = {}

        if ctype == "check_words":
            ok, info = _condition_check_words(user_text, cond)
        elif ctype == "template_sent_status":
            ok, info = _condition_template_sent_status(phone, cond, channel=channel)
        elif ctype == "current_tag":
            ok, info = _condition_current_tag(phone, cond)
        elif ctype == "last_message_sent":
            ok, info = _condition_last_message_sent(phone, cond)
        elif ctype == "sent_count":
            ok, info = _condition_sent_count(phone, cond)
        elif ctype == "schedule":
            ok, info = _condition_schedule(cond)
        else:
            info = {"reason": "unknown_condition_type"}

        evals.append({"type": ctype or "unknown", "ok": bool(ok), "info": info})

    if mode == "any":
        match = any(x.get("ok") is True for x in evals)
    else:
        match = all(x.get("ok") is True for x in evals)

    return bool(match), evals


def _get_admin_phones(default_phone: str = "") -> List[str]:
    raw = str(os.getenv("TRIGGER_ADMIN_PHONES", "") or os.getenv("ADMIN_NOTIFY_PHONES", "")).strip()
    if not raw and default_phone:
        return [default_phone]
    out: List[str] = []
    seen = set()
    for token in raw.split(","):
        p = re.sub(r"\s+", "", str(token or ""))
        if not p or p in seen:
            continue
        seen.add(p)
        out.append(p)
    return out


def _touch_trigger_last_run(trigger_id: int) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE automation_triggers
                SET last_run_at = NOW(),
                    updated_at = NOW()
                WHERE id = :trigger_id
                """
            ),
            {"trigger_id": int(trigger_id)},
        )


def _insert_trigger_execution(
    *,
    trigger_id: int,
    phone: str,
    status: str,
    error: str,
    details: Dict[str, Any],
) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                INSERT INTO trigger_executions (
                    trigger_id,
                    phone,
                    status,
                    executed_at,
                    error,
                    details
                )
                VALUES (
                    :trigger_id,
                    :phone,
                    :status,
                    NOW(),
                    :error,
                    CAST(:details AS jsonb)
                )
                """
            ),
            {
                "trigger_id": int(trigger_id),
                "phone": phone,
                "status": str(status or "ok")[:32],
                "error": (error or "")[:900] or None,
                "details": json.dumps(_safe_json_dict(details), ensure_ascii=False),
            },
        )


def _is_trigger_in_cooldown(trigger_id: int, phone: str, cooldown_minutes: int) -> bool:
    minutes = max(0, int(cooldown_minutes or 0))
    if minutes <= 0:
        return False

    since = datetime.utcnow() - timedelta(minutes=minutes)
    with engine.begin() as conn:
        row = conn.execute(
            text(
                """
                SELECT 1
                FROM trigger_executions
                WHERE trigger_id = :trigger_id
                  AND phone = :phone
                  AND executed_at >= :since
                LIMIT 1
                """
            ),
            {
                "trigger_id": int(trigger_id),
                "phone": phone,
                "since": since,
            },
        ).first()
    return bool(row)


def _trigger_matches_event(trigger_row: Dict[str, Any], event_kind: str) -> bool:
    trigger_type = str(trigger_row.get("trigger_type") or "message_flow").strip().lower()
    flow_event = str(trigger_row.get("flow_event") or "received").strip().lower()
    event_type = str(trigger_row.get("event_type") or "message_in").strip().lower()
    ek = str(event_kind or "received").strip().lower()

    if trigger_type in ("none", "tag_changed"):
        return False

    if trigger_type == "message_flow":
        if ek == "received" and flow_event not in ("received", "both", "all"):
            return False
        if ek == "sent" and flow_event not in ("sent", "both", "all"):
            return False

    if ek == "sent":
        outgoing_event_types = {
            "",
            "message_out",
            "outbound",
            "outgoing",
            "sent",
            "message",
            "all",
            "*",
        }
        if event_type in outgoing_event_types:
            return True
        if "message" in event_type and "out" in event_type:
            return True
        return False

    incoming_event_types = {
        "",
        "message_in",
        "inbound",
        "incoming",
        "received",
        "message",
        "all",
        "*",
    }
    if event_type in incoming_event_types:
        return True
    if "message" in event_type and "in" in event_type:
        return True

    return False


def _parse_run_at(raw: str) -> datetime | None:
    txt = str(raw or "").strip()
    if not txt:
        return None
    try:
        dt = datetime.fromisoformat(txt.replace("Z", "+00:00"))
    except Exception:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(tz=None).replace(tzinfo=None)
    return dt


async def _action_change_tag(phone: str, action: Dict[str, Any]) -> Dict[str, Any]:
    mode = str(action.get("mode") or "add").strip().lower()
    tags_raw = action.get("tags")
    tags_to_apply: List[str] = []

    if isinstance(tags_raw, list):
        tags_to_apply = [str(x or "").strip() for x in tags_raw if str(x or "").strip()]
    elif isinstance(tags_raw, str):
        tags_to_apply = [x.strip() for x in tags_raw.split(",") if x.strip()]

    single_tag = str(action.get("tag") or "").strip()
    if single_tag:
        tags_to_apply.append(single_tag)

    tags_to_apply = [_norm_text(x) for x in tags_to_apply if _norm_text(x)]
    tags_to_apply = list(dict.fromkeys(tags_to_apply))

    if not tags_to_apply and mode != "set":
        return {"ok": False, "error": "empty_tag"}

    conv = _current_conversation(phone)
    current_tags = _split_tags(str(conv.get("tags") or ""))

    if mode == "remove":
        new_tags = [t for t in current_tags if t not in set(tags_to_apply)]
    elif mode == "set":
        new_tags = tags_to_apply
    else:
        merged = current_tags[:]
        for t in tags_to_apply:
            if t not in merged:
                merged.append(t)
        new_tags = merged

    tags_csv = _join_tags(new_tags)

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE conversations
                SET tags = :tags,
                    updated_at = NOW()
                WHERE phone = :phone
                """
            ),
            {"phone": phone, "tags": tags_csv},
        )

    return {"ok": True, "tags": new_tags, "mode": mode}


async def _action_configure_conversation(phone: str, action: Dict[str, Any]) -> Dict[str, Any]:
    takeover_raw = action.get("takeover")
    ai_state = str(action.get("ai_state") or "").strip()
    clear_ai_state = bool(action.get("clear_ai_state"))

    sets: List[str] = ["updated_at = NOW()"]
    params: Dict[str, Any] = {"phone": phone}

    if isinstance(takeover_raw, bool):
        sets.append("takeover = :takeover")
        params["takeover"] = takeover_raw
    elif isinstance(takeover_raw, str):
        token = takeover_raw.strip().lower()
        if token in ("on", "true", "1", "yes"):
            sets.append("takeover = TRUE")
        elif token in ("off", "false", "0", "no"):
            sets.append("takeover = FALSE")

    if clear_ai_state:
        sets.append("ai_state = NULL")
    elif ai_state:
        sets.append("ai_state = :ai_state")
        params["ai_state"] = ai_state

    with engine.begin() as conn:
        conn.execute(text(f"""
            UPDATE conversations
            SET {", ".join(sets)}
            WHERE phone = :phone
        """), params)

    return {
        "ok": True,
        "takeover": params.get("takeover", takeover_raw),
        "ai_state": None if clear_ai_state else (ai_state or None),
    }


async def _action_change_contact_status(phone: str, action: Dict[str, Any]) -> Dict[str, Any]:
    status = str(action.get("status") or "").strip()
    if not status:
        return {"ok": False, "error": "status_required"}

    field_name = str(action.get("field") or "customer_type").strip().lower()
    if field_name not in ("customer_type", "payment_status"):
        field_name = "customer_type"

    with engine.begin() as conn:
        conn.execute(
            text(
                f"""
                UPDATE conversations
                SET {field_name} = :status,
                    updated_at = NOW()
                WHERE phone = :phone
                """
            ),
            {"phone": phone, "status": status},
        )

    if field_name == "customer_type":
        update_crm_fields(phone, tags_add=[f"estado:{status.lower()}"])

    return {"ok": True, "field": field_name, "status": status}


async def _action_notify_admins(phone: str, user_text: str, trigger_name: str, action: Dict[str, Any]) -> Dict[str, Any]:
    phones_value = action.get("phones")
    phone_list: List[str] = []

    if isinstance(phones_value, list):
        phone_list = [str(x or "").strip() for x in phones_value if str(x or "").strip()]
    elif isinstance(phones_value, str):
        phone_list = [x.strip() for x in phones_value.split(",") if x.strip()]

    if not phone_list:
        phone_list = _get_admin_phones(default_phone=phone)

    if not phone_list:
        return {"ok": False, "error": "no_admin_phones"}

    vars_map = _recipient_variables(phone)
    vars_map["incoming_text"] = user_text
    vars_map["trigger_name"] = trigger_name

    body = str(action.get("message") or "").strip()
    if not body:
        body = "Alerta trigger {{trigger_name}} para {{customer_name}} ({{customer_phone}}): {{incoming_text}}"

    rendered = _render_template(body, vars_map)

    sent = 0
    failed = 0
    for admin_phone in phone_list:
        try:
            wa = await send_whatsapp_text(admin_phone, rendered)
            if bool((wa or {}).get("sent")):
                sent += 1
            else:
                failed += 1
        except Exception:
            failed += 1

    return {"ok": sent > 0 and failed == 0, "sent": sent, "failed": failed}


async def _action_extract_conversation_info(phone: str, action: Dict[str, Any]) -> Dict[str, Any]:
    try:
        limit = int(action.get("last_messages") or 10)
    except Exception:
        limit = 10
    limit = max(3, min(limit, 30))

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT direction, msg_type, text, created_at
                FROM messages
                WHERE phone = :phone
                ORDER BY created_at DESC
                LIMIT :limit
                """
            ),
            {"phone": phone, "limit": limit},
        ).mappings().all()

    lines: List[str] = []
    for row in reversed(rows):
        direction = str(row.get("direction") or "").strip().lower()
        prefix = "Cliente" if direction == "in" else "Bot"
        txt = str(row.get("text") or "").strip()
        if not txt:
            continue
        lines.append(f"{prefix}: {txt}")

    summary = " | ".join(lines)[:1200]
    payload = {
        "updated_at": datetime.utcnow().isoformat(),
        "summary": summary,
        "messages_considered": len(rows),
    }

    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE conversations
                SET crm_meta = COALESCE(crm_meta, '{}'::jsonb) || CAST(:patch AS jsonb),
                    updated_at = NOW()
                WHERE phone = :phone
                """
            ),
            {
                "phone": phone,
                "patch": json.dumps({"trigger_extract": payload}, ensure_ascii=False),
            },
        )

    return {"ok": True, "summary_len": len(summary), "messages_considered": len(rows)}


async def _action_schedule_message(
    trigger_id: int,
    phone: str,
    action: Dict[str, Any],
    user_text: str,
    *,
    channel: str = "whatsapp",
) -> Dict[str, Any]:
    ch = str(channel or "whatsapp").strip().lower()
    template_id = _resolve_template_id(
        int(action.get("template_id") or 0),
        str(action.get("template_name") or ""),
        channel=ch,
    )
    if template_id <= 0:
        return {"ok": False, "error": "template_required"}

    run_at = _parse_run_at(str(action.get("run_at") or ""))
    if run_at is None:
        try:
            delay_minutes = int(action.get("delay_minutes") or 0)
        except Exception:
            delay_minutes = 0
        delay_minutes = max(0, min(delay_minutes, 60 * 24 * 30))
        run_at = datetime.utcnow() + timedelta(minutes=delay_minutes)

    payload = {
        "source": "trigger",
        "trigger_id": int(trigger_id or 0),
        "channel": ch,
        "template_id": int(template_id),
        "template_name": str(action.get("template_name") or "").strip(),
        "overrides": _safe_json_dict(action.get("overrides")),
        "trigger_message_text": user_text,
    }

    with engine.begin() as conn:
        scheduled_id = conn.execute(
            text(
                """
                INSERT INTO trigger_scheduled_messages (
                    trigger_id,
                    phone,
                    template_id,
                    payload_json,
                    run_at,
                    status,
                    attempts,
                    created_at
                )
                VALUES (
                    :trigger_id,
                    :phone,
                    :template_id,
                    CAST(:payload_json AS jsonb),
                    :run_at,
                    'pending',
                    0,
                    NOW()
                )
                RETURNING id
                """
            ),
            {
                "trigger_id": int(trigger_id or 0) or None,
                "phone": phone,
                "template_id": int(template_id),
                "payload_json": json.dumps(payload, ensure_ascii=False),
                "run_at": run_at,
            },
        ).scalar()

    try:
        scheduled_id = int(scheduled_id or 0)
    except Exception:
        scheduled_id = 0

    return {
        "ok": scheduled_id > 0,
        "scheduled_id": scheduled_id,
        "run_at": run_at.isoformat(),
        "template_id": template_id,
    }


async def _execute_trigger_assistant(
    *,
    phone: str,
    user_text: str,
    assistant_enabled: bool,
    assistant_message_type: str,
) -> Dict[str, Any]:
    if not assistant_enabled:
        return {"ok": True, "enabled": False, "sent": False}

    text_in = str(user_text or "").strip()
    if not text_in:
        return {"ok": False, "enabled": True, "sent": False, "error": "empty_user_text"}

    meta = build_ai_meta(phone, text_in)
    ai_result = await process_message(phone=phone, text=text_in, meta=meta)
    reply_text = str(ai_result.get("reply_text") or "").strip()
    if not reply_text:
        return {"ok": False, "enabled": True, "sent": False, "error": "empty_reply"}

    mtype = str(assistant_message_type or "auto").strip().lower()
    if mtype not in ("auto", "text", "audio"):
        mtype = "auto"

    if mtype == "audio":
        send_result = await send_ai_reply_as_voice(phone, reply_text)
        return {
            "ok": bool(send_result.get("sent")),
            "enabled": True,
            "sent": bool(send_result.get("sent")),
            "mode": "audio",
            "wa": send_result.get("wa") or {},
        }

    if mtype == "auto":
        voice = _get_voice_settings()
        if bool(voice.get("voice_enabled")) and bool(voice.get("voice_prefer_voice")):
            send_result = await send_ai_reply_as_voice(phone, reply_text)
            return {
                "ok": bool(send_result.get("sent")),
                "enabled": True,
                "sent": bool(send_result.get("sent")),
                "mode": "audio",
                "wa": send_result.get("wa") or {},
            }

    send_result = await send_ai_reply_in_chunks(phone, reply_text)
    return {
        "ok": bool(send_result.get("sent")),
        "enabled": True,
        "sent": bool(send_result.get("sent")),
        "mode": "text",
        "chunks_sent": int(send_result.get("chunks_sent") or 0),
        "wa_last": send_result.get("last_wa") or {},
    }


async def _execute_actions(
    *,
    trigger_row: Dict[str, Any],
    phone: str,
    user_text: str,
) -> Dict[str, Any]:
    trigger_id = int(trigger_row.get("id") or 0)
    trigger_name = str(trigger_row.get("name") or "").strip()
    trigger_channel = str(trigger_row.get("channel") or "whatsapp").strip().lower() or "whatsapp"

    actions = _normalize_actions_payload(_safe_json_dict(trigger_row.get("action_json")))
    action_results: List[Dict[str, Any]] = []

    sent_messages = 0
    failed_actions = 0

    for idx, action in enumerate(actions):
        atype = str(action.get("type") or "").strip().lower()

        try:
            if atype == "send_template":
                result = await send_template_to_phone(
                    phone=phone,
                    template_id=int(action.get("template_id") or 0),
                    template_name=str(action.get("template_name") or ""),
                    trigger_id=trigger_id,
                    source="trigger",
                    channel=trigger_channel,
                    overrides=_safe_json_dict(action.get("overrides")),
                    extra_meta={"action_index": idx, "action_type": atype},
                )
                sent_messages += int(result.get("sent_messages") or 0)

            elif atype == "change_tag":
                result = await _action_change_tag(phone, action)

            elif atype == "configure_conversation":
                result = await _action_configure_conversation(phone, action)

            elif atype == "change_contact_status":
                result = await _action_change_contact_status(phone, action)

            elif atype == "notify_admins":
                result = await _action_notify_admins(phone, user_text, trigger_name, action)

            elif atype == "extract_conversation_info":
                result = await _action_extract_conversation_info(phone, action)

            elif atype == "schedule_message":
                result = await _action_schedule_message(
                    trigger_id,
                    phone,
                    action,
                    user_text,
                    channel=trigger_channel,
                )

            else:
                result = {"ok": False, "error": "unknown_action_type"}

        except Exception as e:
            result = {"ok": False, "error": str(e)[:900]}

        if result.get("ok") is not True:
            failed_actions += 1

        action_results.append(
            {
                "type": atype or "unknown",
                "ok": bool(result.get("ok") is True),
                "result": result,
            }
        )

    assistant_result = await _execute_trigger_assistant(
        phone=phone,
        user_text=user_text,
        assistant_enabled=bool(trigger_row.get("assistant_enabled")),
        assistant_message_type=str(trigger_row.get("assistant_message_type") or "auto"),
    )

    if assistant_result.get("ok") is not True and assistant_result.get("enabled"):
        failed_actions += 1

    ok = failed_actions == 0

    return {
        "ok": ok,
        "actions_total": len(actions),
        "failed_actions": failed_actions,
        "sent_messages": sent_messages,
        "assistant": assistant_result,
        "actions": action_results,
    }


async def execute_incoming_triggers(
    *,
    phone: str,
    user_text: str,
    msg_type: str,
    channel: str = "whatsapp",
) -> Dict[str, Any]:
    p = str(phone or "").strip()
    if not p:
        return {"ok": False, "matched": False, "block_ai": False, "reason": "phone_required"}
    ch = str(channel or "whatsapp").strip().lower() or "whatsapp"

    ensure_conversation_row(p)

    with engine.begin() as conn:
        conv = conn.execute(
            text(
                """
                SELECT takeover
                FROM conversations
                WHERE phone = :phone
                LIMIT 1
                """
            ),
            {"phone": p},
        ).mappings().first()

        rows = conn.execute(
            text(
                """
                SELECT
                    id,
                    name,
                    channel,
                    event_type,
                    trigger_type,
                    flow_event,
                    conditions_json,
                    action_json,
                    cooldown_minutes,
                    assistant_enabled,
                    assistant_message_type,
                    priority,
                    block_ai,
                    stop_on_match,
                    only_when_no_takeover
                FROM automation_triggers
                WHERE is_active = TRUE
                  AND LOWER(COALESCE(channel, 'whatsapp')) = :channel
                ORDER BY priority ASC, id ASC
                """
            ),
            {"channel": ch},
        ).mappings().all()

    takeover_on = bool((conv or {}).get("takeover") is True)

    matched = False
    blocked_ai = False
    sent_any = False
    details: List[Dict[str, Any]] = []

    normalized_msg_type = str(msg_type or "text").strip().lower()
    if normalized_msg_type == "unknown":
        normalized_msg_type = "text"

    for row in rows:
        trigger = dict(row or {})
        trigger_id = int(trigger.get("id") or 0)

        if trigger_id <= 0:
            continue
        if not _trigger_matches_event(trigger, "received"):
            continue

        if bool(trigger.get("only_when_no_takeover")) and takeover_on:
            details.append({"trigger_id": trigger_id, "name": trigger.get("name"), "skipped": "takeover_on"})
            continue

        cooldown = int(trigger.get("cooldown_minutes") or 0)
        if _is_trigger_in_cooldown(trigger_id, p, cooldown):
            details.append({"trigger_id": trigger_id, "name": trigger.get("name"), "skipped": "cooldown"})
            continue

        conditions_ok, condition_evals = _evaluate_conditions(
            p,
            user_text,
            _safe_json_dict(trigger.get("conditions_json")),
            channel=ch,
        )

        if not conditions_ok:
            details.append(
                {
                    "trigger_id": trigger_id,
                    "name": trigger.get("name"),
                    "matched": False,
                    "conditions": condition_evals,
                }
            )
            continue

        matched = True

        try:
            action_result = await _execute_actions(
                trigger_row=trigger,
                phone=p,
                user_text=user_text,
            )
            status = "ok" if action_result.get("ok") is True else "error"
            error = "" if status == "ok" else "actions_failed"

            sent_messages = int(action_result.get("sent_messages") or 0)
            assistant_sent = bool(_safe_json_dict(action_result.get("assistant")).get("sent"))
            sent_now = sent_messages > 0 or assistant_sent
            sent_any = sent_any or sent_now

            should_block = bool(trigger.get("block_ai")) and status == "ok"
            if should_block:
                blocked_ai = True

            execution_details = {
                "message_type": normalized_msg_type,
                "conditions": condition_evals,
                "result": action_result,
                "blocked_ai": should_block,
            }
            _insert_trigger_execution(
                trigger_id=trigger_id,
                phone=p,
                status=status,
                error=error,
                details=execution_details,
            )
            _touch_trigger_last_run(trigger_id)

            details.append(
                {
                    "trigger_id": trigger_id,
                    "name": trigger.get("name"),
                    "matched": True,
                    "status": status,
                    "blocked_ai": should_block,
                    "sent": sent_now,
                    "conditions": condition_evals,
                    "actions": action_result.get("actions") or [],
                }
            )

        except Exception as e:
            _insert_trigger_execution(
                trigger_id=trigger_id,
                phone=p,
                status="error",
                error=str(e)[:900],
                details={
                    "message_type": normalized_msg_type,
                    "conditions": condition_evals,
                },
            )
            details.append(
                {
                    "trigger_id": trigger_id,
                    "name": trigger.get("name"),
                    "matched": True,
                    "status": "error",
                    "error": str(e)[:300],
                    "conditions": condition_evals,
                }
            )

        if bool(trigger.get("stop_on_match")):
            break

    return {
        "ok": True,
        "matched": matched,
        "block_ai": blocked_ai,
        "sent": sent_any,
        "details": details,
    }


async def execute_outgoing_triggers(
    *,
    phone: str,
    user_text: str,
    msg_type: str,
    channel: str = "whatsapp",
) -> Dict[str, Any]:
    p = str(phone or "").strip()
    if not p:
        return {"ok": False, "matched": False, "sent": False, "reason": "phone_required"}
    ch = str(channel or "whatsapp").strip().lower() or "whatsapp"

    ensure_conversation_row(p)

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    id,
                    name,
                    channel,
                    event_type,
                    trigger_type,
                    flow_event,
                    conditions_json,
                    action_json,
                    cooldown_minutes,
                    assistant_enabled,
                    assistant_message_type,
                    priority,
                    block_ai,
                    stop_on_match,
                    only_when_no_takeover
                FROM automation_triggers
                WHERE is_active = TRUE
                  AND LOWER(COALESCE(channel, 'whatsapp')) = :channel
                ORDER BY priority ASC, id ASC
                """
            ),
            {"channel": ch},
        ).mappings().all()

    matched = False
    sent_any = False
    details: List[Dict[str, Any]] = []

    normalized_msg_type = str(msg_type or "text").strip().lower()
    if normalized_msg_type == "unknown":
        normalized_msg_type = "text"

    for row in rows:
        trigger = dict(row or {})
        trigger_id = int(trigger.get("id") or 0)

        if trigger_id <= 0:
            continue
        if not _trigger_matches_event(trigger, "sent"):
            continue

        cooldown = int(trigger.get("cooldown_minutes") or 0)
        if _is_trigger_in_cooldown(trigger_id, p, cooldown):
            details.append({"trigger_id": trigger_id, "name": trigger.get("name"), "skipped": "cooldown"})
            continue

        conditions_ok, condition_evals = _evaluate_conditions(
            p,
            user_text,
            _safe_json_dict(trigger.get("conditions_json")),
            channel=ch,
        )
        if not conditions_ok:
            details.append(
                {
                    "trigger_id": trigger_id,
                    "name": trigger.get("name"),
                    "matched": False,
                    "conditions": condition_evals,
                }
            )
            continue

        matched = True

        try:
            action_result = await _execute_actions(
                trigger_row=trigger,
                phone=p,
                user_text=user_text,
            )
            status = "ok" if action_result.get("ok") is True else "error"
            error = "" if status == "ok" else "actions_failed"

            sent_messages = int(action_result.get("sent_messages") or 0)
            assistant_sent = bool(_safe_json_dict(action_result.get("assistant")).get("sent"))
            sent_now = sent_messages > 0 or assistant_sent
            sent_any = sent_any or sent_now

            execution_details = {
                "message_type": normalized_msg_type,
                "conditions": condition_evals,
                "result": action_result,
                "event_kind": "sent",
            }
            _insert_trigger_execution(
                trigger_id=trigger_id,
                phone=p,
                status=status,
                error=error,
                details=execution_details,
            )
            _touch_trigger_last_run(trigger_id)

            details.append(
                {
                    "trigger_id": trigger_id,
                    "name": trigger.get("name"),
                    "matched": True,
                    "status": status,
                    "sent": sent_now,
                    "conditions": condition_evals,
                    "actions": action_result.get("actions") or [],
                }
            )

        except Exception as e:
            _insert_trigger_execution(
                trigger_id=trigger_id,
                phone=p,
                status="error",
                error=str(e)[:900],
                details={
                    "message_type": normalized_msg_type,
                    "conditions": condition_evals,
                    "event_kind": "sent",
                },
            )
            details.append(
                {
                    "trigger_id": trigger_id,
                    "name": trigger.get("name"),
                    "matched": True,
                    "status": "error",
                    "error": str(e)[:300],
                    "conditions": condition_evals,
                }
            )

        if bool(trigger.get("stop_on_match")):
            break

    return {
        "ok": True,
        "matched": matched,
        "sent": sent_any,
        "details": details,
    }


def _claim_due_scheduled_trigger_messages(now: datetime, limit: int) -> List[Dict[str, Any]]:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                WITH due AS (
                    SELECT
                        sm.id,
                        sm.trigger_id,
                        sm.phone,
                        sm.template_id,
                        sm.payload_json,
                        sm.run_at,
                        sm.attempts,
                        COALESCE(t.channel, 'whatsapp') AS channel
                    FROM trigger_scheduled_messages sm
                    LEFT JOIN automation_triggers t ON t.id = sm.trigger_id
                    WHERE LOWER(status) = 'pending'
                      AND sm.run_at <= :now
                    ORDER BY sm.run_at ASC, sm.id ASC
                    LIMIT :limit
                    FOR UPDATE SKIP LOCKED
                )
                UPDATE trigger_scheduled_messages t
                SET status = 'processing',
                    attempts = t.attempts + 1
                FROM due
                WHERE t.id = due.id
                RETURNING
                    due.id,
                    due.trigger_id,
                    due.phone,
                    due.template_id,
                    due.payload_json,
                    due.run_at,
                    due.attempts,
                    due.channel
                """
            ),
            {"now": now, "limit": int(limit)},
        ).mappings().all()

    return [dict(r) for r in rows]


def _mark_scheduled_trigger_message_sent(msg_id: int) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE trigger_scheduled_messages
                SET status = 'sent',
                    sent_at = NOW(),
                    last_error = NULL
                WHERE id = :id
                """
            ),
            {"id": int(msg_id)},
        )


def _mark_scheduled_trigger_message_failed(msg_id: int, error: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE trigger_scheduled_messages
                SET status = 'failed',
                    last_error = :error
                WHERE id = :id
                """
            ),
            {"id": int(msg_id), "error": (error or "send_failed")[:900]},
        )


async def process_due_scheduled_trigger_messages(*, limit: int = 50) -> Dict[str, Any]:
    now = datetime.utcnow()
    rows = _claim_due_scheduled_trigger_messages(now, max(1, min(int(limit or 50), 500)))

    sent = 0
    failed = 0

    for row in rows:
        scheduled_id = int(row.get("id") or 0)
        phone = str(row.get("phone") or "").strip()
        template_id = int(row.get("template_id") or 0)
        trigger_id = int(row.get("trigger_id") or 0)
        channel = str(row.get("channel") or "whatsapp").strip().lower() or "whatsapp"
        payload = _safe_json_dict(row.get("payload_json"))

        if scheduled_id <= 0 or not phone or template_id <= 0:
            failed += 1
            if scheduled_id > 0:
                _mark_scheduled_trigger_message_failed(scheduled_id, "invalid_scheduled_message")
            continue

        try:
            result = await send_template_to_phone(
                phone=phone,
                template_id=template_id,
                trigger_id=trigger_id,
                source="trigger_scheduled",
                channel=channel,
                overrides=_safe_json_dict(payload.get("overrides")),
                extra_meta={"scheduled_message_id": scheduled_id},
            )

            if bool(result.get("ok")):
                sent += 1
                _mark_scheduled_trigger_message_sent(scheduled_id)
            else:
                failed += 1
                _mark_scheduled_trigger_message_failed(scheduled_id, str(result.get("error") or "send_failed"))

        except Exception as e:
            failed += 1
            _mark_scheduled_trigger_message_failed(scheduled_id, str(e)[:900])

    return {
        "ok": True,
        "claimed": len(rows),
        "sent": sent,
        "failed": failed,
        "ts": now.isoformat(),
    }
