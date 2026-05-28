# ADR-012 Scentra Admin Production Operations

Status: Implemented on 2026-05-24.

## Context

Phase 2 requires the internal Scentra Admin to operate tenants, plans, subscriptions, feature flags, audit, queues, and operational health without exposing production bootstrap or mixing tenant and platform auth.

## Decision

Deploy the Admin as a dedicated frontend surface backed by the existing SaaS API:

- Add `admin-frontend` to `docker-compose.saas.yml`.
- Route `admin.scentra-ai.online` through Traefik labels to the admin Nginx service.
- Use build-time `ADMIN_VITE_*` variables for API base, client app base, CAPTCHA, Turnstile site key, and bootstrap UI toggle.
- Keep HTTP `/admin/auth/bootstrap` local-only.
- Provide first-superadmin creation through the existing `app_saas.tools.create_platform_admin` tool and optional Compose profile service `platform-admin-seed`.
- Keep all admin mutations role-gated in backend and audited through `saas_audit_events`.
- Show effective feature flags in the admin UI by combining plan/default/trial state with tenant overrides.

## Consequences

- The repo can now build and serve the Admin from the same Compose topology as API/worker.
- Production does not need an open bootstrap endpoint.
- Local development can still show bootstrap on localhost or with `VITE_ADMIN_BOOTSTRAP_ENABLED=true`.
- Production deploys must provide correct `ADMIN_VITE_API_BASE`, `ADMIN_VITE_CLIENT_APP_BASE`, `SAAS_CORS_ORIGINS`, secrets, and CAPTCHA env vars.
- Real DNS/TLS issuance remains an environment operation outside the repository.

## Evidence

- `saas-version/docker-compose.saas.yml`
- `saas-version/admin-frontend/Dockerfile`
- `saas-version/admin-frontend/src/AdminApp.jsx`
- `saas-version/backend/app_saas/config.py`
- `saas-version/backend/app_saas/admin/router.py`
- `saas-version/backend/app_saas/tools/create_platform_admin.py`
