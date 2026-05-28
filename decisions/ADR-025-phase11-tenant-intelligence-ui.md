# ADR-025: Phase 11 Tenant Intelligence UI

Date: 2026-05-26

## Status

Accepted

## Context

Phase 11 already exposed tenant Intelligence APIs for feature state, feature snapshots, predictions, recommendations, feedback and model metrics. Admin `AI Predictivo` could govern tenant grants and model rollout, but tenant users had no direct product surface to inspect or validate predictive outputs.

The codebase already uses a React/Vite client shell in `saas-version/frontend/src/App.jsx` with domain panels and a shared `apiCall` helper for `/saas/v1` routes.

## Decision

Add a tenant-facing `Inteligencia` navigation item and implement `saas-version/frontend/src/IntelligencePanel.jsx` as a thin UI over existing `/saas/v1/intelligence/*` APIs.

The panel supports:

- viewing AI premium grants, modes, sources, quota usage and feature state;
- recomputing tenant feature snapshots;
- generating gated baseline predictions;
- listing predictions and recommendations;
- submitting prediction feedback;
- dismissing open recommendations;
- viewing tenant ModelOps metrics.

No backend contracts, migrations, dependencies, ML runtimes, event brokers, model servers, or trained artifacts are added by this decision.

## Consequences

- Tenants can now validate and use Phase 11 baseline predictive features without platform admin access.
- Backend remains the authority for tenant isolation, roles, grants, quotas, tenant status and model rollout controls.
- Predictions remain rule-based baselines until trained ML pipelines are introduced.
- Seeded tenant API smoke remains required in Docker/staging before production acceptance.

## Safety Rules

- Do not bypass `/saas/v1/intelligence` backend gates from the frontend.
- Do not expose full predictive automation to all tenants by default.
- Keep recommendations advisory unless an explicit future workflow adds approval/preflight execution.
- Reload tenant Intelligence state when the active tenant changes.
