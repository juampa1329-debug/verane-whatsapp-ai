# FILE_MAP

Scope: SaaS only.

## Root SaaS

- `saas-version/README.md`: SaaS workspace notes.
- `saas-version/*/AGENTS.md` and `saas-version/backend/app_saas/**/AGENTS.md`: hierarchical Codex CLI domain rules.
- `saas-version/docker-compose.saas.yml`: SaaS db/api/worker compose; API runs migrate + schema_check before Uvicorn and healthchecks `/saas/v1/ready`.
- `saas-version/admin-frontend/Dockerfile`: production admin frontend image for `admin.scentra-ai.online`.
- `saas-version/infra/`: deployment notes.
- `saas-version/docs/`: product/phase docs already present inside SaaS workspace.
- `saas-version/keys/`: key material; handle as sensitive.

## Backend

- `saas-version/backend/Dockerfile`: API/worker image.
- `saas-version/backend/Dockerfile.ml`: optional ML service image for Compose profile `ml`.
- `saas-version/backend/requirements.txt`: Python deps.
- `saas-version/backend/requirements-ml.txt`: optional ML deps; includes base requirements plus MLflow, BentoML, XGBoost, LightGBM, sklearn stack and metrics client.
- `saas-version/backend/app_saas/main.py`: FastAPI app and router mounting.
- `saas-version/backend/app_saas/config.py`: settings/env parsing.
- `saas-version/backend/app_saas/db.py`: engine/session/tenant context.
- `saas-version/backend/app_saas/shared/`: auth, secrets, captcha, request/security events, schema readiness.
- `saas-version/backend/app_saas/shared/email.py`: stdlib SMTP helper for password recovery emails.
- `saas-version/backend/app_saas/shared/mfa.py`: Phase 13 email OTP challenge creation, verification and security notices.
- `saas-version/backend/app_saas/shared/schema_readiness.py`: critical SaaS migration/table/column readiness contract for startup and `/ready`.
- `saas-version/backend/app_saas/tools/`: migrations/admin tools.
- `saas-version/backend/app_saas/tools/create_platform_admin.py`: first platform admin seed tool.
- `saas-version/backend/app_saas/tools/schema_check.py`: deploy/startup CLI that exits non-zero when schema readiness fails.
- `saas-version/backend/app_saas/workers/`: async processors.
- `saas-version/backend/app_saas/workers/billing.py`: recurring billing lifecycle processor with advisory lock/interval throttle.
- `saas-version/backend/app_saas/workers/intelligence.py`: Phase 11 derived event pipeline, feature recompute, gated baseline prediction, model-metric worker, Agent OS sync, Autonomous Operations analysis and Enterprise AI Network refresh.
- `saas-version/backend/app_saas/workers/reliability.py`: Phase 12 reliability worker wrapper for SLO snapshots and enabled retention dry-runs.
- `saas-version/backend/app_saas/observability/service.py`: admin health, channel diagnostics, worker heartbeat, Meta/AI Gateway status, dead-letter sync/retry helpers.
- `saas-version/backend/app_saas/reliability/`: Phase 12 Performance/Reliability control-plane for SLOs, backpressure, index audit, retention dry-runs, backup readiness, snapshots and drills.
- `saas-version/backend/app_saas/verticals/`: Phase 10 industry pack catalog/service/router for tenant verticalization, including enterprise pack codes used by vertical intelligence.
- `saas-version/backend/app_saas/intelligence/`: Phase 11 Intelligence Engine events, safe inline capture, features, predictions, feedback, model metrics, model rollout governance, recommendations, grants, Autonomous Operational Intelligence, Enterprise AI Network, Phase 16 Real-Time Intelligence, Phase 24 premium provider controls, multimodal observability, safe rollout and tenant APIs.
- `saas-version/backend/app_saas/intelligence/premium.py`: Phase 24.8 plan feature limits, provider policies, provider availability/quota/cost enforcement, credential summaries and cost estimates.
- `saas-version/backend/app_saas/intelligence/operations.py`: Autonomous Operational Intelligence policies, playbooks, anomaly detection, supervised actions, reports and premium/demo access checks.
- `saas-version/backend/app_saas/intelligence/network.py`: Enterprise AI Network service for privacy-safe vertical benchmarks, tenant benchmark comparisons, vertical insights, playbooks, advisors, industry model metadata and aggregate knowledge-network nodes.
- `saas-version/backend/app_saas/intelligence/revenue.py`: Phase 19 Autonomous Revenue Engine service for supervised revenue opportunities, forecasts, reports, playbooks, full-mode gating, policy enforcement and control-plane opportunity actions.
- `saas-version/backend/app_saas/intelligence/memory_network.py`: Phase 20 AI Enterprise Memory Network service for tenant-scoped memory graph sync, policy enforcement, export/import/delete, node review, graph edges, sync runs and privacy-safe memory routing.
- `saas-version/backend/app_saas/intelligence/realtime.py`: Phase 16 PostgreSQL-first live Intelligence snapshots, sanitized event feed, session/cursor state, advisory alerts, Admin realtime overview and metric snapshots.
- `saas-version/backend/app_saas/ecosystem/`: Phase 11 AI Platform Ecosystem control-plane for marketplace, plugins, tools, event subscriptions, developer apps, external integration metadata and tenant AI apps.
- `saas-version/backend/app_saas/trust_center/`: Phase 22 AI Trust Center control-plane for policies, risk assessments, model cards, incidents, reports, audits and admin trust overview.
- `saas-version/backend/app_saas/compliance/`: Phase 13 tenant-scoped account/customer exports and privacy delete-request workflow.
- `saas-version/backend/app_saas/ml_service/`: optional Phase 11 ML service for synthetic training, Postgres auto-label dataset building, autolabel training, trained inference, drift evaluation, MLflow/BentoML integration and Prometheus metrics.
- `saas-version/backend/app_saas/ml_service/datasets.py`: builds ML datasets from `saas_ml_auto_labels` plus `saas_intelligence_feature_values`.

