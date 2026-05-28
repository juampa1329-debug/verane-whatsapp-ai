# DATABASE

Scope: SaaS only. Schema source: `saas-version/migrations/*.sql`.

## Engine And Access

Code paths:

- `saas-version/backend/app_saas/db.py`
- `saas-version/backend/app_saas/tools/migrate.py`

Behavior:

- PostgreSQL database configured by `DATABASE_URL`.
- SQLAlchemy engine/session are used with Core/raw SQL.
- `db_session()` provides transaction/session lifecycle.
- `set_tenant_context(conn, tenant_id)` sets `app.current_tenant` for DB-level tenant context.
- Migration runner applies SQL files from `saas-version/migrations`.

## Migration Timeline

- `001_saas_core.sql`: tenants, users, memberships, integrations, webhook endpoints/events, billing base, usage, audit.
- `002_tenant_columns_non_breaking.sql`: tenant columns on shared/legacy-like tables.
- `003_conversations_cutover.sql`: conversation migration/cutover support.
- `004_rls_policies.sql`: row-level security policies.
- `005_saas_webhook_events.sql`: webhook event hardening.
- `006_saas_crm_core.sql`: SaaS CRM conversations/messages.
- `007_webhook_signature_hardening.sql`: webhook signatures.
- `008_outbound_messages.sql`: outbound queue.
- `009_saas_customers_labels.sql`: customers and labels.
- `010_saas_campaigns_core.sql`: campaign core.
- `011_saas_broadcasts.sql`: broadcasts.
- `012_saas_ads_social.sql`: ads/social.
- `013_saas_template_broadcast_manager.sql`: Meta templates/media assets.
- `014_saas_trigger_runtime.sql`: trigger runtime.
- `015_saas_broadcast_reporting.sql`: broadcast reporting.
- `016_saas_platform_admin.sql`: platform admin and flags.
- `017_saas_api_credentials.sql`: tenant API credentials.
- `018_saas_ai_agent.sql`: AI settings/memory.
- `019_saas_remarketing_runtime.sql`: remarketing.
- `020_saas_ai_pending_replies.sql`: pending AI replies.
- `021_whatsapp_subscription_checks.sql`: WhatsApp subscription checks.
- `022_instagram_business_integration.sql`: Instagram integration.
- `023_ai_gateway_core.sql`: AI gateway.
- `024_saas_advisor_phase1.sql` to `027_saas_advisor_phase5_observability.sql`: advisor.
- `028_saas_ai_agents_registry.sql` to `030_saas_ai_agent_memory_vault_limits.sql`: AI agents and limits.
- `031_saas_observability_dead_letter.sql`: dead-letter observability.
- `032_saas_inbox_crm_runtime.sql`: inbox CRM runtime/tasks/status events.
- `033_saas_billing_monetization.sql`: billing monetization.
- `034_saas_ai_agents_phase6_governance.sql`: AI governance.
- `035_saas_ai_agent_orchestrator_phase7.sql`: agent orchestrator.
- `036_saas_knowledge_rag_phase8.sql`: knowledge/RAG.
- `037_saas_campaigns_phase7_enterprise.sql`: campaign enterprise/preflight/versions.
- `038_saas_phase1_security_hardening.sql`: account lockout fields, 2FA-prep fields, password reset tokens, and security-event indexes.
- `039_saas_phase3_observability_hardening.sql`: worker heartbeats plus queue/dead-letter correlation IDs.
- `040_saas_crm_commercial_phase5.sql`: CRM custom fields, configurable pipelines/stages, timeline events, and merge audit.
- `041_saas_knowledge_rag_phase6_operational.sql`: sparse-vector chunk metadata and tenant-scoped RAG evaluation records.
- `042_saas_campaigns_phase7_operational.sql`: campaign quiet-hours settings and A/B execution events.
- `043_saas_ai_agents_phase8_operational.sql`: AI agent custom prompt/preflight/eval fields and conversation AI ownership.
- `044_saas_billing_phase9_operational.sql`: billing lifecycle notice timestamps, invoice PDF tracking, provider checkout event recency, and lifecycle indexes.
- `045_saas_verticalization_phase10.sql`: tenant industry state, vertical pack snapshot, and vertical pack application audit records.
- `046_saas_intelligence_engine_phase11.sql`: Intelligence Engine event store, feature values, predictions, recommendations, premium grants, model registry, and usage counters.
- `047_saas_intelligence_modelops_phase11.sql`: Intelligence prediction feedback, model metrics, and feedback-aware baseline registry metadata.
- `048_saas_intelligence_model_rollouts_phase11.sql`: Intelligence model rollout controls and auditable rollout events.
- `049_saas_ml_infrastructure_phase11.sql`: optional ML training jobs, model artifacts, inference run logs, and drift snapshots.
- `050_saas_ml_training_strategy_phase11.sql`: Intelligence event contracts/replay cursors, auto-labels, feature sets, feature pipeline runs, training datasets, model evaluations, and feature-value version metadata.
- `051_saas_multi_agent_operating_system_phase11.sql`: Agent OS inter-agent messages, runtime traces, tool-run traces, event subscriptions, and Agent OS premium feature flags.
- `052_saas_autonomous_operational_intelligence_phase11.sql`: Autonomous Operational Intelligence policies, playbooks, anomalies, actions, reports, and premium feature flags.
- `053_saas_ai_platform_ecosystem_phase11.sql`: AI Platform Ecosystem marketplace, plugins, tool registry, event subscriptions, developer apps, external integration metadata, tenant AI apps, traces/metrics, and ecosystem premium feature flags.
- `054_saas_enterprise_ai_network_phase11.sql`: Enterprise AI Network vertical industry models, anonymized benchmarks, tenant benchmark comparisons, vertical insights, AI playbooks, knowledge-network nodes, network metrics, and premium feature flags.
- `055_saas_performance_reliability_phase12.sql`: Performance/reliability SLO policies, backpressure policies, retention policies, cleanup runs, snapshots, drills, and high-volume queue/index audit support.
- `056_saas_phase13_security_compliance.sql`: email OTP MFA challenges and tenant privacy request records.
- `057_saas_ai_workflow_composer_phase18.sql`: Workflow Composer templates, workflows, versions, simulations, approvals, materializations, and premium feature flags.
- `058_saas_ai_trust_compliance_governance_phase22.sql`: AI Trust Center policies, attestations, risk assessments, model cards, incidents, reports, audits, and premium feature flags.
- `059_saas_realtime_intelligence_phase16.sql`: Real-Time Intelligence sessions, user cursors, metric snapshots, and premium feature flags.
- `060_saas_voice_intelligence_phase24.sql`: Voice Intelligence analysis cache and premium feature flags.
- `061_saas_vision_intelligence_phase24.sql`: Vision Intelligence/OCR-style analysis cache and premium feature flags.
- `062_saas_web_image_search_intelligence_phase24.sql`: Web/Image Search Intelligence run/result records and premium feature flags.
- `063_saas_agent_multimodal_tools_phase24.sql`: Agent multimodal tool premium flags and a filtered index on existing Agent OS tool-run traces.
- `064_saas_multimodal_memory_training_events_phase24.sql`: Multimodal memory/training/RAG event records plus premium feature flags.
- `065_saas_multimodal_admin_gating_phase24.sql`: Phase 24.8 plan-level AI feature limits and provider policy/cost controls.
- `066_saas_revenue_memory_network_phase19_20.sql`: Phase 19 revenue policies/opportunities/forecasts/experiments/reports plus Phase 20 enterprise memory graph policies/nodes/edges/sync runs/access logs and premium feature flags.
- `067_saas_multimodal_observability_rollout_phase24.sql`: Phase 24.9/24.10 multimodal observability snapshots, rollout policies/events and default-off observability/rollout feature flags.
- `068_saas_federated_learning_phase17.sql`: Phase 17 federated learning policies, rounds, tenant update packages, aggregate rows, global intelligence signals and default-off federated/global feature flags.
- `069_saas_auth_billing_schema_drift_repair.sql`: production drift repair for missing auth/MFA/security-event and billing runtime/lifecycle columns/tables.
- `070_saas_crm_intelligence_schema_drift_repair.sql`: production drift repair for missing CRM, integrations, campaign, verticalization and Intelligence runtime columns/tables used by registration, Inbox, dashboard and Advisor boot.
- Phase 24.7 added no migration; Inbox reference UX reuses Web/Image Search, multimodal memory and CRM outbound tables.

