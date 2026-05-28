# ADR-046: Phase 24.2 Voice Intelligence

Status: accepted

Date: 2026-05-28

Scope: SaaS only, `saas-version/`.

## Context

Phase 24.1 added a safe internal attachment contract to the AI Gateway but intentionally did not analyze Inbox media. The next valuable multimodal capability for Scentra is audio intelligence because WhatsApp/Instagram operations commonly include customer voice notes.

Scentra already has:

- tenant-scoped CRM conversations/messages.
- local media assets and WhatsApp media proxy helpers.
- AI Gateway provider routing and run logging.
- tenant encrypted AI credentials.
- Intelligence premium/demo gating and usage recording.

## Decision

Implement Phase 24.2 as an explicit user-triggered Voice Intelligence endpoint for existing tenant audio messages.

Backend:

- Add `saas_voice_intelligence_analyses`.
- Add feature flags `voice_intelligence`, `voice_transcription`, and `voice_sentiment_intent`.
- Expose `POST /saas/v1/media/messages/{message_id}/voice/analyze`.
- Load audio only from tenant-owned existing message media:
  - local `saas_media_assets`.
  - inbound WhatsApp media through existing Meta media helpers.
- Route real audio analysis through Google/Gemini via the AI Gateway attachment contract.
- Persist transcript, summary, sentiment, intent, urgency, language, confidence and safe metadata.
- Mirror a compact result into `saas_messages.payload_json.voice_intelligence`.

Frontend:

- Add Voice Intelligence provider selection to tenant Settings > IA.
- Show a Voice Intelligence card in Inbox audio bubbles.
- Allow analyze/reanalyze from the audio message.

## Safety Boundaries

- No automatic CRM mutation.
- No ticket/task creation.
- No campaign, trigger, workflow or remarketing execution.
- No outbound message send.
- No agent tool execution.
- No OCR, web search, web image retrieval or image sending.
- No model training.
- No raw audio/base64 persistence in analysis rows or AI run metadata.
- Non-Google providers are not treated as audio-capable until their adapter/model support is validated.

## Consequences

Positive:

- Tenants can extract searchable/visible meaning from audio without leaving Inbox.
- Analysis is cached to control provider cost.
- The first runtime multimodal feature reuses existing AI Gateway, credentials, quota and Intelligence gating.

Tradeoffs:

- Production acceptance requires real Gemini credentials and real audio samples.
- Transcripts and summaries are sensitive conversation derivatives and must follow tenant isolation and retention policy.
- Provider coverage is intentionally narrow until adapter-specific audio support is proven.

## Validation

- Backend targeted `py_compile` passed for touched modules.
- Tenant frontend build passed with existing large-bundle warning.
- Docker Compose config passed.
- API/worker rebuild applied/skipped migration `060`.
- Container backend compileall passed for touched backend domains.
- API health and Swagger returned OK.
- OpenAPI contains the new voice endpoint.
- PostgreSQL confirms `saas_voice_intelligence_analyses` and `voice_intelligence` plan flag.
