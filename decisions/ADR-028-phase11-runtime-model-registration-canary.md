# ADR-028: Phase 11 Runtime Model Registration And Canary Routing

Date: 2026-05-26

Status: Accepted

Updated by ADR-029 on 2026-05-27: optional ML service execution is now available when `SAAS_ML_ENABLED=true`; deterministic canary routing and baseline fallback remain mandatory.

Scope: SaaS only, `saas-version/`.

## Context

Phase 11 already had Intelligence Engine events, feature snapshots, baseline predictions, premium gating, ModelOps feedback/metrics, and rollout governance columns. The remaining governance gap was operational: Admin could inspect and patch existing registry rows, but could not register a new candidate model from the platform panel, and canary traffic settings were not applied by the prediction runtime.

At the time of this decision, project safety rules still prohibited automatic dependency installation and the platform had no approved MLflow/BentoML/Kafka/NATS serving stack. ADR-029 later approved optional MLflow/BentoML infrastructure behind the `ml` profile; Kafka/NATS remain out of scope.

## Decision

Implement dependency-light model registration and deterministic registry-level canary routing.

- Add Admin API `POST /saas/v1/admin/intelligence/models`.
- Add Admin `AI Predictivo` model registration form.
- Store candidate/external/pending model metadata in `saas_intelligence_model_registry`.
- Record create/update actions in `saas_intelligence_model_rollout_events`.
- Select canary registry rows at prediction time with a deterministic bucket based on tenant, prediction type, subject and window.
- Keep baseline fallback explicit. After ADR-029, optional ML-service scoring can run only when `SAAS_ML_ENABLED=true` and an artifact is ready.

## Consequences

Positive:

- Admin can stage and govern future model candidates without schema changes.
- Canary `traffic_percent` is now runtime behavior, not only stored metadata.
- Smoke tests can validate `100%` canary selection and `0%` fallback.
- Predictions and events expose the selected scoring engine, reducing product and agent hallucination risk.

Tradeoffs:

- Registered `artifact_uri` values are metadata only.
- External artifacts are not loaded, served or invoked.
- Real trained ML quality still requires labeled data, model training, model registry integration, serving, drift monitoring and production acceptance.

## Validation

- Backend compile passed for Intelligence/Admin modules.
- Admin frontend build passed.
- Clean Docker/PostgreSQL stack applied migrations through `048`.
- Authenticated smoke passed for admin model registration, tenant grant, feature recompute, canary `100%`, fallback `0%`, and explicit baseline scoring metadata.
- Browser smoke loaded Scentra Admin without console errors.
