# API_REFERENCE

Scope: SaaS only. Base path: `/saas/v1`.

This is a compact map for agent navigation. Inspect router files for schemas, parameters, and exact response shapes before implementation.

## Health

- `GET /health`: lightweight liveness.
- `GET /ready`: DB connectivity plus schema readiness contract; returns `503` with `schema_not_ready` when migrations/tables/columns are incomplete.

## Tenant Auth

- `POST /auth/register`
- `POST /auth/login`
- `POST /auth/login/verify-otp`
- `POST /auth/password/forgot`
- `POST /auth/password/reset`
- `POST /auth/password/change`
- `GET /auth/security`
- `PATCH /auth/security/2fa`
- `POST /auth/refresh`
- `POST /auth/switch-tenant`
- `GET /auth/me`

Tenant Auth notes:

- Tenant login can return `{mfa_required: true, challenge_token, method: "email_otp"}` before issuing access/refresh tokens.
- `POST /auth/login/verify-otp` verifies the email OTP challenge and returns MFA-verified access/refresh tokens.
- `PATCH /auth/security/2fa` currently supports `email_otp` and `none`; TOTP/authenticator apps are not implemented.

## Platform Admin

- `POST /admin/auth/bootstrap`
- `POST /admin/auth/login`
- `POST /admin/auth/login/verify-otp`
- `GET /admin/auth/me`
- `GET /admin/auth/security`
- `PATCH /admin/auth/security/2fa`
- `GET /admin/feature-flags/catalog`
- `GET /admin/intelligence/catalog`
- `GET /admin/intelligence/tenants`
- `GET /admin/intelligence/tenants/{tenant_id}`
- `PATCH /admin/intelligence/tenants/{tenant_id}/features`
- `GET /admin/intelligence/premium-gating`
- `PATCH /admin/intelligence/plans/{plan_code}/features`
- `PATCH /admin/intelligence/provider-policies`
- `GET /admin/intelligence/model-metrics`
- `POST /admin/intelligence/model-metrics/recompute`
- `GET /admin/intelligence/models`
- `POST /admin/intelligence/models`
- `GET /admin/intelligence/models/{model_key}/assessment`
- `PATCH /admin/intelligence/models/{model_key}`
- `GET /admin/intelligence/training-dataset`
- `GET /admin/intelligence/mlops`
- `POST /admin/intelligence/ml-training/synthetic`
- `POST /admin/intelligence/auto-labels/generate`
- `POST /admin/intelligence/feature-pipelines/recompute`
- `POST /admin/intelligence/ml-datasets/build`
- `POST /admin/intelligence/ml-training/autolabel`
- `GET /admin/intelligence/realtime`
- `POST /admin/intelligence/realtime/metrics/refresh`
- `GET /admin/overview`
- `GET /admin/tenants`
- `GET /admin/tenants/{tenant_id}`
- `PATCH /admin/tenants/{tenant_id}`
- `POST /admin/tenants/{tenant_id}/feature-flags`
- `POST /admin/tenants/{tenant_id}/impersonate`
- `GET|POST /admin/plans`
- `PATCH /admin/plans/{plan_code}`
- `GET /admin/subscriptions`
- `PATCH /admin/subscriptions/{tenant_id}`
- `GET|POST /admin/billing/invoices`
- `GET /admin/billing/invoices/{invoice_id}/pdf`
- `GET|POST /admin/billing/credits`
- `POST /admin/billing/lifecycle/sync`
- `GET /admin/audit`
- `GET /admin/audit/export.csv`
- `GET /admin/security/compliance`
- `GET /admin/operations/queues`
- `POST /admin/operations/webhooks/process`
- `POST /admin/operations/outbound/process`
- `POST /admin/operations/triggers/process`
- `POST /admin/operations/ai/process`
- `POST /admin/operations/remarketing/process`
- `POST /admin/operations/agents/process`
- `POST /admin/operations/intelligence/process`
- `POST /admin/operations/reliability/process`
- `POST /admin/operations/meta-tokens/process`
- `GET /admin/trust-center/overview`
- `GET /admin/trust-center/tenants`
- `GET /admin/reliability/overview`
- `GET /admin/reliability/index-audit`
- `GET /admin/reliability/backpressure`
- `PATCH /admin/reliability/backpressure/{queue_key}`
- `POST /admin/reliability/snapshot`
- `POST /admin/reliability/drills/{drill_type}`
- `PATCH /admin/reliability/retention/{policy_key}`
- `POST /admin/reliability/retention/run`
- `GET /admin/observability/health`
- `GET /admin/observability/meta-errors`
- `GET /admin/observability/dead-letter`
- `POST /admin/observability/dead-letter/sync`
- `POST /admin/observability/dead-letter/{event_id}/retry`
- `POST /admin/observability/dead-letter/{event_id}/resolve`

Admin Intelligence notes:

