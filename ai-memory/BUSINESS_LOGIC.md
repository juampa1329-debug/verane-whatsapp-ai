# BUSINESS_LOGIC

Scope: SaaS only. This file summarizes observed domain behavior from code structure and endpoint names; inspect implementation before changing logic.

## Tenant Lifecycle

- Tenant users register/login through `/auth`.
- Registration creates user/tenant/membership/trial subscription flow.
- Users can switch tenant through membership validation.
- Platform admins are separate from tenant users and use `/admin/auth/*`.
- Password recovery uses `/auth/password/forgot` and `/auth/password/reset` with hashed, expiring, single-use DB tokens.
- Password change uses `/auth/password/change` for authenticated users.
- Repeated failed tenant/admin logins increment `saas_users.failed_login_count` and can set `locked_until`.
- 2FA is managed through `/auth/security/2fa`; Phase 13 enforces email OTP challenge/verification during tenant/admin login when enabled or role-required.
- Tenant privacy exports and delete requests live under `/compliance`; delete requests are review records and do not hard-delete data automatically.
- Production first platform admin is created with `app_saas.tools.create_platform_admin` or Compose profile `platform-admin-seed`; HTTP bootstrap is local-only.
- Admin support impersonation creates a short-lived tenant token and must stay audited.

## Roles

Tenant role hierarchy is defined in `shared/security.py`:

- owner
- admin
- supervisor
- agent
- viewer

Platform roles include:

- superadmin
- platform_admin
- billing_admin
- support
- viewer

## CRM/Inboxes

- Conversations, customers, messages, labels, tasks, status events, scoring, read/takeover, custom fields, configurable pipeline stages, timeline, dedupe/merge, and outbound messages are handled in `crm/`.
- The client Inbox separates DMs from comments; DMs use `crm/` conversations/messages and comments use `social/` comment APIs.
- Inbox operations include server-side channel/queue filtering, unread/read state, assign-to-me/release assignment, SLA/hot lead filters, human takeover, message delivery status timeline, unified CRM timeline, dedupe merge, tasks, CRM side panel, attachments, voice notes, emojis, and product cards.
- Tenant CRM custom-field definitions live in `saas_crm_custom_fields`; values are stored on `saas_conversations.profile_json.custom_fields`.
- Pipeline configuration lives in `saas_crm_pipelines` and `saas_crm_pipeline_stages`; conversations still expose the active stage through `crm_stage`.
- Customer merge audits snapshots in `saas_crm_merge_events`, moves known conversation references, and records `crm_merged` timeline events.
- Ads/social comments/leads can be converted into inbox conversations; social comments also have direct reply/reaction/AI-suggestion paths.
- Outbound processing can be triggered by CRM/admin operations and workers.

## Campaigns And Broadcasts

- Campaigns include templates, segments, campaign items, triggers, and flows.
- Trigger/remarketing processing is handled by workers.
- Phase 7 trigger conditions cover words/comments/templates/tags/schedules plus CRM stage, payment status, customer type, and intent.
- Trigger and flow activation is gated by preflight; failed high-severity checks block activation.
- Global quiet hours live in `saas_campaign_quiet_hours`; trigger/flow-local quiet hours remain in JSON fields.
- A/B variants are selected deterministically per recipient and logged to `saas_campaign_ab_events` for trigger/flow reporting.
- `block_ai` prevents AI reply scheduling when a matched trigger successfully handles the message.
- Broadcasts manage Meta templates, recipients, enqueueing, reporting, retry, and CSV export.
- Broadcast enqueue and outbound dispatch both enforce approved Meta template status before sending template messages.

## Verticalization

