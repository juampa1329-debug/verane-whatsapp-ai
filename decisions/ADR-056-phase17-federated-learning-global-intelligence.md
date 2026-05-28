# ADR-056 Phase 17 Federated Learning And Global Intelligence

Date: 2026-05-28

## Status

Accepted

## Context

Scentra needs global and vertical intelligence without exposing private tenant content. The SaaS already has Intelligence Engine events, feature values, ML infrastructure, Enterprise AI Network benchmarks and premium gating. Phase 17 must improve cross-tenant learning while preserving strict multi-tenant isolation.

## Decision

Implement Phase 17 as a federated learning control-plane, not as uncontrolled distributed model training.

Tenants can opt in to generate local aggregate update packages for:

- lead scoring
- churn prediction
- smart remarketing
- operational anomaly detection

The backend stores tenant policies, federated rounds, aggregate update packages, aggregate results and global intelligence signals. The Intelligence worker can participate only when the tenant has full access, opt-in is enabled and auto-participation is enabled.

## Privacy Model

Federated update packages include counts, rates, quality score, feature summaries, feature-importance metadata and privacy metadata only.

They do not include:

- raw messages
- raw conversations
- raw media/base64
- prompts
- decrypted secrets
- provider payloads
- tenant names
- private customer content

Global signals require cohort thresholds and remain model-candidate/benchmark signals, not production model promotion.

## Consequences

Benefits:

- Enables privacy-safe global learning and benchmarking.
- Preserves SaaS tenant isolation and premium gating.
- Gives tenants and workers a real opt-in/auto-participation lifecycle.
- Keeps model promotion under existing ModelOps governance.

Tradeoffs:

- Current aggregation is weighted statistical aggregation, not full gradient/model-weight federation.
- Production ML benefit depends on real tenant sample volume and label quality.
- Future advanced secure aggregation or differential privacy math needs a separate reviewed implementation before claims beyond metadata readiness.

## Implementation

- Migration: `saas-version/migrations/068_saas_federated_learning_phase17.sql`
- Backend: `saas-version/backend/app_saas/intelligence/federated.py`
- API routes: `saas-version/backend/app_saas/intelligence/router.py`
- Schemas: `saas-version/backend/app_saas/intelligence/schemas.py`
- Worker: `saas-version/backend/app_saas/workers/intelligence.py`
- Tenant UI: `saas-version/frontend/src/IntelligencePanel.jsx`
- Feature catalog and defaults: `intelligence/catalog.py`, `billing/limits.py`, `admin-frontend/src/AdminApp.jsx`

## Non-Goals

- No raw cross-tenant data sharing.
- No automatic production model promotion.
- No external federated framework dependency.
- No provider calls, Meta sends, CRM mutation, campaign activation, workflow execution, billing changes or agent auto-actions.
