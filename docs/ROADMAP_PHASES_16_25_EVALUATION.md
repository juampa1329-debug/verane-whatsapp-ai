# ROADMAP_PHASES_16_25_EVALUATION

Scope: SaaS only.

## Executive Recommendation

The phases are viable and strategically strong, but they should not all be treated as near-term implementation phases. The full local analysis of `external-repos/agency-agents/` shaped the safe path: Phase 18 provides a reviewed Workflow Composer control-plane, Phase 22 provides the AI governance/trust control-plane, Phase 16 provides a PostgreSQL-first realtime intelligence surface, Phase 19 now provides supervised revenue intelligence, and Phase 20 now provides tenant-scoped enterprise memory before broader marketplace/cloud/federated expansion.

Recommended order now, with Phase 18, Phase 22, Phase 16, Phase 24, Phase 19, Phase 20 and Phase 17 implemented:

1. Phase 21: Scentra AI Cloud Platform.
2. Phase 23: AI Marketplace Economy.
3. Phase 25: Enterprise Decision Intelligence.

Reason: the external repository's strongest value is agent taxonomy, NEXUS-style workflows, handoffs, QA/eval and governance. Those should shape Workflow Composer and enterprise controls before high-autonomy, marketplace economy or global/federated intelligence.

## Phase Evaluation

| Phase | Name | Viability | Priority | Recommendation |
| --- | --- | --- | --- | --- |
| 16 | AI Real-Time Intelligence Layer | High | Implemented control-plane | Implemented as PostgreSQL-first live intelligence with sanitized event feed, sessions/cursors, Admin overview, snapshots and bounded SSE. Broker infrastructure remains future scale work. |
| 17 | Federated Learning & Global Intelligence | Medium | Implemented control-plane | Implemented as opt-in, premium-gated, aggregate-only federated control-plane with tenant policies, update packages, rounds, aggregates and global signals. Production acceptance still needs cohort rehearsal, privacy/legal review and ModelOps promotion runbook. |
| 18 | AI Workflow Composer | High | Completed control-plane | Implemented with templates, graph editor, preflight, simulation, approvals, versions and `composer_only` activation. Runtime deployment still needs a future materialization design. |
| 19 | Autonomous Revenue Engine | High value / high risk | Implemented control-plane | Implemented as supervised revenue opportunities/forecasts/reports/playbooks with no automatic sends, payment calls, CRM mutation or campaign/workflow activation. Real customer revenue attribution still needs tenant commerce/order data. |
| 20 | AI Enterprise Memory Network | Medium-high | Implemented/hardened control-plane | Implemented as tenant-scoped memory graph with policy enforcement, sync/review/export/import/delete of bounded summaries from collective memory, Knowledge/RAG, multimodal events and vertical insights. Runtime prompt/RAG use should consume published nodes only after routing acceptance. |
| 21 | Scentra AI Cloud Platform | Medium | Later | Strategic platformization. Needs stable APIs, SDK, marketplace, billing and operations maturity. |
| 22 | AI Trust, Compliance & Governance Enterprise | Very high | Completed control-plane | Implemented with policies, risk assessments, model cards, incidents, reports, audits and premium gating. Legal certification and automatic enforcement remain out of scope. |
| 23 | AI Marketplace Economy | Medium-high | Later | Good business model, but requires sandbox, review, revenue share, abuse controls and legal terms. |
| 24 | Voice & Multimodal Intelligence | High | Implemented through 24.8 | Implemented for gateway attachments, audio, vision/docs, web/image search with approval, agent tools, multimodal memory, Inbox reference UX and Admin premium/provider gating. |
| 25 | Enterprise Decision Intelligence | High | Later | Endgame BI/advisor layer. Needs mature data warehouse, model trust, governance and executive workflows. |

## Suggested Roadmap Order

Recommended practical sequence after full local repo analysis:

1. Phase 15.1A: Full Repo Audit And Inventory. Status: documentation-level complete.
2. Phase 15.1B: Template Normalizer And Risk Classifier. Status: offline artifact complete.
3. Phase 15.1C: Disabled Draft Marketplace Import. Status: disabled draft metadata complete, no runtime import.
4. Phase 15.2: NEXUS Playbooks And Handoff Model. Status: offline artifact complete.
5. Phase 15.3: Agent Eval And QA Harness. Status: offline artifact complete.
6. Phase 18: AI Workflow Composer.
7. Phase 22: AI Trust, Compliance & Governance Enterprise. Status: implemented control-plane.
8. Phase 16: AI Real-Time Intelligence Layer. Status: implemented control-plane.
9. Phase 24: Voice & Multimodal Intelligence. Status: implemented through 24.8.
10. Phase 19: Autonomous Revenue Engine. Status: implemented control-plane.
11. Phase 20: AI Enterprise Memory Network. Status: implemented control-plane.
12. Phase 17: Federated Learning & Global Intelligence. Status: implemented control-plane.
13. Phase 21: Scentra AI Cloud Platform.
14. Phase 23: AI Marketplace Economy.
15. Phase 25: Enterprise Decision Intelligence.

## Phase 15.1B: Template Normalizer And Risk Classifier

Goal:

- Convert external Markdown agents into Scentra-safe normalized template previews without importing active agents.

Deliverables:

- Read-only parser. Done: `saas-version/scripts/phase15-agent-template-intake.mjs`.
- Scentra template JSON schema. Done: `docs/phase15_1/agent_template_inventory.json`.
- License/source metadata.
- Tool-permission classifier.
- Prompt-injection and unsafe-action checks.
- Vertical/compliance risk tags.
- Admin review summary. Done: `docs/phase15_1/agent_template_risk_report.md`.

Risks:

- Unsafe external `tools` declarations if mapped directly.
- Healthcare/legal/finance prompts need compliance rewriting.
- Upstream commit/tag is still unverified.

## Phase 15.1C: Disabled Draft Marketplace Import

Goal:

- Import only reviewed templates as disabled Admin-visible drafts.

Deliverables:

- 29 pilot template drafts generated as metadata.
- Source path/license/hash metadata.
- Disabled review-required state.
- No tenant activation by default.
- Premium-gated install intent only after future review.

Current boundary:

- Drafts exist in `docs/phase15_1/agent_template_drafts.json`.
- No database import was performed.
- No Admin UI exposure was added.

Risks:

- Brand mismatch and quality inconsistency.
- Imported prompts can overpromise capabilities unless preflight/evals block activation.

## Phase 15.2: NEXUS Playbooks And Handoff Model

Goal:

- Turn strategy/playbook/handoff docs into Scentra workflow blueprints.

Status:

- Complete as offline generated artifacts.

Deliverables:

- 7 handoff contracts generated in `docs/phase15_1/nexus_handoff_contracts.json`.
- 7 phase playbook blueprints and 4 scenario runbooks generated in `docs/phase15_1/nexus_playbooks.json`.
- QA PASS/FAIL, escalation, evidence and retry policies captured as draft contracts.
- Runtime import: none.
- Tenant exposure: none.

Risks:

- Workflow complexity can confuse tenants unless surfaced through progressive UX.
- These blueprints are not active automations until Phase 18 creates simulation/preflight/approval UX.

## Phase 15.3: Agent Eval And QA Harness

Goal:

- Convert testing/reality/evidence agents into eval rubrics for Scentra agents and workflows.

Status:

- Complete as offline generated artifacts.

Deliverables:

- 6 eval rubrics generated in `docs/phase15_1/agent_eval_rubrics.json`.
- 29 disabled drafts evaluated in `docs/phase15_1/agent_eval_results.json`.
- 29 drafts are structurally `admin_review_ready`.
- 0 drafts are active.
- All activation remains blocked pending human review.

Risks:

- Eval outputs are advisory until validated with real tenant examples.
- Future Admin certification must enforce these results before tenant install.

## Phase 16: AI Real-Time Intelligence Layer

