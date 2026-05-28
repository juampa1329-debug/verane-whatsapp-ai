# ADR-040: Phase 15.1B/15.1C Offline Agent Template Intake

Date: 2026-05-27

## Status

Accepted as offline intake and disabled draft generation. Not accepted as runtime marketplace import.

## Context

The user approved continuing Phase 15.1B and 15.1C using the local external repo at `external-repos/agency-agents/`, with the explicit constraint that Scentra must not be affected.

Scentra already has a Phase 11 AI Ecosystem control-plane with marketplace metadata, plugin metadata and tenant-scoped installs. However, importing third-party templates directly into `saas_ai_marketplace_items` would create review, attribution, security and activation risk before a formal approval flow exists.

## Decision

Implement Phase 15.1B/15.1C as an offline, deterministic intake pipeline:

- Add `saas-version/scripts/phase15-agent-template-intake.mjs`.
- Use Node built-ins only.
- Read external Markdown files from `external-repos/agency-agents/`.
- Parse agent frontmatter and sections.
- Normalize agent metadata into Scentra-oriented JSON.
- Classify recommended surface, role, industry, compliance domains, risk and safe tool scopes.
- Generate disabled draft marketplace metadata artifacts under `docs/phase15_1/`.
- Do not insert rows into Postgres.
- Do not update API/worker/frontend runtime behavior.
- Do not execute external repo scripts.

Generated artifacts:

- `docs/phase15_1/agent_template_inventory.json`
- `docs/phase15_1/agent_template_inventory.csv`
- `docs/phase15_1/agent_template_drafts.json`
- `docs/phase15_1/agent_template_risk_report.md`

## Consequences

- Scentra now has a reusable intake step for future Admin review.
- 184 external agents are normalized as inventory.
- 29 selected templates are available as disabled draft metadata only.
- Generated drafts are premium-gated, approval-first and activation-disabled by design.
- Future implementation can import reviewed drafts into the real AI Marketplace after a separate explicit approval.

## Guardrails

- Generated drafts are not active agents.
- Generated drafts are not database records.
- Generated drafts must not be exposed to tenants until reviewed and imported through an approved path.
- External tool declarations are not trusted; they are remapped to safe Scentra tool recommendations.
- Outbound/customer-facing behavior remains suggest-only.
- Healthcare/legal/finance/paid-media/outbound/security-sensitive templates require compliance/security review before tenant use.

## Open Risks

- Upstream URL/commit/tag remains unverified.
- A formal secret scan is still recommended before commercial import.
- Risk classification is heuristic and conservative; human review remains mandatory.
- Some external prompts may need rewriting for Scentra tone, policies, Spanish localization and vertical compliance.