- Tenants have an `industry_code` plus vertical pack snapshot fields on `saas_tenants`.
- Public vertical pack summaries are used during registration so a tenant can start with an industry baseline.
- Applying a vertical pack is tenant scoped and idempotent; it updates the default CRM pipeline, custom fields, labels, CRM message templates, saved segments, trigger drafts, remarketing flow drafts, quiet-hours defaults, and optional recommended factory agents.
- Current vertical pack codes include general, retail, ecommerce, restaurant, hotel, health, education, real estate, support, automotive, financial services, legal, insurance, beauty, and services.
- Trigger resources created by vertical packs remain inactive and flow resources remain draft so operators must review/preflight/activate them before customer-facing automation.
- Recommended agents are not created automatically during registration, tenant creation, or admin industry changes. Client-side pack application can explicitly request agent creation and must respect plan limits.
- Admin tenant industry changes apply the same backend pack without tenant-session assumptions.

## Integrations

- Tenant integrations are stored under SaaS integration records.
- WhatsApp/Meta token health and refresh endpoints exist.
- Instagram OAuth/connect/diagnostics endpoints exist separately under `/integrations/instagram`.
- WooCommerce appears as a configured integration/provider in SaaS UI/API context.

## Billing

- Billing exposes subscription, overview, entitlements, limits, usage, plans, checkout sessions, invoices, credits, provider webhooks, and dev plan change.
- Trial config comes from `SAAS_TRIAL_DAYS` and `SAAS_TRIAL_PLAN_CODE`.
- Billing changes can affect feature availability and workers/AI limits.
- Platform admin can update tenant status/plan/subscription, manual credits/invoices, and plan feature flags; these changes must keep tenant status and billing state aligned.
- Stripe, MercadoPago, and Wompi webhooks must pass provider signature checks before subscription/payment state changes.
- Billing lifecycle runs from admin sync plus embedded/standalone workers; it expires trials/subscriptions, applies past-due grace, suspends overdue tenants, creates open invoices, ages uncollectible invoices, and sends one-time notices.
- Non-operational tenant statuses block unsafe tenant writes globally, while billing/auth/admin/health routes remain reachable for recovery.
- Tenant/admin invoice PDFs are generated by backend endpoints and downloaded through authenticated frontend calls.

## AI And Knowledge

