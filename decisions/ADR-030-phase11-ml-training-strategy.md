# ADR-030: Phase 11 ML Training Strategy

Status: Accepted

Date: 2026-05-27

Scope: SaaS only.

## Context

Scentra Phase 11 already had Intelligence events, feature snapshots, baseline predictions, premium gating, ModelOps, rollout governance, optional MLflow/BentoML infrastructure, and shadow inference. The platform does not yet have huge curated historical datasets, so training must start from real SaaS state/events and avoid expensive or unsafe deep-learning infrastructure.

The user explicitly authorized MLflow, BentoML, ML libraries, training pipelines, inference services, registry, drift monitoring, workers and feature pipelines, while preserving multi-tenant isolation and current WhatsApp/Instagram/Meta runtime behavior.

## Decision

Implement an incremental, event-based ML training strategy:

- Add migration `050_saas_ml_training_strategy_phase11.sql`.
- Store event contracts and replay cursors in PostgreSQL.
- Generate auto-labels from existing SaaS state/events instead of requiring manual labeling first.
- Recompute feature sets into the existing Intelligence feature store with feature key/version/quality metadata.
- Build ML datasets by joining `saas_ml_auto_labels` with `saas_intelligence_feature_values`.
- Train only lightweight tabular models initially: LightGBM, XGBoost, and sklearn fallback.
- Record training datasets and offline model evaluations in PostgreSQL.
- Log MLflow experiments and BentoML model packages from the optional ML service when available.
- Expose Admin-only controls for label generation, feature pipeline recompute, dataset materialization and autolabel training.
- Keep `SAAS_ML_AUTO_TRAIN_ENABLED=false` by default.
- Keep trained models behind registry, shadow/canary rollout, premium feature gates, tenant grants, quotas and baseline fallback.

Initial tasks:

- `lead_scoring`
- `churn_prediction`
- `smart_remarketing`
- `operational_anomaly`

## Consequences

- Scentra can now bootstrap real ML training from its own operational data without external private datasets.
- Training remains cost-efficient and explainable; no GPU, deep learning or LLM training is introduced.
- Auto-labels are auditable through evidence JSON and confidence fields, but they are still heuristic labels.
- Production promotion requires label-quality review, drift checks, cost checks, tenant-isolation review and staged rollout.
- The default API/worker runtime remains compatible because heavy ML dependencies and training execution stay in the optional ML service.
- The current event store remains PostgreSQL-backed; Kafka/NATS are still future scale decisions.

## Safety Rules

- Do not promote synthetic or auto-label models directly to production full mode.
- Do not share raw messages, conversations or sensitive tenant payloads across tenants for shared models.
- Do not enable automatic training broadly without explicit rollout approval.
- Do not expose ML service endpoints publicly without auth/proxy design.
- Do not let shadow inference change baseline business results or trigger customer-facing recommendations.
- Preserve premium gating, demo mode, tenant-level enablement, quotas, registry status and rollback paths.
