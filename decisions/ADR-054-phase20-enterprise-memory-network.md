# ADR-054 - Phase 20 AI Enterprise Memory Network

## Status

Accepted.

## Context

Scentra already has agent memory, collective memory, Knowledge/RAG, multimodal memory events and Enterprise AI Network. Phase 20 must connect useful organizational memory without leaking tenant-private content or allowing unreviewed customer content to drive agents.

## Decision

Implement AI Enterprise Memory Network as a tenant-scoped memory graph under `/saas/v1/intelligence/memory-network/*`.

The network:

- syncs candidates from collective memory, Knowledge sources, approved/safe multimodal memory events and vertical insights
- stores bounded summaries, source metadata, content hashes, quality/confidence scores and graph edges
- keeps memory review explicit through publish/archive/reject status
- exposes policy enforcement for privacy mode, retention, allowed scopes, customer-content review and cross-agent retrieval
- supports audited tenant export, sanitized import-as-candidate and tenant-scoped node delete
- supports cross-agent routing only inside the same tenant
- records sync runs, source counts and Intelligence events

## Safety Boundaries

- No raw media/base64 is stored.
- No cross-tenant raw content sharing.
- Customer-content nodes remain tenant-private and reviewable.
- No automatic RAG publication outside tenant context.
- No agent prompt injection changes outside existing approved context paths.
- Import never creates published nodes automatically.
- Export is scoped to the current tenant and contains summaries/metadata/hashes only.
- Delete removes only the tenant-owned memory node and DB-cascaded graph edges, with an access log and Intelligence event.

## Consequences

Phase 20 is operational as a governance and retrieval substrate with explicit lifecycle controls. Future runtime prompt routing can consume published memory nodes only after a dedicated prompt-context ADR and acceptance.

## Validation

Accepted with active Docker migration `066`, OpenAPI checks, full-mode tenant smoke for memory sync/node publish, and clean isolated PostgreSQL bootstrap through `001-066`.