- `POST /admin/intelligence/models` registers model metadata for ModelOps/rollout governance.
- `POST /admin/intelligence/ml-training/synthetic` calls the optional ML service and can register the resulting artifact as a shadow candidate when `SAAS_ML_ENABLED=true`.
- `POST /admin/intelligence/auto-labels/generate` creates training labels from real SaaS events/state; it does not require manual labeling or external datasets.
- `POST /admin/intelligence/feature-pipelines/recompute` recomputes ML training features per tenant/task/window and records pipeline run stats.
- `POST /admin/intelligence/ml-datasets/build` asks the optional ML service to materialize a dataset from Postgres auto-labels and feature-store rows.
- `POST /admin/intelligence/ml-training/autolabel` trains a LightGBM/XGBoost/sklearn model from the auto-label dataset, logs MLflow/BentoML artifacts when available, and can register the result as a shadow candidate.
- `GET /admin/intelligence/premium-gating` returns Phase 24.8-24.10 tenant feature state, plan feature limits, provider policies, credential readiness and estimated AI/search provider costs.
- `PATCH /admin/intelligence/plans/{plan_code}/features` upserts plan-level Intelligence feature mode/quota; tenant grants still override plan limits.
- `PATCH /admin/intelligence/provider-policies` upserts global/plan/tenant AI/search/TTS provider policy, availability, quota and cost metadata used by AI Gateway and Web/Image Search provider routing.
- `GET /admin/intelligence/realtime` returns tenant-level live Intelligence activity, sessions, recent predictions/recommendations and realtime feature modes.
- `POST /admin/intelligence/realtime/metrics/refresh` writes metric snapshots only to `saas_realtime_intelligence_metrics`; it does not process queues or mutate tenant runtime.
- Model registry and ML training writes require platform admin roles and create audit/rollout events when registry rows change.
- Current tenant predictions still use baseline fallback by default; trained inference runs only when ML is explicitly enabled and a registry artifact is ready.

Admin Reliability notes:

- `GET /admin/reliability/overview` feeds the Phase 12 Performance view with SLO metrics, backpressure state, index audit, backup readiness, retention policies, cleanup runs, drills and snapshots.
- `POST /admin/reliability/snapshot` records an SLO/backpressure snapshot only; it does not mutate queues/providers.
- `POST /admin/reliability/drills/{drill_type}` supports `load_smoke`, `backup_readiness`, `retention_dry_run`, and `slo_snapshot`.
- `POST /admin/reliability/retention/run` defaults to `dry_run=true`. Destructive retention requires `dry_run=false` and a platform admin/superadmin role; cleanup SQL is allowlisted in backend service code.
- `POST /admin/operations/reliability/process` runs the safe reliability worker tick: snapshot if due plus enabled retention dry-run. It does not call Meta or alter business queues.

Admin Security/Compliance notes:

- Admin login can return `{mfa_required: true, challenge_token, method: "email_otp"}` before issuing a platform token.
- `POST /admin/auth/login/verify-otp` verifies the email OTP challenge and returns a platform token with MFA verification claim.
- `GET /admin/auth/security` and `PATCH /admin/auth/security/2fa` manage the current platform admin email OTP preference.
- `GET /admin/security/compliance` feeds the Admin `Security` view with 2FA, webhook signature, security-event and privacy-request metrics.
- `GET /admin/audit/export.csv` exports recent audit rows as CSV for platform review.

Admin AI Trust notes:

- `GET /admin/trust-center/overview` feeds Admin `Trust AI` with aggregate open risks, high risks, incidents, policies, model cards, tenant source signals and recent governance audit events.
- `GET /admin/trust-center/tenants` returns the same tenant-level trust snapshot for platform review.
- Admin Trust endpoints are read-only control-plane surfaces; they do not mutate tenant agents, workflows, models, queues, providers or billing state.

## Tenants

- `GET /tenants`
- `POST /tenants`
- `PATCH /tenants/{tenant_id}`

Tenant notes:

- Register/create tenant payloads can include `industry_code`.
- Tenant responses include `industry_code` and `vertical_pack_applied_at` when available.

## Verticals

- `GET /verticals/public-packs`
- `GET /verticals/packs`
- `GET /verticals/state`
- `POST /verticals/apply`

## Compliance

- `GET /compliance/me/export`
- `GET /compliance/customers/{conversation_id}/export`
- `POST /compliance/customers/{conversation_id}/delete-request`
- `GET /compliance/privacy-requests`

Compliance notes:

- All compliance endpoints are tenant scoped and require authenticated tenant context.
- Customer exports are tied to a tenant conversation id; cross-tenant conversation ids are not returned.
- Delete requests create `saas_privacy_requests` rows for review. They do not hard-delete conversations, messages, CRM records, RAG files, agent memories or audit history automatically.
- Owner/admin roles can create and list privacy requests; current-user export is available to any authenticated tenant user.

Vertical notes:

- Public packs are available without tenant auth for registration/onboarding selectors.
- Authenticated state/apply calls are tenant scoped and mounted under `/saas/v1`.
- `POST /verticals/apply` can optionally request recommended factory agent creation; triggers remain inactive and flows remain draft after pack application.

## CRM Inbox

- `GET|POST /customers`
- `GET|PATCH /customers/{conversation_id}`
- `GET /customers/{conversation_id}/dedupe-candidates`
- `POST /customers/{target_conversation_id}/merge`
- `GET /crm/config`
- `POST /crm/custom-fields`
- `PATCH|DELETE /crm/custom-fields/{field_id}`
- `GET /crm/pipeline`
- `POST /crm/pipeline/presets/{industry_code}`
- `POST /crm/pipeline/stages`
- `PATCH|DELETE /crm/pipeline/stages/{stage_id}`
- `GET /dashboard/overview`
- `GET|POST /labels`
- `PATCH /labels/{label_id}`
- `POST|DELETE /customers/{conversation_id}/labels/{label_id}`
- `GET /conversations`
  - Optional query: `search`, `channel`, `queue`, `agent_id`, `limit`.
  - `queue`: `all`, `unread`, `mine`, `unassigned`, `sla`, `hot`, `human`, `ai`.
