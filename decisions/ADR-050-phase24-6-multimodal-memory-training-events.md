# ADR-050: Phase 24.6 Multimodal Memory & Training Events

Status: Accepted

Date: 2026-05-28

Scope: SaaS only, `saas-version/`.

## Context

Phase 24.2, 24.3, 24.4 and 24.5 already produce useful multimodal outputs:

- Voice analysis rows.
- Vision/document analysis rows.
- Human-approved external source results.
- Completed agent multimodal tool traces.

Those outputs were useful for operators and agent prompts, but they were not normalized into a durable memory/training/RAG layer.

## Decision

Add a tenant-scoped table `saas_multimodal_memory_events` and a backend service `agents/multimodal_memory.py`.

The service captures sanitized signals from existing multimodal sources, deduplicates by replay key, emits Intelligence events, refreshes conversation feature values, and exposes operator-controlled materialization to Knowledge/RAG and collective agent memory.

Agent OS screens call several agent endpoints concurrently. Runtime agent table checks in `agents/service.py` are therefore serialized with a process lock and PostgreSQL advisory lock before running idempotent DDL, preventing `ALTER TABLE ... IF NOT EXISTS` deadlocks during active UI loads.

Feature gates:

- `multimodal_memory_events`: memory sync/list.
- `multimodal_training_events`: training-ready flags.
- `multimodal_rag_materialization`: Knowledge/RAG materialization.
- `multimodal_agent_memory`: agent collective-memory use.
- `ai_premium` can unlock full premium access under the existing Intelligence rules.

Training readiness remains separate from memory capture. A row may be stored as memory while `eligible_for_training=false` if the tenant does not have training access.

## Consequences

- Agents can use curated multimodal memory instead of scraping raw tool outputs.
- ML feature pipelines can consume explicit training-signal records later.
- RAG/Knowledge ingestion becomes operator-controlled and auditable.
- External source content still requires human approval before prompt/RAG use.
- Customer content from voice/vision requires explicit materialization approval.
- Concurrent Agent OS UI loads should no longer fail due to runtime table-check deadlocks.

## Non-Goals

- No automatic model training.
- No raw media/base64 persistence.
- No automatic customer replies or media sends.
- No CRM/task/ticket/campaign/workflow mutation.
- No Meta runtime, billing runtime or worker queue behavior change.
- No crawling of result URLs.

## Validation

Validation passed for this ADR:

- Backend compile/import.
- Tenant/Admin frontend builds.
- Docker Compose config.
- SQL BOM/UTF-8 scans.
- Active SaaS migration through `064`.
- Clean PostgreSQL bootstrap through `064`.
- API health and Swagger.
- OpenAPI endpoint checks.
- Authenticated sync/materialization smoke.
- Browser smoke for Agent OS memory UI after API rebuild.
- Recent API/worker log scan without new 500/deadlock/traceback patterns.
