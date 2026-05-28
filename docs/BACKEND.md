# BACKEND

Scope: SaaS only. Backend root: `saas-version/backend/app_saas`.

## App Entry

File: `saas-version/backend/app_saas/main.py`.

- FastAPI app title: `Scentra +AI API`
- Version: `0.1.0`
- Public router prefix: `/saas/v1`
- CORS origins come from settings.
- Request middleware adds request metadata and guards CORS error responses.
- On startup, the API can launch an embedded worker loop when `settings.saas_embedded_worker_enabled` is true.

## Router Modules

All mounted under `/saas/v1`:

- `health`: `/health`, `/ready`
- `admin`: `/admin/*`
- `auth`: `/auth/*`
- `tenants`: `/tenants*`
- `verticals`: `/verticals/*`
- `intelligence`: `/intelligence/*`
- `ecosystem`: `/ecosystem/*`
- `compliance`: `/compliance/*`
- `crm`: `/customers`, `/dashboard`, `/labels`, `/conversations`, `/crm/config`, `/crm/tasks`, `/outbound`
- `campaigns`: `/campaigns/*`
- `commerce`: `/commerce/*`
- `broadcasts`: `/broadcasts/*`
- `ads`: `/ads/*`
- `integrations`: `/integrations/*`
- `instagram`: `/integrations/instagram/*`
- `internal`: `/internal/*`
- `api_credentials`: `/api-credentials/*`
- `advisor`: `/advisor/*`
- `agents`: `/agents/*`
- `ai_gateway`: `/ai-gateway/*`
- `knowledge`: `/knowledge/*`
- `diagnostics`: `/diagnostics/*`
- `ai_agent`: `/ai/*`
- `media`: `/media/*`
- `social`: `/social/*`
- `billing`: `/billing/*`
- `webhooks`: `/webhooks/*`

## Module Map

- `admin/`: platform admin auth, MFA, tenants, plans, subscriptions, billing ops, audit, observability, Security Center.
- `auth/`: tenant user register/login/email-OTP MFA/recovery/reset/password-change/security-status/2FA/refresh/switch-tenant/me.
- `tenants/`: tenant CRUD for authenticated tenant users.
- `verticals/`: Phase 10 industry packs, tenant vertical state, safe pack application, and Phase 11 extended vertical codes for enterprise intelligence.
- `intelligence/`: Phase 11 events, feature store, predictions, recommendations, AI premium gating, grants, usage, rollout governance, optional ML inference handoff, Autonomous Operational Intelligence, Enterprise AI Network, Phase 16 Real-Time Intelligence, Phase 17 Federated Learning/Global Intelligence, Phase 24 plan/provider premium controls, multimodal observability and safe rollout.
- `ecosystem/`: Phase 11 AI Platform Ecosystem control-plane for marketplace, plugin center, developer apps, tool registry, event subscriptions, external integration metadata and tenant AI apps.
- `compliance/`: Phase 13 tenant-scoped privacy exports and delete-request records.
- `reliability/`: Phase 12 Performance, Reliability & Scale control-plane for SLO snapshots, queue backpressure, index audit, retention dry-runs, backup readiness and reliability drills.
- `ml_service/`: optional Phase 11 ML service for synthetic training, Postgres auto-label dataset building, trained inference, drift evaluation, MLflow/BentoML integration, and Prometheus metrics.
- `crm/`: customer/conversation/message/task/label/outbound inbox.
- `campaigns/`: campaign catalog, templates, segments, items, triggers, flows.
- `broadcasts/`: Meta templates, broadcasts, recipients, reports, CSV export.
- `ads/`: ad accounts, campaigns, leads, comments, social webhook processing.
- `integrations/`: WhatsApp/Meta/WooCommerce integration records and token checks.
- `billing/`: tenant subscription, plans, entitlements, usage, invoices, credits, webhooks.
- `webhooks/`: tenant webhook endpoints, verification, inbound provider events.
- `api_credentials/`: encrypted tenant provider credentials and model listing.
- `ai_gateway/`: provider registry, routes, run history, Phase 24.8 provider policy enforcement before external AI calls, and standard provider HTTP headers for Groq/Cloudflare compatibility.
- `ai_agent/`: tenant AI settings, conversation memory, process/test actions.
- `agents/`: AI agent registry, memories, governance, orchestrator events, and Phase 11 Multi-Agent Operating System control-plane.
- `advisor/`: assistant/advisor threads, memory, actions, recommendations.
- `knowledge/`: source upload/url ingestion, search, health, reindex/delete.
- `workers/`: background processors for webhooks, triggers, remarketing, AI replies, orchestration, outbound, Meta tokens.
- `shared/`: security, MFA email OTP helper, captcha, secrets, request metadata, security events.
- `tools/`: migration runner and platform admin creation.
- `ml_service/`: optional ML runtime mounted by `Dockerfile.ml`, not imported by the default API/worker image path.

## Phase 24.8 Admin Premium Gating

Code-operational at repository level.

- `intelligence/premium.py` owns Phase 24 plan limits, provider policies, credential summaries and provider cost summaries.
- `admin/router.py` exposes Admin control-plane endpoints for premium-gating overview, plan feature limit upsert and provider policy upsert.
- `intelligence/service.py` applies plan-level feature limits below tenant grants and above inherited plan/default/demo flags.
- `ai_gateway/service.py` calls provider policy enforcement before using external AI credentials.
- `media/router.py` calls provider policy enforcement before Web/Image Search provider calls.
- Explicit provider policies can disable a provider/model or enforce monthly request/cost limits.
- Default policy behavior remains compatibility-safe: no explicit policy or zero quota/cost limit does not block current tenants.
- Cost summaries use `saas_ai_runs` token counts and `saas_web_search_intelligence_runs` request counts; commercial accuracy depends on Admin-entered pricing metadata.

## AI Gateway Resilience

Operational hardening added after provider/model transient failures such as Google/Gemini `http_503` high demand.

- `ai_gateway/service.py` now retries retryable provider failures across model candidates inside the same provider before moving to the next provider in the chain.
- Retryable model failover covers `408`, `409`, `425`, `429`, `500`, `502`, `503`, `504`, provider unavailable/timeouts, empty provider responses and high-demand/temporary markers.
- Model candidates come from the tenant-selected credential model, optional `settings.metadata_json.model_fallbacks_json`, provider default model and provider static models, capped by `model_fallback_attempt_limit` default `4`.
- Every failed/skipped/success attempt is still recorded in `saas_ai_runs`; success metadata includes candidate models, attempt indexes and whether model fallback was used.
- Provider policies are checked per candidate model before external calls. Admin-disabled providers/models, missing credentials and quota/cost policy blocks are not bypassed.
- Conversation AI, assigned agents, custom agents, Agent OS runtime paths and Advisor inherit the behavior through `generate_with_gateway`.
- If all candidates fail from retryable provider errors, `ai_agent/service.py` returns `ai_generation_error` so `saas_ai_pending_replies` remains retryable instead of being permanently skipped.

