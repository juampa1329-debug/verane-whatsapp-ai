# SAAS_PROJECT_STATUS

Scope: SaaS only. Source root: `saas-version/`.
Date: 2026-05-28.

## Basis

This status is derived from code inspection of `saas-version/`, SaaS migrations, Docker config, backend routers/services/workers, client frontend, and admin frontend.

Runtime validation note: clean Docker/PostgreSQL bootstrap was validated for Phase 11 on 2026-05-27 with fresh SaaS Compose rebuilds and earlier temporary stacks. The active SaaS stack was later rebuilt through Phase 24.7 with API/worker healthy, OpenAPI checks for the new approved-reference endpoint, frontend build, browser frontend smoke and Phase 24.6 migration `064` already applied. Phase 24.8 validation passed with backend compile, Admin build, Docker Compose config, SQL scans, active Docker rebuild API/worker/Admin, migration `065`, API health, Swagger, Admin health, OpenAPI Phase 24.8 checks, authenticated Admin premium-gating/provider-policy smoke, log scan, Browser Admin-login render smoke and clean isolated PostgreSQL bootstrap `001` to `065`. Phase 19/20 validation passed with backend compile, tenant/Admin builds, Docker Compose config, SQL scans, active Docker rebuild API/worker/Admin, migration `066`, API health, Swagger, OpenAPI Revenue/Memory Network checks, DB confirmation of 10 new tables, authenticated full-mode smoke for revenue opportunities/approve/execute and memory sync/publish, Browser Admin smoke and clean isolated PostgreSQL bootstrap `001` to `066`. Phase 24.9/24.10 local validation passed with backend py_compile, tenant/Admin builds, Docker Compose config, SQL scans, tracked diff whitespace check and manual touched-file whitespace scan; active Docker migration/API/Swagger/clean bootstrap through `067` is pending because Docker was not reachable from the latest Codex session. Phase 24.6 validation covered API/worker/Admin healthy, Swagger `/docs` 200, OpenAPI multimodal memory endpoint checks, DB migration/feature-flag checks, backend compile/import, tenant/Admin frontend builds, SQL scans, Compose config, authenticated multimodal memory sync/materialization smoke, Browser Agent OS UI smoke and clean isolated PostgreSQL bootstrap `001` to `064`. Earlier Phase 24.5 validation covered agent multimodal tools through migration `063`. Earlier Phase 24.4 validation covered web/image search through migration `062`. Earlier Phase 24.3 validation added image/document analysis checks through migration `061`. Earlier Phase 24.2 validation covered voice analysis through migration `060`. Earlier Phase 16 validation covered migration `059`, clean isolated bootstrap `001`-`059`, realtime tenant/Admin API smokes, log scans and browser smokes. Earlier Phase 22 validation covered Trust AI tenant/Admin smokes and browser smokes. Earlier Phase 13 validation also covered Admin reliability smoke, tenant/admin MFA smokes, tenant compliance export smoke, Admin Security Compliance smoke, reliability retention dry-run, AI Ecosystem tenant smoke and Enterprise AI Network tenant smoke. Earlier Phase 11 stacks also validated optional ML profile services, MLflow, Qdrant, auto-label generation, feature pipeline recompute, dataset build, autolabel training, prediction, drift smoke, Admin ML training/registry smoke, shadow inference, inline CRM/Billing events, gated predictive recommendations, tenant predictive smokes, model registration, deterministic canary routing, synthetic training, Agent OS, Autonomous Operations, and admin UI.

Latest Phase 20 hardening validation passed backend `py_compile`, tenant/Admin frontend builds, Docker Compose config and SQL BOM/UTF-8 scans. Active Docker API/Swagger/authenticated export/import/delete smoke remains pending because Docker Desktop was not reachable from the latest Codex session.

## Product Snapshot

Scentra +AI SaaS is a multi-tenant customer messaging, CRM, campaigns, billing, integrations, observability, knowledge/RAG, AI-agent, product-facing predictive intelligence, supervised autonomous operations, AI ecosystem, vertical enterprise intelligence, privacy-safe federated/global intelligence, supervised revenue intelligence and tenant-scoped enterprise memory platform.

Technology detected:

- Backend: FastAPI under `saas-version/backend/app_saas`.
- API base path: `/saas/v1`.
- Database: PostgreSQL 16 in Docker; SQLAlchemy Core/raw SQL.
- Migrations: SQL files executed by `app_saas.tools.migrate`.
- Client app: React 19 + Vite in `saas-version/frontend`.
- Admin app: React 19 + Vite in `saas-version/admin-frontend`.
- Workers: Python worker runner under `app_saas.workers`.
- Integrations: Meta WhatsApp/Instagram/Facebook, WooCommerce, AI provider gateway, Stripe, MercadoPago, Wompi.
- Containers: `saas-version/docker-compose.saas.yml` defines Postgres, API, worker, admin frontend, optional platform admin seed service, and an optional `ml` profile with MLflow, ML service, and Qdrant.

## Migration Repair Status

Completed:

- `022_instagram_business_integration.sql`: UTF-8 BOM removed.
- All `.sql` migrations checked with strict UTF-8 decoding: no BOM and no UTF-8 decode errors remain.
- `030_saas_ai_agent_memory_vault_limits.sql`: ambiguous `max_memory_archives` reference qualified with `saas_ai_agent_plan_limits.max_memory_archives`.
- `036_saas_knowledge_rag_phase8.sql`: `saas_knowledge_sources` now exists before its `ALTER TABLE`; table includes compatibility fields used by runtime knowledge code.
- `002_tenant_columns_non_breaking.sql`: guarded for clean SaaS DBs where legacy root tables do not exist.
- `003_conversations_cutover.sql`: guarded for clean SaaS DBs where legacy root tables do not exist.
- `038_saas_phase1_security_hardening.sql`: added account lockout fields, password reset token table, 2FA-prep fields, and security event indexes.
- `039_saas_phase3_observability_hardening.sql`: added `saas_worker_heartbeats` and `correlation_id` fields/indexes for webhook, outbound, trigger, AI, and dead-letter queues.
- `041_saas_knowledge_rag_phase6_operational.sql`: added sparse-vector metadata on knowledge chunks and tenant-scoped RAG evaluation records.
- `042_saas_campaigns_phase7_operational.sql`: added tenant/channel/entity global quiet-hours configuration and A/B event telemetry for campaign, trigger, and flow execution.
- `043_saas_ai_agents_phase8_operational.sql`: added custom-agent prompt fields, persisted preflight state, eval records, and conversation-level AI ownership.
- `044_saas_billing_phase9_operational.sql`: added billing lifecycle notice timestamps, invoice PDF tracking, provider checkout event recency, and lifecycle indexes.
- `045_saas_verticalization_phase10.sql`: added tenant industry state, vertical pack snapshot fields, and vertical pack application audit.
- `046_saas_intelligence_engine_phase11.sql`: added Intelligence Engine event store, feature values, predictions, recommendations, premium grants, model registry, and usage counters.
- `047_saas_intelligence_modelops_phase11.sql`: added prediction feedback, tenant/model metrics, and feedback-aware baseline registry metadata.
- `048_saas_intelligence_model_rollouts_phase11.sql`: added model rollout governance columns and auditable rollout events.
- `049_saas_ml_infrastructure_phase11.sql`: added tenant-scoped ML training jobs, model artifacts, inference runs, and drift snapshots for optional ML infrastructure.
- `050_saas_ml_training_strategy_phase11.sql`: added event contracts, replay cursors, auto-labels, feature sets/runs, training datasets, model evaluations, and feature-store version metadata.
- `051_saas_multi_agent_operating_system_phase11.sql`: added Agent OS inter-agent messages, runtime traces, tool-run traces, event subscriptions, and Agent OS premium flags.
- `052_saas_autonomous_operational_intelligence_phase11.sql`: added Autonomous Operational Intelligence policies, playbooks, anomalies, actions, reports, and AI operations premium flags.
- `053_saas_ai_platform_ecosystem_phase11.sql`: added AI Marketplace, installations, plugins, tool registry, event subscriptions, developer apps, external integration metadata, tenant AI apps, ecosystem traces/metrics, and AI ecosystem premium flags.
- `054_saas_enterprise_ai_network_phase11.sql`: added Enterprise AI Network vertical industry models, anonymized benchmarks, tenant benchmark comparisons, vertical insights, AI playbooks, aggregate-only knowledge-network nodes, network metrics, and premium flags.
- `055_saas_performance_reliability_phase12.sql`: added reliability SLO policies, backpressure policies, retention policies, cleanup run history, snapshots, drills and performance indexes for high-volume SaaS queues and diagnostics.
- `056_saas_phase13_security_compliance.sql`: added email OTP challenge storage and tenant-scoped privacy request records for Phase 13 security/compliance.
- `057_saas_ai_workflow_composer_phase18.sql`: added Workflow Composer templates, workflows, versions, simulations, approvals, materializations and premium flags.
- `058_saas_ai_trust_compliance_governance_phase22.sql`: added AI Trust Center policies, attestations, risk assessments, model cards, incidents, reports, audits and premium flags.
- `059_saas_realtime_intelligence_phase16.sql`: added Real-Time Intelligence sessions, user cursors, metric snapshots and realtime premium flags.
- `060_saas_voice_intelligence_phase24.sql`: added Voice Intelligence analysis cache and voice premium feature flags.
- `061_saas_vision_intelligence_phase24.sql`: added Vision Intelligence analysis cache and vision/document premium feature flags.
- `062_saas_web_image_search_intelligence_phase24.sql`: added Web/Image Search Intelligence run/result records and external source premium feature flags.
- `063_saas_agent_multimodal_tools_phase24.sql`: added Agent Multimodal Tools premium flags and filtered Agent OS tool-run index.
- `064_saas_multimodal_memory_training_events_phase24.sql`: added Multimodal Memory & Training Events records and premium feature flags.
- Phase 24.7 did not require a migration; it reuses search, multimodal memory and CRM outbound tables.
- `065_saas_multimodal_admin_gating_phase24.sql`: added Phase 24.8 plan feature limits and AI/search/TTS provider policy/cost controls.
- `066_saas_revenue_memory_network_phase19_20.sql`: added Phase 19 revenue policies/opportunities/forecasts/experiments/reports plus Phase 20 enterprise memory graph policies/nodes/edges/sync runs/access logs and premium feature flags.
- `067_saas_multimodal_observability_rollout_phase24.sql`: added Phase 24.9 multimodal observability snapshots plus Phase 24.10 safe-rollout policies/events and default-off feature flags.
- `068_saas_federated_learning_phase17.sql`: added Phase 17 federated learning policies, rounds, update packages, aggregate rows, global intelligence signals and default-off federated/global feature flags.

Checks run:

- `NO_SQL_BOM`.
- `ALL_SQL_UTF8_STRICT`.
- Static order/FK heuristic: `NO_STATIC_ORDER_ISSUES`.
- Docker Compose config: `COMPOSE_CONFIG_OK`.
- Docker/PostgreSQL bootstrap: migrations `001` through `056` applied successfully in the latest Phase 13 validation stack.
- FastAPI health: `/saas/v1/health` returned OK.
- Swagger: `/docs` returned 200.
- Worker: standalone and embedded workers started and reported heartbeat OK.
- Admin frontend: `/health` and index returned 200.
- Knowledge/RAG smoke: tenant register, TXT upload, indexing/vectorization, search, evaluation, and health passed.
- Phase 9 local checks: backend `py_compile`, client build, admin build, Compose config, SQL BOM scan, and `git diff --check` passed.
- Phase 10 local checks: backend `compileall`, client build, admin build, Compose config, SQL BOM scan, strict UTF-8 SQL scan, and SaaS-scope diff whitespace check passed.
- Phase 7 local validation: backend `py_compile`, client build, admin build, Compose config, SQL BOM/UTF-8 checks passed; latest Phase 13 Docker rebuild covered migrations through `056`.
- Phase 8 local validation: backend `py_compile`, client build, admin build, Compose config, SQL BOM scan, and strict UTF-8 SQL scan passed; latest Phase 13 Docker rebuild covered migrations through `056`.