## Backend Domains

- `admin/`: platform operations.
- `auth/`: tenant auth and email OTP MFA.
- `tenants/`: tenant CRUD.
- `crm/`: inbox/customer/conversation/task/label/custom-fields/pipeline/timeline/dedupe.
- `campaigns/`: campaign engine.
- `broadcasts/`: broadcast/template/report.
- `ads/`: ads/leads/comments.
- `social/`: social comment automation.
- `integrations/`: WhatsApp/Meta/WooCommerce/Instagram.
- `webhooks/`: endpoint/event ingestion.
- `billing/`: plans/subscriptions/usage/invoices/credits/checkout/provider webhooks/lifecycle/PDF.
- `verticals/`: industry onboarding packs, tenant vertical state, pack application audit, plus extended codes for retail, ecommerce, support, automotive and financial services.
- `intelligence/`: event store, feature store, predictive baselines, recommendation engine, premium AI gating, usage, Autonomous Operations, Enterprise AI Network, Phase 17 Federated Learning/Global Intelligence, multimodal observability and safe rollout.
- `api_credentials/`: encrypted provider credentials.
- `ai_gateway/`: provider routing/runs; Phase 24.1 internal attachment contract used by Phase 24.2 Voice Intelligence and Phase 24.3 Vision Intelligence.
- `ai_agent/`: tenant AI settings, assigned-agent conversation processing, budget checks, RAG/collective-memory/multimodal-context prompt assembly.
- `agents/`: multi-agent registry/governance/orchestrator, custom agents, preflight/evals, memory vault, collective memory.
- `agents/multimodal_tools.py`: Phase 24.5 agent-scoped read-only multimodal tools that reuse media/search endpoints and Agent OS tool-run traces.
- `agents/multimodal_memory.py`: Phase 24.6 sanitized multimodal memory/training/RAG event capture and materialization.
- `agents/orchestrator.py`: multi-agent orchestration queue; ingestion enqueue is optional and savepoint-isolated.
- `agents/operating_system.py`: Phase 11 Agent OS control-plane for overview, inter-agent messages, tool-run traces, event subscriptions and Intelligence-to-orchestrator sync.
- `advisor/`: advisor chat/actions/insights.
- `knowledge/`: RAG sources, PDF/TXT/CSV upload, safe URL ingestion, sparse-vector search, citations, reindex, delete, evaluations.
- `media/`: uploads, WhatsApp media retrieval, Phase 24.2 Voice Intelligence, Phase 24.3 Vision Intelligence, Phase 24.4 Web/Image Search Intelligence endpoint/cache/approval integration, Phase 24.7 approved-reference preparation reused by Inbox UX, Phase 24.8 provider-policy enforcement before search provider calls, and Phase 24.10 safe-rollout checks before voice/vision/search provider execution; media search remains approval-first and customer sends go through CRM outbound.
- `diagnostics/`: operational diagnostics.
- `reliability/`: admin-only Phase 12 performance, reliability and scale control-plane.
- `compliance/`: tenant privacy exports and non-destructive delete requests.
- `internal/`: internal checks.
- `commerce/`: products.

