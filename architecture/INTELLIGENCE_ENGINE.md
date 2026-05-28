# Intelligence Engine Architecture

Scope: SaaS only. Current implementation is Phase 11 foundation plus optional ML profile.

## System Map

```mermaid
flowchart TB
  Admin["Scentra Admin<br/>AI Predictivo"] --> AdminApi["/saas/v1/admin/intelligence/*"]
  TenantUi["Tenant client<br/>Inteligencia"] --> TenantApi["/saas/v1/intelligence/*"]
  EcosystemUi["Tenant client<br/>AI Ecosystem"] --> EcosystemApi["/saas/v1/ecosystem/*"]
  TenantUi --> RealtimeApi["/saas/v1/intelligence/realtime/*"]
  Admin --> AdminRealtime["/saas/v1/admin/intelligence/realtime*"]
  Inline["CRM/Billing inline capture"] --> Events
  Worker["Intelligence worker"] --> Events
  Worker --> Features
  Worker --> Predictions
  Worker --> Metrics["saas_intelligence_model_metrics"]
  AutoLabels["Auto-labels<br/>saas_ml_auto_labels"] --> Datasets["Training datasets<br/>saas_ml_training_datasets"]
  Features --> Datasets
  Datasets --> MlService["Optional ML service<br/>FastAPI + BentoML image"]
  MlService --> Predictions
  MlService --> MlTables["saas_ml_training_jobs<br/>saas_ml_model_artifacts<br/>saas_ml_inference_runs<br/>saas_ml_drift_snapshots"]
  MlService --> Mlflow["MLflow"]
  MlService --> Qdrant["Qdrant<br/>future vector infra"]
  AdminApi --> Grants["saas_intelligence_feature_grants"]
  AdminApi --> Registry["saas_intelligence_model_registry"]
  AdminApi --> RolloutEvents["saas_intelligence_model_rollout_events"]
  TenantApi --> Events["saas_intelligence_events"]
  TenantApi --> Features["saas_intelligence_feature_values"]
  Features --> Predictions["saas_intelligence_predictions"]
  Predictions --> Feedback["saas_intelligence_prediction_feedback"]
  Feedback --> Metrics
  Metrics --> Registry
  Registry --> Predictions
  Predictions --> Recommendations["saas_intelligence_recommendations"]
  Recommendations --> Advisor["Advisor context"]
  Predictions --> AutoOps["Autonomous Operational Intelligence"]
  Metrics --> AutoOps
  RealtimeApi --> RealtimeState["saas_realtime_intelligence_sessions<br/>saas_realtime_intelligence_cursors"]
  RealtimeApi --> Events
  RealtimeApi --> Predictions
  RealtimeApi --> Recommendations
  RealtimeApi --> AutoOps
  AdminRealtime --> RealtimeMetrics["saas_realtime_intelligence_metrics"]
  AutoOps --> OpsTables["saas_ai_operation_*"]
  EcosystemApi --> EcosystemTables["saas_ai_marketplace/plugins/tools/apps/*"]
  TenantApi --> Network["Enterprise AI Network"]
  Network --> NetworkTables["saas_ai_vertical_*<br/>saas_ai_knowledge_network<br/>saas_ai_network_metrics"]
  Network --> Benchmarks["Privacy-safe industry benchmarks"]
  Grants --> EcosystemApi
  Grants --> Network
  EcosystemApi --> Agents["Existing agents service<br/>template creation only"]
  Metrics --> Admin
  RealtimeMetrics --> Admin
  Billing["saas_plan_limits + saas_tenant_feature_flags"] --> Grants
  Billing --> TenantApi
  Billing --> RealtimeApi
```

## Event Flow

```mermaid
sequenceDiagram
  participant Source as "CRM/Webhook/Campaign/AI"
  participant Inline as "record_inline_event"
  participant API as "Intelligence API"
  participant DB as "PostgreSQL"
  Source->>API: "POST /intelligence/events"
  API->>DB: "insert saas_intelligence_events"
  DB-->>API: "event id"
  API-->>Source: "ok"
  Source->>Inline: "selected business writes"
  Inline->>DB: "nested transaction insert"
  Inline-->>Source: "None on telemetry failure"
```

Current event transport is PostgreSQL. Future event streaming should add NATS JetStream first for replay/fanout, then Kafka/Redpanda if high-volume analytics requires it.