- API credentials store tenant provider credentials.
- AI gateway exposes providers, routes, and runs.
- AI Gateway is the shared resilience layer for conversation AI, assigned/custom agents and Advisor. Retryable provider/model failures such as `429`, `503`, unavailable, high demand, timeout or empty output now try allowed model candidates in the same provider before moving to the next provider in the configured chain.
- Model failover is policy-aware: each candidate model is checked through Admin provider policies before the external call, and missing credentials or disabled/quota-blocked providers are recorded rather than bypassed.
- If every model/provider attempt for a pending conversation reply fails due to retryable provider errors, `ai_agent/service.py` maps it to `ai_generation_error` so the existing `saas_ai_pending_replies` worker retry path can process it again later.
- Conversation AI keeps continuity through CRM context, conversation memory summary, facts, Knowledge/RAG, collective memory, approved multimodal context and a bounded recent-message transcript.
- Humanized reply mode is enabled by default for conversation AI: output tokens are capped for short WhatsApp-style replies, recent raw transcript is compacted, responses are naturally chunked into delayed outbound fragments, and Meta typing indicator is attempted best-effort before generation.
- Fragmented AI replies preserve the existing outbound queue, quota checks, status tracking and worker dispatch path; each fragment counts as one outbound message.
- Conversation AI still uses one AI Gateway call with full context before splitting the answer. Splitting is a delivery/UX step, not multiple independent model calls, so the AI does not lose conversation memory between fragments.
- Triggers, Meta templates, approved-template enforcement and `block_ai` are backend/runtime automation behavior. The LLM can recommend or write text, but it does not autonomously choose/send Meta templates unless backend trigger/campaign/outbound logic queues them.
- Trigger, broadcast and legacy outbound jobs must be visible in the Inbox when they are sent. Dispatch creates a local `saas_messages` row for any queued outbound that reaches sending without `message_id`, then links the outbound row before provider delivery.
- AI-written CRM internal notes are compacted before persistence: repeated `IA:` note units are deduplicated, non-AI human notes are preserved, and manual CRM saves also compact duplicated AI note lines.
- Phase 24.1 extends the internal AI Gateway request shape with optional attachments for future multimodal calls; existing text-only callers remain compatible.
- Phase 24.2 lets authorized tenant users analyze existing Inbox audio messages. The backend loads tenant-owned audio, runs premium/demo gating, calls Google/Gemini through the AI Gateway, stores transcript/summary/sentiment/intent output, and mirrors compact results to message payloads.
- Phase 24.3 lets authorized tenant users analyze existing Inbox images/documents/files. The backend loads tenant-owned media, runs premium/demo gating, calls the AI Gateway with image/document attachments, stores visual description/OCR-style extracted text/summary/sentiment/intent output, and mirrors compact results to message payloads.
- Phase 24.4 lets authorized tenant users run external web/image search from the Inbox CRM side panel with source URLs, snippets, optional images/thumbnails and approval status.
- Web/Image Search Intelligence loads encrypted tenant credentials for Tavily, Brave Search API or SerpAPI, validates conversation/message ownership when provided, screens result URLs for public HTTP(S) safety and stores runs/results in tenant-scoped tables.
- Search results start as `pending`; humans can approve or reject them. Blocked/unsafe results cannot be approved.
- Phase 24.5 lets authorized tenant users execute agent-scoped multimodal tools for a selected agent: audio analysis, image/document analysis and web/image search.
- Agent multimodal tools require the selected agent to declare the requested tool in `tools_json`, pass premium/demo feature gates and reuse the existing media/search endpoints rather than adding a separate media runtime.
- Agent tool runs are stored in `saas_ai_agent_tool_runs`; web/image search tool output remains pending until each result is approved through the existing media approval endpoint.
- Assigned conversation agents can receive compact multimodal context in their prompt. Web/image search sources are included only when the source result is approved and not blocked.
- Phase 24.6 captures useful voice, vision, approved-source and agent-tool outputs as sanitized `saas_multimodal_memory_events` for agent memory, RAG review and ML feature signals.
- Training readiness is separate from memory capture. Events are marked training-ready only when `multimodal_training_events`, `ml_predictions`, or `ai_premium` is enabled.
- Operators can materialize a multimodal memory event into Knowledge/RAG and/or collective agent memory; customer content requires explicit approval.
- Phase 24.7 lets authorized Inbox operators prepare approved external references and use/send them from the selected conversation.
- Approved-reference preparation is handled by `/media/search/results/{result_id}/reference`; actual customer delivery must use `/conversations/{conversation_id}/messages` so quota, outbound, status and audit behavior are preserved.
- Blocked or unapproved external sources cannot be prepared, and agents/workers do not auto-send references.
- Phase 24.8 lets platform admins control Phase 24 feature modes/quotas by tenant and by plan, plus AI/search/TTS provider policies by global/plan/tenant scope.
- Provider policies can disable providers/models and enforce monthly request or cost limits before AI Gateway and Web/Image Search provider calls. If no explicit policy exists, the compatibility default allows current providers.
- Provider cost estimates are calculated from Admin-entered pricing metadata, AI token logs and search run counts; they are operational estimates, not legal invoices.
- Phase 24.9 lets authorized tenants view multimodal observability for voice, vision, web/image search, agent tools and multimodal memory: request count, estimated cost, latency, errors, quality/confidence and sources used.
- Phase 24.9 snapshots are optional persisted aggregate rows; they store safe metrics/metadata only and reuse Admin provider pricing for cost estimates.
- Phase 24.10 lets authorized tenants configure safe rollout policies by feature/modality/provider with `off`, `demo`, `canary` or `full` mode.
- Phase 24.10 enforcement is opt-in. Without rollout feature access and an enabled explicit tenant policy, voice/vision/search runtime keeps compatibility behavior.
- Canary decisions are deterministic per tenant/user/subject; non-selected users can fall back to demo when the policy allows it.
- Voice/Vision/Web Search/Agent Multimodal/Multimodal Memory Intelligence is decision support only. It does not send replies/media by itself, mutate CRM, create tickets/tasks, launch campaigns, execute workflows, train models automatically or assign agents.
- Gateway run logs store safe attachment metadata only and must not store raw base64, media bytes or decrypted provider credentials.
- Kimi is an official AI Gateway provider in the SaaS codebase and is used for deep reasoning/long-context Advisor paths.
- Intelligence Engine handles events, feature values, predictions, recommendations, AI premium grants and usage under `/intelligence`.
- Intelligence worker derives canonical events from existing SaaS tables, recomputes tenant feature snapshots, and generates gated baseline predictions with cooldown.
- Inline Intelligence capture now records selected high-value events during CRM outbound message creation and billing subscription changes; failures are isolated with nested transactions and do not abort the business write.
- Tenant `Inteligencia` UI is an operational surface over existing `/intelligence` APIs; it does not bypass backend grants, role checks, quotas or model rollout controls.
- Intelligence ModelOps stores tenant prediction feedback and model metrics; feedback emits `ai.prediction.feedback_recorded` and refreshes model metrics.
- Intelligence model registry controls registration, status, stage, shadow/canary/production rollout, traffic percent, promotion status, and production-readiness thresholds from Admin.
- Disabled/paused predictive models are blocked at prediction time; deterministic canary routing can select active approved canary registry rows by traffic percent, while shadow/unapproved canary predictions are persisted as `shadow` and do not create recommendations automatically.
- Current Phase 11 scoring uses `baseline_rules` by default. When `SAAS_ML_ENABLED=true` and a selected artifact is ready, prediction runtime can call the optional ML service; when `SAAS_ML_SHADOW_INFERENCE_ENABLED=true`, trained output is captured under `ml_inference` without changing the baseline business result.
- Optional ML infrastructure logs training jobs, model artifacts, inference runs and drift snapshots under `saas_ml_*` tables. Synthetic/autolabel training is bootstrap-only until real labels validate production quality.
- Phase 11 training data now includes event contracts, replay cursors, auto-labels, feature sets, feature pipeline runs, training datasets and model evaluations through migration `050`.
- Auto-labeling derives labels from existing SaaS state/events: conversions from CRM/payment states, churn risk from inactivity/negative engagement windows, remarketing outcomes from campaign/broadcast response/failure signals, and operational anomalies from recent failure rates.
- Training feature pipelines compute subject-level feature rows for lead scoring, churn prediction and smart remarketing, plus tenant-level operational features. Rows include feature set key, version and quality metadata.
- Autolabel training materializes CSV/manifest datasets from Postgres feature-store rows and labels, then trains in the optional ML service with LightGBM, XGBoost or sklearn fallback. MLflow/BentoML artifacts and offline evaluations are recorded when available.
- `SAAS_ML_AUTO_TRAIN_ENABLED` is off by default. When enabled, the Intelligence worker can prepare labels/features for training, but model promotion still requires registry/rollout review.
- Predictive features are gated by tenant status, plan flags, tenant feature overrides, intelligence grants, demo/full mode and monthly quotas.
- Product-facing Predictive Intelligence is exposed through `/intelligence/overview`, CRM `predictive_intelligence`, Dashboard predictive strip, Inbox badges/filter, CRM predictive cards, and Advisor `/briefing`.
- Conversation-level prediction buttons in CRM call `/intelligence/predict` with `subject_type = conversation`; latest conversation predictions are read from `saas_intelligence_predictions` and otherwise fall back to CRM baseline signals.
- Advisor `/briefing` merges predictive overview, seeded insights, recommendations, actions, activity, metrics and memory. It is proactive, but actions still require approval before execution.
- Persisted predictive recommendations have their own gate: prediction preview/access does not imply recommendation persistence. `predictive_recommendations` must be enabled and within quota before `saas_intelligence_recommendations` is written.
- Demo mode can show limited previews; full predictive features require premium enablement.
- Baseline Phase 11 predictions are registered as safe baseline models; trained artifacts must pass shadow/canary/production gates before use.
- Current accuracy/drift metrics and synthetic ML smokes are governance signals, not proof of production model quality.
- Advisor context and briefing include recent Intelligence Engine predictions and open recommendations but still propose actions through existing approval patterns.
- Phase 13 email OTP challenges are stored hashed/expiring in `saas_mfa_challenges`; JWTs issued after verification include MFA context for refresh enforcement.
- AI agent settings/memory/process/test live under `/ai`.
- Advisor handles chat, memory, metrics, insights, recommendations, and executable/dismissible actions.
- Agents domain handles templates, catalog, custom agents, fillable system prompts, memories, governance, collective memory, prompt versions, preflight/evals, budgets, action drafts, runtime, orchestrator events, and lifecycle.
- Agent OS adds a tenant-scoped control-plane over existing agents: inter-agent messages, event subscriptions, tool-run traces, runtime traces, core-agent coverage and Intelligence-to-orchestrator sync.
- Agent OS event sync consumes recent Intelligence predictions/recommendations and can enqueue orchestration jobs only when premium full mode is enabled. Demo mode returns candidates without writing jobs.
- Agent OS tool runs are approval-first: requests are recorded and create Advisor action drafts by default; direct execution of side-effect tools is intentionally not performed from this layer.
- Autonomous Operational Intelligence adds a tenant-scoped operations control-plane over events/features/queues/worker heartbeats/Meta checks/CRM/campaign signals.
- Operation policies store autonomy level, sensitivity, daily action limits, approval level, auto-remediation and low-risk auto-execute settings in `saas_ai_operation_policies`.
- Operation playbooks define supervised remediation/optimization templates for webhook retries, outbound queue triage, Meta subscription review, token health, trigger/campaign optimization, churn recovery, lead prioritization and queue degradation triage.
- Operation analysis writes anomalies, supervised actions and reports to `saas_ai_operation_anomalies`, `saas_ai_operation_actions` and `saas_ai_operation_reports`.
- Demo mode can run previews and analysis but forces `auto_remediation_enabled=false` and `low_risk_auto_execute=false`.
- Current autonomous action execution records controlled/auditable results and does not directly mutate Meta, queues, campaigns, CRM or billing.
- Level 4 can only auto-mark low-risk/report-only records executed when full mode and tenant policy explicitly allow it.
- Intelligence worker runs autonomous analysis in a nested transaction so failures do not break existing Intelligence, Meta, CRM, trigger, webhook or Agent OS processing.
- AI Platform Ecosystem adds a tenant-scoped control-plane under `/ecosystem` for marketplace items/installations, plugins, tool registry, event subscriptions, developer apps, external integration metadata and AI app manifests.
- Ecosystem feature gates are `ai_marketplace`, `ai_plugin_center`, `ai_developer_console`, `ai_tool_registry`, `ai_app_framework`, plus umbrella `ai_premium`.
- Demo mode can preview ecosystem state, but install/create/update operations require full feature mode.
- Plugin, tool, external integration and AI app records are metadata/control-plane manifests. API/worker do not execute untrusted plugin code from these records.
- Developer app keys are stored as hashes with one-time raw display; do not use them as public API auth until a dedicated gateway/auth design exists.
- Marketplace agent-template installs can optionally create agents through the existing agent-template service, preserving agent limits/preflight lifecycle.
- Enterprise AI Network adds a tenant-facing vertical intelligence layer under `/intelligence/network/*` for industry benchmarks, tenant-vs-industry comparisons, vertical insights, vertical advisor cards, playbooks, industry model metadata and aggregate knowledge-network nodes.
- Enterprise AI Network feature gates are `enterprise_ai_network`, `vertical_ai_intelligence`, `industry_ai_models`, `benchmark_intelligence`, `cross_tenant_intelligence`, `vertical_ai_advisors`, `ai_playbook_library`, plus umbrella `ai_premium`.
- Full Enterprise AI Network refresh/persistence requires full access through `enterprise_ai_network`, `cross_tenant_intelligence`, or `ai_premium`; demo access can preview center/playbook data without persisting tenant benchmark state.
- Cross-tenant intelligence is privacy-safe and aggregate-only: no raw messages, conversations, tenant names, private content or sensitive data are shared across tenants.
- Industry benchmark aggregates require minimum sample count 3 before being treated as usable cohort data.
- Vertical playbooks are recommendation templates only. They do not auto-activate triggers, flows, campaigns, workflows or provider-side changes.
- Intelligence worker refreshes Enterprise AI Network in a nested transaction and skips tenants without full access so network processing does not fail the rest of the pipeline.
- Federated Learning adds a tenant opt-in control-plane under `/intelligence/federated/*` for aggregate update packages, federated rounds, weighted aggregate results and global signals.
- Federated Learning feature gates are `federated_learning`, `federated_model_updates`, `privacy_safe_model_aggregation`, `global_intelligence`, `federated_benchmarking`, plus umbrella `ai_premium`.
- Federated local packages are built from tenant-owned aggregate metrics and feature summaries. They include counts/rates/quality/hash/privacy metadata only, not raw messages, conversations, media, prompts, provider secrets, tenant names or private customer content.
- Persisted federated update submission and aggregation require full feature access and tenant opt-in. Demo/read access can show safe previews.
- Worker auto-participation only runs when full feature access, `opt_in_enabled=true` and `auto_participation_enabled=true`.
- Federated aggregates write candidate/global signals after cohort thresholds. They do not promote production ML models automatically and do not mutate CRM/campaign/workflow/billing/Meta/agent runtime.
- Autonomous Revenue Engine adds a tenant-scoped revenue intelligence layer under `/intelligence/revenue/*`.
- Revenue feature gates are `autonomous_revenue_engine`, `revenue_opportunity_detection`, `revenue_forecasting`, `revenue_playbooks`, `revenue_experiments`, plus umbrella `ai_premium`.
- Revenue analysis detects opportunities from real CRM/conversation/prediction signals such as hot lead score, pending payment, proposal/quote stages and inactive warm leads.
- Revenue full mode persists opportunities, forecasts and reports; approve/execute/dismiss actions only change revenue control-plane records.
- Revenue policy can restrict approve/execute to selected playbook action types and cap monthly control-plane executions.
- Revenue execution does not send messages, mutate CRM, launch campaigns, execute workflows, call payment providers, charge customers or change Meta runtime.
- Enterprise Memory Network adds a tenant-scoped graph under `/intelligence/memory-network/*`.
- Memory feature gates are `enterprise_memory_network`, `memory_graph`, `memory_governance`, `cross_agent_memory_routing`, `memory_quality_scoring`, plus umbrella `ai_premium`.
- Memory sync captures bounded summaries from collective memory, Knowledge/RAG, multimodal memory events and vertical insights into reviewable graph nodes/edges.
- Memory nodes can be candidate, published, rejected or archived. Cross-agent routing is tenant-internal only and should consume published nodes after review.
- Memory policy enforces privacy mode, retention days, allowed memory scopes and customer-content review. Policy updates archive active nodes outside allowed scopes and demote published customer-content nodes when review is required.
- Memory export returns tenant-scoped policy/nodes/edges/safety metadata; import accepts bounded JSON, sanitizes fields and stores rows as `candidate`; node delete removes the tenant node and cascaded graph edges with access/event audit.
- Enterprise Memory Network does not share raw content across tenants, store raw media/base64, or auto-publish customer content into prompts without review.
- Workflow Composer lets tenants design AI workflows from safe templates or custom graphs, run preflight, simulate without side effects, request/review approval, restore versions and activate a `composer_only` workflow.
- Workflow Composer feature gates are `workflow_composer_templates` for template/demo surfaces and `ai_workflow_composer` for write/control operations.
- Composer activation is not runtime deployment. It does not send messages, mutate CRM, activate triggers/flows/campaigns or hand off agents until a future explicit materialization path is approved.
- Trust AI lets tenants and platform admins manage AI governance records: policies, attestations, risk assessments, model cards, incidents, compliance report snapshots and governance audits.
- Trust AI feature gates are `ai_trust_center`, `ai_governance_policies`, `ai_risk_assessments`, `ai_model_cards`, `ai_compliance_reports`, and `ai_audit_exports`.
- Trust AI risk scans read metadata from agents, Workflow Composer, model registry, tool registry, plugins and Autonomous Operations actions when available, but they do not execute repairs, promote models, activate workflows, pause agents or mutate runtime systems.
- Trust AI reports are operational evidence snapshots, not legal certification.
- Real-Time Intelligence adds a tenant/Admin live control-plane over existing Intelligence, Autonomous Ops and Trust AI signals.
- Real-Time Intelligence feature gates are `realtime_intelligence_layer`, `realtime_event_stream`, `realtime_ai_alerts`, and `realtime_intelligence_dashboard`.
- Tenant realtime APIs expose sanitized event feeds, live metrics, advisory alerts, sessions and user cursors under `/intelligence/realtime/*`.
- Admin realtime APIs expose per-tenant live activity and metric snapshot refresh under `/admin/intelligence/realtime*`.
- Phase 16 defaults to polling with bounded SSE available for future clients; it does not add Kafka, NATS, Redis Streams, WebSockets or new dependencies.
- Realtime alerts are advisory only and do not execute CRM, campaign, Meta, billing, workflow, agent, Trust or model-rollout side effects.
- Agent activation requires preflight readiness; runtime AI budget hard stop is enforced before provider execution.
- Conversations can have one AI owner through `assigned_ai_agent_id`/`ai_owner_mode`. Manual Inbox assignment and orchestrator/auto-router assignment move the conversation from general AI to the selected reply-capable agent.
- If an assigned agent is inactive or unavailable, conversation AI skips rather than silently falling back to general AI; operators must release or reassign the conversation.
- If an assigned runtime agent is active but is not customer-facing because it lacks the `conversation.reply` tool (for example `Advisor Agent`), the conversation AI runtime records an agent event, releases that invalid chat owner, and continues with general conversation AI on the next cycle.
- Agent-specific memory is preserved by default when an agent is archived/deleted; the memory vault can restore, export, import, or delete memories later.
- Collective memory exists at tenant level and is injected into assigned-agent conversation prompts so agents do not operate only from isolated memories.
- Knowledge domain handles PDF/TXT/CSV source upload, safe URL ingestion, sparse-vector plus lexical search, citations, health, reindex, deletion, retrieval logs, and quality evaluations.
- Conversation AI retrieves tenant-scoped Knowledge/RAG context through `knowledge_context_for_query` and receives internal citations in the prompt.