## Groq Provider Compatibility

Operational hardening added after observed Groq `http_403: error code: 1010`.

- `ai_gateway/providers/http.py` now sends explicit `User-Agent: ScentraAI/1.0 (+https://scentra-ai.online)` and `Accept: application/json` on provider GET/POST calls.
- `api_credentials/router.py` sends the same headers when listing provider models from Groq/Mistral/OpenRouter/Kimi/Google/TTS providers.
- `ai_agent/service.py` legacy direct provider helper also uses the same headers if that path is reused later.
- Groq static model fallbacks now avoid the older `llama-3.1-70b-versatile` entry and prefer currently documented production options such as `llama-3.1-8b-instant` and `llama-3.3-70b-versatile`.
- Residual risk: Groq/Cloudflare can still block a VPS/IP/project by provider policy. Keep another AI provider configured as fallback.

## Phase 17 Federated Learning Backend

Code-operational at repository level.

- `intelligence/federated.py` owns tenant opt-in policy, local aggregate package generation, federated round upsert, update submission, weighted aggregation and global signal persistence.
- Tenant APIs are mounted under `/saas/v1/intelligence/federated/*`.
- Mutation endpoints require owner/admin/supervisor role plus full Intelligence feature access through `federated_learning`, `federated_model_updates`, `privacy_safe_model_aggregation` or `ai_premium`.
- Read/demo center access can show local previews through demo/global/federated feature gates.
- The Intelligence worker calls `process_federated_learning` in a nested transaction and skips tenants unless full access, `opt_in_enabled=true` and `auto_participation_enabled=true`.
- Stored packages are aggregate/statistical only: counts, rates, feature summaries, feature importance, quality score, hashes and privacy metadata.
- No raw messages, conversations, media/base64, prompts, decrypted secrets, provider payloads, tenant names or private customer content are shared across tenants.
- Aggregation writes candidate/global signals only; production model promotion still requires separate ModelOps review and registry rollout.

## Patterns

- FastAPI dependency injection for auth/context.
- Pydantic schemas in domain `schemas.py` files.
- SQLAlchemy Core/raw SQL through `db_session()`.
- Explicit tenant filtering in SQL; DB helper can set `app.current_tenant`.
- Secrets are encrypted with Fernet via `shared/secrets.py`.
- Platform admin auth is separate from tenant user auth.
- Billing limits are enforced through billing services/helpers and plan data.

## Phase 1 Security Base

Code-complete and smoke-tested on 2026-05-24 for clean Docker/PostgreSQL bootstrap.

- Production schema-drift repair exists in migration `069_saas_auth_billing_schema_drift_repair.sql` for environments where migration versions were marked applied but login columns such as `saas_users.locked_until` were missing.
- Tenant auth and tenant-list responses now coalesce nullable `plan_code` and `industry_code` to compatibility defaults before Pydantic response serialization.
- Cloudflare Turnstile is verified server-side when `SAAS_CAPTCHA_ENABLED=true`.
- Tenant login/register and platform admin login/bootstrap use endpoint-specific rate limits by combined key, principal/email, and IP.
- Failed login counters and `locked_until` live on `saas_users`; tenant and platform-admin login both return controlled lockout responses.
- Password recovery uses hashed, expiring, single-use tokens in `saas_password_reset_tokens`; raw tokens are never stored.
- Password reset/change updates Argon2 hashes and clears login lock state.
- Security events are written to `saas_security_events`; blocked rate-limit events are persisted with an isolated write so rollback does not erase the audit trail.
- 2FA preparation fields were added in Phase 1; Phase 13 now enforces email OTP login challenges for configured users/roles.
- Password reset email delivery uses stdlib SMTP when configured. Local mode exposes a dev reset token for smoke testing only.

## Phase 13 Security, 2FA And Compliance

Code-operational and smoke-tested on 2026-05-27 with Docker API/worker rebuild.

- `shared/mfa.py` creates hashed email OTP challenges in `saas_mfa_challenges`, enforces expiry/attempt limits, and sends security notices through the existing SMTP helper.
- Tenant `/auth/login` and Admin `/admin/auth/login` can return an MFA challenge instead of tokens. Verification endpoints issue JWTs with an MFA claim.
- Role-based mandatory MFA is configured by `SAAS_MFA_REQUIRED_ROLES` and `SAAS_ADMIN_MFA_REQUIRED_ROLES`.
- Tenant and Admin `/auth/security/2fa` support email OTP only. TOTP/authenticator apps are intentionally not implemented in this phase.
- `compliance/router.py` exports current user/account data, exports selected customer/conversation data, records privacy delete requests, and lists privacy requests by tenant.
- Admin `security/compliance` aggregates user 2FA, platform admin 2FA, webhook signature, security event and privacy request metrics.
- Admin `audit/export.csv` provides a compact CSV export of audit rows.
- Delete requests are review records, not destructive data deletion.

## Background Work

API startup embedded loop in `main.py` can call:

- `process_due_webhook_events`
- `process_due_scheduled_trigger_messages`
- `process_due_remarketing_flows`
- `process_due_ai_replies`
- `process_due_agent_orchestration`
- `process_due_outbound_messages`
- `process_due_meta_token_refreshes`
- `process_due_intelligence`
- `process_due_reliability`

Standalone worker:

- `saas-version/backend/app_saas/workers/runner.py`
- Docker service name: `worker`

Warning: API embedded loop and standalone worker can both be enabled. Any change to queue processors must preserve idempotency and locking assumptions.

## Phase 2 Admin Operations

Code-complete and smoke-tested on 2026-05-24 with a clean Docker/PostgreSQL stack.

- Platform admin auth remains separate from tenant auth under `/saas/v1/admin/auth/*`.
- Local HTTP bootstrap remains blocked outside `SAAS_ENV=local/dev/development`.
- Production first-admin creation uses `app_saas.tools.create_platform_admin`, available through the optional Compose profile service `platform-admin-seed`.
- Admin routes cover tenants, plans, subscriptions, feature flags, billing credits/invoices, lifecycle sync, audit, queues, observability, dead-letter, and support impersonation.
- Role gates remain in backend for mutation/operations routes.

## Phase 3 Observability And Diagnostics

Code-complete and smoke-tested on 2026-05-24 with a clean Docker/PostgreSQL stack.

