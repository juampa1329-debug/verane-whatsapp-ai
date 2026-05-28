# ADR-061: Schema Readiness Gate

Date: 2026-05-28

## Status

Accepted

## Context

Production showed route-level 500s after deploy because PostgreSQL migration records and actual runtime schema drifted apart. Examples observed in logs included missing auth/billing columns and later missing CRM/Intelligence columns used by tenant login, registration, Inbox boot, dashboard, integrations and Advisor.

The previous Docker healthcheck targeted `/saas/v1/health`, which only proved that the FastAPI process was alive. That allowed a container to become healthy even when the database schema could not support active SaaS routes.

## Decision

Keep `/saas/v1/health` as a lightweight liveness endpoint.

Make `/saas/v1/ready` the production traffic gate. It checks:

- database connectivity
- expected migration versions for the active `SAAS_MIGRATION_PROFILE`
- critical SaaS runtime tables
- critical columns used by auth, registration, billing lifecycle, Inbox, CRM, campaigns, verticalization, Advisor and Intelligence boot paths

Add `app_saas.tools.schema_check` as a startup/deploy CLI that runs the same contract after `app_saas.tools.migrate` and before Uvicorn.

Change Docker API healthcheck to call `/saas/v1/ready` instead of `/health`.

## Consequences

- A schema-drifted API container should fail startup/readiness instead of serving user-facing 500s.
- Worker/admin services that depend on API health now wait for schema readiness, not only process liveness.
- Production deploys should apply migrations and verify readiness before traffic switch.
- Future schema-critical additions must update `app_saas.shared.schema_readiness`; otherwise the readiness contract can become incomplete.

## Non-Goals

- No business logic was refactored.
- No migration was changed or added.
- No auth, billing, provider, Meta, worker or frontend runtime behavior was changed.
- This is not a replacement for clean PostgreSQL bootstrap tests or staging smoke tests.
