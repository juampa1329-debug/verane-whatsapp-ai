# LOCALIZATION_PRODUCT_OPS

Scope: SaaS only. Phase 14 covers product copy governance, release readiness checks and safe handoff practices for `saas-version/`.

## Implemented

- Tenant catalog: `saas-version/frontend/src/i18n.js`.
- Admin catalog: `saas-version/admin-frontend/src/i18n.js`.
- Default locale: `es-CO`.
- Optional frontend envs:
  - `VITE_APP_LOCALE`
  - `VITE_ADMIN_LOCALE`
- Product Ops scripts:
  - `node saas-version/scripts/phase14-copy-audit.mjs`
  - `node saas-version/scripts/phase14-release-check.mjs`

## Current Coverage

Critical user-facing mixed-language fragments were normalized in:

- Tenant main navigation and page metadata.
- Tenant auth shell and brand subtitle.
- Tenant settings tabs.
- Meta/Facebook connection copy.
- Broadcast Meta template labels.
- AI Agents hero/actions/tabs labels.
- AI Ecosystem tabs and default AI app name.
- Intelligence benchmark/advisor labels.
- Admin navigation.
- Admin plan AI-agent labels.
- Admin Performance/Reliability labels.

## Release Gate

Run before handoff:

```powershell
node saas-version\scripts\phase14-copy-audit.mjs
node saas-version\scripts\phase14-release-check.mjs
npm --prefix saas-version\frontend run build
npm --prefix saas-version\admin-frontend run build
docker compose -f saas-version\docker-compose.saas.yml config --quiet
```

When Docker is available, also run migrations and health checks:

```powershell
docker compose -f saas-version\docker-compose.saas.yml up -d --build api worker admin-frontend
docker compose -f saas-version\docker-compose.saas.yml exec -T api python -m app_saas.tools.migrate /app/migrations
```

Then verify:

- API `/saas/v1/health`.
- Swagger `/docs`.
- Admin `/health` or local admin shell.
- Tenant and Admin browser smoke.

## Rules

- Add new user-facing labels to the nearest catalog when they belong to global shell/navigation/product ops.
- Do not add an external i18n dependency without explicit approval.
- Do not translate provider/product names that are official names: Meta, WhatsApp, Instagram, Wompi, Stripe, MercadoPago, OpenRouter, Gemini, Kimi, Mistral.
- Keep API keys, enum values, DB values and provider payload fields unchanged.
- Keep Product Ops checks deterministic and dependency-free unless a future test framework is approved.

## Residual Risk

- The catalog is intentionally lightweight and does not yet externalize every domain-specific sentence in large panels.
- The copy audit protects critical mixed-language regressions, not every possible English word in identifiers, provider names or technical payload examples.
- Full E2E automation is not present; Phase 14 provides reproducible release gates and local build/smoke checks.
