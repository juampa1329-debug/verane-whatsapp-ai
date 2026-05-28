# ADR-022: Phase 11 Derived Intelligence Worker

Date: 2026-05-26

## Status

Accepted.

## Context

Scentra Phase 11 already has an Intelligence event store, feature store, baseline predictions, recommendations and premium gating. The remaining gap was automatic operation: events and features depended on explicit API calls, while existing SaaS domains already write CRM, messages, webhooks, outbound, triggers, campaign A/B, remarketing, AI runs and billing records.

Changing every producer path inline would increase regression risk across Inbox, workers, billing and integrations.

## Decision

Add `app_saas.workers.intelligence` as a derived-event and prediction pipeline.

The worker:

- derives canonical Intelligence events from existing SaaS tables using deterministic `replay_key` values;
- recomputes tenant feature snapshots;
- generates baseline predictions only when premium/demo/full feature gates and quota checks allow it;
- uses a PostgreSQL advisory lock to remain safe when embedded and standalone workers both run;
- is available from embedded worker, standalone worker and Admin Operations.

No new external event broker, ML framework or model-serving dependency is introduced in this step.

## Consequences

- Phase 11 becomes operational without invasive rewrites in all producer domains.
- Event history is idempotent and replay-friendly.
- Automatic predictions now consume Intelligence quotas and must be configured carefully before broad rollout.
- Inline event emission or external streaming can be added later without changing the persisted event schema.