## Operational Logic

- Webhook events, trigger messages, remarketing flows, AI replies, agent orchestration, outbound messages, Intelligence processing, reliability snapshots/dry-runs, billing lifecycle, and Meta token refresh are processed asynchronously.
- Worker and browser polling must be tuned together. Active Inbox polling is intentionally lightweight and skips optional heavy reads on normal ticks; DB pool settings are configurable to avoid API-wide connection starvation.
- WooCommerce product messages are stored/rendered as `product` in Scentra. For WhatsApp delivery, a product with public `image_url` is queued as an image-link media message with the formatted product caption; without a usable image URL it remains caption/text only. If Meta rejects the remote product image, dispatch falls back to text caption delivery rather than losing the reply.
- Admin endpoints expose queue processing and dead-letter/observability controls.
- Phase 3 admin health combines API/DB, worker heartbeats, Meta status, AI Gateway status, queue snapshots, channel diagnostics, Meta error history, and dead-letter candidates.
- Dead-letter retry can requeue outbound, webhook, trigger, AI pending, remarketing, and agent orchestration sources.
- Correlation IDs are propagated through request middleware and stored on key queue/dead-letter records for diagnostics.
- Phase 12 reliability is an admin-only control-plane over existing observability. It records SLO/backpressure snapshots, audits expected indexes, runs backup-readiness metadata drills, and can execute allowlisted retention dry-runs.
- Reliability backpressure recommendations are advisory only. This domain does not throttle providers, pause campaigns, mutate queues or repair Meta subscriptions automatically.
- Retention cleanup is disabled and dry-run by default. Destructive cleanup requires explicit admin request, platform-admin/superadmin role and backend allowlisted SQL.
