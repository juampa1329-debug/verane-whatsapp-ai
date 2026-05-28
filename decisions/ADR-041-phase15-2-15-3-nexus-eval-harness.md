# ADR-041: Phase 15.2/15.3 Offline NEXUS And Eval Harness

Status: accepted

Date: 2026-05-27

Scope: SaaS only.

## Context

Phase 15 uses the local external repository at `external-repos/agency-agents/` as reviewed input for Scentra agent templates, NEXUS playbooks, handoff contracts and eval/governance patterns.

Phase 15.1B/15.1C already produced disabled agent-template draft metadata without importing anything into SaaS runtime. The next safe step is to convert strategy/playbook/handoff/testing material into offline artifacts that can guide future Workflow Composer, marketplace certification and Admin review flows.

## Decision

Implement Phase 15.2 and Phase 15.3 as a dependency-free offline harness:

- script: `saas-version/scripts/phase15-nexus-eval-harness.mjs`
- outputs:
  - `docs/phase15_1/nexus_handoff_contracts.json`
  - `docs/phase15_1/nexus_playbooks.json`
  - `docs/phase15_1/agent_eval_rubrics.json`
  - `docs/phase15_1/agent_eval_results.json`
  - `docs/phase15_1/phase15_2_15_3_report.md`

The harness parses external NEXUS strategy docs and Phase 15.1C disabled draft metadata, then generates:

- 7 NEXUS handoff contracts
- 7 phase playbook blueprints
- 4 scenario runbook blueprints
- 6 Scentra eval rubrics
- eval results for 29 disabled draft templates

## Guardrails

- No database writes.
- No API, frontend, worker, Docker or migration changes.
- No tenant exposure.
- No active marketplace rows.
- No active agents.
- No external scripts executed.
- All evaluated drafts remain blocked pending human review.

## Consequences

Positive:

- Phase 15.2/15.3 become reproducible, reviewable artifacts instead of loose notes.
- Future Phase 18 Workflow Composer can consume structured playbook/handoff blueprints.
- Future marketplace certification can use structured eval rubrics and blocked activation state.
- The safety model remains compatible with Scentra preflight, premium gating, tenant isolation and one-AI-owner conversation behavior.

Tradeoffs:

- These artifacts are not yet runtime features.
- Eval results are advisory until Admin review and certification UI/API exist.
- Source URL, commit/tag, secret scan and attribution decision remain required before any commercial import.

## Follow-Up

- Use these artifacts as inputs for Phase 18 AI Workflow Composer.
- Use the eval rubrics in future marketplace/Admin certification workflows.
- Do not import or activate external templates until a reviewed DB import plan and separate ADR exist.