## Important Table Families

- Identity/tenant: `saas_tenants`, `saas_users`, `saas_memberships`, `saas_platform_admins`, tenant vertical columns on `saas_tenants`.
- Security/admin: `saas_security_events`, `saas_password_reset_tokens`, `saas_mfa_challenges`, `saas_privacy_requests`, auth lockout/2FA fields on `saas_users`, audit/event tables, feature flags.
- CRM: `saas_conversations`, `saas_messages`, customer/label/task/status runtime tables, custom-field definitions, pipeline stages, timeline, merge audit, AI owner assignment fields.
- Campaigns: campaign templates, segments, items, triggers, flows, preflight/version tables, global quiet-hours settings, A/B event telemetry.
- Broadcasts: broadcast definitions, recipients, report/status tables, Meta template records.
- Integrations/webhooks: `saas_integrations`, webhook endpoints/events, subscription check tables.
- Billing: plans, subscriptions, entitlements/limits, usage, invoices/PDF tracking, credits, checkout sessions, provider events, lifecycle notice timestamps.
- Verticalization: `saas_vertical_pack_applications`, tenant `industry_code`, `vertical_pack_version`, `vertical_pack_json`, and `vertical_pack_applied_at`.
- Intelligence: `saas_intelligence_events`, `saas_intelligence_event_contracts`, `saas_intelligence_event_replay_cursors`, `saas_intelligence_feature_values`, `saas_intelligence_predictions`, `saas_intelligence_prediction_feedback`, `saas_intelligence_model_metrics`, `saas_intelligence_model_rollout_events`, `saas_intelligence_recommendations`, `saas_intelligence_feature_grants`, `saas_intelligence_plan_feature_limits`, `saas_intelligence_model_registry`, `saas_intelligence_usage`, `saas_ml_training_jobs`, `saas_ml_model_artifacts`, `saas_ml_inference_runs`, `saas_ml_drift_snapshots`, `saas_ml_auto_labels`, `saas_ml_feature_sets`, `saas_ml_feature_pipeline_runs`, `saas_ml_training_datasets`, `saas_ml_model_evaluations`, `saas_ai_provider_policies`, `saas_ai_operation_policies`, `saas_ai_operation_playbooks`, `saas_ai_operation_anomalies`, `saas_ai_operation_actions`, `saas_ai_operation_reports`, `saas_ai_marketplace_items`, `saas_ai_marketplace_installations`, `saas_ai_plugins`, `saas_ai_tool_registry`, `saas_ai_ecosystem_event_subscriptions`, `saas_ai_developer_apps`, `saas_ai_external_integrations`, `saas_ai_apps`, `saas_ai_ecosystem_traces`, `saas_ai_ecosystem_metrics`, `saas_ai_vertical_industry_models`, `saas_ai_vertical_benchmarks`, `saas_ai_vertical_tenant_benchmarks`, `saas_ai_vertical_insights`, `saas_ai_vertical_playbooks`, `saas_ai_knowledge_network`, `saas_ai_network_metrics`, `saas_federated_learning_policies`, `saas_federated_learning_rounds`, `saas_federated_learning_updates`, `saas_federated_learning_aggregates`, `saas_global_intelligence_signals`, `saas_ai_revenue_policies`, `saas_ai_revenue_opportunities`, `saas_ai_revenue_forecasts`, `saas_ai_revenue_experiments`, `saas_ai_revenue_reports`, `saas_enterprise_memory_policies`, `saas_enterprise_memory_nodes`, `saas_enterprise_memory_edges`, `saas_enterprise_memory_sync_runs`, `saas_enterprise_memory_access_logs`, `saas_ai_workflow_templates`, `saas_ai_workflows`, `saas_ai_workflow_versions`, `saas_ai_workflow_simulations`, `saas_ai_workflow_approvals`, `saas_ai_workflow_materializations`, `saas_ai_governance_policies`, `saas_ai_governance_policy_attestations`, `saas_ai_risk_assessments`, `saas_ai_model_cards`, `saas_ai_governance_incidents`, `saas_ai_governance_reports`, `saas_ai_governance_audits`, `saas_realtime_intelligence_sessions`, `saas_realtime_intelligence_cursors`, `saas_realtime_intelligence_metrics`, `saas_voice_intelligence_analyses`, `saas_vision_intelligence_analyses`, `saas_web_search_intelligence_runs`, `saas_web_search_intelligence_results`, `saas_multimodal_memory_events`, `saas_multimodal_observability_snapshots`, `saas_multimodal_rollout_policies`, `saas_multimodal_rollout_events`, and Agent OS `saas_ai_agent_tool_runs` for multimodal tool traces.
- AI: API credentials, gateway providers/routes/runs, AI settings/memory, agent registry/events/preflight/evals, agent memory vault, collective memory, Agent OS messages/runtime traces/tool runs/event subscriptions, AI ecosystem marketplace/plugin/tool/developer/app metadata, knowledge sources/chunks/retrieval logs/evaluations.
- Observability/reliability: `saas_worker_heartbeats`, `saas_dead_letter_events`, queue correlation IDs, AI gateway runs, Meta subscription/token checks, `saas_reliability_slo_policies`, `saas_reliability_backpressure_policies`, `saas_reliability_retention_policies`, `saas_reliability_cleanup_runs`, `saas_reliability_snapshots`, and `saas_reliability_drills`.
- Compliance: `saas_mfa_challenges` stores hashed short-lived OTP login challenges; `saas_privacy_requests` stores tenant-reviewed export/delete request workflow state.

