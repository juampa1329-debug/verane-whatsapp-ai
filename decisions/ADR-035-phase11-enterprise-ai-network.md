# ADR-035: Phase 11 Enterprise AI Network And Vertical Intelligence

Date: 2026-05-27

## Status

Accepted.

## Context

Scentra already has Phase 11 foundations: Intelligence Engine, optional ML profile, predictive UI, Advisor briefing, Agent OS, Autonomous Operations and AI Ecosystem control-plane.

The closeout requirement is to add enterprise AI network capabilities:

- vertical AI intelligence
- industry model routing
- anonymized cross-tenant intelligence
- benchmark engine
- vertical advisors
- AI playbook library
- global/industry knowledge network

The platform is multi-tenant, so raw messages, conversations, tenant names, private content and sensitive data must never be shared across tenants.

## Decision

Implement Enterprise AI Network as a privacy-safe control-plane layer inside `app_saas/intelligence`, backed by migration `054_saas_enterprise_ai_network_phase11.sql`.

The layer stores:

- industry model metadata and routing hints
- anonymized benchmark aggregates
- tenant-scoped benchmark comparisons
- tenant-scoped vertical insights
- published vertical playbooks
- aggregate-only knowledge-network nodes
- tenant-private network metric snapshots

Read/preview is allowed in demo mode. Persisted refresh requires full feature access through `enterprise_ai_network`, `cross_tenant_intelligence` or umbrella `ai_premium`.

Industry model records are metadata/routing entries, not heavy LLM training or GPU systems. Playbooks are recommendations/drafts only and do not activate automation.

## Consequences

Positive:

- Phase 11 gains enterprise vertical intelligence without breaking existing runtime flows.
- Tenants can see sector-specific benchmarks, playbooks and advisors in `Inteligencia`.
- Admin plan defaults expose the new feature flags.
- Worker refresh is nested and skip-safe for tenants without full access.
- Cross-tenant intelligence uses aggregate metrics and a minimum sample threshold.

Tradeoffs:

- Benchmarks are useful only after enough tenants exist in the same industry.
- Industry model rows are routing metadata until real reviewed datasets and model promotion exist.
- Additional production tuning is needed for metric definitions, cohorts and benchmark accuracy.

## Safety Rules

- Do not lower the benchmark sample threshold without privacy review.
- Do not include raw message text, conversation bodies, tenant names or sensitive metadata in cross-tenant aggregates.
- Do not auto-activate playbooks, triggers, flows or campaigns from this layer.
- Keep full refresh behind premium/full gating.
- Keep model routing compatible with existing ML registry and baseline fallback rules.
