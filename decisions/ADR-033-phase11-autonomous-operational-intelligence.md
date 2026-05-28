# ADR-033: Phase 11 Autonomous Operational Intelligence

Date: 2026-05-27

Status: Accepted

Scope: SaaS only.

## Context

Scentra Phase 11 already includes Intelligence Engine, optional ML infrastructure, product-facing predictive intelligence, Advisor briefing, and Multi-Agent OS. The next requirement is Autonomous Operational Intelligence: detect anomalies, recommend optimizations, support self-healing, and expose an AI Operations Center / AI Control Center without uncontrolled autonomy.

The platform has sensitive runtime paths: Meta webhooks, outbound WhatsApp/Instagram dispatch, billing, CRM, triggers, workers and tenant AI agents. Direct autonomous mutation of these systems would be high risk without staged approvals, rollback and provider-specific acceptance.

## Decision

Implement Autonomous Operational Intelligence as a tenant-scoped supervised control plane:

- Add migration `052_saas_autonomous_operational_intelligence_phase11.sql`.
- Add `app_saas/intelligence/operations.py` for policies, playbooks, anomaly detection, action records, reports and access checks.
- Add tenant APIs under `/saas/v1/intelligence/operations/*`.
- Add tenant UI sections in `IntelligencePanel.jsx`: AI Operations Center, AI Control Center, Autonomous actions and Operational reports.
- Add billing/Intelligence feature flags disabled by default:
  - `autonomous_operations`
  - `ai_self_healing`
  - `ai_control_center`
- Integrate the Intelligence worker with autonomous analysis in an isolated nested transaction.

The execution model is intentionally conservative:

- Demo mode can preview/analyze but cannot persist auto-remediation or low-risk auto-execute.
- Level 4 can mark only low-risk/report-only actions as controlled executions.
- Provider-impacting or data-mutating remediation remains approval-first.
- Current action execution records result/audit metadata and does not directly mutate Meta, queues, campaigns, CRM or billing.

## Consequences

Positive:

- Adds an operational AI surface without risking uncontrolled side effects.
- Keeps autonomy premium-gated, tenant-scoped, auditable and rollback-aware.
- Allows future self-healing to be added per playbook after staging acceptance.
- Worker failures in this layer do not break existing Intelligence/Meta/CRM runtime.

Tradeoffs:

- "Self-healing" is currently supervised/control-plane first; real remediation must be added playbook by playbook.
- Production value depends on real operational data volume and tenant feature enablement.
- Per-tenant worker-degradation anomalies may be noisy until thresholds are tuned with staging traffic.

## Validation

Validated in the active SaaS Docker stack:

- Frontend tenant build passed.
- API container `py_compile` passed for touched backend modules.
- `docker compose -f saas-version/docker-compose.saas.yml up -d --build` applied migration `052`.
- API health returned OK.
- Swagger `/docs` returned 200.
- Migration `052` is recorded in `saas_schema_migrations`.
- New operation tables exist in PostgreSQL.
- OpenAPI contains the new operations endpoints.
- Authenticated tenant smoke confirmed demo operations center and dry-run analysis.
- Demo policy smoke confirmed auto-remediation and low-risk auto-execute are forced off in demo mode.
- SQL migration BOM and strict UTF-8 scans passed.
