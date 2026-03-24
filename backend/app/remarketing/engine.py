from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Any, Dict, List, Tuple

from sqlalchemy import text

from app.automation.trigger_engine import send_template_to_phone
from app.db import engine


def _env_int(name: str, default: int, *, min_v: int, max_v: int) -> int:
    raw = (os.getenv(name, "") or "").strip()
    if not raw:
        return default
    try:
        val = int(raw)
    except Exception:
        return default
    return max(min_v, min(max_v, val))


def _env_bool(name: str, default: bool) -> bool:
    raw = (os.getenv(name, "") or "").strip().lower()
    if raw in ("1", "true", "yes", "y", "on"):
        return True
    if raw in ("0", "false", "no", "n", "off"):
        return False
    return default


def remarketing_settings() -> Dict[str, Any]:
    return {
        "enabled": _env_bool("REMARKETING_ENGINE_ENABLED", True),
        "batch_size": _env_int("REMARKETING_BATCH_SIZE", 200, min_v=1, max_v=2000),
        "new_enrollments_per_flow": _env_int("REMARKETING_NEW_PER_FLOW", 100, min_v=1, max_v=2000),
        "resume_after_minutes": _env_int("REMARKETING_RESUME_AFTER_MINUTES", 720, min_v=1, max_v=60 * 24 * 60),
        "retry_minutes": _env_int("REMARKETING_RETRY_MINUTES", 30, min_v=1, max_v=60 * 24),
        "service_window_hours": _env_int("REMARKETING_SERVICE_WINDOW_HOURS", 24, min_v=1, max_v=48),
    }


def _safe_json_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _split_tags(raw: str) -> List[str]:
    out: List[str] = []
    seen = set()
    for item in str(raw or "").split(","):
        tag = str(item or "").strip().lower()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        out.append(tag)
    return out


def _join_tags(tags: List[str]) -> str:
    seen = set()
    out: List[str] = []
    for item in tags:
        tag = str(item or "").strip().lower()
        if not tag or tag in seen:
            continue
        seen.add(tag)
        out.append(tag)
    return ",".join(out)


def _build_rules_sql(rules: Dict[str, Any], prefix: str) -> Tuple[str, Dict[str, Any]]:
    rules = _safe_json_dict(rules)
    clauses: List[str] = []
    params: Dict[str, Any] = {}

    tag = str(rules.get("tag") or "").strip().lower()
    if tag:
        key = f"{prefix}_tag"
        params[key] = f"%{tag}%"
        clauses.append(f"LOWER(COALESCE(c.tags, '')) LIKE :{key}")

    intent = str(rules.get("intent") or "").strip().upper()
    if intent:
        key = f"{prefix}_intent"
        params[key] = intent
        clauses.append(f"UPPER(COALESCE(c.intent_current, '')) = :{key}")

    payment_status = str(rules.get("payment_status") or "").strip().lower()
    if payment_status:
        key = f"{prefix}_payment"
        params[key] = payment_status
        clauses.append(f"LOWER(COALESCE(c.payment_status, '')) = :{key}")

    city = str(rules.get("city") or "").strip().lower()
    if city:
        key = f"{prefix}_city"
        params[key] = f"%{city}%"
        clauses.append(f"LOWER(COALESCE(c.city, '')) LIKE :{key}")

    customer_type = str(rules.get("customer_type") or "").strip().lower()
    if customer_type:
        key = f"{prefix}_customer_type"
        params[key] = customer_type
        clauses.append(f"LOWER(COALESCE(c.customer_type, '')) = :{key}")

    takeover = rules.get("takeover")
    if isinstance(takeover, bool):
        key = f"{prefix}_takeover"
        params[key] = takeover
        clauses.append(f"c.takeover = :{key}")

    if not clauses:
        return "TRUE", params
    return " AND ".join(clauses), params


def _conversation_matches_rules(conv: Dict[str, Any], rules: Dict[str, Any]) -> bool:
    rules = _safe_json_dict(rules)
    if not rules:
        return False

    tags_text = str(conv.get("tags") or "").lower()
    intent_current = str(conv.get("intent_current") or "").strip().upper()
    payment_status = str(conv.get("payment_status") or "").strip().lower()
    city = str(conv.get("city") or "").strip().lower()
    customer_type = str(conv.get("customer_type") or "").strip().lower()
    takeover = bool(conv.get("takeover") is True)

    tag = str(rules.get("tag") or "").strip().lower()
    if tag and tag not in tags_text:
        return False

    intent = str(rules.get("intent") or "").strip().upper()
    if intent and intent != intent_current:
        return False

    pay = str(rules.get("payment_status") or "").strip().lower()
    if pay and pay != payment_status:
        return False

    city_rule = str(rules.get("city") or "").strip().lower()
    if city_rule and city_rule not in city:
        return False

    ctype_rule = str(rules.get("customer_type") or "").strip().lower()
    if ctype_rule and ctype_rule != customer_type:
        return False

    takeover_rule = rules.get("takeover")
    if isinstance(takeover_rule, bool) and takeover_rule != takeover:
        return False

    return True