- `main.py` assigns/returns request correlation IDs and includes the ID in guarded 500 responses.
- `observability/service.py` now reports global API/DB/worker/Meta/AI Gateway/queue health, channel diagnostics, Meta error history, dead-letter diagnosis, retry metadata, and worker heartbeat state.
- `saas_worker_heartbeats` records embedded and standalone worker liveness/result/error snapshots.
- Admin observability endpoints include health, Meta errors, dead-letter list/sync/resolve/retry.
- Admin operation endpoints can process webhooks, outbound, scheduled triggers, AI pending replies, remarketing, agent orchestration, and Meta token refresh queues.
- Webhook ingestion preserves `correlation_id` from headers or generates one for stored webhook events.
- Webhook processing isolates each event with a PostgreSQL savepoint so one failed event cannot abort the whole batch.
- Agent orchestration enqueue uses safe nullable UUID casting and savepoint isolation when called from ingestion.

## Phase 4 Inbox Backend

Code-complete at repo level on 2026-05-25; clean Docker bootstrap was later rerun successfully in Phase 6.

- `crm/router.py` remains the canonical tenant Inbox API for conversations, messages, read state, takeover, tasks, lead score, assignment, and status events.
- `GET /conversations` remains backward compatible and now accepts optional `channel` and `queue` query filters.
- Supported `queue` filters: `all`, `unread`, `mine`, `unassigned`, `sla`, `hot`, `human`, `ai`.
- Assignment uses existing `PATCH /customers/{conversation_id}` with `assigned_user_id`; clearing assignment uses an empty string and `CAST(NULLIF(...))`.
- `social/router.py` remains the public comments API for separated comment workflows.
- Workers continue to own inbound ingestion, unread/SLA updates, outbound dispatch, and provider delivery status events.

## Phase 5 CRM Backend

Code-complete at repo level on 2026-05-25; migration `040` was later validated in the Phase 6 clean Docker bootstrap.

- `040_saas_crm_commercial_phase5.sql` adds tenant custom-field definitions, configurable default pipeline/stages, CRM timeline events, and merge audit records.
- `crm/router.py` exposes `/crm/config`, custom-field CRUD, pipeline preset/stage management, conversation timeline, duplicate candidates, and controlled customer merge.
- Custom-field values are stored under `saas_conversations.profile_json.custom_fields` to preserve existing customer/conversation contracts.
- Customer merge is tenant scoped, audits source/target snapshots, merges labels/memory/profile fields, moves known conversation references, and records a timeline event.
- `ai_agent/service.py` includes custom fields in CRM context and only updates configured custom-field keys when the active agent allows `crm.update` and `can_update_crm` is not false.

## Phase 6 Knowledge/RAG Backend

Code-complete and smoke-tested on 2026-05-25 with a clean Docker/PostgreSQL stack.

- `041_saas_knowledge_rag_phase6_operational.sql` adds local sparse-vector metadata on chunks and tenant-scoped RAG quality evaluations.
- `knowledge/router.py` supports PDF/TXT/CSV uploads, URL ingestion, tenant source listing, health, search, source/global reindex, delete, quality evaluation, and evaluation history.
- Search remains dependency-light: it combines local sparse-vector cosine scoring with lexical scoring; no pgvector or external vector DB dependency was introduced.
- URL ingestion validates scheme, credentials, DNS, and resolved IPs to block localhost/private network fetches before crawling.
- CSV uploads are normalized into column/row text before chunking, so product catalogs and FAQ sheets become searchable context instead of raw CSV blobs.
- AI conversation prompts receive RAG context with internal citations and instructions to rely on sources rather than invent missing facts.

## Phase 7 Campaigns Backend

Code-complete at repo level on 2026-05-25; local validation passed. Later Phase 11 Docker rebuild covered migrations through `054`.

- `037_saas_campaigns_phase7_enterprise.sql` provides trigger/flow preflight, versioning, quiet-hours, and A/B JSON fields.
- `042_saas_campaigns_phase7_operational.sql` adds centralized `saas_campaign_quiet_hours` and `saas_campaign_ab_events`.
- `campaigns/router.py` exposes global quiet-hours settings, A/B reports, campaign/trigger/flow preflight, trigger simulation, trigger version listing, and restore/rollback.
- Trigger creation/update/copy and flow creation/update recalculate preflight and block activation when high-severity checks fail.
- Trigger conditions include words/comments/templates/tags/schedules plus CRM stage, payment status, customer type, and intent.
- `workers/triggers.py` and `workers/remarketing.py` enforce quiet hours, cooldown, A/B variant selection, event telemetry, and `block_ai` handoff.
- `workers/dispatch.py` revalidates approved Meta templates at dispatch time so queued/retried template broadcasts cannot send if approval was lost.

## Phase 8 AI Agents Backend

Code-complete at repo level on 2026-05-25; local validation passed. Later Phase 11 Docker rebuild covered migrations through `054`.

- `043_saas_ai_agents_phase8_operational.sql` adds custom-agent fields, rendered system prompts, stored preflight state, eval records, and conversation AI ownership fields.
- `agents/service.py` now supports factory and custom agents with fillable system prompt templates, variables JSON, rendered prompts, custom-agent catalog entries, and active-agent assignment helpers.
- Agent activation is gated by `preflight_agent`; failed preflight raises `agent_preflight_not_ready` instead of activating.
- Runtime budget hard stop is enforced through `assert_agent_budget_available` before conversation AI calls the provider gateway.
- `crm/router.py` exposes `PATCH /conversations/{conversation_id}/ai-agent` for manual assignment/release and `GET /conversations?agent_id=` for agent-specific Inbox filtering.
- `runtime_agent_for_conversation` honors persisted `assigned_ai_agent_id`; an assigned inactive/missing agent prevents silent fallback to general AI so two AIs do not answer the same conversation.
- `agents/orchestrator.py` persists the selected agent as conversation AI owner after orchestration.
- `ai_agent/service.py` injects the assigned agent system prompt and collective memory context into the conversation prompt.
- `ai_agent/service.py` now applies humanized WhatsApp reply defaults: shorter output cap, compact recent transcript, preserved CRM/memory/RAG/collective/multimodal context, natural chunking, delayed outbound fragments, and best-effort Meta typing indicator before generation.
- Agent archive now preserves memory by default; the memory vault remains available for later restore/export/import/delete.

## Phase 9 Billing Backend

Code-complete at repo level on 2026-05-25; local validation passed. Later Phase 11 Docker rebuild covered migrations through `054`.