## Known Schema Cautions

- Some SaaS migrations/services create non-`saas_` table names such as `social_posts`, `social_comments`, and `comment_ai_settings`. If SaaS shares a DB/schema with another app, verify collisions before touching social features.
- Runtime code contains defensive `CREATE TABLE IF NOT EXISTS` in some services. Schema truth is therefore split between migrations and service code; inspect both before changing tables.
- RLS policies exist in migrations. Do not remove explicit tenant filters in application SQL just because RLS exists.
- Generated build/dependency folders exist under SaaS frontends; do not treat them as schema/source.

## Bootstrap Repair 2026-05-24

User requested historical migration normalization for clean Docker/PostgreSQL bootstrap.

Applied:

- `022_instagram_business_integration.sql`: UTF-8 BOM removed; all SQL files checked with strict UTF-8 decoding.
- `030_saas_ai_agent_memory_vault_limits.sql`: ambiguous `max_memory_archives` assignment qualified with `saas_ai_agent_plan_limits.max_memory_archives`.
- `036_saas_knowledge_rag_phase8.sql`: creates `saas_knowledge_sources` before ALTER; includes compatibility columns plus runtime knowledge fields.
- `002_tenant_columns_non_breaking.sql`: legacy root-table tenantization guarded with `to_regclass`.
- `003_conversations_cutover.sql`: legacy conversation/message cutover guarded with `to_regclass`.
- `038_saas_phase1_security_hardening.sql`: added as forward migration for reproducible Phase 1 security state on clean PostgreSQL.
- `039_saas_phase3_observability_hardening.sql`: added as forward migration for reproducible Phase 3 observability state on clean PostgreSQL.
- `041_saas_knowledge_rag_phase6_operational.sql`: added as forward migration for reproducible sparse-vector RAG and evaluation state on clean PostgreSQL.
- `042_saas_campaigns_phase7_operational.sql`: added as forward migration for reproducible Phase 7 quiet-hours/A-B state on clean PostgreSQL.
- `043_saas_ai_agents_phase8_operational.sql`: added as forward migration for reproducible Phase 8 custom-agent, preflight, eval, budget-guard, and conversation ownership state.
- `044_saas_billing_phase9_operational.sql`: added as forward migration for reproducible billing lifecycle notices, invoice PDF tracking, provider event recency, and lifecycle indexes.
- `045_saas_verticalization_phase10.sql`: added as forward migration for reproducible Phase 10 tenant industry state and vertical pack application audit.
- `046_saas_intelligence_engine_phase11.sql`: added as forward migration for reproducible Phase 11 predictive events/features/predictions/recommendations/grants/model registry/usage state.
- `047_saas_intelligence_modelops_phase11.sql`: added as forward migration for reproducible Phase 11 prediction feedback and model metrics state.
- `048_saas_intelligence_model_rollouts_phase11.sql`: added as forward migration for reproducible Phase 11 model registry rollout governance and rollout-event audit state.
- `049_saas_ml_infrastructure_phase11.sql`: added as forward migration for reproducible optional Phase 11 ML jobs/artifacts/inference/drift state.
- `050_saas_ml_training_strategy_phase11.sql`: added as forward migration for reproducible event contracts, auto-label training data, feature pipelines, ML datasets and offline model evaluations.
- `051_saas_multi_agent_operating_system_phase11.sql`: added as forward migration for reproducible Agent OS communication, observability, tool-run approval traces and event-driven subscriptions.
- `052_saas_autonomous_operational_intelligence_phase11.sql`: added as forward migration for reproducible Autonomous Operational Intelligence policies, playbooks, anomaly/action/report records and premium controls.
- `053_saas_ai_platform_ecosystem_phase11.sql`: added as forward migration for reproducible AI Marketplace, Plugin Center, Developer Console, Tool Registry, AI Apps and ecosystem observability records.
- `054_saas_enterprise_ai_network_phase11.sql`: added as forward migration for reproducible Enterprise AI Network industry models, benchmarks, tenant comparisons, insights, playbooks, knowledge network, metric snapshots and premium controls.
- `055_saas_performance_reliability_phase12.sql`: added as forward migration for reproducible SLO/backpressure/retention/snapshot/drill state and expected performance indexes.
- `056_saas_phase13_security_compliance.sql`: added as forward migration for reproducible MFA challenge storage and privacy request tracking.
- `057_saas_ai_workflow_composer_phase18.sql`: added as forward migration for reproducible Workflow Composer templates, workflows, versions, simulations, approvals, materializations and premium feature flags.
- `058_saas_ai_trust_compliance_governance_phase22.sql`: added as forward migration for reproducible AI Trust Center governance policies, attestations, risk assessments, model cards, incidents, reports, audits and premium feature flags.
- `059_saas_realtime_intelligence_phase16.sql`: added as forward migration for reproducible AI Real-Time Intelligence sessions, cursors, metrics and premium feature flags.
- `060_saas_voice_intelligence_phase24.sql`: added as forward migration for reproducible Voice Intelligence analyses and premium feature flags.
- `061_saas_vision_intelligence_phase24.sql`: added as forward migration for reproducible Vision Intelligence/OCR-style analyses and premium feature flags.
- `062_saas_web_image_search_intelligence_phase24.sql`: added as forward migration for reproducible Web/Image Search Intelligence run/result records and premium feature flags.
- `063_saas_agent_multimodal_tools_phase24.sql`: added as forward migration for reproducible Agent multimodal tool flags and filtered tool-run index.
- `064_saas_multimodal_memory_training_events_phase24.sql`: added as forward migration for reproducible sanitized multimodal memory, training-signal and RAG materialization state.
- `065_saas_multimodal_admin_gating_phase24.sql`: added as forward migration for reproducible Phase 24.8 plan feature limits and AI/search/TTS provider policy/cost controls.
- `066_saas_revenue_memory_network_phase19_20.sql`: added as forward migration for reproducible Phase 19 Autonomous Revenue Engine and Phase 20 AI Enterprise Memory Network state.
- `067_saas_multimodal_observability_rollout_phase24.sql`: added as forward migration for reproducible Phase 24.9 Observability and Phase 24.10 Safe Rollout state.
- `068_saas_federated_learning_phase17.sql`: added as forward migration for reproducible Phase 17 federated policies, rounds, aggregate updates, aggregate results, global signals and default-off federated/global feature flags.
- `069_saas_auth_billing_schema_drift_repair.sql`: added as forward repair migration for production databases where earlier auth/billing migrations were marked applied but columns or runtime billing tables were missing. It restores Phase 1 login/MFA/security-event columns/tables, tenant industry columns, Phase 5 billing runtime tables and Phase 9 billing lifecycle notice columns/indexes.
- `070_saas_crm_intelligence_schema_drift_repair.sql`: added as forward repair migration for production databases where earlier CRM/campaign/verticalization/Intelligence migrations were marked applied but app-boot and registration columns/tables were missing. It restores missing Inbox conversation fields, CRM labels/tasks/pipeline/custom-field/timeline tables, campaign template/segment/trigger/flow/quiet-hours tables, vertical pack audit state, integration list columns, and Intelligence predictions/recommendations.

