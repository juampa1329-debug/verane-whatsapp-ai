# ADR-021: Scentra Intelligence Engine Phase 11

Date: 2026-05-26.

## Status

Accepted.

## Context

Scentra SaaS already has CRM, Inbox, campaigns, triggers, remarketing, observability, AI Gateway, Advisor, AI Agents, billing and verticalization. The next requested capability is an enterprise-grade hybrid AI + ML intelligence layer with premium feature management, predictive recommendations and multi-tenant safety.

The existing codebase is FastAPI + PostgreSQL + React/Vite. Billing feature flags and tenant overrides already exist. Kimi is already registered as an official AI Gateway provider in `023_ai_gateway_core.sql` and `ai_gateway/registry.py`.

## Decision

Implement Phase 11 as a dependency-light foundation inside the existing SaaS architecture:

- Use a new `intelligence` backend domain.
- Add forward migration `046_saas_intelligence_engine_phase11.sql`.
- Store events, feature values, predictions, recommendations, feature grants, model registry rows and usage in PostgreSQL.
- Add tenant APIs under `/saas/v1/intelligence`.
- Add admin APIs under `/saas/v1/admin/intelligence`.
- Add admin UI view `AI Predictivo`.
- Extend existing billing feature flags instead of creating a separate licensing silo.
- Add tenant-specific grants with `disabled`, `demo` and `full` modes plus quotas.
- Feed latest predictions and recommendations into Advisor context.
- Keep current prediction models as rule-based baselines until real labeled data, ML evaluation and serving infrastructure are ready.

## Consequences

Positive:

- Reproducible clean bootstrap remains possible through SQL migrations.
- No new package, broker or serving dependency is introduced prematurely.
- Premium AI can be controlled by plan, tenant override, grant, quota and admin audit.
- Advisor can use predictive context without auto-executing actions.
- Future ML services can replace baseline predictions behind the same tables/APIs.

Tradeoffs:

- Baseline predictions are not trained ML and must not be sold as final model quality.
- PostgreSQL event storage is sufficient for foundation and audit, but high-volume event streaming will require NATS JetStream or Kafka/Redpanda later.
- Admin UI is the operational control plane; ADR-025 later adds the tenant-facing `Inteligencia` UX on top of the same tenant APIs.

## Guardrails

- Do not train custom LLMs initially.
- Do not add Kafka, Ray, BentoML, MLflow or vector DB dependencies without a focused phase and explicit approval.
- Keep every prediction tenant-scoped.
- Keep feature access gated by billing status, plan flags, tenant flags, grants and quotas.
- Keep recommendations as suggestions unless a separate approved workflow executes them.