- `GET /conversations/{conversation_id}/messages`
- `POST /conversations/{conversation_id}/messages`
- `GET /conversations/{conversation_id}/tasks`
- `POST /conversations/{conversation_id}/tasks`
- `GET /crm/tasks`
- `PATCH /crm/tasks/{task_id}`
- `POST /conversations/{conversation_id}/score`
- `GET /conversations/{conversation_id}/status-events`
- `GET /conversations/{conversation_id}/timeline`
- `PATCH /conversations/{conversation_id}/ai-agent`
- `POST /outbound/process`
- `POST /conversations/{conversation_id}/read`
- `POST /conversations/{conversation_id}/takeover`

## Campaigns

- `GET /campaigns/catalog`
- `GET /campaigns/templates/params/catalog`
- `GET /campaigns/triggers/catalog`
- `GET /campaigns/summary`
- `GET|PATCH /campaigns/settings/quiet-hours`
- `GET /campaigns/ab-report`
- `GET|POST /campaigns/templates`
- `PATCH /campaigns/templates/{template_id}`
- `POST /campaigns/segments/preview`
- `GET|POST /campaigns/segments`
- `PATCH /campaigns/segments/{segment_id}`
- `GET|POST /campaigns/items`
- `POST /campaigns/items/preflight`
- `POST /campaigns/items/{campaign_id}/preflight`
- `PATCH /campaigns/items/{campaign_id}`
- `GET|POST /campaigns/triggers`
- `POST /campaigns/triggers/preflight`
- `POST /campaigns/triggers/simulate`
- `POST /campaigns/triggers/{trigger_id}/preflight`
- `GET /campaigns/triggers/{trigger_id}/versions`
- `POST /campaigns/triggers/{trigger_id}/versions/{version_id}/restore`
- `PATCH|DELETE /campaigns/triggers/{trigger_id}`
- `POST /campaigns/triggers/{trigger_id}/copy`
- `GET|POST /campaigns/flows`
- `POST /campaigns/flows/process`
- `POST /campaigns/flows/preflight`
- `POST /campaigns/flows/{flow_id}/preflight`
- `PATCH /campaigns/flows/{flow_id}`

## Commerce

- `GET /commerce/products`

## Broadcasts

- `GET /broadcasts/meta/templates`
- `POST /broadcasts/meta/templates/sync`
- `POST /broadcasts/meta/templates`
- `PATCH /broadcasts/meta/templates/{template_id}`
- `GET|POST /broadcasts`
- `POST /broadcasts/preview`
- `PATCH /broadcasts/{broadcast_id}`
- `POST /broadcasts/{broadcast_id}/enqueue`
- `GET /broadcasts/{broadcast_id}/report`
- `GET /broadcasts/{broadcast_id}/export.csv`
- `POST /broadcasts/{broadcast_id}/retry-failed`
- `GET /broadcasts/{broadcast_id}/recipients`

## Ads And Social

- `GET /ads/summary`
- `GET|POST /ads/accounts`
- `PATCH /ads/accounts/{account_id}`
- `GET|POST /ads/campaigns`
- `PATCH /ads/campaigns/{campaign_id}`
- `GET /ads/leads`
- `POST /ads/leads/import`
- `PATCH /ads/leads/{lead_id}`
- `POST /ads/leads/{lead_id}/to-inbox`
- `GET /ads/comments`
- `POST /ads/comments/import`
- `PATCH /ads/comments/{comment_id}`
- `POST /ads/comments/{comment_id}/to-inbox`
- `POST /ads/webhook-events/process`
- `GET /social/comments`
- `GET|PATCH /social/comments/settings`
- `POST /social/comments/{comment_id}/reply`
- `POST /social/comments/{comment_id}/react`
- `POST /social/comments/{comment_id}/generate-ai`
- `POST /social/comments/ensure-tables`

## Integrations

- `GET|POST /integrations`
- `DELETE /integrations/{integration_id}`
- `GET /integrations/meta/{channel}/token-health`
- `POST /integrations/meta/{channel}/token-refresh`
- `GET /integrations/meta/facebook/diagnostics`
- `GET /integrations/meta/whatsapp/phone-numbers`
- `POST /integrations/meta/whatsapp/register-phone`
- `POST /integrations/instagram/oauth/start`
- `GET /integrations/instagram/oauth/callback`
- `GET /integrations/instagram/oauth/assets`
- `POST /integrations/instagram/connect`
- `POST /integrations/instagram/connect-facebook`
- `GET /integrations/instagram/diagnostics`
- `GET /internal/whatsapp/check-subscription`

## Credentials, AI, Knowledge

