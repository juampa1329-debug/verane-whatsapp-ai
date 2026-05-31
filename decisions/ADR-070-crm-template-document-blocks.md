# ADR-070 CRM Template Document Blocks

## Status

Accepted.

## Context

CRM templates are used by triggers and remarketing flows to send sequence messages. The frontend already supported text, image, video and audio blocks, while the backend media domain and outbound dispatcher already supported tenant-owned `document`/`file` media.

Users need to send catalogs, PDFs and other documents from those CRM templates without creating a separate document runtime.

## Decision

CRM template sequences now support `document` blocks that reuse the existing `/saas/v1/media/upload` asset store and the existing WhatsApp outbound `document` dispatcher.

The trigger worker renders template blocks as typed outbound jobs:

- `text` -> text outbound.
- `image`/`video` -> media outbound with optional caption.
- `audio` -> audio outbound.
- `document`/`file` -> document outbound with optional filename and caption.

If a media block has no media id/link but has caption text, it falls back to text instead of silently dropping the template response.

## Consequences

- No new provider, dependency, migration or storage path is required.
- Triggers and remarketing can send PDF/catalog-style documents through the same quota, outbound, status and audit path used by other messages.
- Existing templates remain compatible because text/body fallback behavior is preserved.
- Per-block delay semantics remain unchanged by this ADR.
