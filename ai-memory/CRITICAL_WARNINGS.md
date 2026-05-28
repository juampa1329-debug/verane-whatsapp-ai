# CRITICAL_WARNINGS

Scope: SaaS only.

## Security

- Production must override `SAAS_JWT_SECRET`; compose has a local fallback.
- Treat `saas-version/keys/saasprivate.key` as sensitive until verified.
- Do not log decrypted provider credentials.
- `SAAS_SECRET_KEY` is the SaaS provider-credential encryption root. Do not rotate it casually, set it to a Meta token, or differ it between API/worker deployments after credentials exist; encrypted AI/TTS/search credentials become unreadable until the old key is restored or tenant credentials are re-saved.
- Do not bypass `get_current_user`, `get_current_platform_admin`, role checks, or billing limits.
- Captcha/rate-limit behavior is configurable; inspect settings before auth/security changes.
- Password reset raw tokens must never be stored or logged; only hashed tokens belong in `saas_password_reset_tokens`.
- Phase 13 email OTP MFA is active for configured tenant/admin users/roles. Do not enable MFA in production without valid SMTP.
- TOTP/authenticator-app MFA is not implemented; do not present it as supported.
- Privacy delete requests are non-destructive review records. Do not add hard-delete behavior without legal/retention approval, backup/export path and ADR.
- Knowledge URL ingestion blocks localhost/private-network targets. Do not loosen this without an explicit allowlist/proxy design and SSRF review.
- AI agent activation must remain preflight-gated; do not add alternate activation paths that bypass `agent_preflight_not_ready`.
- Conversation AI must keep one owner at a time. Assigned agent ownership should block silent general-AI fallback until the conversation is released or reassigned.
- Intelligence Engine predictive features must stay gated by plan flags, tenant grants, demo/full mode, quotas, tenant status, and admin permissions. Do not expose full ML predictions to all tenants by default.
- Phase 11 optional ML infrastructure exists, but API/worker default to `SAAS_ML_ENABLED=false`. Do not enable full ML broadly without staging acceptance.
- Phase 11 synthetic/autolabel training is for bootstrap and smoke validation only. Do not market those artifacts as production ML accuracy.
- Phase 11 feedback/model metrics, model registration, rollout controls, MLflow/BentoML artifacts and drift snapshots do not replace real eval datasets, production labels, alerting, rollback runbooks or model-risk review.
- Phase 11 canary routing can call optional ML service only when enabled and artifact-ready; baseline fallback must remain intact.
- Shadow ML inference must not alter the tenant-facing baseline score, recommendation gate, or business action.
- Phase 11 can now mark predictions as `shadow`; shadow/unapproved canary predictions intentionally do not create recommendations automatically.
- Do not persist `saas_intelligence_recommendations` from predictions unless `predictive_recommendations` access/quota is enabled. Demo prediction access alone is not enough.
- The Intelligence worker can generate automatic predictions and consume quota when tenant features are enabled. Review quotas/cooldowns before broad full-mode rollout.
- Intelligence recommendations must remain advisory by default. Do not auto-execute campaign, billing, CRM, or agent actions from recommendations without explicit approval/preflight.
- Autonomous Operational Intelligence must remain supervised. Do not add real Meta, queue, campaign, CRM, billing or webhook mutations to autonomous action execution without an ADR, explicit user approval, rollback design and staging smoke.
- Phase 12 reliability must remain control-plane first. Do not add automatic provider throttling, campaign pausing, queue mutation, destructive retention or real backup/restore execution without explicit user approval, ADR, rollback design and staging smoke.
- Phase 12 retention SQL must remain allowlisted. Never concatenate user-provided table names, timestamp columns or cleanup conditions.
- Demo mode for Autonomous Operations must keep auto-remediation and low-risk auto-execute disabled even if the UI sends true values.
- Inline Intelligence event capture must remain non-blocking; telemetry failures must not abort CRM, billing, webhook or customer-facing writes.
- Billing provider webhooks must verify Stripe/MercadoPago/Wompi signatures before mutating checkout, subscription, invoice, or tenant state.
- Non-operational tenant statuses must keep unsafe writes blocked while billing/auth/admin recovery routes remain reachable.
- Vertical packs must not auto-activate triggers or flows; keep human review/preflight before customer-facing automation.
- External agent libraries must be treated as untrusted input. `external-repos/agency-agents/` has been analyzed read-only and contains useful templates/playbooks, but its local folder has no standalone Git commit metadata. Do not run install/convert scripts, execute plugin code, install global agents, map external tool declarations directly, bypass preflight, bypass premium gating, or bypass the one-AI-owner conversation rule.
- Phase 15.1B/15.1C/15.2/15.3 generated offline draft, handoff, playbook and eval artifacts in `docs/phase15_1/`. These are not active marketplace rows, active workflows, active eval certifications or tenant-visible products and must not be exposed to tenants or imported into `saas_ai_marketplace_items` without explicit approval, secret scan, Admin review flow, attribution decision and ADR.
- Workflow Composer activation is `composer_only`. Do not change it to deploy executable triggers, flows, campaigns, Meta sends, CRM writes or agent handoffs without a new materialization design, ADR, approval/preflight path and staging smoke.
- Trust AI Phase 22 is governance/control-plane only. Do not convert risk assessments, model cards, incidents or reports into automatic enforcement against agents, workflows, plugins, models, Meta, CRM, billing or queues without a new ADR, feature flags, approvals, rollback and staging evidence.
- Trust AI compliance reports are not legal certification. Commercial compliance claims require legal/security review, sampled audit evidence, retention policy approval and tenant-specific attestation.
- Phase 16 Real-Time Intelligence is a live control-plane only. Do not turn realtime alerts, event feed rows or Admin snapshots into automatic CRM/campaign/Meta/billing/workflow/agent/model actions without a new ADR, approval gates, rollback and staging evidence.
- Phase 16 currently uses PostgreSQL polling plus bounded SSE; do not add Kafka, NATS, Redis Streams, WebSocket brokers or new realtime dependencies without explicit approval and capacity/rollback planning.
- Phase 24.2/24.3 add explicit Inbox audio/image/document analysis only. Phase 24.4 adds explicit external search with human approval only. Phase 24.5 adds agent-scoped multimodal tool runs, but they remain read-only/contextual and approval-bound. Phase 24.6 adds sanitized multimodal memory/training/RAG events, not automatic training. Phase 24.7 adds human-operated approved-reference preparation/send UX, not automatic AI/agent customer actions.
- Voice/Vision Intelligence handles sensitive conversation content. Never log raw media bytes, base64 payloads, decrypted provider credentials or provider media URLs containing secrets.
- Voice Intelligence currently uses Google/Gemini for real audio analysis. Do not route audio to other providers until adapter/model support is validated with real credentials.
- Vision Intelligence currently constrains document/OCR analysis to Google/Gemini. Do not advertise Kimi/OpenRouter document extraction until adapter/model support is validated with real credentials.
- Voice/Vision Intelligence output is advisory and does not authorize automatic CRM mutation, campaign execution, ticket creation, outbound messages or customer replies.
- Phase 24.4 Web/Image Search Intelligence is external-source assistance only. Never auto-send web links/images, crawl result pages, mutate CRM/campaigns/workflows or train models from search results without explicit new design approval.
- Phase 24.5 Agent Multimodal Tools must use `agents/multimodal_tools.py` and existing media/search endpoints. Do not add direct raw media fetching, decrypted secret logging, automatic customer send, CRM mutation, campaign launch, workflow execution, agent assignment or model training in this path.
- Phase 24.6 Multimodal Memory must use `agents/multimodal_memory.py` and `saas_multimodal_memory_events`. Do not store raw media/base64, mark rows training-ready without `multimodal_training_events`/`ml_predictions`/`ai_premium`, or materialize customer content without explicit approval.
- Phase 24.7 approved references must use `/media/search/results/{result_id}/reference` for preparation and `/conversations/{conversation_id}/messages` for delivery. Never send blocked/unapproved sources, bypass CRM quotas/outbound/status events, or let agents/workers auto-send external references without a new ADR.
- Phase 24.8 provider policies are enforced before AI Gateway and Web/Image Search provider calls. Do not bypass `assert_provider_enabled`, and do not treat zero cost/quota values as commercial pricing or blocking policy.
- AI Gateway model/provider failover is for retryable external failures and must remain policy-aware. Do not use fallback to bypass disabled providers/models, missing credentials, tenant plan gates, cost/request quotas, assigned-agent ownership or agent budget hard stops.
- When changing AI retry behavior, preserve `saas_ai_pending_replies` retry semantics: transient provider outages should remain retryable, while missing credentials, disabled providers and inactive assigned agents should stay operator-visible instead of silently falling back to general AI.
- Phase 24.9 multimodal observability stores aggregate metrics and safe source metadata only. Do not persist raw media/base64, decrypted secrets, full provider payloads or full conversation content in observability snapshots.
- Phase 24.9 cost estimates depend on Admin-entered provider policy pricing. Do not present zero estimates as free usage or invoice-grade billing.
- Phase 24.10 safe rollout is default-off and opt-in. Do not add implicit rollout blocking; enforcement must require feature access plus an explicit enabled tenant policy.
- Phase 24.10 rollout decisions must not mutate CRM, campaigns, workflows, billing, Meta runtime, agent ownership or provider credentials without a new ADR, approval gates and staging evidence.
- Autonomous Revenue Engine is supervised control-plane only. Do not add automatic WhatsApp/Instagram sends, payment-provider calls, CRM mutations, campaign/workflow activation or billing actions to revenue opportunity execution without a new ADR, explicit approval, rollback design and staging smoke.
- Autonomous Revenue Engine must not invent customer revenue. Keep estimated commercial value at `0` unless a real tenant commerce/order/revenue source is integrated and reviewed.
- Preserve Revenue Engine policy enforcement for allowed playbook action types and monthly control-plane execution caps when modifying opportunity actions.
- Phase 17 Federated Learning must remain opt-in, premium-gated and aggregate-only. Do not include raw messages, full conversations, media/base64, prompts, decrypted secrets, provider payloads, tenant names or private customer content in federated update packages, aggregates or global signals.
- Phase 17 global signals are candidate/benchmark intelligence only. Do not promote models, change ModelOps rollout, mutate CRM/campaign/workflows, send Meta messages, alter billing or execute agents from federated aggregation without a new ADR, approval path, rollback and staging validation.
- Worker auto-participation for Federated Learning must require full feature access plus `opt_in_enabled` and `auto_participation_enabled`; never infer consent from demo/read access.
- AI Enterprise Memory Network must remain tenant-scoped and reviewable. Do not route candidate/private memory into prompts, RAG context or cross-tenant intelligence without published status, tenant filters and privacy review. Exports must stay tenant-scoped and summary/metadata/hash only.
- AI Enterprise Memory Network must not store raw media/base64 or cross-tenant raw content. Keep graph nodes bounded to summaries, metadata, source ids and content hashes.
- Memory import must never create published nodes automatically. Keep imported memories as `candidate`, enforce allowed scopes/retention/customer review, and preserve audit logs for export/import/delete.
- Agent conversation prompts may include external search context only from approved, non-blocked `saas_web_search_intelligence_results`.
- Conversation AI humanized replies must preserve CRM/memory/facts/Knowledge/RAG/collective/multimodal context. Do not lower context windows further or remove memory injection just to reduce tokens without an explicit quality review.
- AI reply fragments are real outbound messages. Do not bypass `ensure_monthly_message_quota`, queue status tracking, or worker dispatch when changing chunking/typing behavior.
- WhatsApp typing indicators are best-effort. Do not build billing, SLA or delivery-state logic from typing indicator success/failure.
- Web/image search results must remain human-approved. Blocked/unsafe results must not be approvable or customer-facing.
- Do not log search provider credentials, decrypted API keys, private result URLs, or provider response payloads containing secrets.
- Do not log gateway attachment `data_base64`, raw media bytes, customer media content, provider file URIs containing secrets, or decrypted provider credentials.
- Remaining proposed phases 21, 23 and 25 are roadmap candidates, not active architecture. Do not implement them without explicit user approval, ADR, feature flags and scope-specific validation.

