# ADR-063: Phase 24 Inbox Multimodal Drift Repair

Date: 2026-05-28

## Status

Accepted.

## Context

Production browser logs showed 500s and feature-gate 403s after entering the tenant app and opening Inbox conversations.

Code inspection showed that opening a conversation always reads Phase 24 multimodal side panels:

- `GET /saas/v1/media/search/runs?conversation_id=...&limit=8`
- `GET /saas/v1/agents/multimodal-memory/events?conversation_id=...&limit=24`

These are read paths, but they depend on Phase 24 tables and dependency tables. Older production databases can have migrations marked applied or partially applied while some tables/columns are still absent.

## Decision

Add a forward, idempotent repair migration:

- `072_saas_phase24_inbox_multimodal_drift_repair.sql`

The migration repairs only schema drift for Phase 24 read/runtime tables:

- `saas_voice_intelligence_analyses`
- `saas_vision_intelligence_analyses`
- `saas_web_search_intelligence_runs`
- `saas_web_search_intelligence_results`
- `saas_multimodal_memory_events`
- dependency tables used by multimodal memory: `saas_intelligence_events`, `saas_knowledge_sources`, `saas_ai_agent_collective_memory`

Runtime `ensure_*` helpers now add missing columns for partial Phase 24 tables.

Schema readiness now checks these tables/columns because the current frontend calls the read endpoints during normal Inbox use.

`GET /saas/v1/media/search/runs` returns an empty disabled-access model when Web/Image Search is not enabled, so tenants without that premium feature do not see normal Inbox boot as a 403 failure. Provider execution endpoints remain premium-gated.

## Consequences

- A production DB with Phase 24 drift can be repaired without data deletion.
- Future deployments fail readiness when Phase 24 runtime-critical schema is missing.
- Web/Image Search history loading is no longer noisy for tenants without the feature enabled.
- Meta media proxy 403 behavior is unchanged; those errors still indicate Meta token, permission, WABA/asset, or media-expiration problems.

## Non-Goals

- No Meta runtime changes.
- No provider credential changes.
- No CRM mutation or outbound send changes.
- No agent ownership changes.
- No billing or premium execution bypass.
