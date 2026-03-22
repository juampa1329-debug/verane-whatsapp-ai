from __future__ import annotations

import asyncio
import json
import os
from datetime import datetime
from typing import Any, Dict, List

from sqlalchemy import text

from app.db import engine
from app.automation.trigger_engine import process_due_scheduled_trigger_messages
from app.remarketing.engine import process_due_remarketing
from app.routes.whatsapp import send_whatsapp_media_id, send_whatsapp_text


def _env_int(name: str, default: int, *, min_v: int, max_v: int) -> int:
    raw = (os.getenv(name, "") or "").strip()
    if not raw:
        return default
    try:
        v = int(raw)
    except Exception:
        return default
    return max(min_v, min(max_v, v))


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name, "") or "").strip().lower()
    if raw in ("1", "true", "yes", "y", "on"):
        return True
    if raw in ("0", "false", "no", "n", "off"):
        return False
    return default


def engine_settings() -> Dict[str, Any]:
    return {
        "enabled": _env_bool("CAMPAIGN_ENGINE_ENABLED", True),
        "interval_sec": _env_int("CAMPAIGN_ENGINE_INTERVAL_SEC", 8, min_v=2, max_v=120),
        "batch_size": _env_int("CAMPAIGN_BATCH_SIZE", 20, min_v=1, max_v=500),
        "send_delay_ms": _env_int("CAMPAIGN_SEND_DELAY_MS", 250, min_v=0, max_v=10000),
    }


def _safe_json_dict(v: Any) -> Dict[str, Any]:
    if isinstance(v, dict):
        return v
    return {}


def _render_template(body: str, variables: Dict[str, Any]) -> str:
    out = body or ""
    for k, v in (variables or {}).items():
        key = (k or "").strip()
        if not key:
            continue
        out = out.replace(f"{{{{{key}}}}}", str(v if v is not None else ""))
    return out.strip()


def _recipient_variables(row: Dict[str, Any]) -> Dict[str, Any]:
    first_name = str(row.get("first_name") or "").strip()
    last_name = str(row.get("last_name") or "").strip()
    full_name = f"{first_name} {last_name}".strip()

    return {
        "nombre": full_name or row.get("phone") or "",
        "first_name": first_name,
        "last_name": last_name,
        "city": str(row.get("city") or "").strip(),
        "customer_type": str(row.get("customer_type") or "").strip(),
        "interests": str(row.get("interests") or "").strip(),
        "tags": str(row.get("tags") or "").strip(),
        "payment_status": str(row.get("payment_status") or "").strip(),
        "phone": str(row.get("phone") or "").strip(),
        "campaign_name": str(row.get("campaign_name") or "").strip(),
        "objective": str(row.get("objective") or "").strip(),
        "business_name": str(os.getenv("BUSINESS_NAME", "Verane")).strip(),
        "business_phone": str(os.getenv("BUSINESS_PHONE", "")).strip(),
        "business_email": str(os.getenv("BUSINESS_EMAIL", "")).strip(),
        "assistant_name": str(os.getenv("ASSISTANT_NAME", "Asistente Verane")).strip(),
        "assistant_phone": str(os.getenv("ASSISTANT_PHONE", "")).strip(),
        "customer_name": full_name or row.get("phone") or "",
        "customer_phone": str(row.get("phone") or "").strip(),
        "customer_tag": str(row.get("tags") or "").strip(),
        "customer_country": str((row.get("crm_meta_country") or row.get("country") or "CO")).strip(),
        "first_message_date": str(row.get("first_message_date") or "").strip(),
        "last_message_date": str(row.get("last_message_date") or "").strip(),
    }


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

        if kind == "image":
            media_id = str(item.get("media_id") or "").strip()
            image_url = str(item.get("image_url") or item.get("url") or "").strip()
            caption = str(item.get("caption") or item.get("text") or "").strip()
            if not media_id and not image_url:
                continue
            out.append(
                {
                    "kind": "image",
                    "media_id": media_id,
                    "image_url": image_url,
                    "caption": caption,
                    "delay_ms": delay_ms,
                }
            )
            continue

        text_val = str(item.get("text") or item.get("content") or item.get("body") or "").strip()
        if not text_val:
            continue
        out.append({"kind": "text", "text": text_val, "delay_ms": delay_ms})

    if out:
        return out

    fallback = str(body_fallback or "").strip()
    if fallback:
        return [{"kind": "text", "text": fallback, "delay_ms": 0}]
    return []