Runtime notes:

- Compose requires external Docker network `coolify`; validation used it locally.
- Local validation used alternate ports when defaults were busy; latest Phase 6 stack used `SAAS_API_HOST_PORT=8060` and `SAAS_ADMIN_HOST_PORT=8061`.
- Avoid running multiple temporary SaaS Compose projects on the same external `coolify` network at the same time because duplicate service aliases such as `scentra-saas-db` can collide.
- Earlier Phase 11 check passed clean Docker/PostgreSQL validation through migration `048`.
- Latest Phase 11 inline-capture check passed tenant smoke for CRM `message.sent` and billing `billing.subscription.changed` events.
- Latest Phase 11 predictive check passed tenant smoke for demo/full grants, feature recompute, gated predictions, recommendation gating, feedback, model metrics, and recommendation dismiss.
- Latest Phase 11 canary check passed admin model registration, `100%` canary selection, `0%` production fallback, and explicit `baseline_rules` scoring metadata.
- Latest Phase 11 ML infrastructure check passed with optional `ml` profile: MLflow, BentoML runtime image, XGBoost, LightGBM, sklearn fallback, Prometheus metrics, Qdrant readiness, synthetic training, auto-label generation, feature pipelines, dataset materialization, autolabel training, prediction, drift evaluation, Admin ML training/registry registration, and shadow inference. Default API/worker remain ML-disabled unless `SAAS_ML_ENABLED=true`.
- Latest Phase 11 Agent OS check passed: migration `051` applied, new Agent OS tables exist, API compileall inside rebuilt container passed, frontend build passed, API health OK, Swagger `/docs` 200, and API/admin/worker/PostgreSQL are running.
- Latest Phase 11 Autonomous Operations check passed: migration `052` applied, new operation policy/playbook/anomaly/action/report tables exist, OpenAPI includes `/intelligence/operations/*`, API `py_compile` for touched modules passed, frontend build passed, API health OK, Swagger `/docs` 200, and authenticated tenant demo/control smoke passed.
- Latest Phase 11 AI Platform Ecosystem check passed: migration `053` applied, ecosystem tables exist, OpenAPI includes `/ecosystem/*`, API compileall passed, frontend build passed, API health OK, Swagger `/docs` 200, tenant demo gating smoke passed, premium-enabled marketplace install/plugin/tool/developer-app smoke passed, and browser smoke loaded `AI Ecosystem` with no console errors.
- Latest Phase 11 Enterprise AI Network check passed: migration `054` applied, vertical network tables exist, OpenAPI includes `/intelligence/network/*`, API compileall passed, frontend/admin builds passed, API health OK, Swagger `/docs` 200, tenant demo center/preview smoke passed, full refresh blocked without full access, premium-enabled full refresh persisted benchmark comparisons and insights, and client/admin browser smokes loaded without console errors.
- Phase 12 Performance, Reliability & Scale is implemented as an admin-only control-plane: migration `055`, reliability service/worker, Admin reliability endpoints, Admin `Performance` view, SLO snapshots, backpressure state, index audit, retention dry-runs, backup-readiness drills and high-volume indexes.
- Phase 13 Security, 2FA & Compliance is implemented: migration `056`, email OTP MFA for tenant/admin login, security notices, Admin Security Center/compliance metrics, audit CSV export, tenant privacy exports and delete-request workflow.
- Phase 14 Localization & Product Ops is implemented: local tenant/Admin Spanish catalogs, critical copy audit, release readiness check, docs/architecture/ADR, and build/browser/Docker validation.

## Phase Progress

Progress is an engineering estimate from detected code, not a production acceptance result.

| Phase | Area | Progress | Status |
| --- | --- | ---: | --- |
| 1 | Seguridad Base | 100% | Code-complete and smoke-tested |
| 2 | Scentra Admin | 100% | Code-complete and smoke-tested |
| 3 | Observabilidad y Diagnostico | 100% | Code-complete and smoke-tested |
| 4 | Inbox Robusto | 100% | Code-complete; build/browser-smoke tested |
| 5 | CRM Comercial | 100% | Code-complete; clean-stack migration validated |
| 6 | Knowledge Base y RAG | 100% | Code-complete and smoke-tested |
| 7 | Campanas, Triggers y Remarketing | 100% | Code-complete; local validation passed |
| 8 | AI Agents Enterprise | 100% | Code-complete; local validation passed |
| 9 | Billing y Monetizacion | 100% | Code-complete; local validation passed |
| 10 | Verticalizacion | 100% | Code-complete; local validation passed |
| 11 | ML, Predictive Intelligence, Agent OS, Autonomous Ops, AI Ecosystem & Enterprise AI Network | 100% | Code-operational with event contracts, auto-labeling, feature pipelines, Postgres dataset builds, MLflow/BentoML image, XGBoost/LightGBM autolabel training, model artifacts, Admin controls, drift/inference logs, shadow inference, product predictive UI, Advisor briefing, Multi-Agent OS control-plane, supervised Autonomous Operational Intelligence, AI Platform Ecosystem marketplace/plugin/tool/developer control-plane, and privacy-safe vertical benchmarks/playbooks/advisors; production acceptance still requires reviewed real tenant data, benchmark cohort tuning and sandbox policy review before executable plugins |
| 12 | Performance, Reliability & Scale | 100% | Code-complete with SLO/backpressure/index/retention/backup-readiness control-plane; production load testing and threshold tuning remain acceptance work |
| 13 | Security, 2FA & Compliance | 100% | Code-operational with email OTP MFA for tenant/admin login, admin Security Center, audit CSV export, privacy exports/delete requests, security notices, and Docker/API smoke validation; production acceptance requires SMTP/Turnstile/secret configuration plus legal review of privacy retention |
| 14 | Localization & Product Ops | 100% | Code-operational with local tenant/Admin Spanish catalogs, critical copy normalization, Product Ops audit scripts, release readiness checks, docs/ADR and validation gates; broader sentence-level catalog expansion remains incremental as modules evolve |
| 15 | Agent Framework Research & Integration | 60% | Phase 15.1A/15.1B/15.1C/15.2/15.3 complete as offline artifacts: 184 templates normalized, 29 disabled drafts evaluated, 7 handoff contracts, 7 playbooks, 4 runbooks and 6 eval rubrics generated; no DB/runtime import yet |
| 16 | AI Real-Time Intelligence Layer | 100% | Code-operational as PostgreSQL-first premium-gated live control-plane with sanitized event feed, tenant sessions/cursors, advisory alerts, Admin realtime overview, metric snapshots, tenant UI and bounded SSE; production acceptance needs traffic/capacity tuning before low-latency SLA claims |
| 17 | Federated Learning & Global Intelligence | 100% | Code-operational as opt-in, premium-gated, aggregate-only control-plane with tenant policies, local update packages, federated rounds, weighted aggregates, global signals, worker auto-participation behind full gates and tenant UI; production acceptance needs Docker/bootstrap through `068`, multi-tenant cohort rehearsal, privacy review and ModelOps promotion runbook |
| 18 | AI Workflow Composer | 100% | Code-operational as premium-gated control-plane: templates, graph editor, preflight, side-effect-free simulation, approvals, versions, rollback and `composer_only` activation; runtime trigger/flow/campaign deployment intentionally requires a future explicit materialization design |
| 19 | Autonomous Revenue Engine | 100% | Code-operational and hardened as premium-gated supervised revenue control-plane: configurable policies, action-type allowlist, monthly metadata execution cap, opportunities, forecasts, reports, playbooks, tenant endpoints, worker integration and tenant UI; no sends, CRM mutations, campaign/workflow activation or payment-provider calls |
| 20 | AI Enterprise Memory Network | 100% | Code-operational and hardened as tenant-scoped memory graph: policies, nodes, edges, sync runs, node review, export/import/delete, worker integration, tenant UI controls, allowed-scope/retention/customer-review enforcement; no raw cross-tenant content sharing and no candidate memory publication without review |
| 22 | AI Trust, Compliance & Governance | 100% | Code-operational as premium-gated governance control-plane: policies, attestations, risk assessments, model cards, incidents, reports, audits, tenant Trust AI UI and Admin Trust AI overview; legal certification and automatic enforcement remain out of scope |
| 24 | Voice & Multimodal Intelligence | 100% | Phase 24.1 through 24.10 are code-operational: AI Gateway attachments, Voice Intelligence, Vision Intelligence, Web/Image Search with approval, Agent Multimodal Tools, Multimodal Memory & Training Events, Inbox analysis/reference UX, Admin/Premium Gating, observability for cost/latency/errors/quality/sources, and Safe Rollout with default-off flags, demo mode and canary. Automatic AI/agent reference sending remains intentionally out of scope. |

## Phase 1: Seguridad Base

Implemented evidence:

- Client Turnstile in login/register: `saas-version/frontend/src/App.jsx`.
- Client Turnstile in password recovery/reset: `saas-version/frontend/src/App.jsx`.
- Admin Turnstile in login/bootstrap/recovery/reset: `saas-version/admin-frontend/src/AdminApp.jsx`.
- Backend CAPTCHA verification: `app_saas/shared/captcha.py`.
- Rate limiting and security events: `app_saas/shared/security_events.py`.
- Auth/admin routes call CAPTCHA/rate-limit/security logs: `app_saas/auth/router.py`, `app_saas/admin/router.py`.
- Admin bootstrap is locally restricted in backend.
- Temporary account lockout is persisted on `saas_users.failed_login_count` and `saas_users.locked_until`.
- Password recovery/reset is implemented with hashed, expiring, single-use tokens in `saas_password_reset_tokens`.
- Password change is implemented for authenticated users.
- 2FA preparation is persisted with `two_factor_enabled`, `two_factor_method`, `two_factor_secret_ref`, and recovery hash metadata fields.
- Docker Compose passes Phase 1 lockout/reset/SMTP env vars into API/worker containers.
- Phase 1 smoke test passed on a clean Docker/PostgreSQL stack: register/trial, login, forgot/reset, login after reset, 2FA preference, password change, admin bootstrap/login, and lockout after failed attempts.

- Operational notes:

- Full login challenge enforcement is now handled by Phase 13 using email OTP MFA. TOTP remains intentionally unimplemented until a separate authenticator-app design is approved.
- Password recovery email delivery in production requires SMTP env vars.
- CAPTCHA closure depends on `SAAS_CAPTCHA_ENABLED=true`, `TURNSTILE_SECRET_KEY`, `VITE_CAPTCHA_ENABLED=true`, and `VITE_TURNSTILE_SITE_KEY` in deployment.
- Production secret/CORS values still need deployment verification before public traffic.

## Phase 2: Scentra Admin

Implemented evidence:

- Admin frontend exists: `saas-version/admin-frontend`.
- Admin auth login/bootstrap: `app_saas/admin/router.py`.
- Admin routes cover tenants, plans, subscriptions, feature flags, audit, queues, billing, observability, and operations.
- Manual platform admin creation tool exists: `app_saas/tools/create_platform_admin.py`.
- Admin frontend Dockerfile exists and `docker-compose.saas.yml` now includes `admin-frontend`.
- Traefik labels route `admin.scentra-ai.online` to the admin frontend service.
- `ADMIN_VITE_API_BASE`, `ADMIN_VITE_CLIENT_APP_BASE`, `ADMIN_VITE_CAPTCHA_ENABLED`, `ADMIN_VITE_TURNSTILE_SITE_KEY`, and `ADMIN_VITE_BOOTSTRAP_ENABLED` drive admin build-time config.
- CORS includes `https://admin.scentra-ai.online` and the local admin compose port `8011`.
- Optional Compose profile service `platform-admin-seed` runs `app_saas.tools.create_platform_admin` for secure first-superadmin creation without opening bootstrap in production.
- Admin UI hides local bootstrap outside localhost unless explicitly enabled.
- Tenant feature flag view now shows effective plan/default/trial features plus tenant overrides instead of only explicit override rows.

