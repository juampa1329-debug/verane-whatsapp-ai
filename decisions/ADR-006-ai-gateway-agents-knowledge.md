# ADR-006 AI Gateway, Agents, Advisor, And Knowledge Domains

Status: Detected in code.

## Context

SaaS includes tenant API credentials, AI gateway routing, AI agent settings, advisor workflows, multi-agent governance/orchestration, and knowledge/RAG.

## Decision

Keep AI capabilities modular across dedicated SaaS domains:

- `api_credentials`
- `ai_gateway`
- `ai_agent`
- `agents`
- `advisor`
- `knowledge`

## Consequences

- Provider credentials stay separated from provider routing/runs.
- Agent memory/governance/limits must be considered before changing AI behavior.
- Knowledge/RAG changes can affect advisor/agents and search.
- Do not hardcode provider keys or collapse these domains without explicit architecture approval.

## Evidence

- `saas-version/backend/app_saas/api_credentials`
- `saas-version/backend/app_saas/ai_gateway`
- `saas-version/backend/app_saas/ai_agent`
- `saas-version/backend/app_saas/agents`
- `saas-version/backend/app_saas/advisor`
- `saas-version/backend/app_saas/knowledge`

