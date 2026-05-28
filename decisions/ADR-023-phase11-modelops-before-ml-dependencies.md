# ADR-023: Phase 11 ModelOps Before ML Dependencies

Date: 2026-05-26

## Status

Accepted.

Updated by ADR-029 on 2026-05-27: optional MLflow/BentoML/ML dependency infrastructure is now approved and implemented behind the `ml` profile. This ADR remains historical sequencing context.

## Context

At the time of this decision, Phase 11 needed real predictive intelligence but the SaaS codebase ran without external ML runtimes, event brokers, model servers, or trained model artifacts. Adding Kafka/NATS/MLflow/BentoML or ML packages before labels, feedback, tenant isolation tests and operational metrics were ready would have increased deployment risk.

## Decision

Add a dependency-light ModelOps foundation first:

- Store tenant-scoped prediction feedback in `saas_intelligence_prediction_feedback`.
- Store tenant/model quality snapshots in `saas_intelligence_model_metrics`.
- Expose feedback and model metrics through tenant Intelligence APIs.
- Expose model metrics and recompute through Scentra Admin.
- Recompute metrics from the Intelligence worker after tenant event/feature/prediction processing.
- Keep current predictions as registered baseline rule models until labeled datasets and dependency approval exist.

## Consequences

- Phase 11 can collect labels and quality signals before trained ML is introduced.
- Admin can monitor feedback count, sample size, accuracy and drift baseline without new infrastructure.
- No dependency, package or architecture churn is introduced.
- Metrics are governance baselines, not final ML quality guarantees.
- MLflow, BentoML, Kafka/NATS and trained model serving remain future controlled steps.