- `GET|POST /api-credentials`
- `GET /api-credentials/{provider_code}/models`
- `GET /ai-gateway/providers`
- `GET /ai-gateway/routes`
- `GET /ai-gateway/runs`
- `GET /intelligence/catalog`
- `GET /intelligence/state`
- `GET /intelligence/overview`
- `GET /intelligence/realtime/center`
- `GET /intelligence/realtime/events`
- `POST /intelligence/realtime/sessions`
- `PATCH /intelligence/realtime/cursor`
- `POST /intelligence/realtime/sessions/{session_id}/close`
- `GET /intelligence/realtime/stream`
- `POST /intelligence/events`
- `GET /intelligence/features`
- `POST /intelligence/features/recompute`
- `POST /intelligence/predict`
- `GET /intelligence/predictions`
- `GET /intelligence/feedback`
- `POST /intelligence/predictions/{prediction_id}/feedback`
- `GET /intelligence/model-metrics`
- `GET /intelligence/recommendations`
- `POST /intelligence/recommendations/{recommendation_id}/dismiss`
- `GET /intelligence/network/center`
- `POST /intelligence/network/refresh`
- `GET /intelligence/network/playbooks`
- `GET /intelligence/federated/center`
- `PATCH /intelligence/federated/policy`
- `POST /intelligence/federated/rounds/prepare`
- `POST /intelligence/federated/rounds/{round_id}/submit-update`
- `POST /intelligence/federated/rounds/{round_id}/aggregate`
- `GET /intelligence/operations/center`
- `PATCH /intelligence/operations/control`
- `POST /intelligence/operations/analyze`
- `GET /intelligence/operations/actions`
- `POST /intelligence/operations/actions/{action_id}/approve`
- `POST /intelligence/operations/actions/{action_id}/execute`
- `POST /intelligence/operations/actions/{action_id}/dismiss`
- `GET /intelligence/multimodal/observability/center`
- `POST /intelligence/multimodal/observability/refresh`
- `GET /intelligence/multimodal/rollout/center`
- `PATCH /intelligence/multimodal/rollout/policy`
- `GET /ecosystem/overview`
- `GET /ecosystem/marketplace`
- `GET /ecosystem/installations`
- `POST /ecosystem/marketplace/{item_id}/install`
- `PATCH /ecosystem/installations/{installation_id}`
- `GET|POST /ecosystem/plugins`
- `PATCH /ecosystem/plugins/{plugin_id}`
- `GET|POST /ecosystem/tools`
- `PATCH /ecosystem/tools/{tool_id}`
- `GET|POST /ecosystem/event-subscriptions`
- `PATCH /ecosystem/event-subscriptions/{subscription_id}`
- `GET|POST /ecosystem/developer/apps`
- `PATCH /ecosystem/developer/apps/{app_id}`
- `POST /ecosystem/developer/apps/{app_id}/rotate-key`
- `GET /ecosystem/sdk/manifest`
- `GET|POST /ecosystem/external-integrations`
- `PATCH /ecosystem/external-integrations/{integration_id}`
- `GET|POST /ecosystem/ai-apps`
- `PATCH /ecosystem/ai-apps/{app_id}`
- `GET /ecosystem/metrics`

Intelligence tenant notes:

- Client `Inteligencia` consumes these endpoints through `IntelligencePanel.jsx`.
- `GET /intelligence/overview` is the compact product-facing Predictive Intelligence payload: premium state, CRM aggregates, latest predictions, recommendations, feature rows, ModelOps observability, predictive cards and executive summaries.
- `GET /intelligence/realtime/center` is the Phase 16 live snapshot for tenant UI: sanitized events, live metrics, alerts, predictions, recommendations, ModelOps, operations and Trust signals.
- `GET /intelligence/realtime/events` returns sanitized event feed rows. Raw event payload content is not exposed.
- `POST /intelligence/realtime/sessions` and `PATCH /intelligence/realtime/cursor` maintain user live-session/cursor state and are gated by realtime feature flags.
- `GET /intelligence/realtime/stream` is bounded SSE with polling fallback semantics; the tenant UI currently uses polling every 8 seconds.
- Prediction writes are role-gated backend-side; generated predictions still require enabled demo/full grants, operational tenant status, quotas, and active model registry state.
- Persisted recommendations are gated separately: `persist_recommendations=true` only writes `saas_intelligence_recommendations` when `predictive_recommendations` is enabled and within quota. Blocked persistence is exposed through prediction `output_json.recommendation_gate`.
- Optional ML output is exposed under prediction `output_json.ml_inference`; shadow inference does not change the baseline score or recommendation persistence.
- Feedback and recommendation dismiss actions are tenant-scoped and intended for owner/admin/supervisor workflows.
- Autonomous operations endpoints feed the tenant AI Operations Center and AI Control Center. They are tenant-scoped, premium/demo gated, and role-gated for policy/action mutations.
- `POST /intelligence/operations/analyze` detects anomalies, updates reports and can create supervised action records according to the tenant autonomy level.
- `POST /intelligence/operations/actions/{action_id}/execute` currently records controlled execution results; it does not directly mutate Meta, queues, campaigns, CRM or billing.
- Demo mode can preview/analyze operations but forces auto-remediation and low-risk auto-execute off.
- Enterprise AI Network endpoints feed Industry Intelligence Center, Benchmark Dashboard, Vertical AI Advisors, AI Playbook Marketplace and AI Knowledge Network in `IntelligencePanel.jsx`.
- `GET /intelligence/network/center` returns current industry profile, feature state, privacy policy, tenant metrics, benchmarks, insights, playbooks, industry-model metadata and knowledge-network nodes.
- `POST /intelligence/network/refresh` supports `dry_run=true` demo previews; `dry_run=false` persists benchmark comparisons/insights and requires full `enterprise_ai_network`, `cross_tenant_intelligence`, or `ai_premium` access.
- `GET /intelligence/network/playbooks` returns published vertical playbooks for the tenant industry and general fallback. Playbooks are recommendations only and do not activate triggers or flows.
- Phase 17 Federated Learning endpoints feed the tenant Federated Learning panel in `IntelligencePanel.jsx`.
- `GET /intelligence/federated/center` returns opt-in policy, local aggregate previews, rounds, tenant updates, aggregate results and global signals. Read/demo access is allowed; mutation requires full feature access.
- `PATCH /intelligence/federated/policy` updates tenant opt-in, auto-participation, privacy mode, sample thresholds and allowed federated tasks.
- `POST /intelligence/federated/rounds/prepare` supports `dry_run=true` local package preview or `dry_run=false` round upsert plus tenant update submission.
- `POST /intelligence/federated/rounds/{round_id}/submit-update` submits the current tenant aggregate package for an existing compatible round.
- `POST /intelligence/federated/rounds/{round_id}/aggregate` computes weighted aggregate metrics and global signals only from submitted aggregate packages.
- Federated endpoints never expose raw messages, conversations, media, provider secrets, prompts, tenant names or private customer content from other tenants, and they do not promote production models automatically.
- Phase 24.9 tenant observability endpoints expose multimodal request volume, estimated cost, latency, errors, quality/confidence and sources used across voice, vision, web/image search, agent tool runs and multimodal memory events.
- `POST /intelligence/multimodal/observability/refresh` can run as preview or persist a snapshot to `saas_multimodal_observability_snapshots`; persisted snapshots require full observability access.
- Phase 24.10 rollout endpoints manage tenant rollout policy rows for multimodal feature/modality/provider combinations.
- Rollout policy modes are `off`, `demo`, `canary` and `full`; runtime enforcement is compatibility-safe and only applies when the tenant has rollout access and an enabled explicit policy.