- `044_saas_billing_phase9_operational.sql` adds lifecycle notice timestamps, invoice PDF tracking, provider checkout event recency, and lifecycle indexes.
- `billing/service.py` verifies Stripe, MercadoPago, and Wompi webhooks before mutating billing state, activates paid checkouts, records provider events/payments/invoices, and syncs subscription state.
- `sync_billing_lifecycle` handles expired trials/subscriptions, past-due grace, suspension, open invoice creation, uncollectible invoice aging, and one-time failed-payment/trial/suspension notices.
- `workers/billing.py`, `workers/runner.py`, and the embedded worker loop run billing lifecycle with interval throttling and an advisory lock.
- `main.py` blocks unsafe tenant writes for non-operational tenant states while keeping billing/auth/admin/health routes reachable.
- `billing/router.py` and `admin/router.py` expose authenticated PDF invoice endpoints for tenant and platform admin surfaces.

## Phase 10 Verticalizacion Backend

Code-complete at repo level; local validation passed. Later Phase 11 Docker rebuild covered migrations through `054`.

- `045_saas_verticalization_phase10.sql` adds tenant industry state and `saas_vertical_pack_applications`.
- `verticals/catalog.py` defines idempotent industry packs for general, retail, ecommerce, restaurant, hotel, health, education, real estate, support, automotive, financial services, legal, insurance, beauty, and services.
- `verticals/service.py` applies a pack tenant-safely across CRM pipeline stages, custom fields, labels, message templates, segments, trigger drafts, remarketing flow drafts, quiet-hours defaults, and optional recommended agent creation.
- `verticals/router.py` exposes public pack summaries plus authenticated pack/state/apply endpoints under `/saas/v1/verticals`.
- Tenant registration and tenant creation accept `industry_code` and apply the pack without auto-creating agents.
- Platform admin tenant patch can change `industry_code` and applies the same pack without auto-creating agents.
- Trigger packs are inserted inactive and flow packs are inserted as draft so verticalization does not start automation without operator review.

## Phase 11 Intelligence Backend

Code-complete at training/data-intelligence, product-facing predictive/Advisor, Multi-Agent OS, Autonomous Operational Intelligence, AI Platform Ecosystem, and Enterprise AI Network levels; local compile/build validation, Docker/PostgreSQL rerun through migration `054`, inline CRM/Billing event smokes, extended tenant predictive smoke, optional ML service smoke, Admin synthetic/autolabel training smoke, dataset build smoke, shadow inference smoke, API health, Swagger, ecosystem tenant smoke, enterprise network tenant smoke and worker startup passed.

- `046_saas_intelligence_engine_phase11.sql` adds event store, feature store, predictions, recommendations, feature grants, model registry and usage tables.
- `047_saas_intelligence_modelops_phase11.sql` adds prediction feedback and model metrics tables.
- `048_saas_intelligence_model_rollouts_phase11.sql` adds model rollout controls and auditable rollout events.
- `049_saas_ml_infrastructure_phase11.sql` adds ML training jobs, model artifact records, inference run logs and drift snapshots.
- `050_saas_ml_training_strategy_phase11.sql` adds event contracts, replay cursors, auto-labels, feature set definitions/runs, training datasets, model evaluations, and feature-value version metadata.
- `051_saas_multi_agent_operating_system_phase11.sql` adds inter-agent messages, runtime traces, tool-run traces, event subscriptions, and Agent OS premium feature flags.
- `054_saas_enterprise_ai_network_phase11.sql` adds vertical industry models, privacy-safe benchmarks, tenant benchmark comparisons, vertical insights, AI playbooks, aggregate-only knowledge network nodes, network metrics, and Enterprise AI Network premium feature flags.
- `intelligence/` exposes tenant endpoints for catalog/state/overview/events/features/predictions/feedback/model-metrics/recommendations under `/saas/v1/intelligence`.
- `intelligence/network.py` exposes the Enterprise AI Network service layer for industry-specific intelligence, privacy-safe benchmark computation, playbook seeding, vertical advisors and tenant-scoped insights.
- Tenant network endpoints are exposed under `/saas/v1/intelligence/network/*` for center, refresh and playbook reads.
- `053_saas_ai_platform_ecosystem_phase11.sql` adds AI marketplace items/installations, plugins, central tool registry, ecosystem event subscriptions, developer apps, external AI integration metadata, tenant AI apps, ecosystem traces/metrics, and premium feature flags.
- `ecosystem/` exposes tenant endpoints under `/saas/v1/ecosystem/*` for marketplace, installations, plugins, tools, event subscriptions, SDK manifest, developer apps, external integrations, AI apps, metrics and overview.
- Ecosystem execution is control-plane only: plugin/app manifests are metadata, developer keys are hashed with one-time display, and no untrusted plugin code runs in API/worker.
- Marketplace agent template installation can create a real agent only when requested and still goes through existing agent service limits/preflight lifecycle.
- Ecosystem mutations require full premium feature enablement; demo mode can preview/list surfaces but cannot install or create plugin/tool/developer resources.
- `GET /saas/v1/intelligence/overview` returns compact predictive cards, CRM aggregates, summaries, recommendations and ModelOps observability for dashboards and Advisor.
- `ml_service/` exposes optional internal endpoints for `/health`, `/models`, `/train/synthetic`, `/datasets/build`, `/train/autolabel`, `/predict`, `/drift/evaluate` and `/metrics`.
- `intelligence/capture.py` provides safe inline event capture with a nested transaction so telemetry failures do not break the business write.
- `admin/router.py` exposes `/admin/intelligence/*` for AI & Predictive Features Management, ModelOps metric listing/recompute, model registry registration/listing, readiness assessment, rollout patching, training dataset readiness, MLops overview and synthetic ML training.
- `workers/intelligence.py` derives canonical Intelligence events from existing CRM/messages/webhooks/outbound/triggers/campaign A-B/remarketing/AI runs/billing tables, recomputes tenant feature snapshots, generates gated baseline predictions on a cooldown, refreshes model metrics, syncs Agent OS signals, and runs Autonomous Operational Intelligence analysis in isolated nested transactions.
- `workers/intelligence.py` also attempts Enterprise AI Network refresh in an isolated nested transaction; tenants without full feature access are skipped and do not fail the pipeline.
- `052_saas_autonomous_operational_intelligence_phase11.sql` adds tenant operation policies, playbooks, anomalies, actions, reports, and premium flags `autonomous_operations`, `ai_self_healing`, and `ai_control_center`.
- `intelligence/operations.py` detects operational anomalies from events/features/queues/worker heartbeats/Meta checks, seeds playbooks, creates supervised action records, records operational reports, and enforces demo/full autonomy policy.
- Tenant operations endpoints are exposed under `/saas/v1/intelligence/operations/*`.
- Autonomous Operations supports Levels 0-4, but current execution is deliberately control-plane first: provider/queue/campaign/CRM mutations are not performed directly by this layer.
- Demo mode can preview/analyze but forces auto-remediation and low-risk auto-execute off.
- `workers/intelligence.py` can also run training-data preparation when `SAAS_ML_AUTO_TRAIN_ENABLED=true`; the flag is off by default so ordinary API/worker and Meta runtime behavior is unchanged.
- Auto-labeling derives labels from real SaaS state/events instead of manual labeling: CRM/payment conversion states, inactivity windows, campaign/broadcast outcomes, operational failures and negative engagement signals.
- Feature pipelines write conversation/customer/tenant features for `lead_scoring`, `churn_prediction`, `smart_remarketing`, and `operational_anomaly` with feature set/version metadata.
- Dataset building joins `saas_ml_auto_labels` to `saas_intelligence_feature_values` and writes CSV/manifest artifacts under the configured ML dataset directory before recording `saas_ml_training_datasets`.
- Autolabel training uses the optional ML service to train LightGBM, XGBoost, or sklearn fallback models from Postgres-derived labels/features, logs MLflow/BentoML artifacts when available, and records offline evaluations.
- CRM outbound message creation and billing subscription state changes now emit first-pass inline Intelligence events using the same replay-key family as the derived worker.
- Embedded and standalone workers now include the Intelligence processor; Admin Operations can run it manually through `/admin/operations/intelligence/process`.

