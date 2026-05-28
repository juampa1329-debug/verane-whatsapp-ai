# ADR-038: Phase 14 Localization And Product Ops

Date: 2026-05-27

## Status

Accepted.

## Context

Scentra SaaS had mixed Spanish/English UI copy and no detected text catalog layer. Phase 14 needed to improve operational release hygiene without changing backend contracts, installing dependencies or refactoring large frontend modules.

## Decision

- Add local dependency-free text catalogs for tenant and Admin frontends.
- Default to Spanish `es-CO`.
- Expose optional build-time locale envs: `VITE_APP_LOCALE` and `VITE_ADMIN_LOCALE`.
- Normalize critical mixed-language UI terms in active tenant/Admin source.
- Add dependency-free Product Ops scripts:
  - `phase14-copy-audit.mjs`
  - `phase14-release-check.mjs`
- Keep official provider/product names unchanged.
- Keep Phase 15 external-agent repository analysis outside `saas-version/` until a separate ADR approves integration.

## Consequences

- Critical copy regressions can be caught before release with a fast Node script.
- The approach is compatible with current React/Vite dependencies and Docker builds.
- Full sentence-level localization remains incremental; the new catalogs provide the safe pattern for future work.
- No API, DB, auth, billing, Meta, worker or ML runtime behavior changes are introduced.

## Validation

Required closeout checks:

- `node saas-version/scripts/phase14-copy-audit.mjs`
- `node saas-version/scripts/phase14-release-check.mjs`
- tenant/admin builds
- Compose config
- Docker migrations/API/Swagger/browser smoke when available