def _build_campaign_blocks(row: Dict[str, Any]) -> List[Dict[str, Any]]:
    body = str(row.get("template_body") or "").strip()
    if not body:
        body = str(row.get("objective") or "").strip() or "Hola {{nombre}}, tenemos novedades para ti."

    variables = _recipient_variables(row)
    defaults = _safe_json_dict(row.get("params_json"))
    for k, v in defaults.items():
        kk = str(k or "").strip()
        if not kk:
            continue
        if kk not in variables or str(variables.get(kk) or "").strip() == "":
            variables[kk] = v
    blocks = _normalize_template_blocks(row.get("blocks_json"), body_fallback=body)
    if not blocks:
        blocks = [{"kind": "text", "text": body, "delay_ms": 0}]

    rendered: List[Dict[str, Any]] = []
    for b in blocks:
        kind = str(b.get("kind") or "text").strip().lower()
        delay_ms = int(b.get("delay_ms") or 0)
        if kind == "image":
            rendered.append(
                {
                    "kind": "image",
                    "media_id": str(b.get("media_id") or "").strip(),
                    "image_url": str(b.get("image_url") or "").strip(),
                    "caption": _render_template(str(b.get("caption") or ""), variables),
                    "delay_ms": delay_ms,
                }
            )
            continue

        rendered.append(
            {
                "kind": "text",
                "text": _render_template(str(b.get("text") or ""), variables),
                "delay_ms": delay_ms,
            }
        )
    return rendered


def _mark_due_campaigns_running(now: datetime) -> int:
    with engine.begin() as conn:
        rs = conn.execute(text("""
            UPDATE campaigns
            SET status = 'running',
                updated_at = NOW(),
                launched_at = COALESCE(launched_at, NOW())
            WHERE LOWER(status) = 'scheduled'
              AND scheduled_at IS NOT NULL
              AND scheduled_at <= :now
        """), {"now": now})

    return int(rs.rowcount or 0)


def _claim_pending_recipients(now: datetime, batch_size: int) -> List[Dict[str, Any]]:
    with engine.begin() as conn:
        rows = conn.execute(text("""
            WITH due AS (
                SELECT
                    cr.id AS recipient_id,
                    cr.campaign_id,
                    cr.phone,
                    c.name AS campaign_name,
                    c.objective,
                    c.template_id,
                    c.channel,
                    t.body AS template_body,
                    t.variables_json,
                    t.blocks_json,
                    t.params_json,
                    conv.first_name,
                    conv.last_name,
                    conv.city,
                    conv.customer_type,
                    conv.interests,
                    conv.tags,
                    conv.payment_status,
                    COALESCE(conv.crm_meta->>'country', '') AS crm_meta_country,
                    (
                        SELECT MIN(m0.created_at)
                        FROM messages m0
                        WHERE m0.phone = cr.phone
                    ) AS first_message_date,
                    (
                        SELECT MAX(m1.created_at)
                        FROM messages m1
                        WHERE m1.phone = cr.phone
                    ) AS last_message_date
                FROM campaign_recipients cr
                JOIN campaigns c ON c.id = cr.campaign_id
                LEFT JOIN message_templates t ON t.id = c.template_id
                LEFT JOIN conversations conv ON conv.phone = cr.phone
                WHERE LOWER(cr.status) = 'pending'
                  AND LOWER(c.status) IN ('running', 'scheduled')
                  AND (c.scheduled_at IS NULL OR c.scheduled_at <= :now)
                ORDER BY COALESCE(c.scheduled_at, c.created_at) ASC, cr.id ASC
                LIMIT :limit
                FOR UPDATE SKIP LOCKED
            )
            UPDATE campaign_recipients r
            SET status = 'processing'
            FROM due
            WHERE r.id = due.recipient_id
            RETURNING
                due.recipient_id,
                due.campaign_id,
                due.phone,
                due.campaign_name,
                due.objective,
                due.template_id,
                due.channel,
                due.template_body,
                due.variables_json,
                due.blocks_json,
                due.params_json,
                due.first_name,
                due.last_name,
                due.city,
                due.customer_type,
                due.interests,
                due.tags,
                due.payment_status,
                due.crm_meta_country,
                due.first_message_date,
                due.last_message_date
        """), {"now": now, "limit": int(batch_size)}).mappings().all()

    return [dict(r) for r in rows]


