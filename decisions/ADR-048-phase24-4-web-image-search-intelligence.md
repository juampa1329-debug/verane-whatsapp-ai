# ADR-048: Phase 24.4 Web & Image Search Intelligence

Status: accepted
Date: 2026-05-28
Scope: SaaS only

## Context

Phase 24.1 added the internal multimodal attachment contract. Phase 24.2/24.3 added explicit audio and vision analysis for media that already belongs to a tenant conversation.

The next requirement is external web/image search that can support conversations and agents with sources, images and references. This has higher risk than local media analysis because it involves third-party search providers, arbitrary external URLs, copyright/source handling and possible customer-facing use.

## Decision

Implement Phase 24.4 as a premium-gated, tenant-scoped, approval-first advisory surface under the existing `media` domain:

- Store search runs in `saas_web_search_intelligence_runs`.
- Store normalized results in `saas_web_search_intelligence_results`.
- Add feature flags `web_search_intelligence`, `image_search_intelligence`, and `external_source_assist`, defaulting to `false`.
- Support encrypted tenant credentials for `tavily`, `brave_search`, and `serpapi` through the existing API Credentials system.
- Expose tenant endpoints:
  - `POST /saas/v1/media/search`
  - `GET /saas/v1/media/search/runs`
  - `POST /saas/v1/media/search/results/{result_id}/approval`
- Require role gates, feature gates, tenant conversation ownership checks, safe provider credentials, bounded limits and public URL safety checks.
- Keep all results as `pending` until a human approves or rejects them.
- Reject blocked/private/unsafe URLs automatically.

## Safety Boundaries

- No result is automatically sent to customers.
- No CRM, campaign, workflow, trigger, agent, billing, Meta or worker side effect is executed.
- No arbitrary result URL is fetched or crawled by the backend.
- External provider credentials are decrypted only at the provider-call boundary and are not logged.
- Search result URLs are screened for public HTTP(S) targets; localhost, private, loopback, link-local, internal and reserved network targets are blocked.
- Provider responses are normalized into short snippets/source metadata, not full-page crawls.

## Consequences

Positive:

- Tenants can research web/image references from the Inbox with auditable sources.
- Agents and operators get a future-safe substrate for external-source assistance without immediate autonomous execution.
- Provider choice is tenant-configurable without new dependencies or new environment variables.

Tradeoffs:

- Real external search quality depends on tenant provider credentials and provider quota.
- Copyright/licensing still requires human review before using images in customer replies.
- Search is advisory and approval-first, so it is intentionally not a fully autonomous media-send capability.

## Validation

- Backend compile passed for touched modules.
- Tenant and Admin frontend builds passed.
- Docker Compose config passed.
- Active Docker rebuild applied migration `062`.
- API health, Swagger `/docs`, OpenAPI route check and worker startup passed.
- Clean isolated PostgreSQL bootstrap applied migrations `001` through `062`.
- Authenticated tenant smoke confirmed run listing and safe `409` behavior when no provider credential is configured.

