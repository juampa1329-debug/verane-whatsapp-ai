# ADR-024: Phase 11 Model Rollout Governance

Date: 2026-05-26

## Status

Accepted.

Updated by ADR-029 on 2026-05-27: optional trained inference can now run through the ML service when explicitly enabled. The rollout governance and baseline-fallback rules in this ADR remain valid.

## Context

Phase 11 already had baseline predictions, feature gating, prediction feedback, and ModelOps metrics. Before adding MLflow, BentoML, event brokers, or trained model artifacts, Scentra needs a safe control plane for model lifecycle decisions so predictive behavior can be paused, shadowed, reviewed, and audited.

## Decision

Add dependency-light rollout governance inside the existing SaaS backend and PostgreSQL schema:

- Extend `saas_intelligence_model_registry` with rollout mode, traffic percent, readiness thresholds, promotion status, approval metadata, and shadow mode.
- Add `saas_intelligence_model_rollout_events` for auditability.
- Expose Admin endpoints to list models, assess production readiness, and patch rollout controls.
- Show model registry and rollout state in Admin `AI Predictivo`.
- Enforce registry status at prediction time: disabled/paused models are blocked, while shadow/canary predictions are persisted as `shadow` and do not create recommendations automatically.

No ML dependency, event broker, MLflow, BentoML, or trained artifact is added in this step.

## Consequences

- Admin can now govern baseline and future ML models without changing tenant APIs.
- Phase 11 has safer production controls before real trained-model serving is introduced.
- Historical note: canary traffic percent started as governance metadata. ADR-028 made deterministic canary selection operational, and ADR-029 added optional ML-service execution when explicitly enabled.
- Baseline rule models remain allowed in production as safe bootstrapping models, but their metrics are not proof of trained ML quality.