Current inline sources are intentionally limited to CRM outbound `message.sent` and billing `billing.subscription.changed`. Runtime smoke validated this first pattern; broader producer coverage should still be added incrementally, preserving deterministic `replay_key` values.

## Real-Time Intelligence Flow

```mermaid
sequenceDiagram
  participant UI as "Tenant Inteligencia"
  participant API as "Realtime API"
  participant DB as "PostgreSQL"
  participant Admin as "Scentra Admin"
  UI->>API: "POST /intelligence/realtime/sessions"
  API->>DB: "upsert live session"
  UI->>API: "GET /intelligence/realtime/center"
  API->>DB: "read sanitized events + predictions + recommendations + ops + trust"
  API-->>UI: "snapshot, alerts, cursor, metrics"
  UI->>API: "PATCH /intelligence/realtime/cursor"
  API->>DB: "upsert last seen event"
  Admin->>API: "POST /admin/intelligence/realtime/metrics/refresh"
  API->>DB: "write metric snapshots only"
```

Phase 16 uses polling as the default product transport and exposes bounded SSE for future clients. It does not add Kafka, NATS, Redis Streams, WebSocket infrastructure or new dependencies. Realtime alerts are advisory and do not execute CRM, campaign, Meta, billing, workflow, agent, Trust or model-rollout side effects.

## Worker Automation Flow

```mermaid
sequenceDiagram
  participant W as "embedded/standalone/admin worker"
  participant DB as "PostgreSQL"
  participant IE as "Intelligence service"
  W->>DB: "advisory lock"
  W->>DB: "derive events from CRM/messages/webhooks/outbound/triggers/campaigns/remarketing/AI/billing"
  W->>IE: "recompute_feature_snapshot"
  W->>IE: "generate_prediction if gated + cooldown"
  IE->>DB: "predictions + recommendations + usage"
  W->>IE: "recompute_model_metrics"
  IE->>DB: "model metrics"
```

- Derived events use deterministic `replay_key` values for idempotency.
- The worker avoids invasive producer rewrites while Phase 11 matures.
- Inline capture uses the same replay-key families as the worker so API writes and derived passes do not duplicate events.
- Full event streaming can later move to NATS/Kafka without changing the persisted event schema.

## Prediction Flow

```mermaid
sequenceDiagram
  participant User as "Tenant Inteligencia UI"
  participant API as "POST /intelligence/predict"
  participant Billing as "Feature flags + grants + quota"
  participant Registry as "Model Registry"
  participant Store as "Feature Store"
  participant Model as "Baseline rules"
  participant ML as "Optional ML service"
  participant Rec as "Recommendation Engine"
  User->>API: "prediction_type"
  API->>Billing: "resolve demo/full access"
  Billing-->>API: "mode + quota"
  API->>Registry: "select production/canary by task + bucket"
  Registry-->>API: "selected model + rollout decision"
  API->>Store: "recompute snapshot"
  Store-->>API: "features"
  API->>Model: "score baseline_rules"
  Model-->>API: "prediction"
  API->>ML: "optional ready/shadow inference"
  ML-->>API: "ml_inference or fallback error"
  API->>Billing: "resolve predictive_recommendations gate"
  API->>Rec: "upsert recommendation only when ready + gated"
  API-->>User: "prediction + mode"
```

Disabled/paused registry states block prediction generation. Canary routing is deterministic by tenant/prediction/subject/window and traffic percent. Shadow/unapproved canary predictions are stored with `status = 'shadow'` and do not create recommendations automatically.

Prediction generation and recommendation persistence are separate gates. Demo prediction access can return a baseline preview, but writing `saas_intelligence_recommendations` requires enabled `predictive_recommendations` access and quota. Blocked recommendation persistence is reflected in prediction `output_json.recommendation_gate`.

Default canary selection changes the registry model key/version and emits `scoring_engine = baseline_rules`. When `SAAS_ML_ENABLED=true` and a registry artifact is loadable by `ml-service`, prediction runtime can call trained inference. Shadow inference is recorded under `output_json.ml_inference` and does not change baseline business output.

## Feedback And ModelOps Flow

