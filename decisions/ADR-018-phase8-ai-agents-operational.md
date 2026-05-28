# ADR-018: Phase 8 AI Agents Operational Governance

Date: 2026-05-25
Scope: SaaS only

## Status

Accepted.

## Context

Phase 8 required AI agents to be premium, measurable, governable, memory-aware, and safe in the Inbox. The code already had agent registry, plan limits, memory vault, collective memory, prompt versions, action drafts, orchestration, runtime metrics, and a preflight endpoint.

Gaps detected in code:

- Preflight existed but activation was not a hard gate.
- Budget was visible but not enforced before provider execution.
- Conversations did not persist a single AI owner.
- Inbox could not filter by responsible AI agent.
- Custom agents and fillable system prompts were not complete as a tenant workflow.
- Collective memory existed but conversation AI did not use it in assigned-agent prompts.

## Decision

- Add forward migration `043_saas_ai_agents_phase8_operational.sql`.
- Persist custom-agent metadata, system prompt template/variables/rendered prompt, last preflight, preflight eval records, and conversation AI ownership.
- Gate agent activation through preflight readiness.
- Enforce budget hard stop before conversation AI provider execution.
- Treat `assigned_ai_agent_id` as the conversation AI owner; once set, general AI does not answer that conversation.
- Allow manual assignment/release from Inbox and automatic assignment from router/orchestrator.
- Preserve agent memory by default when archiving/deleting agents; leave later restore/export/import/delete to the memory vault.
- Inject tenant collective memory into assigned-agent runtime prompts.
- Add Phase 15 as a future research/integration phase for an external specialized-agents repository.

## Consequences

- The platform prevents double-AI replies by design.
- Operators must release or reassign a conversation if its assigned agent becomes inactive; silent general-AI fallback is intentionally blocked.
- Factory and custom agents now share one prompt-template model.
- Preflight/eval data becomes auditable per agent.
- Clean Docker/PostgreSQL bootstrap through migration `043` must be rerun when Docker Desktop is available.

## Key Files

- `saas-version/migrations/043_saas_ai_agents_phase8_operational.sql`
- `saas-version/backend/app_saas/agents/service.py`
- `saas-version/backend/app_saas/agents/orchestrator.py`
- `saas-version/backend/app_saas/ai_agent/service.py`
- `saas-version/backend/app_saas/crm/router.py`
- `saas-version/frontend/src/AiAgentsPanel.jsx`
- `saas-version/frontend/src/App.jsx`