def _flow_resume_after_minutes(flow_entry_rules: Dict[str, Any], cfg: Dict[str, Any]) -> int:
    try:
        val = int(
            flow_entry_rules.get("resume_after_minutes")
            or flow_entry_rules.get("idle_minutes")
            or cfg.get("resume_after_minutes")
            or 720
        )
    except Exception:
        val = int(cfg.get("resume_after_minutes") or 720)
    return max(1, min(val, 60 * 24 * 60))


def _flow_retry_minutes(flow_entry_rules: Dict[str, Any], cfg: Dict[str, Any]) -> int:
    try:
        val = int(flow_entry_rules.get("retry_minutes") or cfg.get("retry_minutes") or 30)
    except Exception:
        val = int(cfg.get("retry_minutes") or 30)
    return max(1, min(val, 60 * 24))


def _find_next_step_order(step_orders: List[int], current_step_order: int) -> int | None:
    for step_order in step_orders:
        if step_order > int(current_step_order):
            return int(step_order)
    return None


def _step_wait_minutes(step: Dict[str, Any]) -> int:
    try:
        val = int(step.get("wait_minutes") or 0)
    except Exception:
        val = 0
    return max(0, min(val, 60 * 24 * 365))


def _ensure_phone_row(conn: Any, phone: str) -> None:
    conn.execute(
        text(
            """
            INSERT INTO conversations (phone, updated_at)
            VALUES (:phone, NOW())
            ON CONFLICT (phone) DO NOTHING
            """
        ),
        {"phone": phone},
    )


def _set_flow_tags(
    conn: Any,
    *,
    phone: str,
    flow_id: int,
    stage_order: int | None,
    state: str,
) -> str:
    _ensure_phone_row(conn, phone)

    row = conn.execute(
        text(
            """
            SELECT tags
            FROM conversations
            WHERE phone = :phone
            LIMIT 1
            """
        ),
        {"phone": phone},
    ).mappings().first()

    tags = _split_tags(str((row or {}).get("tags") or ""))

    prefix = f"rmk_{int(flow_id)}_"
    tags = [t for t in tags if not t.startswith(prefix)]

    state_key = str(state or "active").strip().lower()
    if state_key not in ("clear", "completed", "exited"):
        if "remarketing" not in tags:
            tags.append("remarketing")

    if stage_order and int(stage_order) > 0 and state_key != "clear":
        tags.append(f"{prefix}s{int(stage_order)}")

    if state_key == "hold":
        tags.append(f"{prefix}hold")
    elif state_key == "completed":
        tags.append(f"{prefix}done")
    elif state_key == "exited":
        tags.append(f"{prefix}exit")

    has_any_rmk = any(t.startswith("rmk_") for t in tags)
    if not has_any_rmk:
        tags = [t for t in tags if t != "remarketing"]

    tags_csv = _join_tags(tags)
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
    return tags_csv