Validation:

- Clean Docker/PostgreSQL stack with API, worker, and admin frontend started successfully.
- Admin frontend `/health` returned OK and index returned 200.
- Optional admin seed service created a superadmin on the clean DB.
- Admin login succeeded and `/admin/auth/me` returned `superadmin`.
- Smoke covered overview, tenants, tenant detail, tenant status/plan update, feature flag override, support impersonation token, plan creation, subscriptions, credits, invoices, audit, queues, observability, dead-letter sync, and queue processors.
- CORS preflight succeeded for `https://admin.scentra-ai.online` and local `http://127.0.0.1:8011`.

Operational notes:

- Real DNS, TLS certificate issuance, and Coolify deployment still depend on the production environment, but the repo now contains the deployable service and routing config.
- Production must provide strong `SAAS_JWT_SECRET`, `SAAS_SECRET_KEY`, DB password, CAPTCHA keys, and `ADMIN_VITE_*` build vars.

## Phase 3: Observabilidad y Diagnostico

Implemented evidence:

- Admin health endpoint: `/saas/v1/admin/observability/health`.
- Dead-letter list/sync/resolve/retry endpoints in admin router.
- Queue processing endpoints for webhooks, outbound, scheduled triggers, AI pending replies, remarketing, agent orchestration, and Meta token refresh.
- Observability service computes global health, worker heartbeat, channel diagnostics, failed queues, Meta/webhook/outbound/AI failure signals, AI Gateway state, and Meta error history.
- Meta diagnostics/token health exist in integrations routes.
- Request middleware returns correlation IDs and guarded 500s include the correlation ID.
- Webhook events preserve/generate correlation IDs.
- `039_saas_phase3_observability_hardening.sql` adds worker heartbeats and queue/dead-letter correlation indexes.
- Webhook ingestion isolates each event with a savepoint; optional agent orchestration enqueue is savepoint-isolated and safe for nullable UUID fields.
- Admin UI `Salud` shows global cards, queues, workers, channels, dead-letter diagnosis/retry, and Meta error history.

Validation:

- Clean Docker/PostgreSQL stack applied migrations `001` through `039`.
- API `/saas/v1/health`, Swagger `/docs`, admin `/health`, admin index, admin login, and `Salud` view passed.
- Worker heartbeat reported two fresh workers: `api-embedded-worker` and `worker-local`.
- Admin operation endpoints returned 200 for webhooks, outbound, triggers, AI, remarketing, agents, and Meta token refresh.
- Seeded webhook event processed successfully into inbox/message/orchestrator records without transaction aborts.
- Seeded dead-letter retry requeued an outbound source and preserved its correlation ID.

Operational notes:

- Production log aggregation, retention, alerting, and real provider-error volumes still depend on deployment tooling outside repository code.
- Meta/AI statuses report real configuration state; missing production credentials will correctly surface as degraded/signals.
- A nullable UUID cast bug was fixed in the Phase 3 orchestration path; similar patterns outside Phase 3 should be audited when AI/integration domains are touched.

## Phase 4: Inbox Robusto

Implemented evidence:

- Conversation/message inbox in client app.
- Message states include `sent`, `delivered`, `read`, `failed`, `blocked` in workers/frontend.
- Assignment, SLA fields, filters, hot leads, human takeover, and unread queues exist.
- Comments view and Meta Business Suite-like comment handling exist in frontend/social/ads paths.
- Attachments/audio/emojis are implemented in frontend and outbound worker paths.
- CRM side panel, tasks, status events, and message status cards are present.
- `GET /conversations` now supports optional server-side `channel` and `queue` filters for unread, mine, unassigned, SLA overdue, hot, human takeover, and AI queues.
- Client Inbox now uses visibility-aware polling, avoids overlapping refreshes, shows sync status/errors, pauses in background, and refreshes after filter/search changes.
- Browser notifications are available with explicit browser permission, separate from the in-app sound toggle.
- Conversation assignment can be operated from the Inbox with assign-to-me and release actions.

Validation:

- `python -m py_compile saas-version/backend/app_saas/crm/router.py` passed.
- `npm --prefix saas-version/frontend run build` passed.
- `npm --prefix saas-version/admin-frontend run build` passed.
- `npm --prefix saas-version/admin-frontend run build` passed.
- `docker compose -f saas-version/docker-compose.saas.yml config` passed.
- Browser smoke against Vite client at `http://127.0.0.1:5174/` loaded the app shell with no console errors.

Operational notes:

- Realtime WebSocket/SSE transport is not required for Phase 4 closure; the implemented transport is robust polling with visibility/backoff behavior.
- Live production acceptance still needs real Meta webhook events to verify delivered/read provider status behavior across WhatsApp, Instagram, and Facebook.
- Clean Docker/PostgreSQL bootstrap was rerun in Phase 6 and covers migrations through `041`; Phase 4 live delivered/read status still requires real Meta webhook traffic.

## Phase 5: CRM Comercial

Implemented evidence:

- CRM customers/conversations, labels, stages, tags, notes, payment status, assignment, SLA, tasks, and lead score exist.
- Tenant-scoped custom-field definitions now exist with governed values stored under conversation `profile_json.custom_fields`.
- Configurable default CRM pipeline and stages now exist, including industry presets derived from the SaaS vertical-agent catalog.
- Customer timeline now unifies messages, CRM tasks, delivery/status events, and explicit CRM events.
- Dedupe candidates and controlled customer merge are implemented with merge audit snapshots and timeline trace.
- AI can read configured CRM/custom fields and update only allowed CRM/custom fields with tool and `can_update_crm` policy gating in `app_saas/ai_agent/service.py`.
- Saved segments for campaigns/broadcasts exist through `saas_segments`.
- Tenant frontend can manage custom fields, pipeline presets/stages, customer fichas, timeline, and duplicate merge from the CRM/Inbox UI.

Remaining:

- Lead scoring remains deterministic/rule-based; predictive scoring belongs to Phase 11 ML.
- Production acceptance should include real tenant CRM data, duplicate merge rehearsal, and AI CRM update smoke with configured custom fields.
- Clean Docker/PostgreSQL bootstrap for migration `040` was covered by the Phase 6 clean stack that applied migrations `001` through `041`.

## Phase 6: Knowledge Base y RAG

Implemented evidence:

- Upload endpoint supports file ingestion, including PDF extraction through `pypdf` when available.
- TXT and CSV uploads are supported; CSV is normalized into column/row text before chunking.
- URL ingestion/crawling, source list, health, search, reindex source/all, delete, RAG evaluation, and evaluation-history endpoints exist.
- Source/chunk tables are tenant scoped.
- Search returns scored chunks, sparse-vector score, lexical score, matched terms, context, citations, retrieval logs, and health metrics.
- Chunk indexing stores local sparse-vector metadata in `saas_knowledge_chunks.vector_json`; no new package or external vector DB was introduced.
- `saas_knowledge_evaluations` stores quality score, answerability, pass/fail, expected sources, citations, and metadata per tenant.
- AI prompt context can include knowledge citations.
- URL crawling blocks credentials, localhost, and private-network targets before fetch.
- Client UI shows source status, parser, vectorized chunks, retrieval mode, search citations, and quality-evaluation history.

Validation:

- Clean Docker/PostgreSQL stack `codexsaasphase6` applied migrations `001` through `041`.
- API health, Swagger `/docs`, OpenAPI, worker startup, and admin health passed.
- API smoke passed for tenant registration, TXT upload, indexing/vectorization, RAG search, RAG evaluation, and Knowledge health.

Remaining:

- Production acceptance should include large PDF/CSV samples and real AI reply smoke with tenant provider credentials.
- High-scale semantic search should be revisited in Phase 12 if pgvector/external vector DB becomes necessary.

## Phase 7: Campanas, Triggers y Remarketing

Implemented evidence:

- Trigger conditions/actions, comments, labels, schedules, cooldown, `block_ai`, flow/remarketing worker, and Meta templates exist.
- `037_saas_campaigns_phase7_enterprise.sql` adds simulation/preflight/version/quiet-hours/A-B structures.
- `042_saas_campaigns_phase7_operational.sql` adds `saas_campaign_quiet_hours` and `saas_campaign_ab_events`.
- Backend campaign router has draft and persisted preflight checks, activation blocking for campaigns/triggers/flows when not ready, trigger simulator, trigger version history, rollback restore, global quiet-hours settings, and A/B report endpoints.
- Trigger conditions now cover words, comments, templates, tags, schedules, CRM stage, payment status, customer type, and commercial intent.
- Workers enforce global quiet hours plus trigger/flow quiet hours, cooldown, `block_ai`, A/B variant selection, A/B event telemetry, scheduled-trigger requeue during quiet hours, and remarketing flow pauses during quiet hours.
- Internal trigger/remarketing templates reject archived/non-sendable templates before queueing.
- Broadcast enqueue and outbound dispatch both re-check Meta template approval before sending queued/retried template messages.
- Client Campaigns UI exposes global quiet hours, campaign/flow preflight, flow A/B configuration/reporting, and remarketing controls.
- Client Trigger Builder exposes simulator, preflight, trigger quiet hours, A/B variants/report, version history, rollback, and CRM-stage/status condition simulation.

Validation:

- `py -3 -m py_compile` passed for campaigns router/schemas and trigger, remarketing, dispatch, broadcast workers.
- `npm --prefix saas-version/frontend run build` passed.
- `npm --prefix saas-version/admin-frontend run build` passed.
- `docker compose -f saas-version/docker-compose.saas.yml config --quiet` passed.
- SQL checks returned `NO_SQL_BOM` and `ALL_SQL_UTF8_STRICT`.

Operational notes:

- Latest Phase 13 Docker rebuild covered migrations through `056`; live production acceptance still needs real Meta template/provider traffic.
- Live production acceptance still needs real Meta template/provider traffic to verify approved-template behavior end-to-end.
- A/B reporting currently tracks queued/failed message variants; deeper conversion attribution belongs to a later analytics/ML phase.

## Phase 8: AI Agents Enterprise

Implemented evidence:

- AI agent catalog, plan limits, memory vault, import/export/delete memory, collective memory, prompt version table, tool approvals, budgets, health score, orchestrator, and agent professor exist.
- Preflight endpoint exists: `/saas/v1/agents/{agent_id}/preflight`.
- Runtime metrics include health, tokens, latency, failed/skipped runs, estimated cost, and budget usage.
- Tool/action drafts and human approval surfaces exist.
- `043_saas_ai_agents_phase8_operational.sql` adds custom-agent flags, prompt template/rendered fields, stored preflight result, eval records, and conversation AI ownership columns.
- Agent activation now runs preflight and blocks activation when required checks fail.
- Runtime AI processing enforces agent hard-stop budget before provider execution.
- Factory and custom agents store a system prompt template, prompt variables, and rendered prompt.
- Client UI can create a Custom Agent, edit the fillable system prompt, edit variables JSON, run preflight, and see budget/runtime state.
- Inbox conversations can be manually assigned to an active AI agent or released back to general AI.
- `GET /conversations` supports `agent_id` filtering and returns assigned AI agent name/type/mode.
- Auto-router/orchestrator assignment persists `assigned_ai_agent_id`; once assigned, general AI is disconnected to prevent two AIs replying to the same conversation.
- If an assigned agent becomes unavailable/inactive, conversation AI skips instead of falling back silently to general AI.
- Conversation AI now injects collective memory from `saas_ai_agent_collective_memory` in addition to agent-specific/tenant context.
- Agent archive/delete flow preserves memory by default; archived memory can be restored, exported, imported, or deleted later from the memory vault.

Validation:

- `python -m py_compile` passed for touched agents, orchestrator, conversation AI, and CRM backend modules.
- `npm --prefix saas-version/frontend run build` passed.
- `docker compose -f saas-version/docker-compose.saas.yml config` passed.
- SQL BOM and strict UTF-8 checks passed.

