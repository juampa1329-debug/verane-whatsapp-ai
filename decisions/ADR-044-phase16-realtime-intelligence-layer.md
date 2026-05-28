# ADR-044: Phase 16 Real-Time Intelligence Layer

Date: 2026-05-27

## Status

Accepted

## Context

Scentra already has a PostgreSQL-backed Intelligence Engine with events, feature store, predictions, recommendations, ModelOps, Autonomous Operations, Enterprise AI Network, Workflow Composer and Trust AI.

Phase 16 needs real-time visibility without destabilizing WhatsApp, Instagram, CRM, workers or billing. The current SaaS stack does not run Kafka/NATS/Redis Streams in the default deployment.

## Decision

Implement Phase 16 as a PostgreSQL-first, premium-gated live control-plane:

- Add `saas_realtime_intelligence_sessions`, `saas_realtime_intelligence_cursors`, and `saas_realtime_intelligence_metrics`.
- Add tenant endpoints under `/saas/v1/intelligence/realtime/*`.
- Add Admin overview and metric snapshot endpoints under `/saas/v1/admin/intelligence/realtime*`.
- Use polling as the tenant UI default.
- Expose bounded SSE as an optional transport.
- Sanitize event payloads before returning them.
- Keep alerts advisory and derived from existing Intelligence, Autonomous Ops and Trust AI records.

No broker, WebSocket runtime, new dependency, provider side effect, workflow deployment or autonomous remediation was added.

## Consequences

Positive:

- Phase 16 is deployable on the current Docker/PostgreSQL SaaS stack.
- It preserves tenant isolation and premium/demo gating.
- It creates a clear future seam for NATS/Kafka without changing the persisted event model.
- It improves live operations UX for tenants and platform admins.

Tradeoffs:

- Polling is not as scalable as a real event bus for very high traffic tenants.
- SSE is bounded and API-hosted, not a dedicated streaming service.
- Real-time metrics are operational snapshots, not contractual SLA metrics.

## Safety Rules

- Do not expose raw event payloads without a privacy review.
- Do not auto-execute alerts from this layer.
- Do not add broker infrastructure without a separate ADR, capacity plan, rollback plan and staging validation.
- Do not consume prediction quota on passive dashboard refreshes.
