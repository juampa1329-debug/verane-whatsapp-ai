# ADR-005 DB-Backed Worker Processing

Status: Detected in code.

## Context

SaaS has asynchronous work for webhooks, triggers, remarketing, AI replies, orchestration, outbound messages, and Meta token refreshes.

## Decision

Use DB-backed records/status tables with worker processors. Processing can run through an embedded API loop and/or a standalone worker service.

## Consequences

- Processors must be idempotent and retry-safe.
- Status transitions are part of the concurrency contract.
- Admin operation endpoints can trigger processing manually.
- Running both embedded and standalone workers requires care.

## Evidence

- `saas-version/backend/app_saas/main.py`
- `saas-version/backend/app_saas/workers/runner.py`
- `saas-version/backend/app_saas/workers/*.py`
- `saas-version/docker-compose.saas.yml`

