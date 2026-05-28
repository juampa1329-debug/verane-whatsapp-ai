# ADR-004 SaaS Integrations Through Tenant Records And Provider Routes

Status: Detected in code.

## Context

SaaS supports external channels and providers including Meta WhatsApp, Instagram Business, WooCommerce, AI/TTS providers, billing providers, and Turnstile.

## Decision

Represent tenant integrations in SaaS backend modules and expose provider-specific operations through `/saas/v1/integrations`, `/saas/v1/integrations/instagram`, `/saas/v1/webhooks`, billing routes, and API credential routes.

## Consequences

- Provider credentials must stay encrypted.
- Webhook verification/signature behavior must be preserved.
- Token health/refresh diagnostics are part of operational support.
- Integrations changes can affect workers, CRM inbox, broadcasts, ads/social, and billing.

## Evidence

- `saas-version/backend/app_saas/integrations`
- `saas-version/backend/app_saas/webhooks`
- `saas-version/backend/app_saas/api_credentials`
- `saas-version/backend/app_saas/billing`
- `saas-version/frontend/src/App.jsx`