Operational notes:

- Latest Phase 13 Docker rebuild covered migrations through `056`; production/staging acceptance still needs real provider traffic, assignment and memory-vault rehearsal.
- Production/staging acceptance should include real tenant conversations, budget hard-stop smoke with provider credentials, manual and automatic agent assignment, and memory-vault restore/delete rehearsal.
- Deeper enterprise A/B prompt experimentation and precision/CSAT analytics should be expanded in future analytics/ML work, but core Phase 8 safety gates are now implemented.

## Phase 9: Billing y Monetizacion

Implemented evidence:

- Billing service supports Stripe, MercadoPago, and Wompi checkout/webhooks.
- Admin manual credits and invoices exist.
- Tenant/subscription statuses include trial, active, past_due, cancelled, suspended.
- Plan limits and usage enforcement exist in `app_saas/billing/limits.py`.
- Admin lifecycle sync endpoint exists and billing lifecycle now also runs from embedded/standalone workers.
- `044_saas_billing_phase9_operational.sql` adds lifecycle notice timestamps, invoice PDF tracking, and provider event recency.
- Provider webhooks now verify Stripe, MercadoPago, and Wompi signatures before mutating billing state.
- Stripe checkout/invoice/subscription events, MercadoPago payment events, and Wompi approved/failed events update subscription, invoice, checkout, and payment state.
- Trial/subscription expiry, past-due grace, suspension, open invoice creation, failed-payment notices, and uncollectible invoice aging are handled by `sync_billing_lifecycle`.
- Unsafe tenant writes are blocked centrally when tenant status is not `active` or `trial`, while billing/auth/admin/health remain reachable.
- Tenant and platform admin UIs can list invoices and download generated PDF invoice artifacts.
- Docker Compose exposes `SAAS_BILLING_LIFECYCLE_INTERVAL_MINUTES` and `BILLING_PAST_DUE_GRACE_DAYS`.
- Local validation passed: backend `py_compile`, client build, admin build, Compose config, SQL BOM scan, and `git diff --check`.

Production acceptance:

- Run real sandbox/provider webhook tests for Wompi, Stripe, and MercadoPago with production secrets.
- Confirm legal/tax invoice format requirements for target jurisdictions before using generated PDFs as official tax invoices.
- Latest Phase 13 Docker rebuild covered migrations through `056`; production acceptance still requires provider sandbox/live webhook tests and legal/tax PDF validation.

## Phase 10: Verticalizacion

Implemented evidence:

- `045_saas_verticalization_phase10.sql` adds `industry_code`, vertical pack snapshot fields, and `saas_vertical_pack_applications`.
- `app_saas/verticals` exists with catalog, schemas, router, service, and local `AGENTS.md`.
- Industry packs are implemented for general, retail, ecommerce, restaurant, hotel, health, education, real estate, support, automotive, financial services, legal, insurance, beauty, and services.
- Tenant registration, tenant creation, and admin tenant industry changes accept/apply `industry_code`.
- Vertical pack application updates the default CRM pipeline, CRM custom fields, labels, CRM message templates, segments, trigger drafts, remarketing flow drafts, quiet-hours defaults, and optional recommended agents.
- Trigger packs are seeded inactive and flow packs are seeded as draft.
- Recommended agent creation is explicit in the tenant UI and remains disabled by default during registration/admin changes.
- Client registration has an industry selector backed by `/verticals/public-packs`.
- Client Settings has an `Industria` tab with current pack state, KPI counts, recommended agents, application history, and apply controls.
- Admin tenant detail exposes industry selection and pack-applied status.

Validation:

- Backend `compileall` passed for verticals, main, auth, tenants, admin, and agent service modules.
- `npm run build` passed in `saas-version/frontend`.
- `npm run build` passed in `saas-version/admin-frontend`.
- `docker compose -f saas-version/docker-compose.saas.yml config --quiet` passed.
- SQL checks returned `NO_SQL_BOM` and `ALL_SQL_UTF8_STRICT`.
- SaaS-scope `git diff --check` passed.

Production acceptance:

- Latest Phase 13 Docker rebuild covered migrations through `056`; staging review of each industry pack remains required before changing mature production tenants.
- Review every industry pack on staging with real tenant CRM/campaign data before changing mature production tenants.
- Operators must still run preflight and activate triggers/flows intentionally after applying a pack.

## Phase 11: ML & Predictive Intelligence

Implemented foundation:

- `046_saas_intelligence_engine_phase11.sql` adds tenant-scoped event store, feature values, predictions, recommendations, AI premium grants, model registry and usage counters.
- Backend domain `app_saas/intelligence` exposes catalog/state/events/features/predict/predictions/recommendations APIs.
- Admin APIs under `/admin/intelligence/*` expose AI & Predictive Features Management.
- Admin UI `AI Predictivo` can inspect tenant predictive usage and set feature mode to disabled/demo/full.
- Billing/admin feature catalogs include `intelligence_demo`, `ai_premium`, `ml_predictions`, `lead_scoring_ml`, `churn_prediction`, `smart_remarketing`, `ai_operational_intelligence`, `predictive_recommendations`, `advanced_analytics`, and `ai_advisors_premium`.
- Baseline rule predictions exist for lead scoring, churn prediction, smart remarketing and operational anomaly detection.
- `workers/intelligence.py` derives canonical events from existing SaaS tables, recomputes tenant feature snapshots and generates gated baseline predictions on a cooldown.
- `047_saas_intelligence_modelops_phase11.sql` adds tenant-scoped prediction feedback and model metrics for accuracy, sample size, confidence, error, and drift baselines.
- `048_saas_intelligence_model_rollouts_phase11.sql` adds model registry rollout controls and rollout event audit records.
- `049_saas_ml_infrastructure_phase11.sql` adds tenant-scoped ML training jobs, model artifact records, inference run logs, and drift snapshots.
- `050_saas_ml_training_strategy_phase11.sql` adds event contracts, replay cursors, auto-labels, feature sets/runs, training datasets, model evaluations, and feature-store version metadata.
- `051_saas_multi_agent_operating_system_phase11.sql` adds inter-agent messages, runtime traces, tool-run traces, event subscriptions, and Agent OS premium flags.
- `052_saas_autonomous_operational_intelligence_phase11.sql` adds operation policies, playbooks, anomalies, actions, reports, and AI operations premium flags.
- `053_saas_ai_platform_ecosystem_phase11.sql` adds marketplace/installations, plugins, tool registry, ecosystem event subscriptions, developer apps, external integration metadata, tenant AI apps, ecosystem traces/metrics, and ecosystem premium flags.
- `054_saas_enterprise_ai_network_phase11.sql` adds Enterprise AI Network vertical industry models, anonymized benchmarks, tenant benchmark comparisons, vertical insights, AI playbooks, aggregate-only knowledge network nodes, network metrics, and premium flags.
- Optional ML runtime is isolated behind Compose profile `ml`; default `api` and `worker` stay lightweight and ML-disabled.
- `saas-version/backend/Dockerfile.ml` and `saas-version/backend/requirements-ml.txt` provide the ML image with MLflow, BentoML, XGBoost, LightGBM, scikit-learn, pandas/numpy, joblib, and Prometheus client.
- `app_saas/ml_service` exposes `/health`, `/models`, `/train/synthetic`, `/datasets/build`, `/train/autolabel`, `/predict`, `/drift/evaluate`, and `/metrics`.
- Synthetic and Postgres auto-label training support lead scoring, churn prediction, smart remarketing, and operational anomaly detection without requiring private external datasets.
- ML service logs experiments to MLflow when available, saves local model artifacts, registers BentoML models, records training jobs/artifacts/inference/drift rows when DB access is available, and remains safe if DB logging is unavailable.
- Event contracts and feature set definitions are seeded defensively at runtime and backed by migration `050`.
- Auto-labeling derives labels from existing SaaS events/state: CRM/payment conversions, inactivity/negative engagement windows, campaign/broadcast response or failure signals, and recent operational failure rates.
- Feature pipelines compute subject-level features for lead scoring, churn and smart remarketing plus tenant-level operational anomaly features, with `feature_set_key`, `feature_version`, and quality metadata.
- Dataset building joins `saas_ml_auto_labels` with `saas_intelligence_feature_values`, writes CSV/manifest artifacts, and records `saas_ml_training_datasets`.
- Autolabel training uses LightGBM, XGBoost or sklearn fallback from Postgres-derived labels/features, records offline evaluations, and can register the trained artifact as a shadow candidate.
- The Intelligence worker can prepare labels/features only when `SAAS_ML_AUTO_TRAIN_ENABLED=true`; the default is off.
- Tenant APIs now expose prediction feedback and model metrics.
- Admin APIs and Admin `AI Predictivo` expose ModelOps metrics plus manual recompute.
- Admin APIs and Admin `AI Predictivo` expose model registry registration/status, shadow/canary/production rollout mode, traffic percent, feedback, accuracy, drift and production-readiness assessment.
- Admin APIs and Admin `AI Predictivo` now expose ML infrastructure overview, training dataset readiness, and synthetic ML training/registry registration when `SAAS_ML_ENABLED=true`.
- Prediction generation now blocks disabled/paused models and selects active canary registry rows deterministically by traffic percent.
- Prediction output records `scoring_engine = baseline_rules` by default. When ML is explicitly enabled and a selected registry artifact is ready, scoring can call the ML service; when shadow inference is enabled, the trained candidate runs in parallel without changing the baseline business result.
- ML inference output is nested under `output_json.ml_inference` so baseline fallback, shadow status, model key/version, score, label, latency, and errors are auditable.
- Shadow/unapproved canary predictions are persisted as `shadow` and do not auto-create recommendations.
- Persisted recommendations are gated separately from prediction generation: demo previews can run through `intelligence_demo`, but writing `saas_intelligence_recommendations` requires `predictive_recommendations` access/quota.
- Prediction output includes `recommendation_gate` metadata so clients/admin can audit requested/enabled/created/blocked recommendation persistence.
- Client UI now exposes `Inteligencia` through `saas-version/frontend/src/IntelligencePanel.jsx`.
- Tenant Intelligence now has `/intelligence/overview` for executive summaries, predictive cards, CRM aggregates, latest predictions/recommendations and ModelOps observability.
- Tenant users can inspect grants/usage, feature snapshots, predictions, recommendations, feedback state and model metrics.
- Tenant users can recompute features, generate gated baseline predictions, submit prediction feedback and dismiss recommendations through existing `/saas/v1/intelligence/*` APIs.
- Dashboard, Inbox and CRM now surface predictive signals: latest prediction strip, predictive badges, `Churn` filter, and conversation-level lead/churn/remarketing prediction actions.
- The Intelligence worker recalculates model metrics after tenant pipeline runs.
- Embedded and standalone workers now include Intelligence processing, and Admin Operations exposes `/admin/operations/intelligence/process`.
- Admin `AI Predictivo`, `Operacion` and `Salud` can trigger Intelligence processing manually.
- `intelligence/capture.py` safely records selected inline events with a nested transaction.
- CRM outbound message creation emits `message.sent` events with `message:{id}` replay keys.
- Billing paid checkout activation and subscription state changes emit `billing.subscription.changed` events with worker-compatible replay keys.
- Advisor context includes recent predictions and open recommendations.
- `GET /advisor/briefing` powers the floating Advisor with predictive summaries, proactive insights, recommendations, actions, activity, metrics and memory without auto-executing actions.
- Agent OS exposes `/agents/os`, inter-agent messages, event-sync and tool-run traces for specialized-agent coordination without direct side-effect tool execution.
- Autonomous Operations exposes `/intelligence/operations/center`, `/control`, `/analyze`, `/actions`, and action approve/execute/dismiss endpoints for AI Operations Center and AI Control Center.
- `intelligence/operations.py` detects webhook, outbound, dead-letter, Meta subscription, campaign, trigger, inactivity, lead-priority and worker-degradation signals.
- Autonomous Operations supports Levels 0-4. Demo mode can preview/analyze, but backend policy forces auto-remediation and low-risk auto-execute off.
- Current autonomous execution records controlled/auditable action results and does not directly mutate Meta, queues, campaigns, CRM or billing.
- Intelligence worker runs Agent OS sync and Autonomous Operations analysis in nested transactions so failures do not break existing Intelligence, Meta, CRM or automation runtime.
- Tenant `Inteligencia` now includes AI Operations Center, AI Control Center, autonomous actions and operational reports.
- AI Platform Ecosystem exposes `/ecosystem/*` for marketplace, installations, plugins, tools, event subscriptions, developer apps, SDK manifest, external integrations, tenant AI apps, overview and metrics.
- Enterprise AI Network exposes `/intelligence/network/center`, `/intelligence/network/refresh`, and `/intelligence/network/playbooks` for vertical intelligence, privacy-safe benchmarks, vertical advisors, playbooks, industry-model metadata and knowledge-network nodes.
- Tenant `AI Ecosystem` view exposes Marketplace, Plugin Center, Tool Registry, Event Subscriptions, Developer Console, Integrations and AI Apps.
- Tenant `Inteligencia` view now exposes Industry Intelligence Center, Benchmark Dashboard, Industry Insights Panel, AI Playbook Marketplace, Industry AI Models and AI Knowledge Network.
- Ecosystem records are metadata/control-plane only: untrusted plugin code is not executed by API/worker, and medium/high-risk tool records remain approval-first metadata.
- Ecosystem mutations require full premium feature mode through `ai_marketplace`, `ai_plugin_center`, `ai_developer_console`, `ai_tool_registry`, `ai_app_framework`, or `ai_premium`; demo mode can preview.
- Enterprise AI Network persisted refresh requires full premium feature mode through `enterprise_ai_network`, `cross_tenant_intelligence`, or `ai_premium`; demo mode can preview.
- Enterprise AI Network feature flags are `enterprise_ai_network`, `vertical_ai_intelligence`, `industry_ai_models`, `benchmark_intelligence`, `cross_tenant_intelligence`, `vertical_ai_advisors`, and `ai_playbook_library`.
- Cross-tenant intelligence is aggregate-only with minimum benchmark sample count `3`; raw messages, conversations, tenant names, private content and sensitive data are not shared.
- Architecture and roadmap are documented in `docs/SCENTRA_INTELLIGENCE_ENGINE.md` and `architecture/INTELLIGENCE_ENGINE.md`.

