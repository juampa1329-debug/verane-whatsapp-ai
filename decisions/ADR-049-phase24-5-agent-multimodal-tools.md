# ADR-049: Phase 24.5 Agent Multimodal Tools

## Status

Accepted.

## Context

Scentra already has:

- Phase 24.2 Voice Intelligence for existing tenant audio messages.
- Phase 24.3 Vision Intelligence for existing tenant image/document messages.
- Phase 24.4 Web/Image Search Intelligence with source approval.
- Phase 11 Agent OS tool-run traces in `saas_ai_agent_tool_runs`.
- Phase 8 single-owner conversation assignment for AI agents.

Agents need access to multimodal context without creating a second media runtime, bypassing approvals, or adding customer-facing side effects.

## Decision

Implement Agent Multimodal Tools as a thin, tenant-scoped orchestration layer in `app_saas/agents/multimodal_tools.py`.

The layer:

- exposes `media.voice_analyze`, `media.vision_analyze`, and `media.web_image_search`;
- requires the selected agent to declare the tool in `tools_json`;
- resolves feature access through Intelligence gates;
- records every run in `saas_ai_agent_tool_runs`;
- delegates execution to existing media/search endpoints;
- injects only compact completed outputs into assigned-agent prompts;
- injects external search sources only when the source result is approved and not blocked.

Add migration `063_saas_agent_multimodal_tools_phase24.sql` for default premium flags and a filtered Agent OS tool-run index.

## Consequences

- No new dependency, agent framework, broker, ML service or media runtime is required.
- Agent execution remains observable through Agent OS traces.
- Voice/vision/search provider behavior remains centralized in the media domain.
- Search result approval remains the mandatory human boundary.
- Customer-facing media/reference send remains future work.

## Safety Rules

- Do not log raw media bytes, base64 payloads, decrypted secrets or secret-bearing URLs.
- Do not send customer messages from agent multimodal tools.
- Do not mutate CRM, create tasks, launch campaigns, execute workflows, assign agents or train models from tool output.
- Do not use pending, rejected or blocked search results in agent prompts.

## Validation

- Backend `py_compile` passed for touched modules.
- Tenant frontend build passed.
- Docker Compose config passed.
- SQL BOM/UTF-8 scans passed.
- Active Docker API/worker rebuild applied/skipped through migration `063`.
- API health, Swagger, OpenAPI endpoint checks and DB migration/feature-flag checks passed.
- Authenticated tenant smoke created a custom agent, executed a search tool, received a controlled missing-credential failure and confirmed a failed tool run persisted.
- Clean isolated PostgreSQL bootstrap applied migrations `001` through `063`.
- Browser smoke confirmed the Agent OS multimodal tool UI with no console errors.
