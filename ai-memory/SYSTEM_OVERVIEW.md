# SYSTEM_OVERVIEW

Scope: SaaS only.

## One-Line Architecture

React client apps call a FastAPI SaaS API under `/saas/v1`; FastAPI uses PostgreSQL with tenant-aware raw SQL, encrypted credentials, external integrations, and worker processors for asynchronous workflows.

## Components

- Client app: `saas-version/frontend`
- Admin app: `saas-version/admin-frontend`
- API app: `saas-version/backend/app_saas/main.py`
- Domain routers/services: `saas-version/backend/app_saas/*`
- Database migrations: `saas-version/migrations`
- Background jobs: `saas-version/backend/app_saas/workers`
- Deployment: `saas-version/docker-compose.saas.yml`
- Optional ML runtime: Compose profile `ml` with `mlflow`, `ml-service`, and `qdrant`; default API/worker stay ML-disabled.
- Admin deploy target: `admin.scentra-ai.online` through `admin-frontend` Nginx service and Traefik labels.

## Data Boundaries

- Tenant user auth uses `saas_users` plus tenant memberships.
- Platform admin auth uses `saas_platform_admins`.
- Security state uses `saas_security_events`, `saas_password_reset_tokens`, `saas_mfa_challenges`, `saas_privacy_requests`, and lockout/2FA columns on `saas_users`.
- Tenant data should be filtered by tenant_id in application SQL and protected by RLS where migrated.
- Provider secrets are encrypted before storage.
- Billing limits and entitlements gate SaaS capabilities.
- Billing lifecycle runs through admin sync and worker processors; non-operational tenant statuses block unsafe writes while billing recovery stays reachable.
- Verticalization stores tenant industry state on `saas_tenants` and applies industry packs through `app_saas/verticals`.
- Intelligence stores tenant events, feature values, predictions, prediction feedback, model metrics, model registry rollout state/events, recommendations, feature grants and usage under `saas_intelligence_*`.
- Optional ML stores training jobs, model artifacts, inference runs and drift snapshots under `saas_ml_*`; these are premium/feature-gated and disabled by default.
- Multimodal intelligence stores voice/vision/search outputs in dedicated Phase 24 tables, normalized memory/training/RAG signals in `saas_multimodal_memory_events`, aggregate observability snapshots in `saas_multimodal_observability_snapshots`, and rollout controls in `saas_multimodal_rollout_*`; raw media/base64 must not be stored there.
- Autonomous Revenue Engine stores supervised revenue policies, opportunities, forecasts, experiments and reports in `saas_ai_revenue_*`; it is control-plane only and must not execute customer-facing or payment side effects.
- AI Enterprise Memory Network stores tenant-scoped memory graph policies, nodes, edges, sync runs and access logs in `saas_enterprise_memory_*`; graph nodes are reviewable summaries/metadata/hashes, not raw cross-tenant content. Policy governs scopes/retention/customer review, and export/import/delete are audited lifecycle controls.
- Workflow Composer stores templates, workflow graphs, versions, simulations, approvals and `composer_only` materializations under `saas_ai_workflow_*`; it is a safe control-plane and does not execute runtime side effects.
- AI agent ownership is stored on conversations through `assigned_ai_agent_id`/`ai_owner_mode`; one conversation should have only one AI owner at a time.
- Agent memory is split between agent-specific memory vault records and tenant collective memory.
- Phase 13 privacy/compliance exports are tenant-scoped and non-destructive; delete requests are workflow records, not automatic data deletion.

## API Boundary

All public SaaS endpoints are rooted at:

`/saas/v1`

Never document or call root app endpoints as SaaS endpoints unless a router under `app_saas` exposes them.

## Async Boundary

Queue-like work is processed by:

- API embedded worker loop if enabled.
- Standalone Docker `worker` service.

Processors must be treated as potentially concurrent.
Worker liveness/result/error snapshots are recorded in `saas_worker_heartbeats` for Admin health.

## External Boundaries

- Meta WhatsApp Cloud
- Instagram Business / Meta Graph
- WooCommerce
- AI providers through API credentials/gateway
- AI agents through registry, preflight, budget hard stops, prompts, memory vault, and collective memory
- TTS providers through configured credentials
- Billing providers: Stripe, MercadoPago, Wompi with signed provider webhooks
- Turnstile captcha when enabled

## Admin Boundary

- Platform admin UI is separate from tenant UI.
- Production bootstrap is not exposed through HTTP; use the seed tool/service for first superadmin.
- Admin mutation routes are role-gated in backend and audited in `saas_audit_events`.
- Admin observability exposes global health, channel diagnostics, queue snapshots, Meta/AI Gateway status, dead-letter sync/resolve/retry, and manual queue processing.
