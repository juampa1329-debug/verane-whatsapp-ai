# ADR-052: Phase 24.8 Admin Premium Gating

Date: 2026-05-28

## Status

Accepted.

## Context

Phase 24.1 through 24.7 added multimodal gateway support, Voice Intelligence, Vision Intelligence, Web/Image Search, Agent Multimodal Tools, multimodal memory/training events and Inbox reference UX. Those capabilities need SaaS-level administration for tenant enablement, plan quotas, provider availability and cost reporting without changing the tenant runtime defaults abruptly.

The existing Intelligence Engine already owns tenant grants, usage recording and Admin `AI Predictivo`. The AI Gateway already records provider/model runs in `saas_ai_runs`, and Web/Image Search already records search runs in `saas_web_search_intelligence_runs`.

## Decision

Implement Phase 24.8 as an Admin control-plane extension over the existing Intelligence/Billing/AI Gateway surfaces:

- Add `saas_intelligence_plan_feature_limits` for plan-level AI feature mode/quota overrides.
- Add `saas_ai_provider_policies` for provider/model availability, request quotas and cost metadata by global, plan or tenant scope.
- Keep default provider behavior compatibility-safe: if no explicit policy blocks a provider or sets a quota, existing tenants continue to run.
- Let explicit provider policies block AI Gateway and Web/Image Search providers before external calls.
- Enforce provider monthly request quota and monthly cost limit when configured.
- Keep tenant grants authoritative over plan limits.
- Add Admin endpoints under `/saas/v1/admin/intelligence/*` for premium-gating overview, plan feature limits and provider policies.
- Extend Admin `AI Predictivo` with Phase 24 tenant controls, plan controls, provider policies, credential summaries and estimated monthly costs.

## Consequences

- Platform admins can activate/demo/disable Phase 24 features per tenant or by plan.
- Provider disablement, request quota and cost caps are enforced centrally before AI/search provider calls.
- Cost reporting is only as accurate as the pricing metadata configured by Admin; zero-cost defaults are intentionally non-commercial placeholders.
- Existing tenants are not blocked by default during rollout.
- Production rollout still needs provider-specific pricing review, quota policy review and acceptance with real provider credentials.

## Safety Boundaries

- No tenant-facing feature is enabled automatically beyond existing entitlement behavior.
- No dependencies, provider SDKs or external billing integrations are added.
- No Meta, CRM, campaign, workflow, memory, training or outbound runtime behavior is changed.
- No decrypted secrets are exposed in Admin; credential summaries show only counts/readiness.
- Future automatic provider purchasing, legal billing invoices from AI cost estimates or per-message customer charging require separate design.