## Phase 16 Real-Time Intelligence Backend

Code-operational at repository level.

- `059_saas_realtime_intelligence_phase16.sql` adds `saas_realtime_intelligence_sessions`, `saas_realtime_intelligence_cursors`, `saas_realtime_intelligence_metrics`, and feature flags `realtime_intelligence_layer`, `realtime_event_stream`, `realtime_ai_alerts`, and `realtime_intelligence_dashboard`.
- `intelligence/realtime.py` builds tenant live snapshots from existing Intelligence events, predictions, recommendations, feature values, ModelOps metrics, Autonomous Operations anomalies/actions, and Trust AI incidents/risks.
- Tenant APIs now expose `/saas/v1/intelligence/realtime/center`, `/events`, `/sessions`, `/cursor`, `/sessions/{id}/close`, and bounded `/stream`.
- Admin APIs now expose `/saas/v1/admin/intelligence/realtime` and `/saas/v1/admin/intelligence/realtime/metrics/refresh`.
- Event payloads returned by realtime APIs redact sensitive keys; tenant endpoints never return cross-tenant data.
- Phase 16 is read/control-plane only. It does not mutate Meta, CRM, campaigns, billing, workflows, agents, Trust enforcement or model rollout state.
- `billing/limits.py` now includes premium AI feature flags: `intelligence_demo`, `ai_premium`, `ml_predictions`, `lead_scoring_ml`, `churn_prediction`, `smart_remarketing`, `ai_operational_intelligence`, `predictive_recommendations`, `advanced_analytics`, and `ai_advisors_premium`.
- `billing/limits.py` also includes Enterprise AI Network flags: `enterprise_ai_network`, `vertical_ai_intelligence`, `industry_ai_models`, `benchmark_intelligence`, `cross_tenant_intelligence`, `vertical_ai_advisors`, and `ai_playbook_library`.
- Feature access resolves tenant status, plan flags, tenant overrides, intelligence grants, demo/full mode and monthly quota.
- Baseline rule predictions are available for `lead_scoring`, `churn_prediction`, `smart_remarketing`, and `operational_anomaly`.
- Persisted recommendation creation is gated separately from prediction generation: a tenant can receive a demo prediction through `intelligence_demo`, but `saas_intelligence_recommendations` requires `predictive_recommendations` access/quota.
- Prediction output includes `recommendation_gate` metadata so clients/admins can audit whether recommendation persistence was requested, enabled, created, or blocked.
- Prediction feedback emits `ai.prediction.feedback_recorded` and recalculates tenant/model metrics.
- Model registry rollout controls can register model metadata, block disabled/paused models, select canary registry rows deterministically by traffic percent, and mark shadow/unapproved canary predictions as `shadow` so recommendations are not auto-created from unsafe rollout states.
- Current prediction scoring remains dependency-light `baseline_rules` by default. If `SAAS_ML_ENABLED=true` and the selected registry artifact is loadable, prediction runtime can call the optional ML service. Shadow inference records `ml_inference` metadata without changing the baseline business result.
- Optional ML dependencies live in `requirements-ml.txt` and `Dockerfile.ml`; default API/worker dependencies are unchanged.
- Initial training now supports both synthetic bootstrap datasets and Postgres auto-label datasets. Auto-label models must still pass real tenant-safe label quality, drift and rollout acceptance before broad production promotion.
- Advisor context now includes latest intelligence predictions and open recommendations; Advisor still proposes actions under existing approval patterns.
- `agents/operating_system.py` exposes the Agent OS overview, inter-agent messages, tool-run traces, event subscription seeding, and Intelligence-to-orchestrator event sync.
- Agent OS APIs are tenant scoped under `/saas/v1/agents/os*` and preserve the existing one-owner conversation model from Phase 8.
- Agent OS tool runs create approval-first action drafts by default; direct side-effect execution is not performed from this control-plane.
- Phase 24.5 agent multimodal tools are the only approved path for agent-scoped voice/vision/search execution; they remain read-only and reuse media/search endpoints.
- Phase 24.6 multimodal memory captures sanitized voice/vision/search/tool outputs into `saas_multimodal_memory_events` for agent memory, RAG review and ML feature signals without raw media persistence.
- Agent OS full event-driven mode is gated by `multi_agent_os`, `event_driven_agents`, or `ai_premium`; demo mode returns candidates without enqueuing jobs.
- `GET /saas/v1/advisor/briefing` merges predictive overview, seeded insights, recommendations, actions, activity, metrics and memory for the floating AI Business Advisor.
- CRM conversation/customer payloads now include `predictive_intelligence`; conversation-level predictions are resolved from `saas_intelligence_predictions` when present and fall back to tenant-safe CRM baseline scoring.
- Kimi remains the official deep-reasoning provider through the existing AI Gateway registry and `advisor.insights` route.

## Phase 18 AI Workflow Composer Backend

Code-complete at repository level on 2026-05-27; validation is tracked in `tasks/TASK_STATE.md`.

- `057_saas_ai_workflow_composer_phase18.sql` adds Composer templates, tenant workflows, versions, simulations, approvals and materializations.
- Backend domain: `saas-version/backend/app_saas/workflow_composer/`.
- API prefix: `/saas/v1/workflow-composer`.
- `service.py` seeds safe default workflow templates, validates graph JSON, scores preflight, runs side-effect-free simulation, records approvals, versions and rollback snapshots, and activates workflows as `composer_only` materializations.
- Premium feature flags: `ai_workflow_composer` for write/control actions and `workflow_composer_templates` for template surfaces.
- Demo mode can preview state/templates; create/update/preflight/simulate/approval/activation require full `ai_workflow_composer`.
- Activation is control-plane only. It does not execute WhatsApp, Instagram, campaigns, triggers, flows, CRM mutations or agent handoffs.