def _save_campaign_message(
    *,
    campaign_id: int,
    recipient_id: int,
    phone: str,
    msg_type: str,
    text_msg: str,
    media_id: str,
    media_caption: str,
    sent_ok: bool,
    wa_message_id: str,
    wa_error: str,
) -> int:
    now = datetime.utcnow()
    wa_status = "sent" if sent_ok else "failed"
    payload = {
        "source": "campaign",
        "campaign_id": int(campaign_id),
        "recipient_id": int(recipient_id),
    }

    with engine.begin() as conn:
        message_id = conn.execute(text("""
            INSERT INTO messages (
                phone,
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
        """), {
            "phone": phone,
            "msg_type": (msg_type or "text").strip().lower(),
            "text": text_msg,
            "media_id": media_id or None,
            "media_caption": media_caption or None,
            "wa_status": wa_status,
            "wa_message_id": wa_message_id or None,
            "wa_error": wa_error or None,
            "wa_ts_sent": now if sent_ok else None,
            "ai_meta": json.dumps(payload, ensure_ascii=False),
            "created_at": now,
        }).scalar()

        conn.execute(text("""
            INSERT INTO conversations (phone, updated_at)
            VALUES (:phone, :updated_at)
            ON CONFLICT (phone)
            DO UPDATE SET updated_at = EXCLUDED.updated_at
        """), {"phone": phone, "updated_at": now})

    try:
        return int(message_id)
    except Exception:
        return 0


def _mark_recipient_sent(recipient_id: int, message_id: int, wa_message_id: str) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE campaign_recipients
            SET status = 'sent',
                sent_at = NOW(),
                error = NULL,
                wa_message_id = :wa_message_id,
                message_id = :message_id
            WHERE id = :recipient_id
        """), {
            "recipient_id": int(recipient_id),
            "message_id": int(message_id) if message_id else None,
            "wa_message_id": wa_message_id or None,
        })


def _mark_recipient_failed(recipient_id: int, error: str, message_id: int = 0) -> None:
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE campaign_recipients
            SET status = 'failed',
                error = :error,
                message_id = CASE WHEN :message_id > 0 THEN :message_id ELSE message_id END
            WHERE id = :recipient_id
        """), {
            "recipient_id": int(recipient_id),
            "error": (error or "send_failed")[:900],
            "message_id": int(message_id or 0),
        })


def _refresh_campaign_completion() -> int:
    with engine.begin() as conn:
        rs = conn.execute(text("""
            UPDATE campaigns c
            SET status = 'completed',
                updated_at = NOW()
            WHERE LOWER(c.status) IN ('running', 'scheduled')
              AND EXISTS (
                    SELECT 1
                    FROM campaign_recipients cr0
                    WHERE cr0.campaign_id = c.id
              )
              AND NOT EXISTS (
                    SELECT 1
                    FROM campaign_recipients cr
                    WHERE cr.campaign_id = c.id
                      AND LOWER(cr.status) IN ('pending', 'processing')
              )
        """))

    return int(rs.rowcount or 0)