## Tenant Isolation

- Always include tenant filters in tenant-scoped SQL.
- Do not assume RLS alone is enough.
- Keep platform admin operations separate from tenant user operations.
- `switch-tenant` and membership role checks are security-sensitive.
- Do not enable HTTP admin bootstrap in production; use `create_platform_admin` or `platform-admin-seed`.
- Admin impersonation tokens are short-lived support access and must remain audited.
- Vertical pack application must preserve tenant filters across tenants, CRM, campaigns, and agents.

## Workers

- Embedded worker and standalone worker may both process work.
- Queue processors must be idempotent, lock-aware, and safe under retries.
- Billing lifecycle uses interval throttling plus advisory locking; keep it idempotent because embedded and standalone workers can both run.
- Agent orchestrator assignment can set conversation AI ownership; duplicate worker execution must not create competing AI owners.
- Do not change status transitions without inspecting all processors and admin operation endpoints.
- When validating Docker locally, avoid running multiple SaaS Compose projects on the same external `coolify` network; duplicate service aliases can make one API resolve another project's DB.

## Database

- Migrations are primary schema source, but runtime table creation also exists.
- Non-`saas_` social tables can collide in shared schemas.
- Do not edit historical migrations unless user explicitly confirms local reset semantics.
- Current exception: user explicitly requested SaaS historical migration normalization for clean PostgreSQL bootstrap on 2026-05-24.

## Scope

- Do not touch root `backend/`, root `frontend/`, Android, or `ai-service` for SaaS tasks.
- Do not convert this memory into whole-repo context unless user explicitly asks.