## Phase 22 AI Trust, Compliance & Governance Backend

Code-complete at repository level on 2026-05-27; validation is tracked in `tasks/TASK_STATE.md`.

- `058_saas_ai_trust_compliance_governance_phase22.sql` adds governance policies, attestations, risk assessments, model cards, incidents, reports, audits and Trust AI premium feature flags.
- Backend domain: `saas-version/backend/app_saas/trust_center/`.
- Tenant API prefix: `/saas/v1/trust-center`.
- Admin API prefix: `/saas/v1/admin/trust-center`.
- `service.py` seeds default AI governance policies, resolves premium/demo access through the Intelligence gate, records tenant-scoped audits, scans existing AI control-plane surfaces for governance risk records, and generates compliance report snapshots.
- Feature flags: `ai_trust_center`, `ai_governance_policies`, `ai_risk_assessments`, `ai_model_cards`, `ai_compliance_reports`, and `ai_audit_exports`.
- Demo mode can read/preview trust state; policy/model/incident/report/risk mutations require full access and operational tenant status.
- This domain is control-plane only. It does not execute providers, deploy workflows, mutate CRM/campaigns, promote models, pause agents or run autonomous remediation.

## Phase 24.1 Multimodal Gateway Backend

Code-started at repository level on 2026-05-27 as a compatibility-first gateway foundation.

- `ai_gateway/models.py` now has `GatewayAttachment` and optional `GatewayRequest.attachments`.
- `ai_gateway/service.py` accepts optional `attachments` in `generate_with_gateway`, normalizes a bounded list, and records only safe attachment metadata in `saas_ai_runs`.
- `providers/gemini_adapter.py` can send text plus `inline_data` or `file_data` parts to Gemini when attachments are provided.
- `providers/openai_compatible.py` keeps existing text calls unchanged and can send image attachments as OpenAI-compatible `image_url` content when a selected model supports it.
- Provider catalogs now include `gemini-2.5-flash-lite` and `moonshot-v1-8k-vision-preview`; Kimi is cataloged with multimodal capability for models that support vision.
- No DB migration, dependency, runtime media fetch, OCR, transcription, web search, Inbox media analysis, agent tool, worker or Meta send behavior was added in 24.1.

Safety notes:

- Do not log `data_base64`, raw media bytes, provider file URIs containing secrets, or decrypted credentials.
- Future Inbox/media integration must add feature gates, media-size policy, provider-specific validation and approval UX before customer-facing media sends.
- Web/image search remains a later Phase 24 subphase and must include source/copyright metadata plus human approval.

## Phase 19 Autonomous Revenue Engine Backend

Code-complete and validated at repository/Docker level.

- `066_saas_revenue_memory_network_phase19_20.sql` adds revenue policies, opportunities, forecasts, experiments and reports.
- `intelligence/revenue.py` detects supervised revenue opportunities from real tenant CRM/conversation/prediction signals.
- `intelligence/router.py` exposes `/saas/v1/intelligence/revenue/*` for center, policy, analysis and opportunity status actions.
- Revenue policy enforcement now applies optional `allowed_action_types_json` and `max_monthly_revenue_actions` during approve/execute status changes.
- `workers/intelligence.py` runs revenue analysis inside a nested transaction and skips tenants without full premium access.
- Feature flags: `autonomous_revenue_engine`, `revenue_opportunity_detection`, `revenue_forecasting`, `revenue_playbooks`, `revenue_experiments`, and umbrella `ai_premium`.
- Admin feature catalogs include the new flags through existing AI Predictivo feature management.

Safety notes:

- Full mode is required before persisting opportunities/reports or changing opportunity status.
- Execution is control-plane metadata only. It does not send customer messages, call payment providers, mutate CRM, activate campaigns, execute workflows, trigger agents, or change Meta runtime.
- The engine does not invent customer revenue; estimated value remains `0` when tenant order/revenue data is unavailable.

## Phase 20 AI Enterprise Memory Network Backend

Code-complete and validated at repository/Docker level.

- `066_saas_revenue_memory_network_phase19_20.sql` adds memory policies, graph nodes, graph edges, sync runs and access logs.
- `intelligence/memory_network.py` syncs tenant-scoped memory candidates from collective memory, Knowledge/RAG, multimodal memory events and vertical insights.
- `intelligence/router.py` exposes `/saas/v1/intelligence/memory-network/*` for center, policy, sync, export, import, node review and node delete.
- `workers/intelligence.py` runs memory sync inside a nested transaction and skips tenants without full premium access.
- Feature flags: `enterprise_memory_network`, `memory_graph`, `memory_governance`, `cross_agent_memory_routing`, `memory_quality_scoring`, and umbrella `ai_premium`.
- Memory policy now actively governs sync/import/existing-node state:
  - `allowed_scopes_json` filters new candidates and prevents publishing disallowed scopes.
  - policy updates archive non-rejected/non-archived nodes outside allowed scopes.
  - `require_review_for_customer_content` demotes published customer-content nodes back to `candidate`.
  - `retention_days` refreshes `expires_at` for active nodes.
- Export/import/delete operations write `saas_enterprise_memory_access_logs` and Intelligence events.
- Import accepts bounded JSON memory nodes only, sanitizes summaries/source metadata and stores imported rows as `candidate`.

Safety notes:

- Tenant isolation is mandatory in every memory query.
- Stored nodes contain bounded summaries, metadata and hashes, not raw media/base64.
- Customer/private memory remains tenant-scoped and reviewable through candidate/published/rejected/archived status.
- Published nodes are a governance substrate; prompt/RAG consumers should use published tenant nodes only after explicit context-routing review.

## Phase 24.2 Voice Intelligence Backend

Code-complete at repository level for the first audio-analysis runtime.

- `060_saas_voice_intelligence_phase24.sql` adds `saas_voice_intelligence_analyses` and default plan feature flags for `voice_intelligence`, `voice_transcription`, and `voice_sentiment_intent`.
- `billing/limits.py` and `intelligence/catalog.py` include the new premium/demo feature keys.
- `media/router.py` exposes `POST /saas/v1/media/messages/{message_id}/voice/analyze`.
- Access is tenant scoped and role gated for `owner`, `admin`, `supervisor`, and `agent`.
- The endpoint accepts cached reads by default and reprocesses only with `force=true`.
- Audio sources:
  - local `saas_media_assets.content` when the message points to a local media asset.
  - inbound WhatsApp media through the existing Meta Graph media helpers.
- Runtime checks:
  - message belongs to the current tenant.
  - message type or MIME is audio.
  - media id exists.
  - demo/full feature gate resolves through Intelligence access.
  - audio size is bounded.
  - AI token quota is checked before provider execution.
  - provider chain currently requires Google/Gemini for real audio analysis.
