# AI Trust, Compliance & Governance

Scope: SaaS Phase 22. Code source is `saas-version/backend/app_saas/trust_center/` and migration `saas-version/migrations/058_saas_ai_trust_compliance_governance_phase22.sql`.

## Purpose

Phase 22 adds a tenant-scoped AI governance control-plane for policies, risk assessments, model cards, incidents, audit events and compliance report snapshots.

It is not an automatic enforcement runtime and not legal certification.

## Component Map

```mermaid
flowchart TD
  TenantUI["Tenant Trust AI panel"] --> TenantAPI["/saas/v1/trust-center/*"]
  AdminUI["Admin Trust AI view"] --> AdminAPI["/saas/v1/admin/trust-center/*"]
  TenantAPI --> Service["trust_center/service.py"]
  AdminAPI --> Service
  Service --> Gates["Intelligence premium/demo gates"]
  Service --> DB["PostgreSQL governance tables"]
  Service --> Signals["Existing AI control-plane signals"]
  Signals --> Agents["Agents"]
  Signals --> Composer["Workflow Composer"]
  Signals --> Models["Model registry"]
  Signals --> Ecosystem["Plugins/tools"]
  Signals --> Operations["Autonomous actions"]
```

## Data Flow

```mermaid
sequenceDiagram
  participant User as Tenant/Admin User
  participant API as Trust Center API
  participant Gate as Premium Gate
  participant DB as PostgreSQL
  participant AI as Existing AI Domains

  User->>API: Read overview/policies/risks
  API->>Gate: Resolve demo/full feature mode
  API->>DB: Ensure tables and seed policies
  API->>AI: Read metadata counts/signals
  API-->>User: Tenant-scoped trust snapshot

  User->>API: Run risk assessment
  API->>Gate: Require full ai_risk_assessments for persistence
  API->>AI: Inspect agents/workflows/models/tools/actions
  API->>DB: Persist risk records and audit
  API-->>User: Generated risks and status
```

## Tables

- `saas_ai_governance_policies`
- `saas_ai_governance_policy_attestations`
- `saas_ai_risk_assessments`
- `saas_ai_model_cards`
- `saas_ai_governance_incidents`
- `saas_ai_governance_reports`
- `saas_ai_governance_audits`

All records are tenant scoped through `tenant_id`.

## Feature Gates

- `ai_trust_center`: read/overview trust center.
- `ai_governance_policies`: policy creation/update/attestation.
- `ai_risk_assessments`: persisted risk scans and mitigation state.
- `ai_model_cards`: model card upsert/update.
- `ai_compliance_reports`: report snapshot generation.
- `ai_audit_exports`: audit listing/export capability.

Demo access can preview read-only surfaces. Full access is required for mutations.

## Safety Boundaries

- Risk scans do not pause or activate agents.
- Model cards do not promote or roll back models.
- Incidents do not trigger automatic self-healing.
- Reports do not certify legal compliance.
- Admin trust overview is read-only.
- No raw cross-tenant content is exported.

## Rollout Notes

1. Keep all flags disabled by default in plan limits.
2. Enable demo mode first for selected tenants.
3. Require full mode only after policy owner review.
4. Run risk assessment and generate a report before enabling higher autonomy or marketplace execution.
5. Treat legal/compliance statements as operational evidence, not formal certification.
