# ADR-047: Phase 24.3 Vision Intelligence

Status: accepted
Date: 2026-05-28
Scope: SaaS only, `saas-version/`

## Context

Phase 24.1 added the internal AI Gateway attachment contract and Phase 24.2 used it for explicit Inbox audio analysis. The next safe multimodal step is image/document understanding for media already present in tenant conversations.

## Decision

Implement Phase 24.3 as an explicit, premium-gated Media-domain endpoint:

- `POST /saas/v1/media/messages/{message_id}/vision/analyze`
- cache table `saas_vision_intelligence_analyses`
- compact mirror in `saas_messages.payload_json.vision_intelligence`
- feature flags `vision_intelligence`, `image_understanding`, `document_ocr`

The endpoint accepts only existing tenant messages with image/document/file media. It does not accept arbitrary external URLs.

Provider routing:

- Images can use Google/Gemini, OpenRouter or Kimi when the tenant credential/model supports vision, with Google fallback.
- Documents/OCR-style extraction use Google/Gemini in this phase.

## Safety Boundaries

- No web search or web image retrieval.
- No customer media sends.
- No CRM/task/ticket/campaign/workflow mutations.
- No agent tool execution or agent assignment changes.
- No worker/runtime Meta changes.
- No multimodal training.
- No raw media bytes or base64 persisted in analysis rows or AI run metadata.

## Consequences

Positive:

- Tenants can analyze customer images/documents from Inbox without leaving Scentra.
- Results are cached and visible in the same message context.
- The implementation reuses existing tenant auth, media loading, AI Gateway, feature gating and usage accounting.

Tradeoffs:

- Production acceptance still requires real provider credentials and real media samples.
- Document support is intentionally narrower than image support until non-Google adapter behavior is validated.
- Extracted text is sensitive customer content and must follow tenant isolation, retention and privacy policy.

