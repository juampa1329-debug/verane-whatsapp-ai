# SAFE_MODIFICATION_GUIDE

Scope: SaaS only.

## Universal Workflow

1. Read `docs/AGENT_RULES.md`.
2. Identify the SaaS domain.
3. Inspect router, schema, service/helper, migration, and frontend/admin consumers.
4. Search references with `rg`.
5. Make minimal change.
6. Run targeted checks when feasible.
7. Update memory/docs.

## Backend Change Checklist

- Router: `saas-version/backend/app_saas/<domain>/router.py`
- Schemas: `saas-version/backend/app_saas/<domain>/schemas.py` when present
- Services/helpers: same domain plus `shared/`, `billing/`, `workers/` if relevant
- DB: `saas-version/migrations` and runtime SQL references
- Frontend consumers: `saas-version/frontend/src`, `saas-version/admin-frontend/src`
- Auth: `shared/security.py`, role helpers, platform admin split

## Frontend Change Checklist

- Check `VITE_API_BASE` behavior.
- Check token localStorage keys.
- Check backend route path and response shape.
- Keep client app and admin app separated.
- Do not copy patterns from root `frontend/`.

## DB Change Checklist

- Add a new migration when schema changes.
- Search for table/column references in backend and frontends.
- Preserve tenant_id and RLS expectations.
- If the new table/column is required by auth, registration, app boot, Inbox, Admin boot, billing lifecycle, workers or dashboards, update `saas-version/backend/app_saas/shared/schema_readiness.py`.
- Update docs and diagrams.

## Integration Change Checklist

- Inspect encrypted credential storage.
- Inspect webhook verification/signature code.
- Inspect worker retry/status paths.
- Inspect provider-specific env vars.
- Preserve admin diagnostics if present.

## Observability/Worker Change Checklist

- Inspect `observability/service.py`, `admin/router.py`, `workers/runner.py`, `workers/ingest.py`, and the target processor.
- Preserve worker heartbeat writes for embedded and standalone workers.
- Preserve `FOR UPDATE SKIP LOCKED` and idempotent status transitions.
- Use savepoints or separate transactions when optional side effects can fail inside a larger queue transaction.
- Keep dead-letter retry source updates compatible with admin operation processors.
- Preserve/propagate `correlation_id` when touching request, webhook, queue, or dead-letter code.

## Billing/Limit Change Checklist

- Inspect `billing/service.py`, `billing/limits.py`, router endpoints, migrations, admin routes, and frontend billing UI.
- Preserve trial/plan code behavior unless explicitly changing monetization.
- Preserve provider signature verification before any webhook mutation.
- Preserve worker lifecycle idempotency, advisory locking, and write-block behavior for `past_due`/`suspended` tenants.
- If invoice fields or PDF output change, update tenant/admin download endpoints and tracking docs.

## AI/Agent Change Checklist

