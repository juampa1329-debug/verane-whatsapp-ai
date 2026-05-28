# ADR-045: Phase 24.1 Multimodal Gateway

Date: 2026-05-27

## Status

Accepted

## Context

Scentra already has an AI Gateway with tenant credentials, provider catalog, fallback routing and run history. Phase 24 needs voice and multimodal capabilities, but the current conversation runtime is text-first and must not destabilize WhatsApp, Instagram, CRM, workers, agents or billing.

The user also requested a cleaner tenant API settings UX where providers are added only when needed instead of showing every provider form by default.

## Decision

Implement 24.1 as a compatibility-first gateway foundation:

- Add `GatewayAttachment` and optional `attachments` to `GatewayRequest`.
- Add optional `attachments` to `generate_with_gateway`.
- Normalize internal attachment inputs into a bounded list.
- Send multimodal parts to Gemini through `inline_data` or `file_data`.
- Send image parts to OpenAI-compatible providers through `image_url` content when attachments are provided.
- Record only safe attachment metadata in `saas_ai_runs`.
- Add static catalog entries for `gemini-2.5-flash-lite` and `moonshot-v1-8k-vision-preview`.
- Mark Kimi as multimodal-capable in the provider catalog when a selected model supports it.
- Rework tenant Settings > APIs into expandable provider tiles while keeping saved credentials visible.

No new dependency, DB migration, runtime media fetch, web search, transcription, OCR, agent tool, customer media send, worker change or billing change was added.

## Consequences

Positive:

- Existing text-only AI calls remain compatible.
- Future voice/image/video phases can pass media summaries or inline attachments through the gateway.
- Run logs are safer because they do not persist raw media payloads.
- Tenant API settings are shorter and easier to operate.
- Provider/model discovery remains tenant-controlled through existing encrypted credentials.

Tradeoffs:

- Attachments are not yet connected to Inbox media ingestion.
- Audio transcription, OCR, web/image search and approval UX still require later Phase 24 subphases.
- OpenAI-compatible multimodal behavior depends on the selected provider/model actually supporting image parts.

## Safety Rules

- Do not log `data_base64`, raw media bytes or decrypted provider secrets.
- Do not auto-send web images or AI-selected references without human approval.
- Keep Gemini as the first safe multimodal adapter until other provider-specific payload formats are validated.
- Keep web search/image search behind a future feature gate, source/copyright metadata and approval workflow.
- Preserve one-AI-owner conversation rules when multimodal agents are later connected to Inbox.
