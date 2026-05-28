# ADR-019 Phase 9 Billing Operational

Status: Accepted

Date: 2026-05-25

Scope: SaaS only.

## Context

Phase 9 required billing to move from partial provider support to an operational SaaS monetization layer: provider checkout/webhooks, trial/subscription lifecycle, impago blocking, manual admin corrections, invoice history/PDF, and payment failure notices.

## Decision

Keep billing inside the existing SaaS FastAPI/PostgreSQL architecture and extend the current billing domain instead of introducing a new external billing service.

Implemented decisions:

- Use forward migration `044_saas_billing_phase9_operational.sql` for lifecycle notice fields, invoice PDF tracking, checkout provider event recency, and lifecycle indexes.
- Verify Stripe, MercadoPago, and Wompi webhook signatures in `billing/service.py` before mutating checkout, subscription, invoice, payment, provider-event, or tenant state.
- Process billing lifecycle from both embedded API worker and standalone worker through `workers/billing.py`, using interval throttling and a PostgreSQL advisory lock for duplicate-execution safety.
- Keep admin-triggered lifecycle sync as an operational override.
- Block unsafe tenant writes centrally in `main.py` when tenant status is not `active` or `trial`, while keeping billing/auth/admin/health routes reachable.
- Generate dependency-free invoice PDFs in the backend and expose authenticated tenant/admin PDF endpoints.
- Keep manual credits/invoices in platform admin as correction tools.

## Consequences

- Billing can recover expired trials/subscriptions, suspend overdue tenants, create open invoices, age uncollectible invoices, and send one-time notices without manual admin action.
- Provider webhook acceptance now depends on correct production secrets: `STRIPE_WEBHOOK_SECRET`, `MERCADOPAGO_WEBHOOK_SECRET`, and `WOMPI_EVENTS_KEY`.
- Generated invoice PDFs are operational artifacts; tax/legal invoice compliance must be validated per jurisdiction before production billing.
- Worker billing lifecycle must remain idempotent because embedded and standalone workers may run concurrently.
- Future billing changes must update `docs/API_REFERENCE.md`, `docs/DATABASE.md`, `docs/ENVIRONMENT.md`, `architecture/WORKER_FLOW.md`, and billing memory files.

## Files

- `saas-version/migrations/044_saas_billing_phase9_operational.sql`
- `saas-version/backend/app_saas/billing/service.py`
- `saas-version/backend/app_saas/billing/router.py`
- `saas-version/backend/app_saas/workers/billing.py`
- `saas-version/backend/app_saas/workers/runner.py`
- `saas-version/backend/app_saas/main.py`
- `saas-version/backend/app_saas/admin/router.py`
- `saas-version/frontend/src/App.jsx`
- `saas-version/admin-frontend/src/AdminApp.jsx`
- `saas-version/docker-compose.saas.yml`
