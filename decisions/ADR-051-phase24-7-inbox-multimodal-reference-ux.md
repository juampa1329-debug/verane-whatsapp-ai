# ADR-051: Phase 24.7 Inbox Multimodal Reference UX

Date: 2026-05-28

## Status

Accepted.

## Context

Phase 24.4 introduced approval-first Web/Image Search results. Phase 24.6 introduced sanitized multimodal memory events. Operators now need a practical Inbox workflow that turns those approved references into useful customer responses without creating a second outbound path or allowing autonomous AI sends.

The existing CRM message endpoint already owns tenant validation, monthly message quota, outbound queue insertion, Meta dispatch processing, message status events and `message.sent` Intelligence capture.

## Decision

Implement Phase 24.7 as a human-operated Inbox UX plus a narrow media-domain preparation endpoint:

- Add `POST /saas/v1/media/search/results/{result_id}/reference`.
- Only prepare references from tenant-scoped, approved, non-blocked Web/Image Search results.
- Revalidate public URLs and optional conversation ownership before returning prepared text.
- Do not send from the media endpoint.
- Use the existing CRM `POST /saas/v1/conversations/{conversation_id}/messages` endpoint for actual customer delivery.
- Add `Panel de analisis Inbox` to the tenant Inbox side panel with voice, vision, multimodal memory and approved visual reference signals.
- Require a human click and browser confirmation for direct `Enviar`.

No database migration is required. The implementation reuses:

- `saas_web_search_intelligence_runs`
- `saas_web_search_intelligence_results`
- `saas_multimodal_memory_events`
- `saas_messages`
- `saas_outbound_messages`
- `saas_message_status_events`

## Consequences

- Approved visual references can be used from the Inbox without bypassing source approval.
- Customer sends preserve existing CRM/outbound/Meta behavior.
- The media domain remains advisory/preparation-only.
- Agents and workers still cannot auto-send external references.
- Production rollout still needs real approved-source samples, copyright/source policy, operator training and real Meta outbound smoke.

## Safety Boundaries

- Blocked or unapproved sources cannot be prepared.
- The backend does not crawl result pages.
- Raw media/base64 is not persisted.
- The feature does not mutate CRM records, launch campaigns, execute workflows, assign agents, change billing, change Meta runtime or train models.
- Any future automatic agent/customer send path requires a separate ADR and approval policy.
