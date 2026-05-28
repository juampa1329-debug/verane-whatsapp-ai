# AI Workflow Composer Architecture

Scope: SaaS Phase 18 under `saas-version/`.

## Purpose

AI Workflow Composer is a tenant-scoped control-plane for designing, simulating, approving, versioning and activating AI workflows without directly executing Meta, CRM, campaign, trigger or agent side effects during design.

## Components

```text
Tenant Frontend
  WorkflowComposerPanel.jsx
    - templates
    - graph editor
    - preflight
    - simulation
    - approval
    - version rollback
        |
        v
FastAPI /saas/v1/workflow-composer
  router.py
        |
        v
workflow_composer/service.py
  - premium access resolution
  - template seeding
  - graph validation
  - preflight scoring
  - side-effect-free simulation
  - approval workflow
  - control-plane activation
        |
        v
PostgreSQL
  saas_ai_workflow_templates
  saas_ai_workflows
  saas_ai_workflow_versions
  saas_ai_workflow_simulations
  saas_ai_workflow_approvals
  saas_ai_workflow_materializations
```

## Safety Flow

```text
Template or blank workflow
  -> draft graph
  -> preflight
  -> simulation
  -> approval request
  -> owner/admin approval
  -> composer_only materialization
  -> active Composer workflow
```

Runtime side effects are intentionally blocked in simulation and not materialized into triggers/flows/campaigns unless a future explicit, reviewed deployment path is added.

## Premium Gating

- Read/demo surfaces: `workflow_composer_templates` or demo access.
- Write/control surfaces: `ai_workflow_composer` full access.
- Admin feature catalog now includes `ai_workflow_composer` and `workflow_composer_templates`.

## Data Flow

```text
Graph JSON
  nodes: event, condition, ai_decision, approval, action, delay, handoff, end
  edges: from/to node IDs
  settings: requires_preflight, requires_approval

Preflight JSON
  ready/status/score/risk_level/checks/high_risk_actions

Simulation JSON
  visited_nodes/actions_planned/blockers/side_effects_executed=false
```

## Guardrails

- Every workflow row is tenant-scoped.
- Activation requires ready preflight and approved approval status.
- Graph/config edits reset workflow to draft approval.
- Version snapshots are retained for rollback.
- Composer does not trust external Phase 15 templates as executable code.