- Inspect `api_credentials`, `ai_gateway`, `ai_agent`, `agents`, `advisor`, and `knowledge` interactions.
- Do not hardcode provider keys.
- For multimodal gateway work, inspect provider adapters and never persist raw `data_base64`, media bytes, customer media content or provider URLs that contain secrets.
- Keep text-only gateway calls compatible when adding attachment support.
- For Voice Intelligence work, inspect `media/router.py`, `ai_gateway/service.py`, provider adapters, `billing/limits.py`, `intelligence/catalog.py`, migration `060`, tenant `App.jsx`, and `architecture/VOICE_MULTIMODAL_INTELLIGENCE.md`.
- Preserve the current safety boundary: audio analysis may write `saas_voice_intelligence_analyses` and message payload summaries, but must not auto-send messages, mutate CRM, execute tools, launch campaigns, or train models without a separate approved design.
- Keep raw audio/base64 out of logs, DB rows, AI run metadata and frontend state.
- Do not enable non-Google audio providers until their adapter/model support is tested with real credentials.
- For Vision Intelligence work, inspect `media/router.py`, AI Gateway adapters, `billing/limits.py`, `intelligence/catalog.py`, migration `061`, tenant `App.jsx`, Admin plan feature defaults, and `architecture/VOICE_MULTIMODAL_INTELLIGENCE.md`.
- Preserve the current safety boundary: visual/document analysis may write `saas_vision_intelligence_analyses` and message payload summaries, but must not search the web, fetch arbitrary URLs, send media to customers, mutate CRM, execute tools, launch campaigns, assign agents, or train models without a separate approved design.
- Keep raw image/document bytes and base64 out of logs, DB rows, AI run metadata and durable frontend state.
- For Web/Image Search Intelligence work, inspect `media/router.py`, `api_credentials`, `billing/limits.py`, `intelligence/catalog.py`, migration `062`, tenant `App.jsx`, and `architecture/VOICE_MULTIMODAL_INTELLIGENCE.md`.
- Preserve the current safety boundary: external search may write `saas_web_search_intelligence_runs` and `saas_web_search_intelligence_results`, but must not auto-send links/images, crawl result pages, mutate CRM, execute tools, launch campaigns, assign agents, or train models without a separate approved design.
- Keep search provider credentials encrypted at rest and decrypted only at the provider-call boundary; do not add global search provider env keys unless explicitly requested.
- Keep human approval mandatory before any search/image result can become customer-facing.
- For Multimodal Memory work, inspect `agents/multimodal_memory.py`, `agents/multimodal_tools.py`, `media/router.py`, `ai_agent/service.py`, `intelligence/service.py`, migration `064`, tenant `AiAgentsPanel.jsx`, and `architecture/VOICE_MULTIMODAL_INTELLIGENCE.md`.
- Preserve the current safety boundary: multimodal memory may write sanitized `saas_multimodal_memory_events`, conversation feature values, Knowledge/RAG sources and collective memory only through explicit materialization; it must not store raw media/base64, auto-train models, auto-send replies, mutate CRM, launch campaigns, execute workflows or assign agents.
- Keep `eligible_for_training` gated by `multimodal_training_events`, `ml_predictions` or `ai_premium`; memory capture alone is not training authorization.
- For Phase 24.8 Admin/Premium Gating work, inspect `intelligence/premium.py`, `intelligence/service.py`, `admin/router.py`, `ai_gateway/service.py`, `media/router.py`, migration `065`, Admin `AdminApp.jsx`, and `architecture/VOICE_MULTIMODAL_INTELLIGENCE.md`.
- Preserve the current safety boundary: provider policies can block providers and enforce request/cost limits, but must not expose decrypted secrets, auto-charge billing, train models, mutate Meta/CRM/campaigns/workflows, or enable automatic AI/agent customer sends.
- Keep provider policy defaults compatibility-safe unless the user explicitly requests a breaking rollout.
- For Phase 24.9/24.10 Observability/Safe Rollout work, inspect `intelligence/multimodal_observability.py`, `intelligence/router.py`, `intelligence/schemas.py`, `media/router.py`, `billing/limits.py`, `intelligence/catalog.py`, migration `067`, tenant `IntelligencePanel.jsx`, Admin `AdminApp.jsx`, and `architecture/VOICE_MULTIMODAL_INTELLIGENCE.md`.
- Preserve default-off rollout behavior: do not add implicit blocking or canary behavior without feature access plus an explicit enabled tenant policy.
- Observability snapshots must remain aggregate/safe metadata only; never store raw media/base64, decrypted provider secrets, full provider responses or full customer conversation content there.
- Preserve memory/governance/limit behavior.
- Preserve preflight-gated activation and runtime budget hard-stop enforcement.
- Preserve one-AI-owner behavior for conversations: manual assignment, auto-router/orchestrator assignment, release, and no silent general-AI fallback for inactive assigned agents.
- Preserve separate agent memory vault and tenant collective memory; do not delete memories when archiving agents unless explicitly requested.

## Intelligence/Autonomous Ops Change Checklist

- Inspect `intelligence/router.py`, `intelligence/service.py`, `intelligence/operations.py`, `intelligence/network.py`, `intelligence/catalog.py`, `billing/limits.py`, `workers/intelligence.py`, migrations `046`-`054`, tenant `IntelligencePanel.jsx`, and Admin `AI Predictivo` consumers.
- Preserve premium/demo/full gating, quotas, tenant status checks and role gates.
- Preserve demo behavior for Autonomous Operations: no persisted auto-remediation and no low-risk auto-execute.
- Keep autonomous execution control-plane first unless the user explicitly approves real side effects with ADR, rollback and staging validation.
- Keep Enterprise AI Network aggregate-only: never expose raw messages, conversations, tenant names, private content or sensitive data in cross-tenant intelligence.
- Keep vertical playbooks/advisors as recommendations unless a future approved design adds executable automation with preflight, audit and rollback.
- For Phase 17 Federated Learning work, inspect `intelligence/federated.py`, `intelligence/router.py`, `intelligence/schemas.py`, `intelligence/catalog.py`, `billing/limits.py`, `workers/intelligence.py`, migration `068`, tenant `IntelligencePanel.jsx`, Admin feature defaults and `architecture/FEDERATED_LEARNING_GLOBAL_INTELLIGENCE.md`.
- Preserve opt-in, full-mode gating, minimum cohort thresholds and aggregate-only payloads; never add raw tenant content, tenant names, prompts, media/base64, provider secrets or private customer data to federated tables.
- Keep federated aggregation as candidate/global intelligence only; model promotion must stay in ModelOps with separate review and rollout.
- Use nested transactions for optional worker integrations so Intelligence/Agent OS/Autonomous Ops failures do not break CRM, Meta, billing, webhook, trigger or campaign runtime.
- Update `docs/SCENTRA_INTELLIGENCE_ENGINE.md`, architecture docs, status docs and memory after every Phase 11 change.

## Revenue And Enterprise Memory Change Checklist

