# ADR-032: Phase 11 Multi-Agent Operating System

Date: 2026-05-27

## Status

Accepted.

## Context

Scentra already had AI agent registry/governance, custom agents, memory vault, collective memory, Advisor, Intelligence Engine, predictions, recommendations, and an orchestrator with jobs/locks/handoffs/conflicts. The requested next step was an enterprise multi-agent operating system without breaking WhatsApp, Instagram, CRM, triggers or existing AI ownership rules.

## Decision

Implement Agent OS as a control-plane layer on top of the existing agents/orchestrator/runtime rather than replacing them.

Added:

- `051_saas_multi_agent_operating_system_phase11.sql`.
- `app_saas/agents/operating_system.py`.
- Tenant endpoints under `/saas/v1/agents/os*`.
- Tool-run trace endpoints under `/saas/v1/agents/{agent_id}/tool-runs`.
- Intelligence worker sync from predictions/recommendations to orchestrator jobs.
- Tenant AI Agents UI `Agent OS` tab.

## Consequences

- Existing one-AI-owner conversation behavior is preserved.
- Event-driven enqueue is premium-gated and disabled by default.
- Demo mode can preview candidates without persistent orchestration side effects.
- Tool calls are approval-first and create Advisor action drafts by default.
- Agent OS adds observability and coordination tables without requiring Kafka, LangGraph, Qdrant runtime changes, or direct tool execution.

## Follow-Up

- Add authenticated tenant smoke for `/agents/os` with seeded predictions.
- Decide pricing/plan policy for `multi_agent_os`, `event_driven_agents`, and `agent_tool_tracing`.
- Expand safe tool execution only after per-tool approval, rollback, audit and tenant policy acceptance.
