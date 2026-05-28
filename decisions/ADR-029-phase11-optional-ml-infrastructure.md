# ADR-029: Phase 11 Optional ML Infrastructure

Status: Accepted

Date: 2026-05-27

Scope: SaaS only.

## Context

Scentra Phase 11 already had Intelligence events, feature snapshots, baseline predictions, ModelOps feedback/metrics, model registry rollout controls, tenant/admin UI, and deterministic canary routing. The user explicitly authorized adding real ML infrastructure for Phase 11 while preserving current production flows, tenant isolation, and Meta/WhatsApp/Instagram runtime stability.

Earlier ADRs intentionally avoided MLflow, BentoML, external model serving and ML dependencies until explicit approval. That approval now exists for an isolated, feature-flagged implementation.

## Decision

Add optional ML infrastructure without changing the default production path:

- Keep default API/worker images on existing `requirements.txt`.
- Add `requirements-ml.txt` and `Dockerfile.ml` for the optional ML service image.
- Add Compose profile `ml` with `mlflow`, `ml-service`, and `qdrant`.
- Keep `SAAS_ML_ENABLED=false` by default for API and worker.
- Add migration `049_saas_ml_infrastructure_phase11.sql` for ML jobs/artifacts/inference/drift audit state.
- Add `app_saas/ml_service` for synthetic/autolabel training, trained inference, drift evaluation, MLflow logging, BentoML packaging and Prometheus metrics.
- Add Admin MLops overview, training dataset readiness and synthetic training controls.
- Let prediction runtime call ML service only when explicitly enabled and artifact-ready.
- Preserve baseline fallback for compatibility.
- Keep shadow inference non-authoritative: it records `output_json.ml_inference` but does not change the baseline score, recommendation gate or business action.

Initial model families are:

- lead scoring
- churn prediction
- smart remarketing
- operational anomaly detection

Initial frameworks are:

- LightGBM
- XGBoost
- scikit-learn fallback

## Consequences

- Scentra can now train, package and serve bootstrap ML models in Docker without affecting the default SaaS runtime.
- MLflow and BentoML exist only in the optional ML image; API/worker startup cost and dependency risk remain lower.
- Synthetic/autolabel datasets allow infrastructure validation without private external datasets.
- Production-grade ML quality is still not guaranteed until real labels, eval thresholds, drift monitoring, cost monitoring and staged rollout acceptance exist.
- Qdrant is available for future vector infrastructure but is not wired into the existing Knowledge/RAG runtime.
- Kafka/NATS remain out of scope for this step.

## Safety Rules

- Do not enable `SAAS_ML_ENABLED=true` broadly without staging acceptance.
- Do not promote synthetic/autolabel models directly to production full mode.
- Do not expose ML service endpoints publicly without a dedicated auth/proxy design.
- Do not bypass premium gating, tenant grants, quotas, model status, rollout mode or baseline fallback.
- Do not allow shadow inference to trigger recommendations or customer-facing actions.
