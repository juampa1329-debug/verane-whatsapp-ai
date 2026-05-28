# ADR-002 PostgreSQL With SQLAlchemy Core Raw SQL

Status: Detected in code.

## Context

SaaS backend uses SQLAlchemy sessions/engine while domain routers and services primarily execute raw SQL/text statements.

## Decision

Use PostgreSQL as the SaaS database and SQLAlchemy Core/raw SQL for data access.

## Consequences

- Migrations are critical because there are no ORM models as full schema source.
- Agents must inspect SQL references before table/column changes.
- Tenant filters and indexes are manually important.
- Runtime defensive table creation in services must be considered alongside migrations.

## Evidence

- `saas-version/backend/app_saas/db.py`
- `saas-version/migrations/*.sql`
- Raw SQL usage across `saas-version/backend/app_saas/**`