Still pending for full Phase 11 production acceptance:

- Expand inline event emission beyond CRM outbound and billing subscription changes where near-real-time fanout is required.
- Review auto-label quality/distribution with real tenant-safe data and define acceptance thresholds before production promotion.
- Promote models through staged shadow/canary/full rollout after human review; current synthetic and auto-label models are bootstrap artifacts, not production-quality guarantees.
- Add richer drift/quality monitoring, cost controls, alerting, and rollback runbooks before broad enablement.
- Decide whether Qdrant should become the production vector/RAG layer; it is present in the optional ML profile but not wired into the existing Knowledge/RAG runtime.
- Add external event streaming only when volume requires it; Kafka/NATS were intentionally not added to the default stack.
- Keep Autonomous Operations in supervised mode until each self-healing playbook has staging evidence, rollback rehearsal and explicit approval for real side effects.
- Tune anomaly thresholds and autonomy policies with real tenant traffic before enabling Level 3/4 broadly.
- Design a real plugin sandbox/external developer API gateway before enabling executable third-party plugins or public API-key authentication.
- Tune benchmark cohorts/metrics with real industry traffic before using benchmark deltas in commercial claims.
- Extend production acceptance with real tenant/provider traffic and larger data volumes.

Validation:

- Backend compile passed for touched modules.
- Tenant frontend build passed after the `Inteligencia` UI update.
- Admin frontend build passed.
- Compose config passed with `docker compose -f saas-version/docker-compose.saas.yml config --quiet`.
- SQL BOM scan returned none and strict UTF-8 decode passed.
- SaaS-scope `git diff --check` passed.
- Clean Docker/PostgreSQL stack `codexsaasphase11inline` applied migrations through `048`.
- API `/saas/v1/health`, Swagger `/docs`, OpenAPI `/openapi.json`, admin `/health`, API worker, and standalone worker started.
- Tenant smoke passed for register, customer creation, outbound CRM send, and persisted `message.sent` inline event.
- Billing smoke passed for subscription state change and persisted `billing.subscription.changed` inline event.
- Clean Docker/PostgreSQL stack `codexsaasphase11rollout` applied migrations through `048`; API health, Swagger, OpenAPI, admin health, API worker and standalone worker started.
- Authenticated Admin smoke passed for model registry list, model assessment, model PATCH, rollout event audit, and admin audit event.
- Clean Docker/PostgreSQL stack `codexsaasphase11predictive` applied migrations through `048`; API health, Swagger, OpenAPI, admin health, API worker and standalone worker started.
- Extended tenant predictive smoke passed for tenant registration, seeded CRM customers, feature recompute, disabled `predictive_recommendations`, demo `lead_scoring` prediction, zero persisted recommendations while blocked, full `smart_remarketing` prediction, recommendation creation, feedback, model metrics and recommendation dismiss.
- Clean Docker/PostgreSQL stack `codexsaasphase11canary` applied migrations through `048`; API, worker and admin frontend started.
- Authenticated canary smoke passed for admin model registration, tenant grant, feature recompute, `100%` canary prediction, `0%` fallback to production baseline, and `baseline_rules` scoring metadata.
- Browser smoke loaded Scentra Admin from `http://127.0.0.1:8087/` with no console errors.
- Spanish tracking PDF regenerated from `docs/SEGUIMIENTO_PROYECTO_SAAS_ES.md`.
- Clean Docker/PostgreSQL bootstrap through migration `048` passed with temporary Phase 11 projects including `codexsaasphase11predictive` and `codexsaasphase11canary`.
- Optional ML profile validation stack `codexsaasml` applied migrations through `049`; API, worker, Admin, MLflow, ML service and Qdrant started healthy.
- Direct ML service smoke passed for synthetic LightGBM training, prediction and drift evaluation.
- Admin ML smoke passed for synthetic XGBoost training, artifact logging, MLops overview and registry row creation in shadow mode.
- Optional ML training-strategy validation stack `codexsaasmltrain` applied migrations through `050`; API, worker, Admin, MLflow, ML service and Qdrant started healthy.
- Admin/data-intelligence smoke passed for auto-label generation, feature pipeline recompute, ML dataset build, autolabel training, offline evaluation recording, registry shadow candidate creation, direct prediction and drift evaluation.
- Tenant shadow inference smoke passed: baseline churn prediction stayed authoritative while trained shadow model returned `ml_inference.ok = true` under `baseline_rules+ml_shadow`.
- Active SaaS stack rebuild applied/skipped migrations through `056`; operation policy/playbook/anomaly/action/report tables, Enterprise AI Network tables, reliability tables and Phase 13 MFA/privacy tables exist. OpenAPI exposes `/intelligence/operations/*`, `/intelligence/network/*`, `/admin/reliability/*`, `/admin/security/compliance`, and `/compliance/*`; API health OK, Swagger `/docs` 200, worker tick includes reliability/intelligence processing, and authenticated Admin reliability/Security smokes passed.
- Strict Docker log scan for API and worker found no recent `Traceback`, unhandled exception or `ERROR:` entries after Phase 13 rebuild.

## Phase 12: Performance, Reliability & Scale

Implemented scope:

- `055_saas_performance_reliability_phase12.sql` creates SLO, backpressure, retention, cleanup-run, snapshot and drill tables.
- High-volume indexes were added for webhook processing, outbound dispatch, scheduled triggers, pending AI replies, remarketing, agent orchestration, inbox filters, message analytics, intelligence event windows and audit reads.
- `app_saas/reliability/service.py` exposes SLO status, backpressure state, PostgreSQL index audit, retention policies/runs, snapshots, backup readiness and drills.
- Embedded and standalone workers call `process_due_reliability`, which records snapshots at most every 15 minutes and runs enabled retention dry-runs only.
- Admin backend exposes `/admin/reliability/*` plus `/admin/operations/reliability/process`.
- Admin frontend includes `Performance` with SLO metrics, backpressure by queue, index audit, retention policies, cleanup runs, drills, snapshots and safe action buttons.

Safety model:

- Retention policies are disabled and dry-run by default.
- Destructive cleanup is backend role-gated and SQL-allowlisted.
- Backup readiness is metadata-only; real backup/restore remains infrastructure tooling.
- Backpressure is advisory; no provider throttling, campaign pausing or queue mutation is automatic.

Remaining production acceptance:

- Run dedicated load tests for API, inbox, webhooks, workers, campaigns, RAG and admin views with staging-scale data.
- Tune SLO thresholds, backpressure thresholds and retention windows using real traffic.
- Execute real backup/restore drills with database infrastructure.
- Decide cache/partitioning strategy only after measured bottlenecks.

## Phase 13: Security, 2FA & Compliance

Implemented scope:

- `056_saas_phase13_security_compliance.sql` creates `saas_mfa_challenges` and `saas_privacy_requests`.
- Tenant login can return an email OTP challenge when the user has 2FA enabled or the role is configured as mandatory through `SAAS_MFA_REQUIRED_ROLES`.
- Admin login can return an email OTP challenge when the platform admin has 2FA enabled or the role is configured as mandatory through `SAAS_ADMIN_MFA_REQUIRED_ROLES`.
- OTP verification endpoints issue MFA-verified JWTs; refresh rejects MFA-required sessions that were not verified.
- Tenant and admin security settings expose email OTP state; production enablement requires SMTP outside local mode.
- Security notification emails are triggered for password reset/change and 2FA policy changes when `SAAS_SECURITY_NOTIFY_ENABLED=true`.
- Tenant compliance API exports current-user data and selected customer/conversation data; delete requests are recorded for review instead of hard-deleting automatically.
- Admin Security Center exposes 2FA/user/webhook/security-event/privacy metrics and audit CSV export.
- Admin frontend adds `Security`; tenant settings add compliance export/delete-request actions.
- Worker SQL compatibility fixes removed Phase 11 intelligence tick errors found during Phase 13 validation.

Validation:

- Backend `python -m compileall app_saas`.
- Tenant frontend `npm run build`.
- Admin frontend `npm run build`.
- Docker Compose rebuild of API/worker/admin frontend.
- Migration runner applied/skipped through `056`.
- API `/saas/v1/health` returned OK and Swagger `/docs` returned 200.
- Tenant MFA smoke passed: enable 2FA, login challenge, OTP verify, token returned.
- Admin MFA smoke passed: bootstrap admin, enable 2FA, login challenge, OTP verify, platform token returned.
- Tenant compliance export smoke passed.
- Admin Security Compliance smoke passed and temporary smoke users/tenants were cleaned.
- API/worker logs showed no traceback/error pattern after rebuild.

Remaining production acceptance:

- Configure SMTP, Turnstile, strong JWT/secret keys and production CORS/domains before public rollout.
- Legal/privacy team must approve retention and fulfillment procedure for `saas_privacy_requests`.
- TOTP/authenticator-app support is not implemented; current approved method is email OTP.
- Secret rotation runbooks and webhook signature staging tests remain operational acceptance items.

## Phase 14: Localization & Product Ops

Implemented:

- Local tenant text catalog: `saas-version/frontend/src/i18n.js`.
- Local Admin text catalog: `saas-version/admin-frontend/src/i18n.js`.
- Default locale `es-CO`; optional build-time envs `VITE_APP_LOCALE` and `VITE_ADMIN_LOCALE`.
- Critical Spanish baseline normalization for top-level tenant/Admin navigation, page titles, settings tabs, Meta/Facebook connection flow, Broadcast template labels, AI Agents, AI Ecosystem, Intelligence benchmarks and Admin Performance labels.
- Product Ops copy audit: `node saas-version/scripts/phase14-copy-audit.mjs`.
- Product Ops release gate: `node saas-version/scripts/phase14-release-check.mjs`.
- Frontend package scripts expose `phase14:copy-audit` and `phase14:release-check` without adding dependencies.
- New docs/architecture/ADR: `docs/LOCALIZATION_PRODUCT_OPS.md`, `architecture/LOCALIZATION_PRODUCT_OPS.md`, and `decisions/ADR-038-phase14-localization-product-ops.md`.

Validation target:

- Copy audit and release check must pass before release handoff.
- Tenant/Admin Vite builds must pass.
- Docker Compose config, migrations, API health, Swagger and browser smoke should be rerun when the local Docker stack is available.

Operational notes:

- No backend/API/DB/auth/billing/Meta/worker runtime behavior changed in Phase 14.
- Official provider/product names remain untranslated where they are identifiers or brand names.
- Full long-tail sentence localization remains an incremental maintenance practice, now guided by catalogs and audit gates.

## Phase 15: Agent Framework Research & Integration

Phase 15.1A is complete at documentation level after analyzing the full local repo at `external-repos/agency-agents/` in read-only mode. The earlier external README at `D:\Juan Pablo\Descargas\README.md` was used as initial context only.

Detected from local files:

- The external repo is `agency-agents`, described as "The Agency".
- The local `LICENSE` is MIT.
- 184 valid agent Markdown templates were detected with frontmatter.
- 16 strategy/playbook/docs files were detected without agent frontmatter.
- 14 agent categories plus strategy docs are present.
- The local folder is not a standalone nested Git repo, so exact upstream commit/tag remains unverified.
- Install/convert/lint scripts were reviewed as text only and were not executed.
- Valuable content for Scentra is agent taxonomy, persona structure, NEXUS playbooks/handoffs, success metrics, workflow patterns, eval rubrics and governance inspiration.
- It must not be imported blindly or executed inside Scentra API/worker.

Phase 15.1/15.2/15.3 recommended scope:

- Phase 15.1B: Template Normalizer And Risk Classifier. Completed as offline script/artifacts.
- Phase 15.1C: Disabled Draft Marketplace Import. Completed as disabled draft metadata artifacts only.
- Phase 15.2: NEXUS Playbooks And Handoff Model. Completed as offline handoff/playbook artifacts.
- Phase 15.3: Agent Eval And QA Harness. Completed as offline eval/rubric artifacts.
- License/attribution verification with upstream URL and commit/tag.
- Template normalization for Scentra factory/custom agents.
- Mapping to industries, marketplace packs, Agent OS roles, tool permissions and memory policies.
- Pilot import of reviewed templates as disabled marketplace drafts only after review.
- ADR before any import beyond documentation.

Files added:

- `saas-version/scripts/phase15-agent-template-intake.mjs`
- `saas-version/scripts/phase15-nexus-eval-harness.mjs`
- `docs/PHASE15_1_AGENCY_AGENTS_RESEARCH.md`
- `docs/phase15_1/agent_template_inventory.json`
- `docs/phase15_1/agent_template_inventory.csv`
- `docs/phase15_1/agent_template_drafts.json`
- `docs/phase15_1/agent_template_risk_report.md`
- `docs/phase15_1/nexus_handoff_contracts.json`
- `docs/phase15_1/nexus_playbooks.json`
- `docs/phase15_1/agent_eval_rubrics.json`
- `docs/phase15_1/agent_eval_results.json`
- `docs/phase15_1/phase15_2_15_3_report.md`
- `docs/FASE11_ML_TRAINING_GUIDE_ES.md`
- `docs/ROADMAP_PHASES_16_25_EVALUATION.md`
- `docs/INFORME_FASE15_1_FASE11_ML_ROADMAP_ES.md`
- `docs/Scentra_Fase15_1_Fase11_ML_Roadmap_16_25.pdf`
- `architecture/AGENT_TEMPLATE_INTAKE.md`
- `decisions/ADR-039-phase15-1-agency-agents-research.md`
- `decisions/ADR-040-phase15-1b-1c-offline-agent-template-intake.md`
- `decisions/ADR-041-phase15-2-15-3-nexus-eval-harness.md`

What is still needed before implementation:

- Source URL, upstream commit hash/release tag and attribution requirements.
- Confirmation whether the local folder has private modifications.
- Secret/data scan confirmation before import.
- Approved first categories/templates for real Admin import.
- Admin review UI/import path approval if drafts should enter `saas_ai_marketplace_items`.
- Confirmation that no secrets, tokens, customer data or private prompts are included.

Safety constraints:

- Do not run external install scripts.
- Do not install external agents globally into Codex/Claude.
- Do not run external plugin code in Scentra.
- Keep imported templates disabled/draft until human review.
- Preserve tenant isolation, premium gating, tool approval, memory governance and the one-AI-owner conversation rule.

## Phase 16: AI Real-Time Intelligence Layer

Phase 16 is code-operational as a PostgreSQL-first live intelligence control-plane.

Implemented:

- Migration `059_saas_realtime_intelligence_phase16.sql`.
- Runtime tables `saas_realtime_intelligence_sessions`, `saas_realtime_intelligence_cursors`, and `saas_realtime_intelligence_metrics`.
- Backend service `saas-version/backend/app_saas/intelligence/realtime.py`.
- Tenant endpoints `/saas/v1/intelligence/realtime/center`, `/events`, `/sessions`, `/cursor`, `/sessions/{id}/close`, and bounded `/stream`.
- Admin endpoints `/saas/v1/admin/intelligence/realtime` and `/saas/v1/admin/intelligence/realtime/metrics/refresh`.
- Feature flags `realtime_intelligence_layer`, `realtime_event_stream`, `realtime_ai_alerts`, and `realtime_intelligence_dashboard` in backend defaults, Admin defaults and Intelligence catalog.
- Tenant UI in `IntelligencePanel.jsx` for realtime status, live metrics, advisory alerts, sanitized event feed, event mix, session state and cursor updates.
- Admin `AI Predictivo` realtime overview with per-tenant activity, active sessions, latest metrics and feature modes.
- Event payload redaction for sensitive keys before tenant display.

Safety model:

- Phase 16 is read/control-plane first.
- Default product transport is polling; bounded SSE exists for future clients.
- No Kafka, NATS, Redis Streams, WebSocket broker or new dependency was added.
- Alerts are advisory and do not execute CRM, campaign, Meta, billing, workflow, agent, Trust AI or model rollout side effects.
- Admin metric refresh writes only snapshot rows.

Validation:

- Backend compileall for Intelligence/Admin/Billing modules.
- Tenant frontend build.
- Admin frontend build.
- Docker Compose config.
- SQL BOM and strict UTF-8 migration scans.
- Docker rebuild of API, worker and Admin frontend.
- Active migration runner applied/skipped migrations through `059`.
- Clean isolated PostgreSQL bootstrap applied migrations `001` through `059` and confirmed realtime tables.
- API `/saas/v1/health`, Swagger `/docs` and Admin `/health` returned OK.
- OpenAPI contains tenant/Admin realtime endpoints.
- Tenant realtime smoke passed: event creation, sanitized center/feed, session registration, cursor persistence and session close.
- Admin realtime smoke passed: overview and metric snapshot refresh.
- API/worker recent log scan found no traceback/error pattern.
- Browser smoke loaded tenant `AI Inteligencia`, Admin shell and Swagger with no console errors.
- `git diff --check` passed for SaaS/docs/architecture/memory/task/decision scope.

Remaining production acceptance:

- Run traffic/capacity tests before committing realtime latency SLAs.
- Decide which plans/tenants receive full realtime mode versus demo mode.
- Add broker/event-streaming infrastructure only after measured volume requires it and after a separate ADR.

## Phase 18: AI Workflow Composer

Phase 18 is code-operational as a premium-gated workflow control-plane.

Implemented:

- Migration `057_saas_ai_workflow_composer_phase18.sql`.
- Backend domain `saas-version/backend/app_saas/workflow_composer/`.
- API prefix `/saas/v1/workflow-composer`.
- Tenant frontend panel `saas-version/frontend/src/WorkflowComposerPanel.jsx`.
- Navigation/i18n integration in `App.jsx` and `i18n.js`.
- Feature flags `ai_workflow_composer` and `workflow_composer_templates` in backend defaults, Admin defaults and Intelligence catalog.
- Seeded safe templates for lead qualification, churn recovery, campaign optimization review, operations incident response and NEXUS-style agent discovery/handoff.
- Draft workflow creation from blank graph or template.
- Graph node/edge editor with event, condition, AI decision, approval, action, delay, handoff and end node types.
- Preflight scoring with readiness, risk level and checks for graph completeness, high-risk action approvals and secret avoidance.
- Side-effect-free simulation with planned actions and blockers.
- Approval request/review flow.
- Version snapshots and rollback.
- `composer_only` materialization and activation.

Safety model:

- Demo mode can show overview/templates.
- Write/control endpoints require full `ai_workflow_composer`.
- Simulation never executes side effects.
- Activation does not deploy triggers, flows, campaigns, WhatsApp/Instagram sends, CRM writes or agent handoffs.
- Runtime deployment from Composer requires a future explicit materialization design and ADR.

Validation:

- Backend compileall passed for Composer and app entrypoint.
- Tenant frontend build passed.
- Admin frontend build passed after feature flag additions.
- Docker rebuild applied migration `057`; API and worker started healthy.
- Clean temporary PostgreSQL bootstrap applied migrations `001` through `057`.
- API health OK and Swagger `/docs` returned 200.
- Authenticated smoke passed: instantiate template, preflight ready, simulation completed, approval approved, activation active with `composer_only` materialization.
- Browser smoke loaded the Composer UI and verified demo-state render, reachable nav, templates count and disabled write controls.

Remaining production acceptance:

- Decide which plans/tenants receive full `ai_workflow_composer`.
- Add a separate runtime materialization path if Composer should deploy reviewed drafts into triggers/flows/campaigns.
- Review imported Phase 15 artifacts before exposing them as tenant templates.

## Phase 22: AI Trust, Compliance & Governance

Phase 22 is code-operational as a premium-gated AI governance control-plane.

Implemented:

- Migration `058_saas_ai_trust_compliance_governance_phase22.sql`.
- Backend domain `saas-version/backend/app_saas/trust_center/`.
- Tenant API prefix `/saas/v1/trust-center`.
- Admin API prefix `/saas/v1/admin/trust-center`.
- Tenant frontend panel `saas-version/frontend/src/TrustCenterPanel.jsx`.
- Admin `Trust AI` view in `saas-version/admin-frontend/src/AdminApp.jsx`.
- Feature flags `ai_trust_center`, `ai_governance_policies`, `ai_risk_assessments`, `ai_model_cards`, `ai_compliance_reports`, and `ai_audit_exports` in backend defaults, Admin defaults and Intelligence catalog.
- Default governance policies, policy attestation, risk scan preview/persist, risk mitigation status, model card registry, incident workflow, audit list and compliance report generation.

Safety model:

- Demo mode can preview/read Trust AI state.
- Mutations require full feature access and operational tenant status.
- Risk scans inspect metadata from existing AI surfaces but do not execute repairs, deploy workflows, promote models, pause agents, mutate queues, send messages or change billing.
- Generated reports are operational evidence snapshots, not legal certification.

Validation:

- Backend compileall passed for Trust Center and app entrypoint.
- Tenant frontend build passed.
- Admin frontend build passed after adding Trust AI navigation/view.
- Docker rebuild for API/worker/Admin passed.
- Active migration runner applied/skipped through `058`.
- Clean isolated PostgreSQL bootstrap applied migrations `001` through `058` and confirmed the six core Trust AI tables.
- API health OK, Swagger `/docs` 200, Admin `/health` 200.
- OpenAPI contains tenant/Admin Trust Center endpoints.
- Tenant Trust smoke passed in demo mode and Admin Trust smoke passed with temporary users cleaned afterwards.
- Browser smoke loaded Admin and Swagger with no console errors.

