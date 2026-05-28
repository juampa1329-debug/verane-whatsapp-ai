# ADR-034: Phase 11 AI Platform Ecosystem

Date: 2026-05-27

Status: Accepted

Scope: SaaS only.

## Context

Scentra Phase 11 already includes Intelligence Engine, optional ML infrastructure, product-facing Predictive Intelligence, Advisor briefing, Multi-Agent OS and supervised Autonomous Operational Intelligence. The next requirement is an extensible AI Platform Ecosystem for marketplace items, custom agents, plugin manifests, AI tools, developer apps, event subscriptions, AI apps and external integration metadata.

The platform has sensitive runtime paths: tenant CRM data, Meta channels, outbound messaging, workers, agent execution, billing limits, developer credentials and AI governance. Executing third-party plugin code inside the API or worker would create high operational and security risk without a sandbox, gateway, permission model and staging review.

## Decision

Implement AI Platform Ecosystem as a tenant-scoped control-plane first:

- Add migration `053_saas_ai_platform_ecosystem_phase11.sql`.
- Add backend domain `app_saas/ecosystem` with catalog, schemas, service, router and local `AGENTS.md`.
- Mount tenant APIs under `/saas/v1/ecosystem/*`.
- Add tenant UI `AiEcosystemPanel.jsx` and navigation entry `AI Ecosystem`.
- Add premium feature flags disabled by default:
  - `ai_marketplace`
  - `ai_plugin_center`
  - `ai_developer_console`
  - `ai_tool_registry`
  - `ai_app_framework`
- Allow demo mode to preview catalog/state, but require full feature mode or umbrella `ai_premium` for install/create/update operations.
- Store developer app API keys as hashes and return raw keys only once.
- Keep plugins, tools, AI apps, event subscriptions and external integrations as metadata/control-plane records.
- Allow marketplace agent-template installation to create agent records only through the existing agent service, without bypassing preflight, budgets, memory rules or activation lifecycle.

No untrusted plugin code is executed by the API or worker in this phase.

## Consequences

Positive:

- Creates a governed marketplace/plugin/developer foundation without destabilizing WhatsApp, Instagram, CRM, workers or AI runtime.
- Keeps enterprise ecosystem features tenant-scoped, premium-gated, demo-aware and auditable.
- Preserves existing agent safety controls when marketplace templates create real agent records.
- Provides a clear schema/API/UI surface for future SDK and integration work.

Tradeoffs:

- The current plugin system is not an executable sandbox; it is a registry and lifecycle control-plane.
- Developer app keys are management-plane records only and must not be used as public API authentication until a dedicated gateway exists.
- Event subscriptions record intent and configuration, but broad fanout/execution should be added only after worker/sandbox design review.

## Validation

Validated in the active SaaS Docker stack:

- Frontend tenant build passed.
- API compileall passed inside the rebuilt container.
- `docker compose -f saas-version/docker-compose.saas.yml up -d --build` applied migration `053`.
- API health returned OK.
- Swagger `/docs` returned 200.
- Migration `053` is recorded in `saas_schema_migrations`.
- Ecosystem tables exist in PostgreSQL.
- OpenAPI contains `/saas/v1/ecosystem/overview` and `/saas/v1/ecosystem/marketplace`.
- Authenticated tenant smoke confirmed demo marketplace preview and blocked install without full feature mode.
- Premium-enabled tenant smoke installed a marketplace item and created plugin, tool and developer-app records.
- Browser smoke loaded `AI Ecosystem` with no console errors.
- SQL migration BOM and strict UTF-8 scans passed.
