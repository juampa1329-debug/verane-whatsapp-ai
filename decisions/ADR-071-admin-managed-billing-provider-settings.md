# ADR-071 Admin Managed Billing Provider Settings

Status: accepted

Date: 2026-05-30

## Context

Scentra already supports Wompi and Mercado Pago checkout/webhooks through backend environment variables. This forces operational changes through Coolify and makes sandbox/live testing inconvenient for the platform owner.

## Decision

Store Wompi and Mercado Pago provider settings in PostgreSQL through SaaS Admin.

- Add `saas_billing_provider_settings`.
- Store test and production credentials separately.
- Encrypt secret values with existing `shared/secrets.py`.
- Expose Admin-only endpoints under `/saas/v1/admin/billing/providers/*`.
- Let Admin choose active provider, test mode and default provider.
- Keep environment variables as compatibility fallback when no DB provider row exists.

## Consequences

- Billing configuration can be managed without Coolify access.
- Sandbox tests can run by enabling `test_mode` and saving test keys.
- Rotating `SAAS_SECRET_KEY` can make saved provider secrets unreadable.
- Existing env-only deployments continue working until an Admin row is saved.
- Stripe remains env-only in this change.

## Safety

- Provider responses mask secrets.
- Blank secret inputs preserve stored values.
- Webhook signature verification remains required outside local mode.
- No billing lifecycle, plan, tenant, Meta, auth or AI behavior changes are introduced.
