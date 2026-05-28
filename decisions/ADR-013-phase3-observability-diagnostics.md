# ADR-013: Phase 3 Observability And Diagnostics

Date: 2026-05-24

## Status

Accepted.

## Context

SaaS Phase 3 required an operator-facing way to know whether failures happen in API, worker, DB, Meta, AI Gateway, queue processors, channel flows, or outbound/retry paths. The existing admin surface had observability and dead-letter foundations, but it did not expose all queue processors, worker liveness, Meta/AI Gateway health, or reliable retry handling for all critical queues.

## Decision

- Keep observability inside the existing platform admin domain under `/saas/v1/admin/*`.
- Add `saas_worker_heartbeats` as the DB-backed liveness source for embedded and standalone workers.
- Store `correlation_id` on key queue/dead-letter tables through a forward migration.
- Extend admin health to combine API/DB, worker heartbeat, Meta, AI Gateway, queues, channel diagnostics, Meta error history, and dead-letter candidates.
- Add dead-letter retry for retryable source types and admin processors for AI, remarketing, agent orchestration, and Meta token refresh.
- Preserve DB-backed queue patterns and use savepoints around webhook event processing and optional agent orchestration enqueue to prevent transaction poisoning.

## Consequences

- Admin can see and retry critical failure paths from one operational surface.
- Workers remain safe when embedded and standalone loops run together.
- Correlation IDs improve incident tracing without changing public API contracts.
- Production alerting/log retention still requires deployment tooling outside repository code.
- Local validation must avoid simultaneous Compose projects on the same external `coolify` network unless service aliases are isolated.