AI Platform Ecosystem tenant notes:

- Client `AI Ecosystem` consumes `/ecosystem/*` through `AiEcosystemPanel.jsx`.
- Marketplace lists Scentra-published agent templates, workflows, playbooks, automations, AI packs and AI apps.
- Marketplace install and all create/update ecosystem mutations require full premium feature access such as `ai_marketplace`, `ai_plugin_center`, `ai_developer_console`, `ai_tool_registry`, `ai_app_framework`, or umbrella `ai_premium`.
- Demo mode can read/preview ecosystem state but mutation endpoints return feature/full-mode gating errors.
- Developer app API keys are returned once and stored hashed; raw external provider secrets are not stored in ecosystem tables.
- Plugin, tool, external integration and AI app records are metadata/control-plane manifests. No untrusted plugin runtime is executed from API/worker.

AI Gateway multimodal notes:

- Public AI Gateway endpoints remain read-only catalog/run surfaces: `/ai-gateway/providers`, `/routes`, and `/runs`.
- Phase 24.1 changed the internal `generate_with_gateway` contract, not the public API surface.
- Internal gateway callers can now pass optional attachments with `kind`, `mime_type`, `data_base64`, `uri`, `text`, `name`, and `metadata`.
- Gemini receives attachments through multimodal content parts; OpenAI-compatible providers can receive image parts when the selected provider/model supports them.
- Run history stores safe attachment counts/kinds/MIME types only, never raw base64 or media bytes.
- The internal gateway now performs retryable model failover before provider failover. Transient provider/model errors such as `429`, `503`, temporary high demand, timeout, unavailable or empty provider output can try the next allowed model/provider without losing the pending AI task.
- `GET /ai-gateway/runs` can show multiple failed/skipped attempts followed by a success; success metadata can include `model_fallback_used`, candidate models and attempt summaries.
- Inbox media analysis exists through explicit media-domain endpoints for existing tenant audio/image/document messages.
- Phase 24.4 adds approval-first external source assistance under `/media/search`; Phase 24.7 adds a human-operated reference preparation endpoint and still sends only through the existing CRM outbound path.
- Phase 24.5 adds agent-scoped multimodal tools under `/agents/*/multimodal-tools/*`; these reuse existing media/search endpoints and Agent OS traces.
- Phase 24.8 Admin provider policies can disable a provider/model or enforce monthly request/cost limits before AI Gateway or Web/Image Search calls.
- Phase 24.9/24.10 add observability and safe-rollout policy around the same multimodal runtime; no new direct send, CRM mutation or Meta runtime path is introduced.

Internal ML service notes:

- Optional service base: `SAAS_ML_SERVICE_URL`, default `http://ml-service:8090`.
- Internal endpoints outside `/saas/v1`: `GET /health`, `GET /models`, `POST /train/synthetic`, `POST /datasets/build`, `POST /train/autolabel`, `POST /predict`, `POST /drift/evaluate`, `GET /metrics`.
- These endpoints are for the optional Docker `ml` profile and should not be exposed publicly without an auth/proxy design.
- `GET|PUT /ai/settings`
- `GET /ai/conversations/{conversation_id}/memory`
- `POST /ai/conversations/{conversation_id}/process`
- `POST /ai/test`
- `GET /knowledge/sources`
- `POST /knowledge/search`
- `POST /knowledge/evaluate`
- `GET /knowledge/evaluations`
- `GET /knowledge/health`
- `POST /knowledge/upload`
- `POST /knowledge/url`
- `POST /knowledge/sources/{source_id}/reindex`
- `POST /knowledge/reindex`
- `DELETE /knowledge/sources/{source_id}`

## Advisor And Agents

- `GET /advisor/threads`
- `GET /advisor/threads/{thread_id}`
- `GET /advisor/memory`
- `GET /advisor/metrics`
- `GET /advisor/briefing`
- `GET /advisor/activity`
- `POST /advisor/messages/{message_id}/feedback`
- `POST /advisor/chat`
- `POST /advisor/chat/stream`
- `GET /advisor/insights`
- `GET /advisor/recommendations`
- `GET|POST /advisor/actions`
- `POST /advisor/recommendations/{recommendation_id}/action`
- `POST /advisor/insights/{insight_id}/action`
- `POST /advisor/actions/{action_id}/approve`
- `POST /advisor/actions/{action_id}/dismiss`
- `POST /advisor/actions/{action_id}/execute`
- `POST /advisor/insights/{insight_id}/dismiss`
- `POST /advisor/recommendations/{recommendation_id}/dismiss`