## Frontends

- `saas-version/frontend/src/App.jsx`: client app shell; owns operational Inbox, robust polling, browser notifications, DM/comment separation, CRM side panel, assignment, custom fields, timeline/dedupe, composer, Phase 24.7 Inbox analysis/reference UX, settings, Phase 10 verticalization UI, Phase 11 Intelligence/Ecosystem navigation, predictive Dashboard strip, Inbox predictive badges/churn filter, CRM predictive card, and floating Advisor briefing.
- `saas-version/frontend/src/AiAgentsPanel.jsx`: AI Agents builder plus Agent OS tab for core-agent coverage, memory layers, event-driven subscriptions, messages, tool runs, multimodal tools and traces.
- `saas-version/frontend/src/IntelligencePanel.jsx`: tenant-facing Phase 11/16/17/19/20/24 Intelligence UI for grants, overview summaries/cards, feature snapshots, baseline/ML predictions, recommendations, feedback, model metrics, AI Operations, Enterprise AI Network vertical intelligence, Federated Learning opt-in/rounds/updates/aggregates/signals, Real-Time Intelligence live snapshots, Autonomous Revenue Engine, AI Enterprise Memory Network policy/export/import/review controls, multimodal observability and safe rollout.
- `saas-version/frontend/src/AiEcosystemPanel.jsx`: tenant-facing Phase 11 AI Ecosystem UI for marketplace, plugin center, tool registry, event subscriptions, developer console, external integrations and AI apps.
- `saas-version/frontend/src/WorkflowComposerPanel.jsx`: Phase 18 AI Workflow Composer UI for templates, graph editor, preflight, simulation, approvals, activation and rollback.
- `saas-version/frontend/src/TrustCenterPanel.jsx`: Phase 22 tenant Trust AI UI for governance overview, policies, risk scans, model cards, incidents, audits and reports.
- `saas-version/frontend/src/i18n.js`: Phase 14 tenant Spanish baseline catalog and `VITE_APP_LOCALE` lookup.
- `saas-version/frontend/src/*Panel.jsx`: domain panels.
- `saas-version/admin-frontend/src/AdminApp.jsx`: platform admin shell; includes Admin `AI Predictivo` controls for predictive features, ModelOps, realtime intelligence, Phase 24 tenant/plan/provider premium gating, cost summaries, observability flags and rollout flags.
- `saas-version/admin-frontend/src/i18n.js`: Phase 14 Admin Spanish baseline catalog and `VITE_ADMIN_LOCALE` lookup.
- `saas-version/*frontend/package.json`: frontend deps/scripts.
- `saas-version/*frontend/Dockerfile`: build/runtime images.
- `saas-version/*frontend/nginx.conf`: static serving config.
- `saas-version/scripts/phase14-copy-audit.mjs`: dependency-free critical UI copy audit for localization regressions.
- `saas-version/scripts/phase14-release-check.mjs`: dependency-free Product Ops release readiness gate.
- `saas-version/scripts/phase15-agent-template-intake.mjs`: dependency-free offline normalizer/risk classifier for `external-repos/agency-agents`; writes review artifacts under `docs/phase15_1/` and does not touch runtime/DB.

## Database

