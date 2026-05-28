# PHASE15_1_AGENCY_AGENTS_RESEARCH

Scope: SaaS only.

Source analyzed:

- Initial README provided by user: `D:\Juan Pablo\Descargas\README.md`.
- Full local repository now present at `external-repos/agency-agents/`.

Analysis mode: read-only. No scripts were executed. No templates were imported into Scentra. No runtime code, dependencies, Docker config, migrations, auth, billing, Meta runtime, workers or ML runtime were changed.

## Source Reality Check

The local folder is inside the Scentra workspace, but it is not detected as a standalone nested Git repository. `git -C external-repos/agency-agents rev-parse --show-toplevel` resolves to the main workspace root, so the exact upstream commit/tag is still unverified.

Detected files:

- `README.md`
- `LICENSE`
- `SECURITY.md`
- `CONTRIBUTING.md`
- category folders for agent Markdown files
- `strategy/` docs/playbooks/runbooks
- `examples/`
- `integrations/`
- `scripts/install.sh`
- `scripts/convert.sh`
- `scripts/lint-agents.sh`

License file:

- `LICENSE` is MIT, copyright `2025 AgentLand Contributors`.

Important security note:

- `SECURITY.md` says the repository contains Markdown-based agent definitions and shell scripts, and scripts should be reviewed before running.
- This matches Scentra's posture: treat the repo as untrusted prompt/template input until reviewed and normalized.

## Inventory

Local inventory detected:

- 200 Markdown files under agent/strategy-style folders.
- 184 valid agent files with frontmatter.
- 16 Markdown files without agent frontmatter, mostly strategy/playbook/docs.
- 14 active agent categories plus strategy docs.
- Only 3 agent files declare `services` in frontmatter.
- Word count range: 192 to 4638 words.
- Average agent length: about 1713 words.

Agent category counts:

| Category | Valid agents |
| --- | ---: |
| academic | 5 |
| design | 8 |
| engineering | 29 |
| finance | 5 |
| game-development | 20 |
| marketing | 30 |
| paid-media | 7 |
| product | 5 |
| project-management | 6 |
| sales | 8 |
| spatial-computing | 6 |
| specialized | 41 |
| support | 6 |
| testing | 8 |

Common structure:

- `Your Identity & Memory`
- `Your Core Mission`
- `Critical Rules You Must Follow`
- `Your Workflow Process`
- `Your Technical Deliverables`
- `Learning & Memory`
- `Success Metrics`
- `Advanced Capabilities`

This structure is useful for Scentra because it can map cleanly into factory/custom agent templates, preflight checks, eval rubrics and marketplace metadata.

## Scripts Reviewed

Scripts were inspected as text only.

### `scripts/install.sh`

Purpose:

- Installs or copies agent templates into local AI-tool config folders such as Claude, Copilot, Gemini CLI, OpenCode, Cursor, Aider, Windsurf, OpenClaw, Qwen and Kimi.

Scentra decision:

- Do not run this script.
- It is for developer-machine tool installation, not SaaS runtime.
- It can write outside the repo into user home config directories.

### `scripts/convert.sh`

Purpose:

- Converts agent Markdown into integration formats under `integrations/<tool>`.

Scentra decision:

- Do not run it as part of Scentra.
- Use only as a design reference for a future Scentra template normalizer.

### `scripts/lint-agents.sh`

Purpose:

- Validates frontmatter and recommended sections.

Scentra decision:

- Useful as inspiration for a future import linter.
- Scentra needs its own stricter tenant-safety linter, including tool scopes, prompt-injection review, vertical risk, compliance flags, and one-AI-owner checks.

## Strategy Docs Reviewed

High-value strategy assets:

- `strategy/EXECUTIVE-BRIEF.md`
- `strategy/QUICKSTART.md`
- `strategy/nexus-strategy.md`
- `strategy/coordination/agent-activation-prompts.md`
- `strategy/coordination/handoff-templates.md`
- `strategy/playbooks/phase-0-discovery.md` through `phase-6-operate.md`
- `strategy/runbooks/scenario-startup-mvp.md`
- `strategy/runbooks/scenario-enterprise-feature.md`
- `strategy/runbooks/scenario-marketing-campaign.md`
- `strategy/runbooks/scenario-incident-response.md`

Best reusable concept:

- NEXUS-style coordination: specialized agents, quality gates, handoff templates, Dev-QA loops, evidence-first checks, scenario runbooks and explicit escalation paths.

Scentra fit:

- Strong fit for Agent OS, Workflow Composer, Advisor, AI Operations Center, AI Control Center, marketplace templates and enterprise governance.

## High-Value Assets For Scentra

### 1. Agent Template Schema

The repo's frontmatter and repeated sections can seed a Scentra agent-template schema:

- `source_repo`
- `source_path`
- `source_license`
- `source_attribution`
- `template_name`
- `category`
- `industry`
- `role`
- `mission`
- `critical_rules`
- `workflow_steps`
- `deliverables`
- `success_metrics`
- `allowed_tools`
- `disallowed_tools`
- `memory_policy`
- `approval_policy`
- `risk_level`
- `premium_pack`
- `draft_status`

### 2. Agent Marketplace Seed Content

Good candidates for disabled draft import after review:

- Customer Service
- Sales Outreach
- Sales Pipeline Analyst
- Sales Outbound Strategist
- Paid Social Strategist
- PPC Campaign Strategist
- Tracking & Measurement Specialist
- Content Creator
- Instagram Curator
- Social Media Strategist
- Healthcare Customer Service
- Hospitality Guest Services
- Real Estate Buyer & Seller
- Legal Client Intake
- Retail Customer Returns

These should enter Scentra only as disabled marketplace drafts until reviewed in Admin.

### 3. Internal QA And Governance Agents

Useful for internal Scentra quality workflows:

- Agents Orchestrator
- Automation Governance Architect
- Agentic Identity & Trust Architect
- Workflow Architect
- Evidence Collector
- Reality Checker
- API Tester
- Performance Benchmarker
- Security Engineer
- SRE
- Incident Response Commander
- Database Optimizer
- Technical Writer

These are most useful as internal admin/eval agents, not tenant-facing assistants.

### 4. Vertical Packs

Relevant vertical material:

- healthcare support
- hospitality
- real estate
- legal intake/review
- retail returns
- sales outreach
- paid media
- marketing operations

Scentra should map these to Phase 10 vertical packs and Phase 11 vertical intelligence, but must rewrite high-risk domains for compliance and tenant boundaries.

### 5. Workflow Composer Inputs

The NEXUS playbooks and handoff templates are a better fit for Workflow Composer than for raw chat prompts.

They can become:

- workflow blueprints
- approval gates
- handoff contracts
- QA/eval states
- retry/escalation rules
- scenario runbooks
- advisor recommendation templates

## What Not To Import First

Defer or skip initially:

- game-development agents
- spatial-computing agents
- academic/research-only agents
- Solidity or highly technical engineering agents not tied to Scentra SaaS operations
- region-specific or channel-specific agents that do not match Scentra's markets
- any agent whose frontmatter declares broad filesystem, shell, web or write permissions
- any integration output generated for other AI tools

Reason:

- These dilute the marketplace, add review cost and increase safety risk before the core SaaS business packs are stable.

## Required Safety Rules For Integration

Non-negotiable:

- Do not execute external scripts.
- Do not install global agents into Codex/Claude/Gemini/Kimi tool folders.
- Do not import external prompts as active agents.
- Do not map external `tools` fields directly to Scentra tools.
- Do not grant Bash, file-write, browser, external fetch or messaging actions from imported templates.
- Do not bypass Scentra preflight, budget, memory limits, tool approvals or feature gating.
- Do not bypass the one-AI-owner conversation rule.
- Do not let imported agents send WhatsApp/Instagram/Facebook messages without existing Scentra approvals, quiet hours, Meta template checks and tenant permissions.
- Keep all imported content tenant-scoped, versioned, disabled by default and premium-gated.

## Phase 15.1B/15.1C Implementation Status

Status: complete as offline intake artifacts. No runtime import was performed.

Implemented:

- `saas-version/scripts/phase15-agent-template-intake.mjs`
- `docs/phase15_1/agent_template_inventory.json`
- `docs/phase15_1/agent_template_inventory.csv`
- `docs/phase15_1/agent_template_drafts.json`
- `docs/phase15_1/agent_template_risk_report.md`

Results:

- 184 agent templates normalized.
- 16 strategy/playbook docs counted.
- 29 disabled draft candidates generated.
- Runtime import: none.
- Database writes: none.
- External scripts executed: none.

The generated drafts are metadata only. They are not active marketplace rows, active agents, tenant-visible products or executable plugin code.

## Phase 15.2/15.3 Implementation Status

Status: complete as offline operational artifacts. No runtime import was performed.

Implemented:

- `saas-version/scripts/phase15-nexus-eval-harness.mjs`
- `docs/phase15_1/nexus_handoff_contracts.json`
- `docs/phase15_1/nexus_playbooks.json`
- `docs/phase15_1/agent_eval_rubrics.json`
- `docs/phase15_1/agent_eval_results.json`
- `docs/phase15_1/phase15_2_15_3_report.md`

Results:

- 7 NEXUS handoff contracts generated.
- 7 NEXUS phase playbook blueprints generated.
- 4 scenario runbook blueprints generated.
- 6 Scentra eval rubrics generated.
- 29 disabled draft templates evaluated.
- 29 drafts are structurally `admin_review_ready`.
- 0 drafts are active.
- Runtime import: none.
- Database writes: none.
- Tenant exposure: none.

