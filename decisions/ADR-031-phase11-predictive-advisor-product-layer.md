# ADR-031: Phase 11 Predictive Advisor Product Layer

Status: Accepted

Date: 2026-05-27

Scope: SaaS only.

## Context

Phase 11 already had Intelligence events, feature store, baseline predictions, recommendation gating, ModelOps, optional ML service, MLflow/BentoML infrastructure, auto-label training, model registry, canary routing and shadow inference. Those capabilities were mostly infrastructure/Admin-facing. The user requested that Predictive Intelligence become visible inside the product through CRM, Inbox, dashboards, remarketing and the AI Business Advisor.

The implementation must preserve tenant isolation, premium gating, quotas, model rollout controls, baseline fallback and the existing WhatsApp/Instagram/CRM runtime.

## Decision

Expose Predictive Intelligence as a product layer without changing the underlying event/ML schema:

- Add tenant `GET /saas/v1/intelligence/overview` as a compact RAG/product payload for predictive summaries, cards, latest predictions, open recommendations, CRM aggregates, premium state and ModelOps observability.
- Add tenant `GET /saas/v1/advisor/briefing` to feed the floating Advisor with predictive overview, proactive insights, recommendations, actions, metrics, activity and memory.
- Extend CRM/conversation payloads with `predictive_intelligence` derived from the latest conversation-level predictions when present, with tenant-safe CRM baseline fallback otherwise.
- Surface predictive signals in Dashboard, Inbox and CRM: latest prediction strip, ML/churn badges, `Churn` smart filter, CRM predictive card and conversation-level prediction actions.
- Seed Advisor insights from recent Intelligence predictions and open recommendations, but keep actions as proposals under existing approval patterns.
- Keep persisted predictive recommendations gated separately by `predictive_recommendations`.

## Consequences

- Predictive Intelligence is now visible to tenant users, not only Admin/ModelOps operators.
- The Advisor can behave proactively using stored predictions and recommendations while avoiding hidden side effects.
- CRM and Inbox can request conversation-level scoring for lead, churn and remarketing use cases.
- Product UI can show baseline outputs even when optional ML is disabled, while still exposing ML/shadow metadata when available.
- Production claims still depend on real tenant-safe evaluation; the UI being visible does not certify model accuracy.

## Safety Rules

- Do not let Advisor recommendations auto-execute customer-facing actions.
- Do not bypass feature grants, quotas, model registry status or recommendation gating.
- Do not allow two AI owners to respond to one conversation.
- Do not present bootstrap/autolabel models as certified production accuracy.
- Keep `predictive_intelligence` tenant-scoped and derived only from authorized conversation/customer rows.
- Keep optional ML disabled by default unless a staged rollout explicitly enables it.