- `saas-version/migrations/*.sql`: migration history and schema source.
- `saas-version/migrations/038_saas_phase1_security_hardening.sql`: Phase 1 auth hardening schema.
- `saas-version/migrations/039_saas_phase3_observability_hardening.sql`: Phase 3 worker heartbeat and correlation schema.
- `saas-version/migrations/041_saas_knowledge_rag_phase6_operational.sql`: Phase 6 sparse-vector RAG and evaluation schema.
- `saas-version/migrations/042_saas_campaigns_phase7_operational.sql`: Phase 7 global quiet-hours and A/B event telemetry schema.
- `saas-version/migrations/043_saas_ai_agents_phase8_operational.sql`: Phase 8 custom-agent prompt/preflight/eval and conversation AI ownership schema.
- `saas-version/migrations/044_saas_billing_phase9_operational.sql`: Phase 9 billing lifecycle notice/PDF/provider-event schema.
- `saas-version/migrations/045_saas_verticalization_phase10.sql`: Phase 10 tenant industry and vertical pack application schema.
- `saas-version/migrations/046_saas_intelligence_engine_phase11.sql`: Phase 11 Intelligence Engine schema.
- `saas-version/migrations/047_saas_intelligence_modelops_phase11.sql`: Phase 11 prediction feedback and model metrics schema.
- `saas-version/migrations/048_saas_intelligence_model_rollouts_phase11.sql`: Phase 11 model registry rollout controls and rollout event audit schema.
- `saas-version/migrations/049_saas_ml_infrastructure_phase11.sql`: optional Phase 11 ML training jobs, model artifacts, inference runs and drift snapshots.
- `saas-version/migrations/050_saas_ml_training_strategy_phase11.sql`: Phase 11 event contracts, auto-labels, feature sets/runs, training datasets, model evaluations and feature metadata.
- `saas-version/migrations/051_saas_multi_agent_operating_system_phase11.sql`: Phase 11 Agent OS messages, runtime traces, tool-run traces, event subscriptions and premium flags.
- `saas-version/migrations/052_saas_autonomous_operational_intelligence_phase11.sql`: Phase 11 Autonomous Operational Intelligence policies, playbooks, anomalies, actions, reports and premium flags.
- `saas-version/migrations/053_saas_ai_platform_ecosystem_phase11.sql`: Phase 11 AI Platform Ecosystem marketplace/installations, plugins, tool registry, event subscriptions, developer apps, external integration metadata, tenant AI apps and ecosystem traces/metrics.
- `saas-version/migrations/054_saas_enterprise_ai_network_phase11.sql`: Phase 11 Enterprise AI Network vertical industry models, anonymized benchmarks, tenant benchmark comparisons, vertical insights, AI playbooks, aggregate knowledge-network nodes, network metrics and premium flags.
- `saas-version/migrations/055_saas_performance_reliability_phase12.sql`: Phase 12 SLO/backpressure/retention/snapshot/drill schema and high-volume performance indexes.
- `saas-version/migrations/056_saas_phase13_security_compliance.sql`: Phase 13 email OTP MFA challenge and privacy request schema.
- `saas-version/migrations/057_saas_ai_workflow_composer_phase18.sql`: Phase 18 Workflow Composer templates, workflows, versions, simulations, approvals, materializations and premium flags.
- `saas-version/migrations/058_saas_ai_trust_compliance_governance_phase22.sql`: Phase 22 Trust AI governance tables and premium flags.
- `saas-version/migrations/059_saas_realtime_intelligence_phase16.sql`: Phase 16 Real-Time Intelligence sessions, user cursors, metric snapshots and realtime feature flags.
- `saas-version/migrations/060_saas_voice_intelligence_phase24.sql`: Phase 24.2 Voice Intelligence analysis cache and premium feature flags.
- `saas-version/migrations/061_saas_vision_intelligence_phase24.sql`: Phase 24.3 Vision Intelligence analysis cache and premium feature flags.
- `saas-version/migrations/062_saas_web_image_search_intelligence_phase24.sql`: Phase 24.4 Web/Image Search Intelligence run/result records and premium feature flags.
- `saas-version/migrations/063_saas_agent_multimodal_tools_phase24.sql`: Phase 24.5 Agent Multimodal Tools premium flags and filtered Agent OS tool-run index.
- `saas-version/migrations/064_saas_multimodal_memory_training_events_phase24.sql`: Phase 24.6 Multimodal Memory & Training Events table and premium feature flags.
- `saas-version/migrations/065_saas_multimodal_admin_gating_phase24.sql`: Phase 24.8 plan feature limits and AI/search/TTS provider policy/cost controls.
- `saas-version/migrations/066_saas_revenue_memory_network_phase19_20.sql`: Phase 19 revenue engine tables and Phase 20 enterprise memory network tables/feature flags.
- `saas-version/migrations/067_saas_multimodal_observability_rollout_phase24.sql`: Phase 24.9 multimodal observability snapshots plus Phase 24.10 rollout policies/events and default-off feature flags.
- `saas-version/migrations/068_saas_federated_learning_phase17.sql`: Phase 17 federated policies, rounds, aggregate updates, aggregate results, global signals and default-off federated/global feature flags.
- `saas-version/migrations/069_saas_auth_billing_schema_drift_repair.sql`: production auth/billing schema-drift repair for missing login, MFA/security-event and billing lifecycle/runtime columns/tables.
- `saas-version/migrations/070_saas_crm_intelligence_schema_drift_repair.sql`: production CRM, campaign, verticalization, integration and Intelligence schema-drift repair for app boot and registration paths.
- `saas-version/migrations/071_saas_app_boot_schema_drift_repair.sql`: production app-boot schema-drift repair for base Inbox/messages/outbound, vertical-pack seed support, audit events, campaign preflight/A-B support and Advisor runtime tables.
- `saas-version/migrations/072_saas_phase24_inbox_multimodal_drift_repair.sql`: production Phase 24 Inbox multimodal drift repair for voice/vision/search/memory read paths.
- `saas-version/migrations/README.md`: migration notes.