- Inspect `intelligence/revenue.py`, `intelligence/memory_network.py`, `intelligence/router.py`, `intelligence/schemas.py`, `intelligence/catalog.py`, `billing/limits.py`, `workers/intelligence.py`, migration `066`, tenant `IntelligencePanel.jsx`, Admin feature defaults and architecture ADRs.
- Preserve premium/demo/full gating, quotas, tenant status checks and role gates.
- Keep revenue opportunity execution control-plane only unless the user explicitly approves real CRM/campaign/workflow/payment side effects with ADR, approval path, rollback and staging validation.
- Do not invent revenue or forecast values without a real tenant commerce/order/revenue source.
- Keep Enterprise Memory Network tenant-scoped and reviewable; only published nodes should be candidates for future prompt/RAG routing.
- Preserve Memory Network policy enforcement for allowed scopes, retention, customer-content review and privacy mode before sync/import/publish.
- Keep Memory Network import as `candidate` only and export as tenant-scoped summary/metadata/hash JSON.
- Keep Memory Network delete/export/import access logging intact.
- Do not store raw media/base64, decrypted secrets, full raw conversations or cross-tenant private content in memory graph nodes.
- Use nested transactions for worker revenue/memory integrations so optional failures do not break the rest of Intelligence processing.
- Update API docs, DB docs, worker flow, risks, ADRs and status PDF after Phase 19/20 changes.

## Reliability/Performance Change Checklist

- Inspect `reliability/service.py`, `workers/reliability.py`, `admin/router.py`, `admin/schemas.py`, `main.py`, `workers/runner.py`, migration `055`, and Admin `AdminApp.jsx`.
- Keep reliability admin-only unless the user explicitly requests tenant-facing reliability surfaces.
- Keep retention table names, timestamp columns and conditions allowlisted in backend code.
- Keep retention disabled and dry-run by default; do not add automatic destructive cleanup.
- Do not add provider throttling, campaign pausing, queue mutation or real backup/restore execution without explicit approval, ADR, rollback and staging validation.
- Update `architecture/PERFORMANCE_RELIABILITY_SCALE.md`, `architecture/WORKER_FLOW.md`, status docs, risks and memory after Phase 12 changes.

## Security/Compliance Change Checklist

- Inspect `auth/router.py`, `admin/router.py`, `shared/mfa.py`, `shared/security.py`, `shared/email.py`, `compliance/router.py`, migration `056`, tenant `App.jsx`, and Admin `AdminApp.jsx`.
- Preserve tenant filters on every compliance export/request.
- Do not log raw OTPs, reset tokens, decrypted secrets or exported private content.
- Do not add hard-delete privacy behavior without legal/retention approval, backup/export strategy, ADR and staging validation.
- Keep TOTP unsupported until a separate authenticator-app design is approved.
- Production MFA requires SMTP; local dev OTP output must stay local-only.

## AI Trust/Governance Change Checklist

- Inspect `trust_center/service.py`, `trust_center/router.py`, `trust_center/schemas.py`, `intelligence/service.py`, `billing/limits.py`, migration `058`, tenant `TrustCenterPanel.jsx`, and Admin `AdminApp.jsx`.
- Preserve tenant isolation on policies, risks, model cards, incidents, reports and audits.
- Keep demo/full feature gates intact; read previews may use demo mode, mutations require full access.
- Do not turn governance records into automatic runtime enforcement without explicit approval, ADR, rollback and staging evidence.
- Do not present generated reports as legal certification.
- Update `architecture/AI_TRUST_COMPLIANCE_GOVERNANCE.md`, status docs, risks and memory after Phase 22 changes.

## Real-Time Intelligence Change Checklist

- Inspect `intelligence/realtime.py`, `intelligence/router.py`, `intelligence/schemas.py`, `intelligence/service.py`, `intelligence/catalog.py`, `billing/limits.py`, migration `059`, tenant `IntelligencePanel.jsx`, Admin `AdminApp.jsx`, and `architecture/REALTIME_INTELLIGENCE_LAYER.md`.
- Preserve tenant filters and platform-admin separation on every realtime query.
- Keep event payload redaction before returning realtime events to tenant UI.
- Keep realtime feature gates, demo/full mode and usage limits intact.
- Do not make realtime alerts executable without an approved ADR, human approval path, rollback and staging smoke.
- Do not add Kafka/NATS/Redis Streams/WebSocket infrastructure without explicit user approval and a capacity/rollback plan.
- Update status docs, API docs, DB docs, architecture and memory after Phase 16 changes.

## Verticalization Change Checklist

- Inspect `verticals/catalog.py`, `verticals/service.py`, `verticals/router.py`, tenant/admin/auth consumers, and migration `045_saas_verticalization_phase10.sql`.
- Keep pack application idempotent and tenant scoped.
- Do not auto-activate trigger or flow resources created from packs.
- Do not auto-create recommended agents unless the caller explicitly requests it.
- Verify CRM, campaign, and agent table compatibility before changing pack resource shapes.

## Knowledge/RAG Change Checklist

- Inspect `knowledge/router.py`, `ai_agent/service.py`, `036_saas_knowledge_rag_phase8.sql`, `041_saas_knowledge_rag_phase6_operational.sql`, and the client settings UI.
- Preserve tenant filters on sources, chunks, retrieval logs, and evaluations.
- Keep URL crawling public-only unless an explicit SSRF-reviewed allowlist/proxy is designed.
- Reindex sources after changing chunking, parser, vector, or scoring logic.