async def campaign_engine_tick(*, batch_size: int | None = None, send_delay_ms: int | None = None) -> Dict[str, Any]:
    cfg = engine_settings()
    now = datetime.utcnow()

    batch = int(batch_size or cfg["batch_size"])
    delay_ms = int(send_delay_ms if send_delay_ms is not None else cfg["send_delay_ms"])

    running_now = _mark_due_campaigns_running(now)
    rows = _claim_pending_recipients(now, batch)

    sent = 0
    failed = 0

    for row in rows:
        recipient_id = int(row.get("recipient_id") or 0)
        campaign_id = int(row.get("campaign_id") or 0)
        phone = str(row.get("phone") or "").strip()

        if not recipient_id or not phone:
            failed += 1
            if recipient_id:
                _mark_recipient_failed(recipient_id, "invalid_recipient")
            continue

        blocks = _build_campaign_blocks(row)
        if not blocks:
            failed += 1
            _mark_recipient_failed(recipient_id, "empty_message")
            continue

        recipient_ok = True
        last_message_id = 0
        last_wa_id = ""
        last_error = ""

        for idx, block in enumerate(blocks):
            kind = str(block.get("kind") or "text").strip().lower()
            block_delay_ms = int(block.get("delay_ms") or 0)

            block_text = ""
            media_id = ""
            media_caption = ""

            try:
                if kind == "image":
                    media_id = str(block.get("media_id") or "").strip()
                    media_caption = str(block.get("caption") or "").strip()
                    if not media_id:
                        raise RuntimeError("image block without media_id")
                    wa = await send_whatsapp_media_id(phone, "image", media_id, media_caption)
                    block_text = media_caption
                    msg_type = "image"
                else:
                    block_text = str(block.get("text") or "").strip()
                    if not block_text:
                        raise RuntimeError("text block empty")
                    wa = await send_whatsapp_text(phone, block_text)
                    msg_type = "text"
            except Exception as e:
                recipient_ok = False
                last_error = str(e)[:900]
                last_message_id = _save_campaign_message(
                    campaign_id=campaign_id,
                    recipient_id=recipient_id,
                    phone=phone,
                    msg_type="image" if kind == "image" else "text",
                    text_msg=block_text,
                    media_id=media_id,
                    media_caption=media_caption,
                    sent_ok=False,
                    wa_message_id="",
                    wa_error=last_error,
                )
                break

            ok = bool((wa or {}).get("sent"))
            wa_id = str((wa or {}).get("wa_message_id") or "").strip()
            wa_error = str((wa or {}).get("reason") or (wa or {}).get("whatsapp_body") or "")[:900]

            last_message_id = _save_campaign_message(
                campaign_id=campaign_id,
                recipient_id=recipient_id,
                phone=phone,
                msg_type=msg_type,
                text_msg=block_text,
                media_id=media_id,
                media_caption=media_caption,
                sent_ok=ok,
                wa_message_id=wa_id,
                wa_error=wa_error,
            )
            last_wa_id = wa_id or last_wa_id

            if not ok:
                recipient_ok = False
                last_error = wa_error or "send_failed"
                break

            if idx < len(blocks) - 1 and block_delay_ms > 0:
                await asyncio.sleep(block_delay_ms / 1000.0)

        if recipient_ok:
            sent += 1
            _mark_recipient_sent(recipient_id, last_message_id, last_wa_id)
        else:
            failed += 1
            _mark_recipient_failed(recipient_id, last_error or "send_failed", message_id=last_message_id)

        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)

    completed_now = _refresh_campaign_completion()
    scheduled_result = await process_due_scheduled_trigger_messages(limit=max(10, int(batch)))
    remarketing_result = await process_due_remarketing(limit=max(10, int(batch) * 5))

    return {
        "ok": True,
        "claimed": len(rows),
        "sent": sent,
        "failed": failed,
        "scheduled_to_running": running_now,
        "completed_now": completed_now,
        "trigger_scheduled_claimed": int(scheduled_result.get("claimed") or 0),
        "trigger_scheduled_sent": int(scheduled_result.get("sent") or 0),
        "trigger_scheduled_failed": int(scheduled_result.get("failed") or 0),
        "remarketing_flows": int(remarketing_result.get("flows") or 0),
        "remarketing_enrolled": int(remarketing_result.get("enrolled") or 0),
        "remarketing_checked": int(remarketing_result.get("checked") or 0),
        "remarketing_sent": int(remarketing_result.get("sent") or 0),
        "remarketing_advanced": int(remarketing_result.get("advanced") or 0),
        "remarketing_held": int(remarketing_result.get("held") or 0),
        "remarketing_resumed": int(remarketing_result.get("resumed") or 0),
        "remarketing_completed": int(remarketing_result.get("completed") or 0),
        "remarketing_exited": int(remarketing_result.get("exited") or 0),
        "remarketing_failed": int(remarketing_result.get("failed") or 0),
        "batch_size": batch,
        "send_delay_ms": delay_ms,
        "ts": now.isoformat(),
    }


async def run_campaign_engine_forever(stop_event: asyncio.Event) -> None:
    cfg = engine_settings()
    interval_sec = int(cfg["interval_sec"])

    while not stop_event.is_set():
        try:
            await campaign_engine_tick(batch_size=cfg["batch_size"], send_delay_ms=cfg["send_delay_ms"])
        except Exception as e:
            print("[CAMPAIGN_ENGINE] tick error:", str(e)[:900])

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=interval_sec)
        except asyncio.TimeoutError:
            pass