def list_stage_catalog() -> List[Dict[str, Any]]:
    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    f.id AS flow_id,
                    f.name AS flow_name,
                    f.is_active,
                    s.step_order,
                    s.stage_name,
                    s.wait_minutes,
                    s.template_id,
                    t.name AS template_name
                FROM remarketing_flows f
                LEFT JOIN remarketing_steps s ON s.flow_id = f.id
                LEFT JOIN message_templates t ON t.id = s.template_id
                WHERE f.is_active = TRUE
                ORDER BY f.updated_at DESC, f.id DESC, s.step_order ASC
                """
            )
        ).mappings().all()

    by_flow: Dict[int, Dict[str, Any]] = {}
    for row in rows:
        flow_id = int(row.get("flow_id") or 0)
        if flow_id <= 0:
            continue
        if flow_id not in by_flow:
            by_flow[flow_id] = {
                "id": flow_id,
                "name": str(row.get("flow_name") or "").strip(),
                "is_active": bool(row.get("is_active") is True),
                "steps": [],
            }

        step_order = row.get("step_order")
        if step_order is None:
            continue

        by_flow[flow_id]["steps"].append(
            {
                "step_order": int(step_order),
                "stage_name": str(row.get("stage_name") or "").strip(),
                "wait_minutes": int(row.get("wait_minutes") or 0),
                "template_id": int(row.get("template_id") or 0) if row.get("template_id") is not None else None,
                "template_name": str(row.get("template_name") or "").strip(),
            }
        )

    return list(by_flow.values())


def get_phone_enrollments(phone: str) -> List[Dict[str, Any]]:
    p = str(phone or "").strip()
    if not p:
        return []

    with engine.begin() as conn:
        rows = conn.execute(
            text(
                """
                SELECT
                    e.id,
                    e.flow_id,
                    f.name AS flow_name,
                    e.phone,
                    e.current_step_order,
                    e.state,
                    e.enrolled_at,
                    e.step_started_at,
                    e.next_run_at,
                    e.last_sent_at,
                    e.last_sent_step_order,
                    e.updated_at,
                    e.meta_json,
                    COALESCE(c.tags, '') AS tags,
                    s.stage_name AS current_stage_name,
                    s.template_id AS current_template_id,
                    t.name AS current_template_name
                FROM remarketing_enrollments e
                JOIN remarketing_flows f ON f.id = e.flow_id
                LEFT JOIN conversations c ON c.phone = e.phone
                LEFT JOIN remarketing_steps s ON s.flow_id = e.flow_id AND s.step_order = e.current_step_order
                LEFT JOIN message_templates t ON t.id = s.template_id
                WHERE e.phone = :phone
                ORDER BY e.updated_at DESC, e.id DESC
                """
            ),
            {"phone": p},
        ).mappings().all()

    return [dict(r) for r in rows]


def _parse_stage_token(stage: str) -> Tuple[str, int | None]:
    token = str(stage or "").strip().lower()
    if not token:
        return "", None

    if token in ("clear", "remove", "none"):
        return "clear", None
    if token in ("hold", "pause", "paused"):
        return "hold", None
    if token in ("done", "complete", "completed"):
        return "completed", None
    if token in ("exit", "exited"):
        return "exited", None

    if token.startswith("s") and token[1:].isdigit():
        return "active", int(token[1:])
    if token.isdigit():
        return "active", int(token)

    return "", None


def assign_phone_stage(
    *,
    phone: str,
    flow_id: int,
    stage: str,
    send_now: bool = True,
    source: str = "manual",
) -> Dict[str, Any]:
    p = str(phone or "").strip()
    if not p:
        return {"ok": False, "error": "phone_required"}

    flow_id = int(flow_id or 0)
    if flow_id <= 0:
        return {"ok": False, "error": "flow_id_required"}

    state, stage_order_raw = _parse_stage_token(stage)
    if not state:
        return {"ok": False, "error": "invalid_stage"}

    now = datetime.utcnow()

    with engine.begin() as conn:
        flow = conn.execute(
            text(
                """
                SELECT id, name, entry_rules_json
                FROM remarketing_flows
                WHERE id = :flow_id
                LIMIT 1
                """
            ),
            {"flow_id": flow_id},
        ).mappings().first()
        if not flow:
            return {"ok": False, "error": "flow_not_found"}

        step_rows = conn.execute(
            text(
                """
                SELECT step_order, wait_minutes
                FROM remarketing_steps
                WHERE flow_id = :flow_id
                ORDER BY step_order ASC
                """
            ),
            {"flow_id": flow_id},
        ).mappings().all()

        step_map = {int(r.get("step_order") or 0): dict(r) for r in step_rows if int(r.get("step_order") or 0) > 0}
        if not step_map:
            return {"ok": False, "error": "flow_without_steps"}

        step_orders = sorted(step_map.keys())
        first_step = step_orders[0]

        row = conn.execute(
            text(
                """
                SELECT id, current_step_order, state, last_sent_step_order
                FROM remarketing_enrollments
                WHERE flow_id = :flow_id AND phone = :phone
                LIMIT 1
                """
            ),
            {"flow_id": flow_id, "phone": p},
        ).mappings().first()

        if state == "clear":
            if row:
                conn.execute(
                    text(
                        """
                        DELETE FROM remarketing_enrollments
                        WHERE id = :id
                        """
                    ),
                    {"id": int(row.get("id") or 0)},
                )
            tags_csv = _set_flow_tags(conn, phone=p, flow_id=flow_id, stage_order=None, state="clear")
            return {
                "ok": True,
                "phone": p,
                "flow_id": flow_id,
                "state": "clear",
                "tags": tags_csv,
            }

        target_step = stage_order_raw if stage_order_raw is not None else int(row.get("current_step_order") or first_step) if row else first_step
        if target_step not in step_map:
            target_step = first_step

        wait_minutes = _step_wait_minutes(step_map[target_step])
        next_run_at = now if bool(send_now) else (now + timedelta(minutes=wait_minutes))

        if state == "active":
            if row:
                conn.execute(
                    text(
                        """
                        UPDATE remarketing_enrollments
                        SET current_step_order = :current_step_order,
                            state = 'active',
                            step_started_at = :step_started_at,
                            next_run_at = :next_run_at,
                            last_sent_at = NULL,
                            last_sent_step_order = NULL,
                            updated_at = NOW(),
                            meta_json = COALESCE(meta_json, '{}'::jsonb) || CAST(:meta_patch AS jsonb)
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": int(row.get("id") or 0),
                        "current_step_order": int(target_step),
                        "step_started_at": now,
                        "next_run_at": next_run_at,
                        "meta_patch": '{"manual_stage_assign": true}',
                    },
                )
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO remarketing_enrollments (
                            flow_id,
                            phone,
                            current_step_order,
                            state,
                            enrolled_at,
                            step_started_at,
                            next_run_at,
                            updated_at,
                            meta_json
                        )
                        VALUES (
                            :flow_id,
                            :phone,
                            :current_step_order,
                            'active',
                            :enrolled_at,
                            :step_started_at,
                            :next_run_at,
                            NOW(),
                            CAST(:meta_json AS jsonb)
                        )
                        """
                    ),
                    {
                        "flow_id": flow_id,
                        "phone": p,
                        "current_step_order": int(target_step),
                        "enrolled_at": now,
                        "step_started_at": now,
                        "next_run_at": next_run_at,
                        "meta_json": '{"source":"manual_stage_assign"}',
                    },
                )

            tags_csv = _set_flow_tags(conn, phone=p, flow_id=flow_id, stage_order=int(target_step), state="active")
            return {
                "ok": True,
                "phone": p,
                "flow_id": flow_id,
                "flow_name": str(flow.get("name") or "").strip(),
                "state": "active",
                "current_step_order": int(target_step),
                "next_run_at": next_run_at,
                "send_now": bool(send_now),
                "tags": tags_csv,
                "source": source,
            }

        if state in ("hold", "completed", "exited"):
            effective_state = state
            if row:
                conn.execute(
                    text(
                        """
                        UPDATE remarketing_enrollments
                        SET state = :state,
                            updated_at = NOW(),
                            step_started_at = :step_started_at,
                            next_run_at = :next_run_at
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": int(row.get("id") or 0),
                        "state": effective_state,
                        "step_started_at": now,
                        "next_run_at": (next_run_at if effective_state == "hold" else None),
                    },
                )
            else:
                conn.execute(
                    text(
                        """
                        INSERT INTO remarketing_enrollments (
                            flow_id,
                            phone,
                            current_step_order,
                            state,
                            enrolled_at,
                            step_started_at,
                            next_run_at,
                            updated_at,
                            meta_json
                        )
                        VALUES (
                            :flow_id,
                            :phone,
                            :current_step_order,
                            :state,
                            :enrolled_at,
                            :step_started_at,
                            :next_run_at,
                            NOW(),
                            CAST(:meta_json AS jsonb)
                        )
                        """
                    ),
                    {
                        "flow_id": flow_id,
                        "phone": p,
                        "current_step_order": int(target_step),
                        "state": effective_state,
                        "enrolled_at": now,
                        "step_started_at": now,
                        "next_run_at": (next_run_at if effective_state == "hold" else None),
                        "meta_json": '{"source":"manual_stage_assign"}',
                    },
                )

            stage_for_tag = int(target_step)
            if row and int(row.get("last_sent_step_order") or 0) > 0:
                stage_for_tag = int(row.get("last_sent_step_order") or stage_for_tag)

            tags_csv = _set_flow_tags(conn, phone=p, flow_id=flow_id, stage_order=stage_for_tag, state=effective_state)
            return {
                "ok": True,
                "phone": p,
                "flow_id": flow_id,
                "flow_name": str(flow.get("name") or "").strip(),
                "state": effective_state,
                "current_step_order": int(target_step),
                "next_run_at": (next_run_at if effective_state == "hold" else None),
                "tags": tags_csv,
                "source": source,
            }

    return {"ok": False, "error": "stage_not_supported"}


