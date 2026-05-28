# ADR-062 Registration Vertical Pack Drift Tolerance

## Status

Accepted.

## Context

Production registration can create a SaaS user, tenant, owner membership and trial subscription, then immediately apply an industry vertical pack. The vertical pack writes multiple CRM/campaign/audit tables. When production PostgreSQL schema drift left some of those secondary tables/columns/indexes missing, `POST /saas/v1/auth/register` returned 500 and blocked account creation.

The mandatory account/trial path and the optional tenant baseline seed have different operational criticality.

## Decision

Keep user, tenant, membership and trial subscription creation mandatory.

Run `apply_industry_pack` inside a nested transaction/savepoint during registration. If the seed fails, roll back only the seed work, record `auth.register` warning `vertical_pack_apply_failed`, and allow registration to complete.

Also expand migration `071_saas_app_boot_schema_drift_repair.sql` and schema readiness checks to cover registration-adjacent vertical-pack seed tables/columns/indexes and audit events.

## Consequences

- New tenants can register even if a non-critical vertical pack seed path is drifted.
- Operators still need to apply repair migrations and reapply the industry pack later if a warning is recorded.
- The readiness gate should prevent newly deployed API containers from serving traffic when critical schema drift remains.
- This does not weaken auth, CAPTCHA, rate limits, tenant isolation, trial creation or billing behavior.
