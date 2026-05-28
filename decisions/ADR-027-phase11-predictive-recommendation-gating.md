# ADR-027: Phase 11 Predictive Recommendation Gating

Date: 2026-05-26

## Status

Accepted.

## Context

Phase 11 supports baseline predictions and optional persisted recommendations. The default trial/demo state can allow limited prediction previews through `intelligence_demo`, but predictive recommendations are a premium capability with their own feature flag and usage quota.

During extended tenant smoke, a demo prediction with `persist_recommendations=true` could persist an open recommendation even when `predictive_recommendations` was explicitly disabled for the tenant. That weakened premium feature separation.

## Decision

Prediction generation and recommendation persistence are separate access decisions.

- Base prediction generation continues to use the requested prediction feature, tenant status, demo/full mode, quota and model registry state.
- Persisting `saas_intelligence_recommendations` now requires `predictive_recommendations` access and quota.
- Prediction output records `recommendation_gate` metadata so clients/admin can see whether recommendation persistence was requested, enabled, created or blocked.
- Demo prediction previews remain available when `intelligence_demo` allows them.

## Consequences

- A tenant can receive a demo prediction without receiving a persisted recommendation.
- Premium recommendation output can be licensed, quota-controlled and audited independently.
- Existing API contracts remain compatible because the gate is added inside `output_json`.
- No dependency, schema or provider changes are required.

## Validation

Extended clean Docker/PostgreSQL smoke in temporary project `codexsaasphase11predictive` passed:

- migrations through `048`
- API health, Swagger, OpenAPI, admin health, API worker and standalone worker
- tenant registration and seeded CRM data
- feature recompute
- demo `lead_scoring` prediction with disabled `predictive_recommendations`
- zero persisted recommendations while blocked
- full `smart_remarketing` prediction with persisted recommendation
- prediction feedback, model metrics and recommendation dismiss
