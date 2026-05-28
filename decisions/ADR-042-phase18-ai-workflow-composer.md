# ADR-042: Phase 18 AI Workflow Composer As A Safe Control-Plane

Date: 2026-05-27

## Status

Accepted.

## Context

Scentra needs Phase 18 AI Workflow Composer to let tenants compose AI workflows from templates, Phase 15 handoff/playbook concepts, agents, predictive intelligence and campaign operations.

Directly creating or activating WhatsApp, Instagram, trigger, campaign or agent runtime actions from a new composer would increase operational risk and could bypass existing preflight, approval, billing and Meta template controls.

## Decision

Implement Workflow Composer as a dedicated tenant-scoped control-plane:

- backend domain: `saas-version/backend/app_saas/workflow_composer`
- API prefix: `/saas/v1/workflow-composer`
- migration: `057_saas_ai_workflow_composer_phase18.sql`
- frontend panel: `saas-version/frontend/src/WorkflowComposerPanel.jsx`
- premium gates: `ai_workflow_composer` and `workflow_composer_templates`

Composer activation creates a `composer_only` materialization. It marks the workflow active inside Composer, but does not execute external side effects.

## Consequences

Positive:

- Tenants can design, simulate, approve, activate and rollback workflows safely.
- Phase 15 templates/playbooks can inform Composer without becoming executable code.
- Future runtime deployment can be added behind a separate ADR and explicit materialization path.

Tradeoffs:

- Phase 18 is operational as a supervised design/control surface, not as autonomous trigger deployment.
- Production rollout still needs plan/tenant feature grants before write operations become available outside demo mode.

## Guardrails

- Keep all queries tenant-scoped.
- Keep simulation side-effect free.
- Require preflight and owner/admin approval before activation.
- Reset approval to draft when graph/config changes.
- Do not bypass existing campaign, trigger, flow, agent, budget or Meta template controls.
