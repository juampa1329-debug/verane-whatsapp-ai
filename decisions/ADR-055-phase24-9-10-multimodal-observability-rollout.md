# ADR-055: Phase 24.9-24.10 Multimodal Observability And Safe Rollout

Status: Accepted

Date: 2026-05-28

Scope: SaaS only, `saas-version/`.

## Context

Phase 24 already had multimodal gateway attachments, voice analysis, vision analysis, web/image search with approval, agent multimodal tools, multimodal memory events, Inbox UX and Admin premium/provider gating.

The missing pieces were operational visibility and safe rollout controls:

- cost by media/provider
- latency
- errors
- quality/confidence
- sources used
- default-off rollout flags
- demo mode
- canary

The existing architecture is PostgreSQL-first, tenant-scoped and premium-gated. Phase 24.8 already stores provider policy and pricing metadata in `saas_ai_provider_policies`.

## Decision

Add Phase 24.9/24.10 as a control-plane around the existing multimodal runtime instead of introducing a new media execution path.

Implementation:

- Migration `067_saas_multimodal_observability_rollout_phase24.sql`.
- Tables:
  - `saas_multimodal_observability_snapshots`
  - `saas_multimodal_rollout_policies`
  - `saas_multimodal_rollout_events`
- Default-off feature flags:
  - `multimodal_observability`
  - `multimodal_cost_observability`
  - `multimodal_quality_monitoring`
  - `multimodal_safe_rollout`
  - `multimodal_canary`
- Backend service `app_saas/intelligence/multimodal_observability.py`.
- Tenant endpoints under `/saas/v1/intelligence/multimodal/*`.
- Runtime safe-rollout checks in voice analysis, vision analysis and web/image search before external provider execution.

## Rationale

- Reuses existing audited Phase 24 tables instead of duplicating media state.
- Preserves Phase 24.8 pricing/provider policy as the single source for cost metadata.
- Keeps rollout default-off and opt-in to avoid breaking current tenants.
- Keeps canary deterministic without new dependencies.
- Stores aggregate metrics and rollout decisions only; no raw media or secrets are persisted.

## Safety Boundaries

- No CRM mutation.
- No campaign/workflow activation.
- No billing charges.
- No Meta runtime changes.
- No agent ownership changes.
- No automatic customer sends.
- No raw media/base64/decrypted secret storage.
- No implicit rollout enforcement without feature access and an enabled tenant policy.

## Consequences

- Phase 24 can now be observed and rolled out gradually by tenant/provider/modality.
- Cost estimates are only as accurate as Admin-entered provider pricing metadata.
- Production acceptance still needs real media/search traffic, real provider credentials and real rollout rehearsals.
- Docker runtime validation through migration `067` must be rerun when Docker is reachable.