Advisor notes:

- `GET /advisor/briefing` feeds the floating Advisor with predictive overview, proactive insights, recommendations, actions, activity, metrics and memory in one compact call.
- Advisor briefing and seeded predictive insights do not execute actions; execution still requires the existing action approval flow.
- `GET /agents/templates`
- `GET /agents/limits`
- `GET /agents/catalog`
- `GET /agents/multimodal-tools/catalog`
- `GET /agents/memories`
- `POST /agents/memories/{memory_id}/restore`
- `DELETE /agents/memories/{memory_id}`
- `GET /agents/memories/{memory_id}/export`
- `POST /agents/memories/import`
- `GET|POST /agents`
- `POST /agents/from-template/{agent_type}`
- `GET /agents/governance`
- `GET|POST /agents/collective-memory`
- `DELETE /agents/collective-memory/{memory_id}`
- `POST /agents/{agent_id}/prompt-versions`
- `GET /agents/orchestrator`
- `POST /agents/orchestrator/events`
- `POST /agents/orchestrator/tick`
- `GET /agents/os`
- `GET|POST /agents/os/messages`
- `POST /agents/os/event-sync`
- `GET /agents/multimodal-memory/events`
- `POST /agents/multimodal-memory/sync`
- `POST /agents/multimodal-memory/events/{event_id}/materialize`
- `GET|PATCH /agents/{agent_id}`
- `GET /agents/{agent_id}/runtime`
- `GET /agents/{agent_id}/preflight`
- `GET|POST /agents/{agent_id}/action-drafts`
- `GET|POST /agents/{agent_id}/tool-runs`
- `GET /agents/{agent_id}/multimodal-tools/runs`
- `POST /agents/{agent_id}/multimodal-tools/execute`
- `POST /agents/{agent_id}/activate`
- `POST /agents/{agent_id}/pause`
- `POST /agents/{agent_id}/archive`
- `GET|POST /agents/{agent_id}/events`

Agent notes:

- `GET|POST /agents` supports factory and custom agents; custom/factory prompts include `system_prompt_template`, `system_prompt_variables_json`, and `system_prompt_rendered`.
- `POST /agents/{agent_id}/activate` is gated by preflight.
- Conversation AI ownership is controlled through CRM: `PATCH /conversations/{conversation_id}/ai-agent?agent_id=<uuid>` assigns; an empty `agent_id` releases back to general AI.
- `GET /agents/os` returns the Phase 11 Agent OS control-plane snapshot: core-agent coverage, memory layers, event subscriptions, messages, tool-run traces, runtime traces, model routing, orchestrator state, plan limits and premium/demo status.
- `POST /agents/os/event-sync` scans recent Intelligence predictions/recommendations and enqueues orchestrator jobs only in full premium mode; demo mode returns candidates as a safe preview.
- `POST /agents/{agent_id}/tool-runs` records a tool-run request and creates a human-approval action draft by default. It does not execute side-effect tools directly.
- `GET /agents/multimodal-tools/catalog` returns the Phase 24.5 read-only multimodal tool catalog: `media.voice_analyze`, `media.vision_analyze`, and `media.web_image_search`.
- `POST /agents/{agent_id}/multimodal-tools/execute` requires the selected agent to have the tool in `tools_json`, then executes only existing tenant-owned media/search paths.
- Voice/vision agent tools require a real `message_id`. Search tools require `query` and can include optional `conversation_id`, `message_id`, `search_type`, `provider_code`, and `limit`.
- Agent multimodal runs are persisted in `saas_ai_agent_tool_runs`; web/image search results still require `/media/search/results/{result_id}/approval` before they can be injected into agent context.
- Agent multimodal tools do not send customer messages, mutate CRM, launch campaigns, execute workflows, assign agents, train models, or bypass human approval for external sources.
- `GET /agents/multimodal-memory/events` lists Phase 24.6 tenant-scoped memory/training/RAG events captured from voice analysis, vision analysis, approved external sources and completed multimodal tool runs.
- `POST /agents/multimodal-memory/sync` scans recent multimodal outputs and upserts sanitized `saas_multimodal_memory_events`. Training-ready flags require `multimodal_training_events`, `ml_predictions`, or `ai_premium`; memory access alone stores events without enabling training.
- `POST /agents/multimodal-memory/events/{event_id}/materialize` can materialize a reviewed event to Knowledge/RAG, collective agent memory, or both. Customer-content materialization requires explicit `allow_customer_content=true`.
- Phase 24.6 does not persist raw media/base64, send customer messages, train models automatically, mutate CRM, launch campaigns, execute workflows, assign agents, or bypass source approval.

Conversation AI notes:

- `/ai/settings.metadata_json` supports human reply controls used by `ai_agent/service.py`: `human_reply_style_enabled`, `human_reply_splitting_enabled`, `reply_max_output_tokens`, `reply_chunk_chars`, `reply_initial_delay_ms`, `reply_chunk_delay_ms`, `recent_message_limit`, `message_context_chars`, `typing_indicator_enabled`, and `inbound_cooldown_seconds`.
- Optional `/ai/settings.metadata_json` model resilience keys: `model_failover_enabled` false disables same-provider model failover, `model_fallback_attempt_limit` caps candidates, and `model_fallbacks_json` can define provider-specific candidate arrays such as `{ "google": ["gemini-2.5-flash-lite"] }`.
- Humanized mode preserves CRM/memory/facts/Knowledge/RAG/collective/multimodal context while bounding raw recent transcript to reduce tokens.
- Fragmented replies use the existing CRM outbound queue and quota/status flow; each fragment is a separate outbound message.
- If all model/provider attempts fail with retryable provider errors, pending conversation replies remain eligible for the existing worker retry flow instead of being permanently skipped.

## Workflow Composer

- `GET /workflow-composer/overview`
- `GET /workflow-composer/templates`
- `POST /workflow-composer/templates/{template_key}/instantiate`
- `GET|POST /workflow-composer/workflows`
- `GET|PATCH /workflow-composer/workflows/{workflow_id}`
- `POST /workflow-composer/workflows/{workflow_id}/preflight`
- `POST /workflow-composer/workflows/{workflow_id}/simulate`
- `POST /workflow-composer/workflows/{workflow_id}/approval/request`
- `POST /workflow-composer/workflows/{workflow_id}/approval/review`
- `POST /workflow-composer/workflows/{workflow_id}/materialize`
- `POST /workflow-composer/workflows/{workflow_id}/activate`
- `GET /workflow-composer/workflows/{workflow_id}/versions`
- `POST /workflow-composer/workflows/{workflow_id}/versions/{version_id}/restore`

Workflow Composer notes:

- Template/demo surfaces use `workflow_composer_templates` or demo access.
- Create/update/preflight/simulate/approval/activation require full `ai_workflow_composer`.
- Simulation is side-effect free.
- Activation currently creates a `composer_only` materialization and does not execute WhatsApp, Instagram, trigger, flow, campaign, CRM or agent runtime side effects.

## Autonomous Revenue And Enterprise Memory

- `GET /intelligence/revenue/center`
- `PATCH /intelligence/revenue/policy`
- `POST /intelligence/revenue/analyze`
- `POST /intelligence/revenue/opportunities/{opportunity_id}/approve`
- `POST /intelligence/revenue/opportunities/{opportunity_id}/execute`
- `POST /intelligence/revenue/opportunities/{opportunity_id}/dismiss`
- `GET /intelligence/memory-network/center`
- `PATCH /intelligence/memory-network/policy`
- `POST /intelligence/memory-network/sync`
- `GET /intelligence/memory-network/export`
- `POST /intelligence/memory-network/import`
- `POST /intelligence/memory-network/nodes/{node_id}/review`
- `DELETE /intelligence/memory-network/nodes/{node_id}`

Revenue Engine notes:

- Phase 19 is tenant-scoped and premium-gated through `autonomous_revenue_engine`, the revenue subfeatures, or `ai_premium`.
- Demo/read access can preview policy, metrics and candidates; full mode is required to persist opportunities, forecasts, reports or status changes.
- `PATCH /intelligence/revenue/policy` controls autonomy level, currency, revenue goal, monthly control-plane action cap and optional allowed playbook action types.
- Approve/execute actions enforce the optional action-type allowlist and `max_monthly_revenue_actions` cap when configured.
- Opportunity execution is a control-plane status record only. It does not send messages, charge payment providers, mutate CRM records, activate campaigns/workflows/triggers or change Meta runtime.
- Unknown tenant customer revenue is stored as `0`; the engine does not invent commercial value when no order/commerce data exists.

Enterprise Memory Network notes:

- Phase 20 is tenant-scoped and premium-gated through `enterprise_memory_network`, the memory subfeatures, or `ai_premium`.
- Sync can preview candidates in dry-run mode and persists nodes/edges/sync runs only in full mode.
- Sources are bounded summaries from collective memory, Knowledge/RAG, multimodal memory events and vertical insights.
- Node review supports `candidate`, `published`, `rejected`, and `archived`.
- Policy controls enforce privacy mode, retention days, allowed memory scopes and customer-content review on sync/publish and existing nodes.
- Export returns tenant-scoped policy, nodes, edges and safety metadata; import accepts bounded JSON nodes, sanitizes them, applies policy and stores them as `candidate`.
- Node delete is tenant-scoped, cascades graph edges through DB FK behavior and records an access/audit event.
- The network stores summaries, metadata and hashes only. It does not share raw content across tenants, store raw media/base64 or publish customer memory to prompts without review.

## AI Trust Center

- `GET /trust-center/overview`
- `GET|POST /trust-center/policies`
- `PATCH /trust-center/policies/{policy_id}`
- `POST /trust-center/policies/{policy_id}/attest`
- `GET /trust-center/risk-assessments`
- `POST /trust-center/risk-assessments/run`
- `PATCH /trust-center/risk-assessments/{assessment_id}`
- `GET|POST /trust-center/model-cards`
- `PATCH /trust-center/model-cards/{card_id}`
- `GET|POST /trust-center/incidents`
- `PATCH /trust-center/incidents/{incident_id}`
- `GET /trust-center/audits`
- `GET /trust-center/reports`
- `POST /trust-center/reports/generate`

AI Trust Center notes:

- Tenant reads use `ai_trust_center` or demo access; write/control operations require full feature access for the relevant trust feature and an operational tenant status.
- Policies, risk assessments, model cards, incidents, reports and audits are tenant-scoped governance records.
- Risk scans inspect existing agents, workflows, model registry rows, tool registry rows, plugins and autonomous operation actions when those tables exist. They do not pause, activate, deploy, execute or repair those systems.
- Compliance reports are generated from current governance records and stored as auditable snapshots, not as legal certification.

