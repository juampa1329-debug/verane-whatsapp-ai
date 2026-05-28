# AI Platform Ecosystem Architecture

Scope: SaaS only. Current implementation is Phase 11 AI Platform Ecosystem control-plane.

## Component Map

```mermaid
flowchart LR
  UI["Tenant AI Ecosystem UI"] --> API["/saas/v1/ecosystem/*"]
  API --> Gate["Intelligence/Billing feature gates"]
  Gate --> Marketplace["AI Marketplace"]
  Gate --> Plugins["Plugin Center"]
  Gate --> Tools["AI Tool Registry"]
  Gate --> Dev["Developer Console"]
  Gate --> Apps["AI App Framework"]
  Gate --> Subs["Event Subscriptions"]
  Marketplace --> DB["PostgreSQL ecosystem tables"]
  Plugins --> DB
  Tools --> DB
  Dev --> DB
  Apps --> DB
  Subs --> DB
  API --> Traces["Ecosystem traces/metrics"]
```

## Runtime Rules

- The ecosystem is a control-plane, not an untrusted code runtime.
- Plugin, tool, external integration and AI app manifests are stored as metadata.
- Mutations require full premium feature access. Demo mode can list/preview.
- Developer app API keys are hashed in DB and raw keys are returned once.
- Marketplace agent template installs can create agents only when explicitly requested and still use the existing `agents.service.create_from_template` path.

## Tables

- `saas_ai_marketplace_items`
- `saas_ai_marketplace_installations`
- `saas_ai_plugins`
- `saas_ai_tool_registry`
- `saas_ai_ecosystem_event_subscriptions`
- `saas_ai_developer_apps`
- `saas_ai_external_integrations`
- `saas_ai_apps`
- `saas_ai_ecosystem_traces`
- `saas_ai_ecosystem_metrics`

## Feature Gates

```mermaid
flowchart TB
  Tenant["Tenant request"] --> State["intelligence_feature_state"]
  State --> Demo["Demo: read/preview"]
  State --> Full["Full: install/create/update"]
  Full --> Marketplace["ai_marketplace"]
  Full --> Plugins["ai_plugin_center"]
  Full --> Developer["ai_developer_console"]
  Full --> Tools["ai_tool_registry"]
  Full --> Apps["ai_app_framework"]
  State --> Premium["ai_premium umbrella"]
  Premium --> Full
```

## Safety Boundary

- No direct Meta, WhatsApp, Instagram, CRM, billing or campaign side effects are executed by ecosystem plugin/app records.
- Tools with `medium` or `high` risk are metadata for approval-first execution through existing governed paths.
- Event subscriptions are persisted for future fanout/orchestration; they do not yet bypass Agent OS or worker approval logic.
