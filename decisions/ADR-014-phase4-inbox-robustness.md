# ADR-014: Phase 4 Inbox Robustness

Date: 2026-05-25

## Status

Accepted

## Context

The SaaS client already had an operational Inbox in `saas-version/frontend/src/App.jsx` with DMs, social comments, CRM side panel, tasks, media composer, voice notes, emojis, product cards, takeover, and message status events. The backend CRM router already exposed tenant-scoped conversations, messages, status events, read/takeover, and customer patching.

The remaining Phase 4 risk was not missing schema, but operational robustness: local-only filtering over a limited conversation slice, fixed polling that could overlap, no explicit browser notification flow, and assignment visibility without an operator action in the Inbox.

## Decision

Close Phase 4 with minimal compatible hardening:

- Keep the Inbox in `frontend/src/App.jsx`; do not introduce a new realtime transport or new state library.
- Extend `GET /saas/v1/conversations` with optional `channel` and `queue` filters while preserving existing calls.
- Use robust polling in the client: no overlapping refreshes, visible sync state, filter/search refreshes, and visibility-aware backoff.
- Keep DMs and comments separated in UI and API usage.
- Add explicit browser notifications behind browser permission and keep in-app sound as a separate toggle.
- Add assign-to-me and release actions through the existing `PATCH /customers/{conversation_id}` contract.

## Consequences

- Phase 4 is code-complete without a DB migration or dependency change.
- High-volume inboxes can now filter server-side before client rendering.
- Realtime WebSocket/SSE remains a future optimization, not a Phase 4 blocker.
- Production acceptance still requires real Meta webhook traffic for delivered/read status confirmation.
- Clean Docker rerun remains pending until Docker Desktop engine is available on the host.