Checks:

- `NO_SQL_BOM`
- `ALL_SQL_UTF8_STRICT`
- `NO_STATIC_ORDER_ISSUES`
- `COMPOSE_CONFIG_OK`
- Clean Docker/PostgreSQL bootstrap with project `codexsaasphase6`: migrations `001` through `041` applied, API health OK, worker started, admin frontend started, Swagger `/docs` returned 200.
- Phase 6 Knowledge/RAG smoke: tenant registration, TXT upload, chunk/vector indexing, search, quality evaluation, and health endpoint passed.
- Phase 7 local checks passed for backend compile, frontend/admin builds, Compose config, SQL BOM, and strict UTF-8. Later Phase 13 Docker rebuild covered migrations through `056`.
- Phase 11 optional ML clean Docker/PostgreSQL stack `codexsaasmltrain` applied migrations through `050`; API health, Swagger, OpenAPI, admin health, API worker, standalone worker, ML service, MLflow, Qdrant, auto-label generation, feature pipeline recompute, dataset build, autolabel training, inference, drift, Admin ML training/registry smoke, and shadow inference passed. The temporary stack and volumes were removed after validation.
- Phase 8 local checks passed for backend compile, frontend build, Compose config, SQL BOM, and strict UTF-8. Later Phase 13 Docker rebuild covered migrations through `056`.
- Phase 9 local checks passed for backend compile, frontend/admin builds, Compose config, SQL BOM, and diff whitespace. Later Phase 13 Docker rebuild covered migrations through `056`.
- Phase 10 local checks passed for backend compile, frontend/admin builds, Compose config, SQL BOM, and strict UTF-8. Later Phase 13 Docker rebuild covered migrations through `056`.
- Phase 11 ML checks passed with Docker Desktop available: Compose profile `ml`, migrations through `050`, MLflow, ML service, Qdrant, direct ML smoke, Admin ML smoke, auto-label/dataset/autolabel training smoke, and tenant shadow inference.
- Phase 11 Agent OS check passed on the active SaaS stack: Docker rebuild applied migration `051`, Agent OS tables exist, API health OK, Swagger `/docs` 200, API compileall inside container passed, frontend build passed, and worker/API remained running.
- Phase 11 Autonomous Operations check passed on the active SaaS stack: Docker rebuild applied migration `052`, operation policy/playbook/anomaly/action/report tables exist, OpenAPI includes operations endpoints, API health OK, Swagger `/docs` 200, API `py_compile` for touched modules passed, frontend build passed, and authenticated tenant demo/control smoke passed.
- Phase 11 AI Platform Ecosystem check passed on the active SaaS stack: Docker rebuild applied migration `053`, ecosystem tables exist, OpenAPI includes `/ecosystem/*`, API compileall passed, frontend build passed, API health OK, Swagger `/docs` 200, tenant demo gating smoke passed, premium-enabled marketplace install/plugin/tool/developer-app smoke passed, and browser smoke loaded `AI Ecosystem` with no console errors.
- Phase 11 Enterprise AI Network check passed on the active SaaS stack: Docker rebuild applied migration `054`, vertical network tables exist, OpenAPI includes `/intelligence/network/*`, API compileall passed inside the container, frontend/admin builds passed, API health OK, Swagger `/docs` 200, tenant demo center/preview smoke passed, full refresh was blocked without full access, premium-enabled full refresh persisted benchmark comparisons and insights, and client/admin browser smokes loaded with no console errors.
- Phase 12 Performance/Reliability check passed on the active SaaS stack: Docker rebuild applied migration `055`, reliability tables/indexes exist, API health OK, Swagger `/docs` 200, Admin reliability smoke and retention dry-run passed.
- Phase 13 Security/Compliance check passed on the active SaaS stack: Docker rebuild applied/skipped migration `056`, `saas_mfa_challenges` and `saas_privacy_requests` exist, tenant/admin MFA smokes passed, tenant compliance export passed, Admin Security Compliance passed, and temporary smoke users were cleaned.
- Phase 18 Workflow Composer check passed on the active SaaS stack: Docker rebuild applied migration `057`, clean temporary PostgreSQL migration bootstrap applied `001` through `057`, API health OK, Swagger `/docs` 200, worker started, and authenticated Composer smoke passed through template instantiation, preflight, simulation, approval and `composer_only` activation.
- Phase 22 checks passed: active Docker stack applied/skipped through migration `058`; clean isolated PostgreSQL bootstrap applied migrations `001` through `058` and confirmed the six core Trust AI tables.
- Phase 16 realtime checks passed: active Docker stack applied/skipped through migration `059`; clean isolated PostgreSQL bootstrap applied migrations `001` through `059` and confirmed the three realtime tables; tenant/Admin realtime smokes and OpenAPI endpoint checks passed.
- Phase 24.2 Voice Intelligence checks passed on the active SaaS stack: API/worker rebuild applied/skipped migration `060`, container backend compileall passed for touched domains, API health OK, Swagger `/docs` returned 200, OpenAPI includes the voice analysis endpoint, and PostgreSQL confirmed `saas_voice_intelligence_analyses` plus the new `voice_intelligence` plan flag.
- Phase 24.3 Vision Intelligence checks passed: backend `py_compile`, tenant/Admin builds, SQL UTF-8/BOM scans, Compose config, active Docker rebuild, active migration runner through `061`, DB table/feature-flag check, and clean isolated PostgreSQL bootstrap `001` through `061`.
- Phase 24.4 Web/Image Search Intelligence checks passed: backend `py_compile`, tenant/Admin builds, SQL UTF-8/BOM scans, Compose config, active Docker rebuild, active migration runner through `062`, API/Swagger/OpenAPI checks, DB table/feature-flag check, authenticated tenant safe-failure smoke without provider credential, and clean isolated PostgreSQL bootstrap `001` through `062`.
- Phase 24.5 Agent Multimodal Tools checks passed: backend `py_compile`, tenant build, Compose config, SQL UTF-8/BOM scans, active Docker rebuild, active migration runner through `063`, API/Swagger/OpenAPI checks, DB migration/feature-flag check, authenticated agent tool smoke with controlled search-provider failure, browser UI smoke, and clean isolated PostgreSQL bootstrap `001` through `063`.
- Phase 24.6 Multimodal Memory & Training Events checks passed: backend `py_compile`, tenant/Admin builds, Compose config, SQL UTF-8/BOM scans, active Docker rebuild, active migration runner through `064`, API/Swagger/OpenAPI checks, DB table/feature-flag check, authenticated memory sync/materialization smoke, browser UI smoke, and clean isolated PostgreSQL bootstrap `001` through `064`.

Runtime notes:

- The compose file requires an external Docker network named `coolify`; latest validation reused an existing local `coolify` network.
- Port `8010` was avoided for validation; latest Phase 6 validation used `SAAS_API_HOST_PORT=8060` and `SAAS_ADMIN_HOST_PORT=8061`.
- Do not run two temporary SaaS Compose projects on the same external `coolify` network at the same time unless service aliases are isolated; both projects expose the `scentra-saas-db` network alias.

## DB Change Checklist

1. Inspect all migrations for the target table/column.
2. Inspect backend references with `rg "<table_or_column>" saas-version/backend/app_saas`.
3. Inspect frontend response consumers when API output changes.
4. Add a forward migration; do not edit old migrations unless this is a local unreleased reset and user approves.
5. Update `docs/DATABASE.md`, `architecture/DB_FLOW.md`, `ai-memory/BUSINESS_LOGIC.md`, and `tasks/TASK_STATE.md`.