The generated playbooks and runbooks are future Workflow Composer blueprints, not active automations. Eval results are advisory until Admin review and certification workflows exist.

## Recommended Phase 15.1 Plan

### 15.1A Full Repo Audit And Inventory

Status: complete at documentation level.

Deliverables:

- local repo inventory
- license/security/script review
- candidate category mapping
- high-risk areas
- no runtime import

### 15.1B Template Normalizer And Risk Classifier

Status: complete as offline script and generated artifacts.

Deliverables:

- read-only parser for agent Markdown
- normalized Scentra template JSON
- frontmatter validation
- source attribution fields
- risk classifier
- tool-permission classifier
- compliance-domain classifier
- Spanish/admin review summary

### 15.1C Disabled Draft Marketplace Import

Status: complete as disabled draft metadata artifacts only.

Deliverables:

- generate 29 reviewed-priority templates as disabled draft metadata
- Admin-only review queue
- versioned source metadata
- no tenant activation by default
- no tool execution

Not done:

- no Postgres insert into `saas_ai_marketplace_items`
- no tenant Admin UI exposure
- no active agent creation
- no external prompt execution

### 15.2 NEXUS Playbooks And Handoff Model

Status: complete as offline generated artifacts.

Purpose:

- Convert strategy/playbook docs into Scentra Agent OS and Workflow Composer blueprints.

Deliverables:

- workflow blueprint schema
- handoff contract schema
- QA PASS/FAIL states
- escalation states
- evidence requirements
- retry limits

Implemented artifacts:

- `nexus_handoff_contracts.json`
- `nexus_playbooks.json`
- `phase15_2_15_3_report.md`

### 15.3 Agent Eval And QA Harness

Status: complete as offline generated artifacts.

Purpose:

- Use testing/reality/evidence agents as eval rubrics, not as autonomous code executors.

Deliverables:

- agent preflight eval extensions
- prompt quality checks
- hallucination/evidence checks
- tool-risk checks
- vertical compliance checks
- marketplace certification workflow

Implemented artifacts:

- `agent_eval_rubrics.json`
- `agent_eval_results.json`
- `phase15_2_15_3_report.md`

## Reordered Roadmap After Full Repo Analysis

The repo's biggest value is not real-time infrastructure. It is agent taxonomy, workflow orchestration, QA/eval, governance and marketplace content. Therefore Scentra should insert Phase 15.1/15.2/15.3 before continuing into the larger future roadmap.

Recommended sequence:

1. Phase 15.1A: Full Repo Audit And Inventory.
2. Phase 15.1B: Template Normalizer And Risk Classifier.
3. Phase 15.1C: Disabled Draft Marketplace Import.
4. Phase 15.2: NEXUS Playbooks And Handoff Model. Status: offline artifacts complete.
5. Phase 15.3: Agent Eval And QA Harness. Status: offline artifacts complete.
6. Phase 18: AI Workflow Composer. Status: implemented control-plane.
7. Phase 22: AI Trust, Compliance & Governance Enterprise. Status: implemented control-plane.
8. Phase 16: AI Real-Time Intelligence Layer. Status: implemented control-plane.
9. Phase 24: Voice & Multimodal Intelligence. Status: implemented through 24.8.
10. Phase 19: Autonomous Revenue Engine. Status: implemented control-plane.
11. Phase 20: AI Enterprise Memory Network. Status: implemented control-plane.
12. Phase 17: Federated Learning & Global Intelligence.
13. Phase 21: Scentra AI Cloud Platform.
14. Phase 23: AI Marketplace Economy.
15. Phase 25: Enterprise Decision Intelligence.

Reasoning:

- Agent templates need safe intake before marketplace work.
- NEXUS handoffs and evals should shape Workflow Composer before tenants build complex automations.
- Governance should precede higher autonomy and marketplace economy.
- Real-time intelligence is now available as a safe control-plane; future work should validate capacity before adding broker infrastructure.

## Open Inputs Still Needed

For commercial-grade intake, still obtain or confirm:

- upstream Git URL
- exact commit hash or release tag
- whether this local folder is modified from upstream
- whether product attribution is desired even if MIT does not require prominent UI attribution
- priority categories for first marketplace pack
- confirmation that the folder contains no private prompts, secrets, customer data or proprietary internal content

## Decision

Use `external-repos/agency-agents/` as a reviewed source of agent-template, workflow, handoff, eval and governance ideas.

Do not treat it as:

- an executable runtime
- a plugin sandbox
- a production queue system
- a secure tool framework
- a replacement for Scentra Agent OS
- a source of automatically trusted prompts

Phase 15.1/15.2/15.3 remain intake/governance phases until the user explicitly authorizes DB import, Admin review UI/API or tenant-facing activation.