```mermaid
sequenceDiagram
  participant User as "Tenant owner/admin/supervisor"
  participant API as "Intelligence API"
  participant DB as "PostgreSQL"
  participant Admin as "Scentra Admin"
  User->>API: "POST /intelligence/predictions/{id}/feedback"
  API->>DB: "upsert saas_intelligence_prediction_feedback"
  API->>DB: "record ai.prediction.feedback_recorded"
  API->>DB: "recompute saas_intelligence_model_metrics"
  Admin->>API: "GET /admin/intelligence/model-metrics"
  API-->>Admin: "sample, feedback, accuracy, drift"
```

- Metrics are tenant-scoped and model-scoped.
- Current metrics are governance baselines for rule predictions.
- Trained model quality still requires labeled datasets, eval thresholds, drift monitoring and staged rollout acceptance.

## Model Rollout Governance Flow

```mermaid
sequenceDiagram
  participant Admin as "Scentra Admin"
  participant API as "Admin Intelligence API"
  participant DB as "PostgreSQL"
  Admin->>API: "POST /admin/intelligence/models"
  API->>DB: "insert model registry row"
  API->>DB: "insert create rollout event"
  Admin->>API: "GET /admin/intelligence/models"
  API->>DB: "read registry + aggregate metrics"
  API-->>Admin: "status, rollout, readiness"
  Admin->>API: "PATCH /admin/intelligence/models/{model_key}"
  API->>DB: "update registry"
  API->>DB: "insert rollout event"
  API-->>Admin: "updated model + assessment"
```

- Current controls cover `disabled`, `shadow`, `canary`, and `production`.
- Canary traffic percent is applied by the prediction runtime against registry rows.
- Real inference routing is now available only through the optional ML profile and stays disabled by default. Baseline fallback remains mandatory for compatibility and rollout safety.

## Premium Gating

```mermaid
flowchart LR
  Plan["Plan feature_flags_json"] --> State["Effective intelligence state"]
  TenantFlag["Tenant feature override"] --> State
  Grant["Intelligence grant<br/>disabled/demo/full"] --> State
  Quota["Usage quota"] --> State
  State --> Demo["Demo preview"]
  State --> Full["Full predictive feature"]
  State --> Block["403/402 block"]
```

Rules:

- Demo mode is limited and visible through `intelligence_demo`.
- Full mode requires specific feature enablement, `ai_premium`, or an explicit full grant.
- Recommendation persistence requires the separate `predictive_recommendations` feature; do not infer it from the base prediction feature.
- Usage is recorded in `saas_intelligence_usage`.
- Admin changes are audited in `saas_audit_events`.

## Advisor Integration

```mermaid
flowchart LR
  Overview["GET /intelligence/overview"] --> AdvisorBriefing["GET /advisor/briefing"]
  Predictions["Latest predictions"] --> AdvisorContext["advisor_context"]
  Recommendations["Open recommendations"] --> AdvisorContext
  Predictions --> CRMIntel["CRM predictive_intelligence"]
  Recommendations --> Overview
  CRM["CRM/Inbox metrics"] --> AdvisorContext
  Health["Operational health"] --> AdvisorContext
  AdvisorBriefing --> Floating["Floating Advisor UI"]
  AdvisorContext --> Kimi["Kimi deep reasoning route"]
  AdvisorContext --> Drafts["Advisor actions / approvals"]
```

Advisor does not auto-execute predictive recommendations. It receives context and briefing summaries, then proposes actions under existing approval patterns. CRM/inbox can request conversation-level predictions, but generated recommendations remain gated by `predictive_recommendations`.

## ML Roadmap Deployment Shape

```mermaid
flowchart TB
  Postgres["PostgreSQL OLTP"] --> CDC["Event/CDC pipeline"]
  CDC --> Stream["NATS/Kafka"]
  Stream --> ClickHouse["Analytics DB"]
  Stream --> FeaturePipelines["Feature pipelines"]
  FeaturePipelines --> OnlineStore["Online feature store"]
  FeaturePipelines --> OfflineStore["Offline training store"]
  OfflineStore --> Training["Training jobs"]
  Training --> Registry["MLflow registry"]
  Registry --> Serving["ML service<br/>BentoML / FastAPI"]
  Serving --> Predictions["Prediction API"]
```

The default API/worker images intentionally remain dependency-light. The optional ML topology is enabled only through Compose profile `ml` and explicit ML flags after staging acceptance.

## Autonomous Operational Intelligence Flow

