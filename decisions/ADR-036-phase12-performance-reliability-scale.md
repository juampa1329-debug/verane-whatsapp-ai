# ADR-036 Phase 12 Performance, Reliability & Scale Control-Plane

Date: 2026-05-27

## Status

Accepted.

## Context

Scentra SaaS already has observability, workers, DB-backed queues, AI/ML, campaigns, billing and Meta integrations. Phase 12 needs production-readiness controls without destabilizing provider runtimes or deleting operational history automatically.

## Decision

Implement Phase 12 as an admin-only reliability control-plane:

- Add forward migration `055_saas_performance_reliability_phase12.sql`.
- Add reliability SLO, backpressure, retention, cleanup-run, snapshot and drill tables.
- Add expected high-volume indexes for webhook, outbound, trigger, AI, remarketing, agent, conversation, message, intelligence and audit queries.
- Add `app_saas/reliability/service.py` for SLO status, backpressure, index audit, backup readiness, retention dry-runs, snapshots and drills.
- Add `workers/reliability.py` and call it from embedded and standalone workers.
- Add Admin endpoints and Admin `Performance` UI.

## Safety Constraints

- Retention defaults to disabled and dry-run.
- Destructive retention requires explicit `dry_run=false`, backend allowlisted SQL and platform-admin/superadmin role.
- Backup readiness does not perform backup or restore.
- Backpressure is advisory and does not mutate queues, throttle providers or pause campaigns.
- Reliability worker records snapshots/dry-run telemetry only.

## Consequences

- SaaS has a reproducible Phase 12 schema and Admin surface for operational readiness.
- Operators can detect missing indexes, queue pressure, SLO drift and backup-readiness gaps earlier.
- Real load testing, backup/restore execution and production SLO tuning remain deployment/staging responsibilities, not automatic application behavior.