Status:

- Implemented as Phase 16 control-plane.
- Added migration `059_saas_realtime_intelligence_phase16.sql`, tenant `/intelligence/realtime/*`, Admin `/admin/intelligence/realtime*`, tenant UI, Admin overview, advisory alerts, sessions/cursors and metric snapshots.
- Current transport is polling plus bounded SSE; no Kafka/NATS/Redis Streams/WebSockets were added.

Goal:

- Turn event, prediction and Advisor signals into live operational intelligence.

Deliverables:

- Real-time intelligence feed. Done through sanitized event feed.
- Inbox live predictive badges. Already covered by existing Phase 11 predictive UI; Phase 16 adds intelligence live feed rather than altering Inbox runtime.
- Advisor proactive push alerts. Implemented as advisory realtime alerts in Intelligence UI, not push notifications.
- Live queue/anomaly stream. Implemented from existing operation/trust/prediction signals.
- Real-time feature refresh for critical signals. Implemented as snapshots/read model over existing features/events, not new feature recompute runtime.
- Admin live operations dashboard. Done in Admin `AI Predictivo`.

Risks:

- WebSocket/SSE auth and tenant isolation.
- Event fanout scalability.
- Noise/alert fatigue.

## Phase 18: AI Workflow Composer

Goal:

- Allow tenants to compose AI-assisted workflows safely.

Deliverables:

- Visual workflow builder.
- AI-generated draft workflows.
- Simulation/preflight.
- Approval gates.
- Versioning/rollback.
- Templates by industry.

Risks:

- Unsafe automation if activation is too easy.
- Tool permissions must stay explicit.

## Phase 22: AI Trust, Compliance & Governance Enterprise

Goal:

- Make advanced AI safe enough for enterprise procurement.

Implemented control-plane:

- AI policy center.
- Policy attestation.
- Risk assessments.
- Model cards.
- Governance incidents.
- Compliance report snapshots.
- Governance audit trail.
- Tenant Trust AI panel.
- Admin Trust AI overview.

Still needed for production/commercial claims:

- Legal review of report wording and policy language.
- Tenant-specific policy acceptance.
- Retention/consent operating procedure.
- Broader tenant isolation regression suite.
- Automatic enforcement only after separate ADR and staging evidence.

Risks:

- Legal complexity.
- Must not overclaim compliance frameworks without review.

## Phase 24: Voice & Multimodal Intelligence

Goal:

- Understand audio, images, documents and rich media from omnichannel conversations.

Current status:

- Phase 24.1 is implemented as a gateway foundation.
- Phase 24.2 Voice Intelligence is implemented for explicit analysis of existing Inbox audio messages.
- Phase 24.3 Vision Intelligence is implemented for explicit analysis of existing Inbox image/document/file messages.
- Phase 24.4 Web/Image Search Intelligence is implemented for external search with source approval.
- Phase 24.5 Agent Multimodal Tools is implemented for agent-scoped contextual voice, vision and approved-source search.
- AI Gateway now accepts optional internal attachments and can pass multimodal parts to Gemini or image parts to OpenAI-compatible providers when future callers provide them.
- Tenant Settings > APIs now uses expandable provider tiles instead of showing every provider form by default.
- `POST /saas/v1/media/messages/{message_id}/voice/analyze` can transcribe, summarize, classify sentiment and detect intent from tenant audio messages through Google/Gemini.
- `POST /saas/v1/media/messages/{message_id}/vision/analyze` can describe images, extract text from supported documents, summarize media content and detect intent.
- `POST /saas/v1/media/search` can run approval-first web/image search with tenant search credentials.
- `POST /saas/v1/agents/{agent_id}/multimodal-tools/execute` can run read-only agent-scoped voice/vision/search tools.
- Customer media-send approvals and multimodal training are not active yet.

Deliverables:

- 24.1 Multimodal Gateway foundation. Completed.
- 24.2 Voice Intelligence: audio transcription, voice note summaries, sentiment and intent. Completed for Google/Gemini path.
- 24.3 Vision Intelligence: image/document classification, OCR-style extraction and Inbox analysis cards. Completed for existing tenant media.
- 24.4 Web/image search with source, copyright and human approval controls. Completed as approval-first source assistance.
- 24.5 Agent access to media/search summaries. Completed as read-only tool runs with approved-source prompt context.
- Multimodal CRM enrichment.

Risks:

- Cost, privacy and media retention.
- Provider reliability.

## Phase 19: Autonomous Revenue Engine

Goal:

- Convert insights into controlled revenue actions.

Deliverables:

- Revenue opportunity detection.
- Next-best-action execution drafts.
- Autonomous follow-up proposals.
- Offer/campaign recommendations.
- Revenue impact tracking.

Risks:

- Spam/compliance risk.
- Meta template policy.
- Needs human approvals and quiet hours.

## Phase 20: AI Enterprise Memory Network

Goal:

- Build governed memory across agents, customers, workflows, teams and verticals.

Deliverables:

- Memory graph.
- Memory lineage.
- Tenant-level memory policies.
- Export/delete/import controls.
- Cross-agent shared memory with permissions.

Risks:

- Privacy, retention and deletion complexity.

## Phase 17: Federated Learning & Global Intelligence

Status:

- Implemented as code-level control-plane.

Goal:

- Improve models using tenant-isolated or privacy-safe global intelligence.

Deliverables:

- Aggregate-only global features. Done through `saas_federated_learning_updates`, `saas_federated_learning_aggregates` and `saas_global_intelligence_signals`.
- Federated-learning feasibility prototype. Done as weighted aggregate package control-plane, not raw model-weight federation.
- Differential privacy strategy. Policy metadata exists; advanced DP math remains future work.
- Industry model routing. Done at round/signal level through `industry_code`.
- Consent and opt-out controls. Done through tenant policy `opt_in_enabled` and `auto_participation_enabled`.

Remaining acceptance:

- Active Docker/API/Swagger/worker smoke through migration `068`.
- Clean PostgreSQL bootstrap `001` through `068`.
- Multi-tenant cohort rehearsal with several opted-in tenants.
- Privacy/legal review of cross-tenant learning claims.
- ModelOps promotion runbook before production model selection from federated signals.

Risks:

- High legal/compliance complexity.
- Current implementation is aggregate/statistical federated intelligence, not advanced secure aggregation or raw model-weight federation.
- Real federated learning may be overkill before enough tenant volume exists.

## Phase 21: Scentra AI Cloud Platform

Goal:

- Expose Scentra AI capabilities as a platform.

Deliverables:

- Public/developer APIs.
- SDKs.
- Tenant app framework.
- Integration gateway.
- Developer docs and auth.

Risks:

- Requires mature security, rate limits, billing and support operations.

## Phase 23: AI Marketplace Economy

Goal:

- Monetize templates, agents, plugins and playbooks.

Deliverables:

- Marketplace listing/review workflow.
- Revenue share.
- Ratings/reviews.
- Plugin certification.
- Abuse monitoring.

Risks:

- Untrusted code and monetization disputes.
- Needs sandbox and legal terms.

## Phase 25: Enterprise Decision Intelligence

Goal:

- Convert Scentra into executive decision-support system.

Deliverables:

- Decision dashboards.
- Forecasts.
- Scenario simulation.
- Board-ready reports.
- KPI causality and recommendation impact tracking.

Risks:

- Needs trusted historical data and validated ML.

## Final View

The roadmap is viable if sequenced around safety:

- Normalize and classify external agent templates first. Done offline.
- Convert NEXUS playbooks into handoffs/evals before tenant-facing composition. Done offline.
- Build Workflow Composer on top of reviewed templates and handoff contracts.
- Strengthen trust/governance before high autonomy.
- Add real-time and multimodal once workflows and approvals are clear.
- Delay federated, marketplace economy and cloud platform until governance, sandboxing and model quality are mature.