```mermaid
sequenceDiagram
  participant UI as "Tenant Inteligencia"
  participant API as "Operations API"
  participant DB as "PostgreSQL"
  participant W as "Intelligence worker"
  W->>API: "run_operational_intelligence_analysis"
  API->>DB: "read policy + feature access"
  API->>DB: "collect queues, worker heartbeat, Meta, CRM and campaign signals"
  API->>DB: "upsert anomalies/actions/reports"
  UI->>API: "GET /intelligence/operations/center"
  API-->>UI: "policy, levels, anomalies, actions, reports, playbooks"
  UI->>API: "approve/execute/dismiss action"
  API->>DB: "record controlled action result + event"
```

Autonomous Operations is human-supervised. Current execution does not directly mutate Meta, queues, campaigns, CRM or billing. Demo mode can preview analysis but cannot persist auto-remediation or low-risk auto-execute settings.

## Training Data Intelligence Flow

```mermaid
sequenceDiagram
  participant Admin as "Admin AI Predictivo"
  participant API as "Admin Intelligence API"
  participant DB as "PostgreSQL"
  participant ML as "Optional ML service"
  participant Registry as "Model registry"
  Admin->>API: "POST /admin/intelligence/auto-labels/generate"
  API->>DB: "derive labels from CRM/campaign/billing/ops state"
  Admin->>API: "POST /admin/intelligence/feature-pipelines/recompute"
  API->>DB: "write subject features with feature_set/version"
  Admin->>API: "POST /admin/intelligence/ml-datasets/build"
  API->>ML: "build dataset from labels + features"
  ML->>DB: "record saas_ml_training_datasets"
  Admin->>API: "POST /admin/intelligence/ml-training/autolabel"
  API->>ML: "train XGBoost/LightGBM/sklearn"
  ML->>DB: "record job, artifact, evaluation"
  API->>Registry: "optional shadow candidate registration"
```

Auto-labeling is heuristic and auditable. It uses existing SaaS events/state and evidence JSON, not manual labels or external private datasets. Promotion from shadow to canary/production still depends on registry gates, label-quality review, drift checks and staged rollout.

## Enterprise AI Network Flow

```mermaid
sequenceDiagram
  participant UI as "Tenant Inteligencia"
  participant API as "Network API"
  participant Gate as "Feature gates"
  participant DB as "PostgreSQL"
  UI->>API: "GET /intelligence/network/center"
  API->>Gate: "demo/full read access"
  API->>DB: "load industry, metrics, benchmarks, insights, playbooks"
  API-->>UI: "Industry Intelligence Center payload"
  UI->>API: "POST /intelligence/network/refresh dry_run=true"
  API-->>UI: "preview insights and comparisons"
  UI->>API: "POST /intelligence/network/refresh dry_run=false"
  API->>Gate: "full enterprise_ai_network/cross_tenant_intelligence/ai_premium"
  API->>DB: "persist tenant benchmark comparisons and insights"
  API-->>UI: "persisted network result"
```

Privacy model:

- Cross-tenant output is aggregate only.
- Benchmark rows require sample count >= 3.
- Tenant-private metric snapshots are not exposed as peer data.
- Playbooks and vertical model rows are metadata/recommendations, not active automation or heavy model training.

## Federated Learning Flow

```mermaid
sequenceDiagram
  participant UI as "Tenant Inteligencia"
  participant API as "Federated API"
  participant Gate as "Feature gates"
  participant DB as "PostgreSQL"
  participant W as "Intelligence worker"
  UI->>API: "GET /intelligence/federated/center"
  API->>Gate: "demo/full read gate"
  API->>DB: "load opt-in policy, local previews, rounds, updates, aggregates"
  UI->>API: "PATCH /intelligence/federated/policy"
  API->>Gate: "full federated/AI premium gate"
  API->>DB: "save opt-in/privacy/sample thresholds"
  UI->>API: "POST /rounds/prepare dry_run=false"
  API->>DB: "create round + submit aggregate update package"
  W->>API: "process_federated_learning"
  API->>DB: "auto-submit only if opt-in + auto participation"
  UI->>API: "POST /rounds/{id}/aggregate"
  API->>DB: "write aggregate row + global signal"
```

Phase 17 uses aggregate/statistical update packages only. It does not share raw tenant content, tenant names, prompts, media, provider payloads or secrets. Aggregates are candidate/global signals and do not promote production models automatically.
