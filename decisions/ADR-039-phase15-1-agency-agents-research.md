# ADR-039: Phase 15.1 Agency Agents Research

Date: 2026-05-27

## Status

Accepted as read-only research/intake. Not accepted as runtime integration.

Superseded for follow-up sequencing by ADR-040 and ADR-041. Phase 15.1B/15.1C/15.2/15.3 are now complete as offline artifacts; runtime import is still not accepted.

## Context

The user first provided a README for an external repository described as `The Agency` / `agency-agents`, then added the full local repository at `external-repos/agency-agents/`.

The local repository contains:

- MIT `LICENSE`.
- Markdown agent definitions.
- Strategy/playbook/runbook docs.
- Integration output folders.
- Shell scripts for install/convert/lint workflows.

Read-only inventory found:

- 184 valid agent Markdown files with frontmatter.
- 16 non-agent strategy/playbook/docs files without agent frontmatter.
- 14 agent categories plus strategy docs.

Scentra already has:

- AI Agents Enterprise.
- Custom agents.
- Agent OS.
- AI Marketplace control-plane.
- Tool registry metadata.
- Memory vault and collective memory.
- Premium gating.
- Approval-first tool runs.
- One-AI-owner conversation assignment.

## Decision

Use the external repository as a reviewed source for:

- agent taxonomy
- disabled marketplace template drafts
- vertical agent-pack ideas
- workflow/handoff playbooks
- eval rubrics
- AI governance patterns

Do not use it as:

- executable SaaS runtime
- trusted plugin code
- queue system
- secure tool framework
- automatic agent installer
- replacement for Scentra Agent OS

The safe sequence defined at this point was:

1. Phase 15.1A: Full Repo Audit And Inventory.
2. Phase 15.1B: Template Normalizer And Risk Classifier.
3. Phase 15.1C: Disabled Draft Marketplace Import.
4. Phase 15.2: NEXUS Playbooks And Handoff Model.
5. Phase 15.3: Agent Eval And QA Harness.

## Consequences

- Scentra can reuse specialized role design without bypassing its own runtime.
- Imported content, if later approved, must enter as disabled draft metadata with source attribution.
- External `tools` declarations must be remapped into Scentra approval-first tool scopes.
- The repo's NEXUS strategy should shape Workflow Composer and Agent OS handoffs before broad marketplace import.

## Risks

- The local folder is not a standalone nested Git repo, so exact upstream commit/tag remains unverified.
- Prompt content may contain unsafe assumptions or tool permissions.
- Some verticals, especially healthcare/legal/finance, need compliance rewrites before tenant use.
- Shell scripts write to local AI-tool config directories and must not be run as part of Scentra.
- Marketplace import without risk classification could create hallucination, privacy, tool-use or brand-consistency issues.

## Guardrails

- No external script execution.
- No global agent installation.
- No active tenant import without Admin review.
- No tool permission inheritance from external frontmatter.
- No customer-facing action without existing Scentra preflight, approval, quiet-hour, Meta-template, billing and tenant permission checks.