- Stored output includes transcript, summary, sentiment, sentiment score, intent, intent label, urgency, language, confidence, recommended action, action items, CRM hints, safety flags and provider metadata.
- A compact analysis is mirrored to `saas_messages.payload_json.voice_intelligence` for Inbox display.
- The route records `message.audio.analyzed` as an Intelligence inline event.

Safety notes:

- Raw audio bytes and base64 media are not persisted in analysis rows or AI run metadata.
- Voice analysis is advisory. It does not create leads, tickets, tasks, campaigns, outbound messages, agent tool runs or CRM mutations.
- Non-Google audio providers remain future work until their adapter payload format and model support are validated.

## Phase 24.3 Vision Intelligence Backend

Code-complete at repository level for image/document understanding on existing Inbox media.

- `061_saas_vision_intelligence_phase24.sql` adds `saas_vision_intelligence_analyses` and default plan feature flags for `vision_intelligence`, `image_understanding`, and `document_ocr`.
- `billing/limits.py`, `intelligence/catalog.py`, and Admin plan defaults include the new premium/demo feature keys.
- `media/router.py` exposes `POST /saas/v1/media/messages/{message_id}/vision/analyze`.
- Access is tenant scoped and role gated for `owner`, `admin`, `supervisor`, and `agent`.
- The endpoint accepts cached reads by default and reprocesses only with `force=true`.
- Supported inputs are existing tenant messages with image media or supported document/file MIME types: PDF, plain text, CSV and JSON.
- Media sources are local `saas_media_assets.content` or inbound WhatsApp media through the existing Meta Graph media helpers.
- Provider routing: images can use Google/Gemini, OpenRouter or Kimi when compatible; document/OCR analysis is constrained to Google/Gemini in this runtime path.
- Stored output includes visual description, extracted text, summary, document type, sentiment, intent, urgency, language, confidence, entities, topics, product hints, moderation flags and recommended action.
- A compact result is mirrored to `saas_messages.payload_json.vision_intelligence` for Inbox display.
- The route records `message.visual.analyzed` as an Intelligence inline event.

Safety notes:

- Raw media bytes and base64 media are not persisted in analysis rows or AI run metadata.
- Vision analysis is advisory. It does not search the web, send customer media, create CRM records, launch campaigns, execute tools, assign agents or train models.
- Real provider acceptance still requires tenant credentials and sample images/documents before advertising Kimi/OpenRouter vision broadly.

## Phase 24.4 Web/Image Search Intelligence Backend

Code-complete at repository level for approval-first external source assistance.

- `062_saas_web_image_search_intelligence_phase24.sql` adds `saas_web_search_intelligence_runs`, `saas_web_search_intelligence_results`, and default plan feature flags for `web_search_intelligence`, `image_search_intelligence`, and `external_source_assist`.
- `billing/limits.py` and `intelligence/catalog.py` include the new premium/demo feature keys.
- `media/router.py` exposes `POST /saas/v1/media/search`, `GET /saas/v1/media/search/runs`, and `POST /saas/v1/media/search/results/{result_id}/approval`.
- Access is tenant scoped and role gated for `owner`, `admin`, `supervisor`, and `agent`.
- Search types are `web`, `image`, and `mixed`; demo mode has a lower result limit than full mode.
- Provider credentials are loaded from encrypted tenant API credentials for `tavily`, `brave_search`, or `serpapi`.
- Result URLs are screened before persistence; unsafe/internal/private targets are blocked and cannot be approved.
- Search runs and result review actions emit inline Intelligence events: `external_search.executed` and `external_search.result_reviewed`.
- Frontend usage is intentionally human-in-the-loop: results start as pending, can be approved/rejected, and are not sent automatically.

Safety notes:

- The backend does not fetch/crawl arbitrary result URLs after provider search.
- Search output is advisory and source-based. It does not send customer replies, mutate CRM, create tasks, launch campaigns, execute workflows, assign agents, or train models.
- External provider secrets and decrypted keys must not be logged.

## Phase 24.5 Agent Multimodal Tools Backend

Code-complete at repository level for agent-scoped multimodal context tools.

- `063_saas_agent_multimodal_tools_phase24.sql` adds default plan feature flags for `agent_multimodal_tools`, `agent_voice_tools`, `agent_vision_tools`, and `agent_external_search_tools`.
- The migration also adds a filtered index on existing `saas_ai_agent_tool_runs` for `media.voice_analyze`, `media.vision_analyze`, and `media.web_image_search`.
- `agents/multimodal_tools.py` validates tenant context, selected agent ownership, `tools_json` permission, Intelligence feature access and safe input shape.
- `agents/router.py` exposes:
  - `GET /saas/v1/agents/multimodal-tools/catalog`.
  - `GET /saas/v1/agents/{agent_id}/multimodal-tools/runs`.
  - `POST /saas/v1/agents/{agent_id}/multimodal-tools/execute`.
- `media.voice_analyze` and `media.vision_analyze` call the existing media analysis endpoints for tenant-owned Inbox messages.
- `media.web_image_search` calls the existing web/image search endpoint and leaves each source pending human approval.
- Tool runs are persisted as Agent OS traces in `saas_ai_agent_tool_runs` with compact safe outputs and failed-state auditability.
- `ai_agent/service.py` injects compact completed tool output into assigned-agent prompts; external search sources are injected only when approved and not blocked.
- `AiAgentsPanel.jsx` consumes the endpoints from the Agent OS tab.

Safety notes:

- This path does not send messages, mutate CRM, launch campaigns, execute workflows, assign agents, change Meta/billing runtime or train models.
- Do not add direct media byte loading to the agent domain; keep media access centralized in `media/router.py`.
- Do not bypass `/media/search/results/{result_id}/approval` for external sources.

## Phase 24.6 Multimodal Memory & Training Events Backend

Code-complete at repository level for sanitized memory/training/RAG event capture.

- `064_saas_multimodal_memory_training_events_phase24.sql` adds `saas_multimodal_memory_events` plus default plan flags `multimodal_memory_events`, `multimodal_training_events`, `multimodal_rag_materialization`, and `multimodal_agent_memory`.
- `agents/multimodal_memory.py` collects tenant-scoped candidates from `saas_voice_intelligence_analyses`, `saas_vision_intelligence_analyses`, approved non-blocked `saas_web_search_intelligence_results`, and completed multimodal `saas_ai_agent_tool_runs`.
- `agents/router.py` exposes:
  - `GET /saas/v1/agents/multimodal-memory/events`.
  - `POST /saas/v1/agents/multimodal-memory/sync`.
  - `POST /saas/v1/agents/multimodal-memory/events/{event_id}/materialize`.