Remaining production acceptance:

- Legal/security review of policy language, incident process and compliance report wording.
- Tenant-specific policy attestation before enabling higher autonomy or executable marketplace/runtime features.
- Audit sampling with real tenant data and retention policy approval.
- Plan/tenant enablement policy for full Trust AI features.

## Phase 24: Voice & Multimodal Intelligence

Phase 24.1 is complete as a gateway foundation. Phase 24.2 is complete as the first runtime Voice Intelligence capability. Phase 24.3 is complete as the first runtime Vision Intelligence capability for existing Inbox images/documents/files. Phase 24.4 is complete as approval-first Web/Image Search Intelligence with source tracking. Phase 24.5 is complete as agent-scoped read-only multimodal tools. Phase 24.6 is complete as sanitized multimodal memory/training/RAG event capture. Phase 24.7 is complete as Inbox analysis/reference UX for approved human-operated visual references. Phase 24.8 is complete as Admin/Premium Gating. Phase 24.9 is complete as multimodal observability. Phase 24.10 is complete as default-off safe rollout with demo/canary controls.

Implemented:

- Phase 24.1 gateway foundation:
- `GatewayAttachment` and optional `GatewayRequest.attachments`.
- Optional `attachments` input in `generate_with_gateway`.
- Gemini multimodal request parts using `inline_data` or `file_data` when future callers provide media.
- OpenAI-compatible image parts through `image_url` content while preserving existing text-only behavior.
- Safe attachment metadata in `saas_ai_runs`: count, kinds, MIME types and source shape only.
- Static model catalog additions: `gemini-2.5-flash-lite` and `moonshot-v1-8k-vision-preview`.
- Kimi catalog metadata now includes multimodal capability for compatible selected models.
- Tenant Settings > APIs now uses on-demand provider tiles and keeps saved credentials visible.
- Architecture/ADR added: `architecture/VOICE_MULTIMODAL_INTELLIGENCE.md` and `decisions/ADR-045-phase24-1-multimodal-gateway.md`.
- Phase 24.2 Voice Intelligence:
- `060_saas_voice_intelligence_phase24.sql` adds `saas_voice_intelligence_analyses` and voice feature flags.
- `POST /saas/v1/media/messages/{message_id}/voice/analyze` analyzes existing tenant audio messages.
- Local media assets and inbound WhatsApp audio media can be analyzed.
- Google/Gemini is the current validated real audio provider path through AI Gateway attachments.
- Cached output includes transcript, summary, sentiment, sentiment score, intent, intent label, urgency, language, confidence, recommended action, action items, CRM hints and safety flags.
- Inbox audio messages show Voice Intelligence cards with analyze/reanalyze.
- Tenant Settings > IA exposes the Voice Intelligence provider/model credential state.
- ADR added: `decisions/ADR-046-phase24-2-voice-intelligence.md`.
- Phase 24.3 Vision Intelligence:
- `061_saas_vision_intelligence_phase24.sql` adds `saas_vision_intelligence_analyses` and vision/document feature flags.
- `POST /saas/v1/media/messages/{message_id}/vision/analyze` analyzes existing tenant image, document and file messages.
- Local media assets and inbound WhatsApp media can be analyzed.
- Images can use Google/Gemini, OpenRouter or Kimi when configured/compatible; document/OCR analysis is constrained to Google/Gemini in this phase.
- Cached output includes visual description, extracted text, summary, document type, sentiment, intent, urgency, language, confidence, entities, topics, product hints, moderation flags and recommended action.
- Inbox image/document/file messages show Vision Intelligence cards with analyze/reanalyze.
- Tenant Settings > IA exposes the Vision Intelligence provider/model credential state.
- ADR added: `decisions/ADR-047-phase24-3-vision-intelligence.md`.
- Phase 24.4 Web/Image Search Intelligence:
- `062_saas_web_image_search_intelligence_phase24.sql` adds `saas_web_search_intelligence_runs`, `saas_web_search_intelligence_results`, and feature flags `web_search_intelligence`, `image_search_intelligence`, `external_source_assist`.
- `POST /saas/v1/media/search` runs explicit web/image/mixed searches from the Inbox.
- `GET /saas/v1/media/search/runs` lists recent tenant/conversation search runs.
- `POST /saas/v1/media/search/results/{result_id}/approval` records human approval or rejection.
- Supported provider codes are `tavily`, `brave_search`, and `serpapi`, using encrypted tenant API credentials.
- Result records include source URL, snippet, optional image/thumbnail, provider rank/score, safety status, approval status and metadata.
- Unsafe/private/internal URLs are blocked and cannot be approved.
- Tenant Settings > APIs exposes compact provider tiles for the search providers.
- Tenant Settings > IA exposes the Web/Image Search provider and linked credential state.
- Inbox CRM side panel shows source cards, image previews when available, and approve/reject actions.
- ADR added: `decisions/ADR-048-phase24-4-web-image-search-intelligence.md`.
- Phase 24.5 Agent Multimodal Tools:
- `063_saas_agent_multimodal_tools_phase24.sql` adds premium feature flags `agent_multimodal_tools`, `agent_voice_tools`, `agent_vision_tools`, `agent_external_search_tools` and a filtered index on `saas_ai_agent_tool_runs`.
- `GET /saas/v1/agents/multimodal-tools/catalog` exposes the tool catalog.
- `GET /saas/v1/agents/{agent_id}/multimodal-tools/runs` lists agent-scoped multimodal tool traces.
- `POST /saas/v1/agents/{agent_id}/multimodal-tools/execute` executes `media.voice_analyze`, `media.vision_analyze`, or `media.web_image_search` through existing media/search endpoints.
- Agent tools require the selected agent to declare the tool in `tools_json` and pass premium/demo feature gates.
- Web/image search results remain pending until approved through the existing media approval endpoint.
- Assigned-agent conversation prompts can include compact voice/vision output and only approved, non-blocked external sources.
- AI Agents > Agent OS now exposes the multimodal tool form, recent runs and source approval actions.
- ADR added: `decisions/ADR-049-phase24-5-agent-multimodal-tools.md`.
- Phase 24.6 Multimodal Memory & Training Events:
- `064_saas_multimodal_memory_training_events_phase24.sql` adds `saas_multimodal_memory_events` and feature flags `multimodal_memory_events`, `multimodal_training_events`, `multimodal_rag_materialization`, `multimodal_agent_memory`.
- `GET /saas/v1/agents/multimodal-memory/events` lists tenant-scoped memory/training/RAG events.
- `POST /saas/v1/agents/multimodal-memory/sync` captures sanitized voice, vision, approved search and completed tool-run outputs.
- `POST /saas/v1/agents/multimodal-memory/events/{event_id}/materialize` can write reviewed events to Knowledge/RAG, collective agent memory, or both.
- Conversation-level multimodal features are written to `saas_intelligence_feature_values`.
- Assigned-agent prompts prefer curated `saas_multimodal_memory_events`.
- Training readiness requires `multimodal_training_events`, `ml_predictions`, or `ai_premium`.
- AI Agents > Agent OS now exposes memory/training counts, sync/refresh actions, event rows and RAG/collective-memory materialization controls.
- ADR added: `decisions/ADR-050-phase24-6-multimodal-memory-training-events.md`.
- Phase 24.7 Inbox UX:
- No migration was added; Phase 24.7 reuses search, multimodal memory and CRM outbound tables.
- `POST /saas/v1/media/search/results/{result_id}/reference` prepares bounded text from approved, non-blocked Web/Image Search results.
- The endpoint revalidates tenant ownership, search feature access, public URLs and optional conversation ownership.
- Customer delivery still uses `POST /saas/v1/conversations/{conversation_id}/messages`, preserving message quotas, outbound queueing, Meta status events and `message.sent` Intelligence capture.
- Inbox CRM side panel now includes `Panel de analisis Inbox` with voice/vision/memory highlights, approved/pending reference counts and memory sync/refresh.
- Approved visual references expose `Usar` and `Enviar`; search result cards expose `Aprobar y usar` and `Aprobar y enviar`.
- `Enviar` requires human click and browser confirmation.
- ADR added: `decisions/ADR-051-phase24-7-inbox-multimodal-reference-ux.md`.
- Phase 24.8 Admin/Premium Gating:
- `065_saas_multimodal_admin_gating_phase24.sql` adds plan feature limits and provider policy/cost controls.
- Admin endpoints manage Phase 24 feature mode/quota by tenant/plan and provider/model policies by global/plan/tenant scope.
- AI Gateway and Web/Image Search enforce explicit provider policy before external calls.
- ADR added: `decisions/ADR-052-phase24-8-admin-premium-gating.md`.
- Phase 24.9 Observability and Phase 24.10 Safe Rollout:
- `067_saas_multimodal_observability_rollout_phase24.sql` adds `saas_multimodal_observability_snapshots`, `saas_multimodal_rollout_policies`, `saas_multimodal_rollout_events` and default-off flags.
- New feature flags are `multimodal_observability`, `multimodal_cost_observability`, `multimodal_quality_monitoring`, `multimodal_safe_rollout`, and `multimodal_canary`.
- Tenant endpoints expose observability center/refresh and rollout center/policy update under `/saas/v1/intelligence/multimodal/*`.
- Observability aggregates request count, estimated provider cost, average/P95 latency, error count/rate, quality/confidence and sources used across voice, vision, search, agent tools and multimodal memory.
- Safe rollout supports `off`, `demo`, `canary` and `full` policy modes; enforcement is opt-in and requires rollout access plus an enabled policy.
- Tenant `IntelligencePanel.jsx` shows Phase 24.9 cards/provider rows/source list and Phase 24.10 policy controls/events.
- Admin `AI Predictivo` includes the new feature flags in Phase 24 tenant/plan gating.
- ADR added: `decisions/ADR-055-phase24-9-10-multimodal-observability-rollout.md`.

Intentionally not implemented:

- Automatic AI/agent/worker send flow for approved web/image references.
- Automatic model training from multimodal events.
- Non-Google audio provider validation.
- Voice-driven automatic CRM/task/campaign actions.
- TTS runtime changes.
- Automatic rollout side effects beyond blocking/downgrading the targeted multimodal provider execution.

Validation:

- Targeted backend `py_compile` passed for AI Gateway and API Credentials modules.
- Tenant frontend build passed with the existing Vite large-bundle warning.
- Phase 24.2 backend `py_compile` passed for touched modules.
- Docker Compose config passed.
- API/worker rebuild applied/skipped migration `060`.
- Container backend compileall passed for touched backend domains.
- API health OK and Swagger `/docs` returned 200.
- OpenAPI contains the voice analysis endpoint.
- PostgreSQL confirmed `saas_voice_intelligence_analyses` and `voice_intelligence` plan flag.
- Phase 24.3 backend `py_compile` passed for touched modules.
- Tenant frontend build passed with the existing Vite large-bundle warning.
- Admin frontend build passed.
- Docker Compose config, active Docker rebuild, active migration runner through `061`, API health, Swagger, Admin health, OpenAPI vision endpoint check, DB table/feature flag check, container compileall, recent log scan and clean isolated PostgreSQL bootstrap `001`-`061` passed.
- Phase 24.4 backend `py_compile`, tenant/Admin builds, Docker Compose config, SQL BOM/UTF-8 scans, active Docker rebuild, active migration runner through `062`, API health, Swagger, Admin health, OpenAPI web/image search endpoint checks, DB table/feature flag check, container compileall, authenticated tenant safe-failure smoke without provider credential, Browser Swagger smoke and clean isolated PostgreSQL bootstrap `001`-`062` passed.
- Phase 24.5 backend `py_compile`, tenant build, Docker Compose config, SQL BOM/UTF-8 scans, active Docker rebuild, active migration runner through `063`, API health, Swagger, OpenAPI agent multimodal endpoint checks, DB migration/feature-flag check, container compileall, authenticated agent tool smoke with controlled missing search credential failure, Browser Agent OS UI smoke and clean isolated PostgreSQL bootstrap `001`-`063` passed.
- Phase 24.6 backend `py_compile` and container import/compileall passed, tenant/Admin builds passed, Docker Compose config and SQL BOM/UTF-8 scans passed, active Docker rebuild applied/skipped migration `064`, API health, Swagger, OpenAPI multimodal memory endpoint checks, DB table/feature-flag check, authenticated sync/materialization smoke, Browser Agent OS UI smoke after DDL serialization, recent API/worker log scan without new 500/deadlock/traceback patterns and clean isolated PostgreSQL bootstrap `001`-`064` passed.
- Phase 24.7 backend `py_compile`, tenant frontend build, active Docker API/worker rebuild, API health, OpenAPI reference endpoint check and browser tenant frontend smoke with no console errors passed.
- Phase 24.9/24.10 backend `py_compile`, tenant/Admin builds, Docker Compose config, SQL BOM/UTF-8 scans, tracked diff whitespace check and manual touched-file whitespace scan passed.
- Phase 24.9/24.10 active Docker migration/API/Swagger/clean bootstrap through `067` was not run because Docker was not reachable from the latest Codex session.