async def process_due_remarketing(*, limit: int | None = None, flow_id: int | None = None) -> Dict[str, Any]:
    cfg = remarketing_settings()
    flow_filter_id = int(flow_id or 0)
    if flow_filter_id <= 0:
        flow_filter_id = None

    if not bool(cfg.get("enabled")):
        return {
            "ok": True,
            "enabled": False,
            "flow_id": flow_filter_id,
            "flows": 0,
            "enrolled": 0,
            "checked": 0,
            "sent": 0,
            "advanced": 0,
            "held": 0,
            "resumed": 0,
            "completed": 0,
            "exited": 0,
            "failed": 0,
            "blocked_window": 0,
        }

    now = datetime.utcnow()
    batch_limit = max(1, min(int(limit or cfg.get("batch_size") or 200), 4000))
    service_window_hours = int(cfg.get("service_window_hours") or 24)
    service_window_minutes = max(1, service_window_hours * 60)

    with engine.begin() as conn:
        flow_where = "WHERE is_active = TRUE"
        flow_params: Dict[str, Any] = {}
        if flow_filter_id is not None:
            flow_where += " AND id = :flow_id"
            flow_params["flow_id"] = int(flow_filter_id)

        flow_rows = conn.execute(
            text(
                f"""
                SELECT id, name, entry_rules_json, exit_rules_json
                FROM remarketing_flows
                {flow_where}
                ORDER BY updated_at DESC, id DESC
                """
            ),
            flow_params,
        ).mappings().all()

        steps_where = """
                WHERE s.flow_id IN (
                    SELECT id
                    FROM remarketing_flows
                    WHERE is_active = TRUE
                )
        """
        steps_params: Dict[str, Any] = {}
        if flow_filter_id is not None:
            steps_where += "\n                  AND s.flow_id = :flow_id"
            steps_params["flow_id"] = int(flow_filter_id)

        step_rows = conn.execute(
            text(
                f"""
                SELECT
                    s.flow_id,
                    s.step_order,
                    s.wait_minutes,
                    s.template_id,
                    t.name AS template_name
                FROM remarketing_steps s
                LEFT JOIN message_templates t ON t.id = s.template_id
                {steps_where}
                ORDER BY s.flow_id ASC, s.step_order ASC
                """
            ),
            steps_params,
        ).mappings().all()

    flow_map: Dict[int, Dict[str, Any]] = {}
    for row in flow_rows:
        flow_id = int(row.get("id") or 0)
        if flow_id <= 0:
            continue
        flow_map[flow_id] = dict(row)

    steps_by_flow: Dict[int, List[Dict[str, Any]]] = {}
    for row in step_rows:
        flow_id = int(row.get("flow_id") or 0)
        if flow_id <= 0:
            continue
        steps_by_flow.setdefault(flow_id, []).append(dict(row))

    enrolled = 0
    checked = 0
    sent = 0
    advanced = 0
    held = 0
    resumed = 0
    completed = 0
    exited = 0
    failed = 0
    blocked_window = 0

    new_per_flow = int(cfg.get("new_enrollments_per_flow") or 100)

    for flow_id, flow in flow_map.items():
        steps = steps_by_flow.get(flow_id) or []
        if not steps:
            continue

        step_map = {int(s.get("step_order") or 0): s for s in steps if int(s.get("step_order") or 0) > 0}
        if not step_map:
            continue
        first_step = min(step_map.keys())

        entry_rules = _safe_json_dict(flow.get("entry_rules_json"))
        exit_rules = _safe_json_dict(flow.get("exit_rules_json"))

        entry_sql, entry_params = _build_rules_sql(entry_rules, prefix=f"flow{flow_id}_entry")
        exit_sql, exit_params = _build_rules_sql(exit_rules, prefix=f"flow{flow_id}_exit")

        where_sql = entry_sql
        params: Dict[str, Any] = {
            "flow_id": int(flow_id),
            "limit": max(1, min(new_per_flow, 2000)),
        }
        params.update(entry_params)
        if exit_sql != "TRUE":
            where_sql = f"({where_sql}) AND NOT ({exit_sql})"
            params.update(exit_params)

        with engine.begin() as conn:
            candidate_rows = conn.execute(
                text(
                    f"""
                    SELECT c.phone
                    FROM conversations c
                    WHERE {where_sql}
                      AND NOT EXISTS (
                            SELECT 1
                            FROM remarketing_enrollments e
                            WHERE e.flow_id = :flow_id
                              AND e.phone = c.phone
                      )
                    ORDER BY c.updated_at DESC
                    LIMIT :limit
                    """
                ),
                params,
            ).mappings().all()

            for crow in candidate_rows:
                phone = str(crow.get("phone") or "").strip()
                if not phone:
                    continue

                first_wait = _step_wait_minutes(step_map[first_step])
                next_run_at = now + timedelta(minutes=first_wait)
                conn.execute(
                    text(
                        """
                        INSERT INTO remarketing_enrollments (
                            flow_id,
                            phone,
                            current_step_order,
                            state,
                            enrolled_at,
                            step_started_at,
                            next_run_at,
                            updated_at,
                            meta_json
                        )
                        VALUES (
                            :flow_id,
                            :phone,
                            :current_step_order,
                            'active',
                            :enrolled_at,
                            :step_started_at,
                            :next_run_at,
                            NOW(),
                            CAST(:meta_json AS jsonb)
                        )
                        """
                    ),
                    {
                        "flow_id": int(flow_id),
                        "phone": phone,
                        "current_step_order": int(first_step),
                        "enrolled_at": now,
                        "step_started_at": now,
                        "next_run_at": next_run_at,
                        "meta_json": '{"source":"flow_entry"}',
                    },
                )
                _set_flow_tags(
                    conn,
                    phone=phone,
                    flow_id=int(flow_id),
                    stage_order=int(first_step),
                    state="active",
                )
                enrolled += 1

    with engine.begin() as conn:
        enroll_where_flow = ""
        enroll_params: Dict[str, Any] = {
            "limit": int(batch_limit),
            "now": now,
            "window_start": now - timedelta(minutes=service_window_minutes),
        }
        if flow_filter_id is not None:
            enroll_where_flow = "AND e.flow_id = :flow_id"
            enroll_params["flow_id"] = int(flow_filter_id)

        enroll_rows = conn.execute(
            text(
                f"""
                SELECT
                    e.id,
                    e.flow_id,
                    e.phone,
                    e.current_step_order,
                    e.state,
                    e.enrolled_at,
                    e.step_started_at,
                    e.next_run_at,
                    e.last_sent_at,
                    e.last_sent_step_order,
                    e.updated_at,
                    e.meta_json,
                    COALESCE(c.tags, '') AS tags,
                    c.takeover,
                    c.intent_current,
                    c.payment_status,
                    c.city,
                    c.customer_type,
                    (
                        SELECT MAX(mi.created_at)
                        FROM messages mi
                        WHERE mi.phone = e.phone
                          AND mi.direction = 'in'
                    ) AS last_in_at
                FROM remarketing_enrollments e
                JOIN remarketing_flows f ON f.id = e.flow_id
                LEFT JOIN conversations c ON c.phone = e.phone
                WHERE f.is_active = TRUE
                  {enroll_where_flow}
                  AND (
                        (
                            LOWER(e.state) = 'active'
                            AND COALESCE(e.next_run_at, e.step_started_at, e.enrolled_at, e.updated_at) <= :now
                        )
                        OR
                        (
                            LOWER(e.state) = 'hold'
                            AND EXISTS (
                                SELECT 1
                                FROM messages mi2
                                WHERE mi2.phone = e.phone
                                  AND mi2.direction = 'in'
                                  AND mi2.created_at >= :window_start
                            )
                        )
                  )
                ORDER BY
                    CASE WHEN LOWER(e.state) = 'active' THEN 0 ELSE 1 END ASC,
                    COALESCE(e.next_run_at, e.step_started_at, e.enrolled_at, e.updated_at) ASC,
                    e.id ASC
                LIMIT :limit
                """
            ),
            enroll_params,
        ).mappings().all()

    checked = len(enroll_rows)

    for row in enroll_rows:
        enrollment_id = int(row.get("id") or 0)
        flow_id = int(row.get("flow_id") or 0)
        phone = str(row.get("phone") or "").strip()
        state = str(row.get("state") or "active").strip().lower()

        if enrollment_id <= 0 or flow_id <= 0 or not phone:
            continue

        flow = flow_map.get(flow_id)
        if not flow:
            continue

        steps = steps_by_flow.get(flow_id) or []
        step_map = {int(s.get("step_order") or 0): s for s in steps if int(s.get("step_order") or 0) > 0}
        step_orders = sorted(step_map.keys())
        if not step_orders:
            continue

        current_step_order = int(row.get("current_step_order") or step_orders[0])
        if current_step_order not in step_map:
            current_step_order = step_orders[0]
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE remarketing_enrollments
                        SET current_step_order = :current_step_order,
                            updated_at = NOW()
                        WHERE id = :id
                        """
                    ),
                    {"id": enrollment_id, "current_step_order": current_step_order},
                )

        flow_entry_rules = _safe_json_dict(flow.get("entry_rules_json"))
        flow_exit_rules = _safe_json_dict(flow.get("exit_rules_json"))

        conv_ctx = {
            "tags": row.get("tags"),
            "takeover": row.get("takeover"),
            "intent_current": row.get("intent_current"),
            "payment_status": row.get("payment_status"),
            "city": row.get("city"),
            "customer_type": row.get("customer_type"),
        }

        if _conversation_matches_rules(conv_ctx, flow_exit_rules):
            stage_for_tag = int(row.get("last_sent_step_order") or current_step_order)
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE remarketing_enrollments
                        SET state = 'exited',
                            updated_at = NOW(),
                            next_run_at = NULL
                        WHERE id = :id
                        """
                    ),
                    {"id": enrollment_id},
                )
                _set_flow_tags(
                    conn,
                    phone=phone,
                    flow_id=flow_id,
                    stage_order=stage_for_tag,
                    state="exited",
                )
            exited += 1
            continue

        last_in_at = row.get("last_in_at") if isinstance(row.get("last_in_at"), datetime) else None
        last_sent_at = row.get("last_sent_at") if isinstance(row.get("last_sent_at"), datetime) else None
        last_sent_step_order = int(row.get("last_sent_step_order") or 0)

        if state == "hold":
            resume_after = _flow_resume_after_minutes(flow_entry_rules, cfg)
            should_resume = False
            if last_in_at is not None:
                mins_since_last_in = (now - last_in_at).total_seconds() / 60.0
                within_service_window = mins_since_last_in <= float(service_window_minutes)
                if within_service_window and mins_since_last_in >= resume_after:
                    should_resume = True

            if should_resume:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            """
                            UPDATE remarketing_enrollments
                            SET state = 'active',
                                step_started_at = :step_started_at,
                                next_run_at = :next_run_at,
                                updated_at = NOW(),
                                meta_json = COALESCE(meta_json, '{}'::jsonb) || CAST(:meta_patch AS jsonb)
                            WHERE id = :id
                            """
                        ),
                        {
                            "id": enrollment_id,
                            "step_started_at": now,
                            "next_run_at": now,
                            "meta_patch": '{"hold_reason":"resumed"}',
                        },
                    )
                    stage_for_tag = last_sent_step_order if last_sent_step_order > 0 else current_step_order
                    _set_flow_tags(
                        conn,
                        phone=phone,
                        flow_id=flow_id,
                        stage_order=stage_for_tag,
                        state="active",
                    )
                resumed += 1
            continue

        if last_sent_at and last_in_at and last_in_at > last_sent_at:
            stage_for_tag = last_sent_step_order if last_sent_step_order > 0 else current_step_order
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE remarketing_enrollments
                        SET state = 'hold',
                            step_started_at = :step_started_at,
                            updated_at = NOW(),
                            meta_json = COALESCE(meta_json, '{}'::jsonb) || CAST(:meta_patch AS jsonb)
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": enrollment_id,
                        "step_started_at": now,
                        "meta_patch": '{"hold_reason":"user_replied"}',
                    },
                )
                _set_flow_tags(
                    conn,
                    phone=phone,
                    flow_id=flow_id,
                    stage_order=stage_for_tag,
                    state="hold",
                )
            held += 1
            continue

        step = step_map.get(current_step_order)
        if not step:
            continue

        due_at = row.get("next_run_at") if isinstance(row.get("next_run_at"), datetime) else None
        if due_at is None:
            base_time = row.get("step_started_at") if isinstance(row.get("step_started_at"), datetime) else now
            due_at = base_time + timedelta(minutes=_step_wait_minutes(step))

        if now < due_at:
            continue

        minutes_since_last_in: float | None = None
        if last_in_at is not None:
            minutes_since_last_in = (now - last_in_at).total_seconds() / 60.0
        within_service_window = bool(
            minutes_since_last_in is not None and minutes_since_last_in <= float(service_window_minutes)
        )
        if not within_service_window:
            stage_for_tag = last_sent_step_order if last_sent_step_order > 0 else current_step_order
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE remarketing_enrollments
                        SET state = 'hold',
                            next_run_at = NULL,
                            step_started_at = :step_started_at,
                            updated_at = NOW(),
                            meta_json = COALESCE(meta_json, '{}'::jsonb) || CAST(:meta_patch AS jsonb)
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": enrollment_id,
                        "step_started_at": now,
                        "meta_patch": '{"hold_reason":"outside_service_window"}',
                    },
                )
                _set_flow_tags(
                    conn,
                    phone=phone,
                    flow_id=flow_id,
                    stage_order=stage_for_tag,
                    state="hold",
                )
            blocked_window += 1
            continue

        template_id = int(step.get("template_id") or 0)
        if template_id <= 0:
            retry_minutes = _flow_retry_minutes(flow_entry_rules, cfg)
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE remarketing_enrollments
                        SET next_run_at = :next_run_at,
                            updated_at = NOW()
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": enrollment_id,
                        "next_run_at": now + timedelta(minutes=retry_minutes),
                    },
                )
            failed += 1
            continue

        send_result = await send_template_to_phone(
            phone=phone,
            template_id=template_id,
            source="remarketing",
            overrides={},
            extra_meta={
                "remarketing_flow_id": flow_id,
                "remarketing_flow_name": str(flow.get("name") or "").strip(),
                "remarketing_step_order": int(current_step_order),
                "remarketing_enrollment_id": enrollment_id,
            },
        )

        if bool(send_result.get("ok")):
            sent += 1
            sent_step_order = int(current_step_order)
            next_step_order = _find_next_step_order(step_orders, sent_step_order)

            if next_step_order is None:
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            """
                            UPDATE remarketing_enrollments
                            SET state = 'completed',
                                last_sent_at = :last_sent_at,
                                last_sent_step_order = :last_sent_step_order,
                                next_run_at = NULL,
                                updated_at = NOW()
                            WHERE id = :id
                            """
                        ),
                        {
                            "id": enrollment_id,
                            "last_sent_at": now,
                            "last_sent_step_order": sent_step_order,
                        },
                    )
                    _set_flow_tags(
                        conn,
                        phone=phone,
                        flow_id=flow_id,
                        stage_order=sent_step_order,
                        state="completed",
                    )
                completed += 1
            else:
                next_wait = _step_wait_minutes(step_map[next_step_order])
                with engine.begin() as conn:
                    conn.execute(
                        text(
                            """
                            UPDATE remarketing_enrollments
                            SET current_step_order = :current_step_order,
                                state = 'active',
                                last_sent_at = :last_sent_at,
                                last_sent_step_order = :last_sent_step_order,
                                step_started_at = :step_started_at,
                                next_run_at = :next_run_at,
                                updated_at = NOW()
                            WHERE id = :id
                            """
                        ),
                        {
                            "id": enrollment_id,
                            "current_step_order": int(next_step_order),
                            "last_sent_at": now,
                            "last_sent_step_order": sent_step_order,
                            "step_started_at": now,
                            "next_run_at": now + timedelta(minutes=next_wait),
                        },
                    )
                    _set_flow_tags(
                        conn,
                        phone=phone,
                        flow_id=flow_id,
                        stage_order=sent_step_order,
                        state="active",
                    )
                advanced += 1
        else:
            retry_minutes = _flow_retry_minutes(flow_entry_rules, cfg)
            with engine.begin() as conn:
                conn.execute(
                    text(
                        """
                        UPDATE remarketing_enrollments
                        SET next_run_at = :next_run_at,
                            updated_at = NOW(),
                            meta_json = COALESCE(meta_json, '{}'::jsonb) || CAST(:meta_patch AS jsonb)
                        WHERE id = :id
                        """
                    ),
                    {
                        "id": enrollment_id,
                        "next_run_at": now + timedelta(minutes=retry_minutes),
                        "meta_patch": '{"last_send_error": true}',
                    },
                )
            failed += 1

    return {
        "ok": True,
        "enabled": True,
        "flow_id": flow_filter_id,
        "flows": len(flow_map),
        "enrolled": int(enrolled),
        "checked": int(checked),
        "sent": int(sent),
        "advanced": int(advanced),
        "held": int(held),
        "resumed": int(resumed),
        "completed": int(completed),
        "exited": int(exited),
        "failed": int(failed),
        "blocked_window": int(blocked_window),
        "service_window_hours": int(service_window_hours),
        "ts": now.isoformat(),
    }
