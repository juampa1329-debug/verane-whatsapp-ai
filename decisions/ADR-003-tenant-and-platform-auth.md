# ADR-003 Separate Tenant And Platform Auth

Status: Detected in code.

## Context

SaaS has tenant users/memberships and separate platform admin roles.

## Decision

Use distinct auth paths and authorization models:

- Tenant users: `/saas/v1/auth/*`
- Platform admins: `/saas/v1/admin/auth/*`

## Consequences

- Tenant role checks must not grant platform permissions.
- Platform admin checks must not imply tenant membership.
- JWT validation and role checks are security-critical.
- Impersonation must remain explicit and auditable.

## Evidence

- `saas-version/backend/app_saas/auth/router.py`
- `saas-version/backend/app_saas/admin/router.py`
- `saas-version/backend/app_saas/shared/security.py`