Remaining production acceptance:

- Smoke-test Voice Intelligence with real tenant Google/Gemini credentials and real WhatsApp/local audio samples.
- Smoke-test Vision Intelligence with real tenant Google/OpenRouter/Kimi credentials and real WhatsApp/local image/document samples.
- Smoke-test Web/Image Search Intelligence with real tenant Tavily/Brave/SerpAPI credentials and quota limits.
- Smoke-test Agent Multimodal Tools with real tenant audio/image/document messages, real search credentials, approved sources and assigned-agent prompt behavior.
- Smoke-test Multimodal Memory with real tenant media/search samples, reviewed source materialization, retention policy and operator workflow.
- Smoke-test Inbox reference send with real approved visual references and a real connected Meta outbound channel.
- Review transcript/extracted-text/summary retention and privacy copy before broad production rollout.
- Smoke-test real Kimi/OpenRouter multimodal vision calls with tenant credentials before advertising those media capabilities.
- Add final privacy/source/copyright review before broad approved-reference rollout or any agent-side automatic reference use.
- Configure real provider pricing metadata before using Phase 24.9 cost estimates in operational or commercial reporting.
- Smoke-test Phase 24.10 `off`, `demo`, `canary` and `full` policies with real tenant voice/vision/search samples before broad rollout.
- Run active Docker migration/API/Swagger and clean PostgreSQL bootstrap through migration `067` when Docker is available.

## Phase 19: Autonomous Revenue Engine

Phase 19 is code-operational as a supervised, premium-gated revenue intelligence control-plane.

Implemented:

- `066_saas_revenue_memory_network_phase19_20.sql` adds revenue policies, opportunities, forecasts, experiments and reports.
- `app_saas/intelligence/revenue.py` detects opportunities from real CRM/conversation/prediction signals.
- Tenant endpoints are exposed under `/saas/v1/intelligence/revenue/*`.
- Revenue policy controls are operable from `IntelligencePanel.jsx`: autonomy level, currency, revenue goal, monthly action cap and allowed playbook action types.
- Approve/execute now enforces the optional allowed action-type policy and monthly control-plane execution cap.
- Tenant UI in `IntelligencePanel.jsx` shows access mode, metrics, policy, opportunities, forecasts, reports and playbooks.
- Intelligence worker runs revenue analysis only for full-enabled tenants and isolates failures in nested transactions.
- Feature flags are `autonomous_revenue_engine`, `revenue_opportunity_detection`, `revenue_forecasting`, `revenue_playbooks`, `revenue_experiments`, plus umbrella `ai_premium`.

Safety model:

- Opportunity execution records controlled metadata only.
- No automatic messages, payment-provider calls, billing charges, CRM mutation, campaign/workflow/trigger activation, agent execution or Meta runtime changes.
- Unknown commercial value remains `0` until a real tenant commerce/order/revenue source is integrated.

Validation:

- Backend py_compile passed locally and inside the rebuilt API container.
- Tenant/Admin frontend builds passed.
- Active Docker migration runner applied `066`.
- API health and Swagger `/docs` passed.
- OpenAPI contains revenue endpoints.
- Authenticated full-mode smoke with a temporary tenant created revenue opportunities/reports and approved/executed one opportunity as control-plane metadata.
- Clean isolated PostgreSQL bootstrap applied migrations `001` through `066`.
- Current Phase 19 hardening validation passed backend `py_compile`, tenant/Admin frontend builds, Docker Compose config and SQL UTF-8/BOM scans. Active Docker/API/Swagger rerun for this exact state was blocked by unavailable Docker Desktop pipe.

Remaining production acceptance:

- Connect real tenant commerce/order/payment value before using forecasts as commercial metrics.
- Define whether future revenue actions can materialize into CRM tasks, campaigns or workflows through a separate ADR and approval path.
- Staging review of opportunity categories, operator workflow and plan/tenant enablement policy.

## Phase 20: AI Enterprise Memory Network

Phase 20 is code-operational as a tenant-scoped enterprise memory graph and governance substrate.

Implemented:

- `066_saas_revenue_memory_network_phase19_20.sql` adds memory policies, nodes, edges, sync runs and access logs.
- `app_saas/intelligence/memory_network.py` syncs bounded candidates from collective memory, Knowledge/RAG, multimodal memory events and vertical insights.
- Tenant endpoints are exposed under `/saas/v1/intelligence/memory-network/*` for center, policy, sync, export, import, review and delete.
- Tenant UI in `IntelligencePanel.jsx` shows node/edge counts, routing guidance, sync runs, policy controls, JSON export/import and review/delete actions.
- Memory policy actively enforces privacy mode, retention days, allowed scopes and customer-content review during sync/import/publish and existing-node policy updates.
- Import creates sanitized `candidate` nodes only; export returns tenant-scoped summaries/metadata/hashes and safety metadata; delete is tenant-scoped and access-logged.
- Intelligence worker runs memory sync only for full-enabled tenants and isolates failures in nested transactions.
- Feature flags are `enterprise_memory_network`, `memory_graph`, `memory_governance`, `cross_agent_memory_routing`, `memory_quality_scoring`, plus umbrella `ai_premium`.

Safety model:

- Tenant isolation is mandatory in sync, center and review queries.
- Nodes store bounded summaries, metadata and content hashes, not raw media/base64.
- Export/import/delete operations are tenant scoped and audited in `saas_enterprise_memory_access_logs` plus Intelligence events.
- Candidate/private memory must not enter prompts, RAG runtime or cross-tenant intelligence without published status and routing review.

Validation:

- Backend py_compile passed locally and inside the rebuilt API container.
- Active Docker migration runner applied `066`.
- API health and Swagger `/docs` passed.
- OpenAPI contains memory-network endpoints.
- Authenticated full-mode smoke with a temporary tenant synced memory, created nodes/edges and published one node.
- Clean isolated PostgreSQL bootstrap applied migrations `001` through `066`.
- Latest hardening validation passed backend `py_compile`, tenant/Admin frontend builds, Docker Compose config and SQL BOM/UTF-8 scans. Docker runtime was unavailable, so active export/import/delete smoke remains pending.

Remaining production acceptance:

- Validate retention/export/import/delete workflow with real tenant samples.
- Validate prompt/RAG routing against published tenant nodes only.
- Test with real collective memory, Knowledge/RAG, multimodal and vertical-insight samples.

## Phase 17: Federated Learning & Global Intelligence

Implemented:

- Migration `068_saas_federated_learning_phase17.sql`.
- Tables for tenant policies, federated rounds, aggregate update packages, aggregate rows and global intelligence signals.
- Feature flags default off: `federated_learning`, `federated_model_updates`, `privacy_safe_model_aggregation`, `global_intelligence`, `federated_benchmarking`.
- Backend service `intelligence/federated.py`.
- Tenant endpoints under `/saas/v1/intelligence/federated/*`.
- Worker auto-participation behind full feature access, opt-in and explicit auto-participation.
- Tenant UI in `IntelligencePanel.jsx` for policy, privacy mode, sample thresholds, allowed tasks, local previews, rounds, update submission, aggregation and global signals.

Safety model:

- Update packages contain only aggregate metrics, feature summaries, feature importance, quality score, privacy metadata and hashes.
- No raw messages, full conversations, media/base64, prompts, decrypted secrets, provider payloads, tenant names or private customer content are shared across tenants.
- Aggregates are candidate/global benchmark signals only. They do not automatically promote production models or mutate CRM, campaigns, workflows, billing, Meta, providers or agents.

Validation:

- Backend `py_compile` passed for touched Intelligence/Billing/worker modules.
- Tenant frontend build passed with existing Vite large-bundle warning.
- Admin frontend build passed.
- Docker Compose config passed.

Remaining production acceptance:

- Run active Docker migration/API/Swagger/worker smoke through `068`.
- Run clean PostgreSQL bootstrap `001` through `068`.
- Rehearse with multiple opted-in tenants in the same/general cohort.
- Review privacy/legal copy before commercial cross-tenant learning claims.
- Define ModelOps promotion runbook before using federated signals for production model choice.

## Roadmap 16-25 Evaluation

The proposed phases 16-25 are viable as a long-term roadmap, but should be sequenced by safety and compounding value.

Recommended order after Phase 17 implementation:

1. Phase 21: Scentra AI Cloud Platform.
2. Phase 23: AI Marketplace Economy.
3. Phase 25: Enterprise Decision Intelligence.

Key decision:

- Phase 18 now provides the safe Composer control-plane needed before broad agent marketplace or runtime workflow activation.
- Phase 22 now provides the AI trust/governance layer needed before broad autonomy, federated learning, public developer APIs or marketplace economy features.
- Phase 16 now provides the realtime intelligence surface needed before adding richer multimodal, revenue or decision-automation loops.
- Phase 17 now provides the aggregate/privacy-safe federated control-plane; production use still requires cohort rehearsal, privacy review and ModelOps promotion runbook.
- Phase 23 should wait until sandboxing, review workflows, billing/revenue-share and legal terms are mature.

Detailed evaluation is documented in `docs/ROADMAP_PHASES_16_25_EVALUATION.md`.

## Immediate Priority

1. Configure SMTP and Turnstile production env vars for Phase 1 deployment.
2. Run staging acceptance for Phase 10 vertical packs with real tenant CRM/campaign data.
3. Run sandbox/live billing acceptance for Stripe, MercadoPago, and Wompi webhooks.
4. Keep Phase 14 copy catalogs and Product Ops release checks updated after every frontend/admin change.
5. Add broader tenant isolation/security smoke suites before scaling users.
6. Add broader E2E smoke automation when a dedicated test framework is approved.
7. Confirm upstream URL/commit/tag and approve whether offline drafts can enter Admin/DB after review.
8. Define commercial policy for full predictive features by plan/tenant before enterprise sales.
9. Run Phase 11 ML acceptance with real tenant-safe labels before promoting trained models beyond shadow/canary.
10. Run Phase 12 staging load tests and real backup/restore drills before contractual scale commitments.
11. Run production acceptance for Phase 24.2 through 24.10 with real provider credentials, real media/search/reference samples, approved sources, assigned agents, quota review, pricing metadata, rollout policies, real Meta outbound smoke and source/copyright policy before customer-facing rollout.
12. Run Phase 19 staging acceptance with real tenant order/payment data before commercial revenue forecasting claims.
13. Run Phase 20 staging acceptance with real memory/RAG/multimodal samples, export/import/delete workflow and prompt routing restricted to published nodes.
14. Run Phase 17 Docker/bootstrap through migration `068`, multi-tenant cohort rehearsal, privacy review and ModelOps promotion runbook before using federated signals for production model selection.
15. Continue roadmap with Phase 21, then Phase 23 and Phase 25.
