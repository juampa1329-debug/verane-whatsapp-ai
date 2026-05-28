# ADR-060 Production Auth/Billing Schema Drift Repair

## Status

Accepted

## Context

Production login returned `500 Internal Server Error` on `POST /saas/v1/auth/login`.

Backend logs showed PostgreSQL schema drift:

- `saas_users.locked_until` did not exist during tenant login.
- `saas_billing_subscriptions.payment_failed_notice_sent_at` did not exist during the embedded billing lifecycle worker.

The code expected columns introduced by earlier Phase 1 and Phase 9 migrations. A production database can still drift if an older migration version is marked as applied before all columns were present, because the migration runner skips already-applied versions.

## Decision

Add a new forward migration:

- `069_saas_auth_billing_schema_drift_repair.sql`

The migration is idempotent and repairs:

- tenant industry compatibility columns
- Phase 1 login lockout, password reset, MFA and security-event schema
- Phase 9 billing lifecycle notice columns and indexes

Also coalesce nullable `plan_code` and `industry_code` in tenant auth/list responses to avoid response serialization failures on older tenant rows.

## Consequences

- Existing production data is preserved.
- Demo accounts can be restored immediately by running the same idempotent SQL directly against production PostgreSQL before redeploy.
- Future deploys apply migration `069` automatically even when older drifted migration versions are already marked as applied.
- This does not change auth policy, JWT structure, CAPTCHA behavior, password hashing, billing status semantics, frontend contracts or tenant isolation.

