# PROJECT_CONTEXT

Scope: SaaS only. Source root: `saas-version/`.
Out of scope by default: root `backend/`, root `frontend/`, `ai-service/`, `mobile-android/`, and existing non-SaaS docs. Touch them only if the user explicitly changes scope.

## Product

The active product is Scentra +AI SaaS: a multi-tenant WhatsApp/Instagram/CRM/campaign/AI-agent platform.

Primary code surfaces:

- API: `saas-version/backend/app_saas`
- Client app: `saas-version/frontend`
- Platform admin: `saas-version/admin-frontend`
- Database migrations: `saas-version/migrations`
- SaaS deployment: `saas-version/docker-compose.saas.yml`, `saas-version/infra`

## Runtime Shape

- Backend framework: FastAPI app in `app_saas.main`.
- API base path: all routers are mounted under `/saas/v1`.
- Database: PostgreSQL via SQLAlchemy Core/raw SQL.
- Frontends: React 19 + Vite.
- Containers: Postgres 16, API, worker, frontend image(s) in SaaS folder; optional `ml` profile adds MLflow, ML service and Qdrant.
- Background work: embedded API startup loop plus standalone worker runner.

## Dominant Domains

- Tenant/account lifecycle.
- Tenant users, memberships, roles, platform admins.
- CRM inbox: customers, conversations, messages, labels, tasks, statuses.
- Campaigns, templates, segments, triggers, remarketing flows.
- Broadcasts and Meta WhatsApp template/reporting workflows.
- Ads/social leads/comments and inbox conversion.
- Integrations: WhatsApp Cloud, Instagram Business, WooCommerce, Meta token checks.
- API credentials for AI/TTS providers.
- AI gateway, AI agent settings, advisor, agent registry/governance, knowledge/RAG.
- Voice/multimodal: AI Gateway attachment contract, Voice Intelligence for existing Inbox audio messages, Vision Intelligence for existing Inbox image/document media, Web/Image Search Intelligence with source review and human approval, Agent Multimodal Tools with approved-source prompt context, Multimodal Memory/Training Events for ML/RAG/agent memory capture, Inbox analysis/reference UX for approved human-operated visual references, Admin Phase 24 premium gating for tenant/plan quotas/provider policies/cost controls, multimodal observability, and safe rollout with default-off demo/canary controls.
- Billing, subscriptions, plans, usage, limits, invoices, credits.
- Verticalization, industry packs, onboarding baselines, and tenant pack state.
- Intelligence/ML: feature store, predictions, model registry, optional ML service, training jobs, artifacts, drift, shadow inference, Multi-Agent OS, Autonomous Operational Intelligence, Federated Learning/Global Intelligence, Autonomous Revenue Engine and AI Enterprise Memory Network.
- AI Workflow Composer: premium-gated template/graph/preflight/simulation/approval/versioning control-plane with `composer_only` activation.
- Security/compliance: email OTP MFA, security events, admin security metrics, audit export, privacy exports and delete-request records.
- Webhook endpoints/events and operational observability.

## Source Of Truth

- Do not infer SaaS behavior from the non-SaaS root app.
- For backend behavior, inspect `saas-version/backend/app_saas/**`.
- For schema, inspect `saas-version/migrations/*.sql` first, then runtime SQL in services/routers.
- For frontend behavior, inspect `saas-version/frontend/src/**` and `saas-version/admin-frontend/src/**`.
- For deployment/envs, inspect `saas-version/docker-compose.saas.yml`, `saas-version/backend/app_saas/config.py`, and frontend `README.md` files.
- Root memory files created here are code-derived navigation aids. Pre-existing nested docs under root `docs/` are secondary; verify every claim against `saas-version/` code before acting.

## Agent Memory Contract

After future code changes inside SaaS scope, update:

- `tasks/TASK_STATE.md`
- `ai-memory/CURRENT_STATE.md`
- impacted docs under `docs/`
- impacted diagrams under `architecture/`
- impacted ADRs under `decisions/` when a durable decision changes
- dependency/environment docs when package/env files change

Permanent workflow: before every SaaS task read relevant `AGENTS.md`, `ai-memory/CURRENT_STATE.md`, and `tasks/TASK_STATE.md`; after every change synchronize memory, task state, decisions, affected docs, and risks.
