# ADR-008 Billing Plans Limits And Provider Webhooks

Status: Detected in code.

## Context

SaaS has trials, plan codes, subscriptions, entitlements, limits, usage, invoices, credits, checkout sessions, and provider webhooks.

## Decision

Use a SaaS billing domain to manage subscription state, plan/limit behavior, and provider interactions.

## Consequences

- Feature gating can depend on billing state and limits.
- Trial settings are config-driven.
- Provider webhooks must be verified before mutating billing state.
- Admin billing endpoints and tenant billing endpoints both need compatibility checks.

## Evidence

- `saas-version/backend/app_saas/billing`
- `saas-version/backend/app_saas/admin/router.py`
- `saas-version/migrations/033_saas_billing_monetization.sql`
- `saas-version/backend/app_saas/config.py`