## Tracking Artifacts

- `docs/SAAS_PROJECT_STATUS.md`: code-derived SaaS phase progress, migration repair status, and recommended phases.
- `docs/SEGUIMIENTO_PROYECTO_SAAS_ES.md`: Spanish source for portable phase/progress tracking.
- `docs/Scentra_SaaS_Project_Status.pdf`: portable Spanish project tracking artifact generated from the Spanish status report.
- `docs/ROADMAP_FASES_RESTANTES_ES.md`: Spanish roadmap source for remaining phases after Phase 17.
- `docs/Scentra_Roadmap_Fases_Restantes.pdf`: portable Spanish roadmap PDF for remaining phases.
- `docs/MANUAL_FASES_NUEVAS_ES.md`: Spanish operator manual for the newer AI phases, Phase 11 ML training flow and Oracle Free Tier guidance.
- `docs/Scentra_Manual_Fases_Nuevas.pdf`: portable Spanish manual PDF generated from the new-phase manual.
- `docs/SCENTRA_INTELLIGENCE_ENGINE.md`: Phase 11 hybrid AI + ML architecture, recommendations and roadmap.
- `docs/FASE11_ML_TRAINING_GUIDE_ES.md`: Spanish Phase 11 model training and promotion guide.
- `docs/TUTORIAL_FASE11_ENTRENAMIENTO_MODELOS_ES.md`: step-by-step Spanish operator tutorial for Phase 11 ML training, datasets, shadow/canary and production promotion.
- `docs/Scentra_Fase11_Tutorial_Entrenamiento_Modelos.pdf`: portable PDF generated from the Phase 11 training tutorial.
- `docs/PHASE15_1_AGENCY_AGENTS_RESEARCH.md`: full local Phase 15.1 analysis of `external-repos/agency-agents/`, including inventory, script/license review, Scentra mapping, safety rules and reordered roadmap.
- `docs/phase15_1/agent_template_inventory.json`: Phase 15.1B normalized metadata for 184 external agent templates.
- `docs/phase15_1/agent_template_inventory.csv`: compact Phase 15.1B review index.
- `docs/phase15_1/agent_template_drafts.json`: Phase 15.1C disabled draft metadata for selected external templates; not DB-imported.
- `docs/phase15_1/agent_template_risk_report.md`: Phase 15.1B/15.1C risk and draft summary.
- `docs/phase15_1/nexus_handoff_contracts.json`: Phase 15.2 offline NEXUS handoff contracts.
- `docs/phase15_1/nexus_playbooks.json`: Phase 15.2 offline playbook/runbook blueprints for future Workflow Composer use.
- `docs/phase15_1/agent_eval_rubrics.json`: Phase 15.3 offline eval rubrics for future certification/preflight use.
- `docs/phase15_1/agent_eval_results.json`: Phase 15.3 offline eval results for 29 disabled draft templates; all activation remains blocked.
- `docs/phase15_1/phase15_2_15_3_report.md`: compact Phase 15.2/15.3 generated report.
- `docs/ROADMAP_PHASES_16_25_EVALUATION.md`: viability and updated recommended sequencing for proposed phases 16-25 after the full external agent repo analysis.
- `docs/INFORME_FASE15_1_FASE11_ML_ROADMAP_ES.md`: Spanish source for the additional Phase 15.1/Phase 11/roadmap PDF.
- `docs/Scentra_Fase15_1_Fase11_ML_Roadmap_16_25.pdf`: additional Spanish PDF artifact for tracking Phase 15.1, Phase 11 ML training and roadmap 16-25.
- `architecture/INTELLIGENCE_ENGINE.md`: textual diagrams and flows for Intelligence Engine.
- `architecture/MULTI_AGENT_OS.md`: textual diagrams and flows for Phase 11 Multi-Agent Operating System.
- `architecture/AUTONOMOUS_OPERATIONAL_INTELLIGENCE.md`: diagrams and safety flows for Phase 11 Autonomous Operational Intelligence.
- `architecture/AI_PLATFORM_ECOSYSTEM.md`: diagrams and safety boundaries for Phase 11 AI Platform Ecosystem.
- `architecture/ENTERPRISE_AI_NETWORK.md`: diagrams and privacy boundaries for Phase 11 Enterprise AI Network and Vertical Intelligence.
- `architecture/AGENT_TEMPLATE_INTAKE.md`: Phase 15.1 external agent template intake, NEXUS handoff and eval safety flows.
- `saas-version/scripts/phase15-nexus-eval-harness.mjs`: dependency-free offline generator for Phase 15.2 handoff/playbook artifacts and Phase 15.3 eval artifacts.
- `architecture/PERFORMANCE_RELIABILITY_SCALE.md`: diagrams and safety boundaries for Phase 12 performance/reliability control-plane.
- `architecture/SECURITY_COMPLIANCE.md`: diagrams and safety boundaries for Phase 13 MFA/compliance.
- `architecture/LOCALIZATION_PRODUCT_OPS.md`: Phase 14 text catalog and release-gate flows plus external repo intake guardrails.
- `architecture/AI_WORKFLOW_COMPOSER.md`: Phase 18 Composer control-plane architecture, safety flow and premium gating.
- `architecture/AI_TRUST_COMPLIANCE_GOVERNANCE.md`: Phase 22 Trust AI control-plane architecture, safety boundaries and premium gating.
- `architecture/REALTIME_INTELLIGENCE_LAYER.md`: Phase 16 PostgreSQL-first Real-Time Intelligence architecture, tenant/Admin flows, privacy, premium gating and safety boundaries.
- `architecture/VOICE_MULTIMODAL_INTELLIGENCE.md`: Phase 24 Multimodal Gateway plus Voice Intelligence, Vision Intelligence, Web/Image Search Intelligence, Agent Multimodal Tools, Multimodal Memory, Inbox reference UX, Admin/Premium Gating, observability and safe-rollout flows, provider routing, approval controls and safety boundaries.
- `architecture/AUTONOMOUS_REVENUE_ENGINE.md`: Phase 19 revenue intelligence control-plane, premium gating and no-side-effect safety model.
- `architecture/ENTERPRISE_MEMORY_NETWORK.md`: Phase 20 tenant-scoped memory graph sync/review flow, privacy boundaries and feature gates.
- `architecture/FEDERATED_LEARNING_GLOBAL_INTELLIGENCE.md`: Phase 17 federated learning control-plane, API/worker/data flow, privacy boundaries and feature gates.

## Generated/Heavy Paths

- `saas-version/frontend/dist`
- `saas-version/admin-frontend/dist`
- `saas-version/admin-frontend/node_modules`

Verify intent before staging generated or dependency artifacts.