## Media, Billing, Webhooks, Diagnostics

- `POST /media/upload`
- `POST /media/search`
- `GET /media/search/runs`
- `POST /media/search/results/{result_id}/approval`
- `POST /media/search/results/{result_id}/reference`
- `GET /media/{media_id}`
- `GET /media/whatsapp/{media_id}`
- `POST /media/messages/{message_id}/voice/analyze`
- `POST /media/messages/{message_id}/vision/analyze`

Web/Image Search Intelligence notes:

- Requires tenant auth and one of `owner`, `admin`, `supervisor`, or `agent`.
- Request body supports `query`, `search_type` (`web`, `image`, `mixed`), optional `provider_code` (`tavily`, `brave_search`, `serpapi`), optional `conversation_id`/`message_id`, and bounded `limit`.
- Requires access to `web_search_intelligence`, `image_search_intelligence`, `external_source_assist`, `ai_premium`, or demo mode according to the Intelligence gate.
- Provider credentials are tenant encrypted API credentials; there are no global provider keys in this phase.
- Results are persisted with source URL, image URL/thumbnail when present, snippet, provider rank/score, safety status and approval status.
- `POST /media/search/results/{result_id}/approval` accepts `approval_status` values `pending`, `approved`, or `rejected`; blocked/unsafe results cannot be approved.
- `POST /media/search/results/{result_id}/reference` accepts optional `conversation_id`, `note`, `include_source_url`, and `include_image_url`; it returns prepared text only for approved, non-blocked results and revalidates public URLs/conversation ownership.
- The media search endpoints do not auto-send results, crawl result pages, mutate CRM, launch campaigns, execute workflows, run agent tools or train models.
- Customer-facing delivery of an approved reference must use `POST /conversations/{conversation_id}/messages`, preserving quota, outbound, status and audit behavior.

Voice Intelligence notes:

- Requires tenant auth and one of `owner`, `admin`, `supervisor`, or `agent`.
- Query params: `force=false` to reuse cached completed analysis; `provider_code` optional and currently expected to resolve to Google/Gemini for real audio.
- Requires access to `voice_intelligence`, `voice_transcription`, `voice_sentiment_intent`, `ai_premium`, or demo mode according to the Intelligence gate.
- Input is the existing tenant audio message identified by `message_id`; the API does not accept arbitrary external audio URLs.
- Output includes `analysis.voice_intelligence` with transcript, summary, sentiment, intent, urgency, language, confidence, recommended action and analysis metadata.
- The backend persists the result in `saas_voice_intelligence_analyses` and mirrors compact fields into `saas_messages.payload_json.voice_intelligence`.
- The endpoint does not send customer messages or mutate CRM records.

Vision Intelligence notes:

- Requires tenant auth and one of `owner`, `admin`, `supervisor`, or `agent`.
- Query params: `force=false` to reuse cached completed analysis; `provider_code` optional.
- Requires access to `vision_intelligence`, `image_understanding`, `document_ocr`, `ai_premium`, or demo mode according to the Intelligence gate.
- Input is an existing tenant image/document/file message identified by `message_id`; the API does not accept arbitrary external URLs.
- Supported current runtime media: images, PDF, plain text, CSV and JSON. Documents use the Google/Gemini route in this phase.
- Output includes `analysis.vision_intelligence` with visual description, extracted text, summary, document type, sentiment, intent, urgency, language, confidence, entities, topics, product hints and recommended action.
- The backend persists the result in `saas_vision_intelligence_analyses` and mirrors compact fields into `saas_messages.payload_json.vision_intelligence`.
- The endpoint does not search the web, send images/documents to customers, mutate CRM records, execute tools or train models.

- `GET /billing/subscription`
- `GET /billing/overview`
- `GET /billing/entitlements`
- `GET /billing/limits`
- `GET /billing/usage`
- `GET /billing/plans`
- `GET /billing/checkout-sessions`
- `POST /billing/checkout`
- `GET /billing/invoices`
- `GET /billing/invoices/{invoice_id}/pdf`
- `GET /billing/credits`
- `POST /billing/webhooks/{provider}`
- `POST /billing/dev/change-plan`

Billing webhook notes:

- `provider` supports `stripe`, `mercadopago`, and `wompi`.
- Stripe requires `Stripe-Signature` and `STRIPE_WEBHOOK_SECRET` outside local mode.
- MercadoPago requires `x-signature`, `x-request-id`, and `MERCADOPAGO_WEBHOOK_SECRET` outside local mode.
- Wompi requires event checksum/signature data and `WOMPI_EVENTS_KEY` outside local mode.
- Provider webhooks are unauthenticated externally but must pass provider signature checks before billing state changes.
- `GET|POST /webhooks/endpoints`
- `POST /webhooks/endpoints/{endpoint_id}/rotate-token`
- `POST /webhooks/endpoints/{endpoint_id}/rotate-signature`
- `PATCH|DELETE /webhooks/endpoints/{endpoint_id}`
- `GET /webhooks/endpoints/{endpoint_id}/verify`
- `GET /webhooks/events`
- `POST /webhooks/events/process`
- `GET|POST /webhooks/instagram`
- `GET|POST /webhooks/{provider}/{endpoint_key}`
- `GET /diagnostics/overview`
- `POST /diagnostics/run`
- `POST /diagnostics/whatsapp/simulate-inbound`
