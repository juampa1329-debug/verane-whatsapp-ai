# ADR-026: Phase 11 Inline Event Capture

Date: 2026-05-26

Scope: SaaS only.

## Status

Accepted.

Updated by ADR-029 on 2026-05-27: optional ML infrastructure is now approved, but inline event capture itself remains dependency-light and non-blocking.

## Context

Phase 11 originally relied on `app_saas/workers/intelligence.py` to derive canonical Intelligence events from existing SaaS tables. That keeps producer changes low-risk, but some high-value business transitions benefit from near-real-time event availability.

At the time of this decision, the repository still had no approved ML runtime, event broker, model server, Kafka/NATS, MLflow, or trained model dependency. ADR-029 later approved optional ML infrastructure, but inline capture itself remains dependency-light and non-blocking.

## Decision

Add a small backend helper, `app_saas/intelligence/capture.py`, for safe inline event capture.

Initial inline producers are intentionally limited to:

- CRM outbound message creation: `message.sent`.
- Billing paid checkout activation and subscription state changes: `billing.subscription.changed`.

The helper records through `record_event` inside a nested transaction and returns `None` on telemetry failure, logging a bounded warning instead of aborting the business write.

Inline producers use the same deterministic `replay_key` families as the derived worker, so worker passes and API writes remain idempotent.

## Consequences

- Critical CRM/Billing signals become available to the Intelligence event store earlier.
- No schema, API contract, dependency, broker, model-serving, or trained-model change is introduced.
- Producer coverage is deliberately incomplete; additional domains should be added incrementally after runtime smoke.
- Inline telemetry must never become a hard dependency for customer-facing CRM/Billing operations.

## Safety Rules

- Keep `record_inline_event` non-blocking and failure-isolated.
- Preserve tenant_id on every event.
- Preserve deterministic replay keys.
- Do not emit secrets or decrypted provider credentials in event payloads.
- Do not add broker/ML dependencies through inline capture work without explicit approval.