- Sync emits Intelligence events, upserts deduplicated memory rows by replay key, and refreshes conversation feature values such as `multimodal_event_count`, `approved_external_sources_count`, `multimodal_avg_confidence`, `multimodal_sentiment_score`, `multimodal_urgency_score`, and `multimodal_text_chars`.
- Training-ready rows are gated separately by `multimodal_training_events`, `ml_predictions`, or `ai_premium`. If the training gate is unavailable, the event can still be stored as memory but is not marked training-ready.
- Materialization can create a Knowledge/RAG source, collective agent memory, or both. Customer content requires explicit operator approval in the payload.
- `media/router.py` and `agents/multimodal_tools.py` call memory sync as best-effort after successful voice/vision/search/tool actions; capture failure must not break the original media/tool action.
- `ai_agent/service.py` now prefers curated `saas_multimodal_memory_events` for assigned-agent prompt context and still restricts external source content to approved, non-blocked rows.
- `agents/service.py` serializes runtime agent table checks with a process lock and PostgreSQL advisory lock so concurrent Agent OS requests do not deadlock on idempotent DDL checks.

Safety notes:

- Raw audio/image/document bytes and base64 payloads are not stored in memory/training events.
- Phase 24.6 does not send customer messages, mutate CRM, execute workflows, launch campaigns, assign agents, change Meta/billing runtime or train models automatically.
- RAG materialization of voice/vision customer content requires explicit `allow_customer_content=true`; external source copyright/source review remains a human responsibility.

## Phase 24.7 Inbox Reference UX Backend

Code-complete at repository level for human-operated Inbox reference preparation.

- No migration was added; this phase reuses Web/Image Search, multimodal memory and CRM outbound tables.
- `media/router.py` exposes `POST /saas/v1/media/search/results/{result_id}/reference`.
- The endpoint requires tenant auth with `owner`, `admin`, `supervisor`, or `agent`.
- The endpoint resolves existing Web/Image Search feature access, validates the result belongs to the tenant, requires `approval_status='approved'`, rejects blocked sources, revalidates public URLs and validates optional `conversation_id`.
- The response is a prepared text reference with title, snippet, source URL, optional visual URL and optional license metadata.
- Actual customer delivery remains the existing CRM `POST /saas/v1/conversations/{conversation_id}/messages` endpoint, so message quota, outbound queue, status events, dispatch worker behavior and `message.sent` Intelligence capture are preserved.
- The endpoint emits `external_search.reference_prepared` for audit/Intelligence continuity.

Safety notes:

- There is no automatic customer send path in the media domain.
- Blocked or unapproved sources cannot be prepared.
- Phase 24.7 does not crawl result pages, persist raw media/base64, mutate CRM records, launch campaigns, execute workflows, assign agents, change Meta/billing runtime or train models.

## Phase 24.9-24.10 Multimodal Observability And Safe Rollout Backend

Code-complete at repository level for multimodal cost/latency/error/quality/source tracking and default-off rollout controls.

- `067_saas_multimodal_observability_rollout_phase24.sql` adds:
  - `saas_multimodal_observability_snapshots`.
  - `saas_multimodal_rollout_policies`.
  - `saas_multimodal_rollout_events`.
  - default-off feature flags `multimodal_observability`, `multimodal_cost_observability`, `multimodal_quality_monitoring`, `multimodal_safe_rollout`, and `multimodal_canary`.
- `intelligence/multimodal_observability.py` aggregates multimodal metrics from:
  - `saas_ai_runs`.
  - `saas_voice_intelligence_analyses`.
  - `saas_vision_intelligence_analyses`.
  - `saas_web_search_intelligence_runs/results`.
  - `saas_ai_agent_tool_runs`.
  - `saas_multimodal_memory_events`.
- Tenant endpoints:
  - `GET /saas/v1/intelligence/multimodal/observability/center`.
  - `POST /saas/v1/intelligence/multimodal/observability/refresh`.
  - `GET /saas/v1/intelligence/multimodal/rollout/center`.
  - `PATCH /saas/v1/intelligence/multimodal/rollout/policy`.
- Observability reports request count, estimated cost, average/P95 latency, error rate, quality/confidence and source approval/blocking counts.
- Cost estimates use Admin provider-policy price metadata from Phase 24.8. Missing prices produce zero estimates and must not be treated as free provider usage.
- Safe rollout supports `off`, `demo`, `canary` and `full` policy modes.
- Canary selection is deterministic per tenant/user/subject and can fall back to demo when `demo_enabled=true`.
- `media/router.py` applies safe rollout to Voice Intelligence, Vision Intelligence and Web/Image Search before external provider execution.

Safety notes:

- All new plan flags default to disabled.
- Runtime behavior is unchanged when rollout access or an explicit enabled rollout policy is absent.
- Rollout events are audit/control metadata only.
- Observability snapshots do not store raw media, base64, decrypted provider credentials or full customer conversation content.
- Safe rollout does not mutate CRM, campaigns, workflows, billing, Meta runtime or agent ownership.

## Phase 12 Reliability Backend

Code-complete at repository level on 2026-05-27; validation is tracked in `tasks/TASK_STATE.md`.

- `055_saas_performance_reliability_phase12.sql` adds reliability SLO policies, backpressure policies, retention policies, cleanup runs, snapshots, drills and performance indexes for high-volume queues.
- `reliability/service.py` computes SLO status from existing observability data, audits expected indexes through PostgreSQL catalog/stats, reports queue backpressure, runs allowlisted retention dry-runs, records snapshots and runs readiness drills.
- Retention cleanup is dry-run/control-plane first. Destructive cleanup requires explicit `dry_run=false` plus `superadmin` or `platform_admin`; table names and conditions are backend allowlisted.
- Backup/restore support is readiness-only: it verifies migration/table/database metadata and records drills, but does not execute real backups or restores from the API.
- Admin endpoints under `/saas/v1/admin/reliability/*` expose overview, index audit, backpressure policy updates, snapshots, drills and retention runs.
- Admin Operations exposes `/saas/v1/admin/operations/reliability/process` for a safe worker tick.
- Embedded and standalone workers call `process_due_reliability`; the worker records snapshots at most every 15 minutes and runs only enabled retention dry-runs.
- This phase intentionally does not throttle providers, pause campaigns, mutate queues, repair Meta subscriptions or change WhatsApp/Instagram runtime.

## Backend Safety Rules

- Do not infer behavior from root `backend/`.
- Before editing a router, inspect its schemas, service helpers, migrations, and frontend consumers.
- Before changing SQL fields, inspect all migrations and runtime SQL references.
- Preserve `/saas/v1` compatibility unless explicitly changing API contract.
- Preserve tenant isolation and role checks.
