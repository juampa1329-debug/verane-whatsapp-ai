# KNOWN_ISSUES

Scope: SaaS only. These are risks observed from repository structure/code, not confirmed production incidents.

## Critical

- `saas-version/docker-compose.saas.yml` has a local default `SAAS_JWT_SECRET=change-me-local-saas-secret`. Production must override it.
- `saas-version/keys/saasprivate.key` exists. Treat it as secret material; do not expose, copy, or commit elsewhere without explicit verification.
- API embedded worker and standalone `worker` service can both run. Queue processors must remain idempotent and concurrency-safe.
- Verified production incident on 2026-05-28: tenant login 500 was caused by DB schema drift where `saas_users.locked_until` and `saas_billing_subscriptions.payment_failed_notice_sent_at` were missing. Production also showed missing `saas_billing_invoices`, confirming broader billing migration drift. Migration `069_saas_auth_billing_schema_drift_repair.sql` repairs this permanently; until redeployed, run the provided idempotent SQL hotfix directly in production PostgreSQL.
- Verified follow-up production incident on 2026-05-28: after login, `/conversations`, `/dashboard/overview`, `/integrations`, `/advisor/briefing`, and `/auth/register` can still return 500 when production DB is missing later CRM, verticalization, campaign or Intelligence schema. Migration `070_saas_crm_intelligence_schema_drift_repair.sql` repairs the affected app-boot and registration schema. Production should still run the migration or equivalent SQL manually before relying on demo/user registration.

## High

- Some SaaS social tables are not prefixed with `saas_` (`social_posts`, `social_comments`, `comment_ai_settings`). Shared schemas can collide with non-SaaS tables.
- Schema definition is split between migrations and runtime defensive `CREATE TABLE IF NOT EXISTS` in services. Inspect both before DB edits.
- No dedicated automated test suite was detected for SaaS during inspection; changes need targeted manual or added tests if user requests.
- Password recovery is implemented and smoke-tested locally, but production email delivery depends on valid SMTP env vars. Without SMTP, production users will not receive reset links.
- Email OTP MFA challenge enforcement is implemented in Phase 13 for tenant/admin login. TOTP/authenticator-app support is not implemented.

## Medium

- `dist/` and `node_modules/` content exists under SaaS frontend/admin folders in the working tree. Verify intended tracking before commit operations.
- `saas-version/README.md` appears to contain trailing garbled/null-separated text after the main content.
- Billing webhooks now verify provider signatures in code; production still requires real sandbox/live tests with Stripe, MercadoPago, and Wompi secrets.
- CORS and public URL settings span local and production domains; deployment changes require env review.
- Phase 14 added local tenant/admin text catalogs and a critical-copy audit for mixed Spanish/English UI terms. Broader long-tail product copy should keep moving into catalogs as modules evolve.
- Billing lifecycle runs from admin/manual sync plus embedded/standalone workers; later Phase 11 Docker rebuild covered migrations through `054`.
- Clean Docker bootstrap was validated with a temporary project/volume. The compose file still requires an external Docker network named `coolify`; local environments without that network must create it or adjust compose intentionally.
- Running multiple SaaS Compose projects simultaneously on the same external `coolify` network can cause service-alias collisions such as `scentra-saas-db`; validate clean stacks one at a time or isolate aliases/networks.
- Some non-Phase-3 AI/integration SQL paths still use `CASE WHEN :id = '' THEN NULL ELSE CAST(:id AS uuid) END`; inspect and prefer `CAST(NULLIF(:id, '') AS uuid)` when those domains are modified.
- Phase 4 Inbox is code-complete with robust polling, filters, assignment, notifications, and build/browser smoke checks; live delivered/read status still requires real Meta webhook traffic for production acceptance.
- Clean Docker/PostgreSQL bootstrap was rerun for Phase 6 with migrations `001` through `041`; later Phase 11 Docker rebuild covered migrations through `054`. Phase 7 still needs real Meta template/provider traffic for production acceptance.
- Customer merge is deliberately conservative and tenant scoped; rehearse production merges with backup/export and real duplicate samples before bulk operational use.
- Phase 6 Knowledge/RAG uses local sparse-vector plus lexical retrieval, not pgvector or an external vector DB. This is intentional to avoid new dependencies, but high-scale semantic retrieval should be revisited in Phase 12.
- URL ingestion now blocks localhost/private-network targets for SSRF safety; tenants that need intranet crawling require an explicitly designed allowlist/proxy flow.
- Production RAG acceptance still needs large PDF/CSV samples and real AI reply smoke with tenant provider credentials.
- Phase 7 is code-complete locally; production acceptance still needs real Meta template/provider traffic and a clean Docker/PostgreSQL rerun when Docker is available.
- Phase 8 is code-complete locally with agent preflight activation gating, runtime budget hard stop, custom agents, manual/automatic conversation assignment, and collective-memory prompt injection. Later Phase 11 Docker rebuild covered migrations through `054`; production acceptance still needs real provider traffic, tenant data, and memory-vault rehearsal.
- Assigned inactive/unavailable AI agents intentionally stop conversation AI fallback to prevent two AIs from answering. Operators should release/reassign the conversation from the Inbox when an agent is paused/archived.
- AI Gateway now retries transient model/provider errors across allowed models/providers, but production still needs at least one valid configured AI credential and an allowed fallback provider/model. Admin-disabled providers/models, missing credentials, exhausted quotas or invalid API keys remain operator/configuration issues, not automatic fallback success cases.
- Model failover can create multiple `saas_ai_runs` rows for one customer message; failed provider attempts may affect operational cost/usage estimates depending on provider billing behavior.
- Phase 9 is code-complete locally with provider signature verification, recurring lifecycle worker, payment-state sync, impago write blocking, failed-payment notices, and invoice PDF download. Production acceptance still needs provider sandbox/live webhook tests and legal/tax validation of generated PDFs.
- Phase 10 is code-complete locally with tenant industry state, vertical pack application, client/admin UI, CRM/campaign/template/agent pack seeding, and application audit. Later Phase 11 Docker rebuild covered migrations through `054`; production acceptance still needs staging review of each industry pack with real tenant data.
- Vertical packs intentionally seed triggers inactive and flows as draft; operators must review/preflight/activate automations before sending customer messages.
- Reapplying a vertical pack updates the default CRM pipeline stages for that industry. Staging should verify this behavior before changing industry on tenants with mature production pipelines.
- Phase 11 Intelligence Engine now has optional ML infrastructure, but default production runtime remains `SAAS_ML_ENABLED=false` and baseline rules remain the compatibility fallback.
- Synthetic and Postgres auto-label trained models are infrastructure/bootstrap artifacts, not production-quality ML by themselves. Do not promote them broadly without label-quality review, drift checks, cost checks, tenant isolation review and staged rollout approval.
- Phase 11 canary routing can call the optional ML service when enabled and artifact-ready; otherwise scoring falls back to `baseline_rules`. Shadow inference must not alter baseline business decisions.
- Full predictive features are gated in code, but product/pricing policy must decide which plans or tenants receive `full` mode before production sales.
- Phase 11 tenant inline-capture smoke passed for CRM outbound `message.sent` and billing `billing.subscription.changed`; extended tenant predictive smoke also passed for grants/demo/full, feature recompute, predictions, recommendation gating, feedback, model metrics and recommendation dismiss.
- Phase 11 inline event capture currently covers CRM outbound messages and billing subscription changes only; runtime smoke validated this first pattern, and broader producer coverage should still be added incrementally.
- Intelligence worker now generates automatic predictions when features are enabled; quotas/cooldowns must be reviewed before enabling full mode broadly.
- Clean Docker/PostgreSQL bootstrap through migration `054` passed in the active Phase 11 stack; optional ML profile bootstrap through migration `050` passed in temporary project `codexsaasmltrain`. Production acceptance still needs real provider traffic, tenant data and model-quality acceptance.
- Phase 11 auto-labeling is intentionally heuristic and event/state based. Treat label confidence/evidence as auditable training metadata, and review per-tenant label distributions before promoting any trained model.
- Phase 11 predictive UI and Advisor briefing are now product-visible, but the displayed signals remain governed by baseline fallback or explicitly enabled model artifacts. Production sales/SLAs should phrase them as decision-support until real tenant validation is complete.
- Phase 11 Agent OS is now code-operational, but full event-driven enqueue is disabled unless `multi_agent_os`, `event_driven_agents`, or `ai_premium` is enabled. Demo mode previews candidates without creating orchestration jobs.
- Agent OS tool-run support is intentionally trace/action-draft first. Do not advertise autonomous tool execution until per-tool approval, audit, rollback and safety policies are accepted.
- Phase 11 Autonomous Operational Intelligence is code-operational, but current self-healing is supervised/control-plane first. Action execution records audit/control metadata and does not directly mutate Meta subscriptions, tokens, queues, campaigns, CRM or billing.
- Autonomous Operations full mode requires `autonomous_operations`, `ai_self_healing`, `ai_control_center`, or `ai_premium` enablement. Demo mode previews analysis but forces auto-remediation and low-risk auto-execute off.
- Phase 11 AI Platform Ecosystem is code-operational as a control-plane. Marketplace/plugins/tools/developer apps/event subscriptions/AI apps are premium-gated metadata records; no untrusted plugin runtime is executed in API/worker yet.
- Phase 11 Enterprise AI Network is code-operational and privacy-safe by design, but benchmark value depends on enough tenants per industry. Industry aggregates require sample count >= 3 and should be reviewed before being used in sales claims.
- Enterprise AI Network playbooks are recommendation templates only. Do not auto-activate triggers, flows or campaigns from those playbooks without a later explicit design, preflight and human approval.
- Developer apps store hashed API keys with one-time raw display. Do not expose ecosystem developer keys as public auth until a dedicated external API/auth gateway is designed and reviewed.
- Worker-degradation and queue anomaly thresholds are heuristic. Tune sensitivity in staging with real tenant traffic before enabling higher autonomy levels broadly.
- Qdrant is available only in the optional ML profile and is not wired into the existing Knowledge/RAG runtime yet.
- Kafka/NATS were not added. External event streaming remains a future scale decision, not current architecture.
- A broad encoding scan detected older UTF-8 BOMs in a few non-migration SaaS `.py`, `.jsx` and docs files. SQL migrations are clean; normalize those unrelated files in a separate scoped cleanup if needed.
- Phase 12 Performance/ Reliability is control-plane first: SLOs, backpressure, index audit, snapshots, drills and retention dry-runs are code-operational, but production SLO thresholds and queue limits must be tuned with real traffic before using them as contractual targets.
- Phase 12 retention cleanup defaults to disabled/dry-run and is allowlisted. Do not enable destructive cleanup broadly without backup verification, staging rehearsal and retention/legal policy approval.
- Phase 12 backup readiness is metadata/readiness only. Actual backup and restore execution remains an infrastructure/database-operations responsibility outside the API.
- Phase 12 load smoke is a lightweight DB/API readiness drill, not a full load test. Dedicated load tests are still needed before high-scale commercial commitments.
- Phase 13 email OTP depends on valid SMTP in production. Local dev OTP exposure must not be enabled for public environments.
- Phase 13 privacy delete requests are review records only. They do not hard-delete CRM, conversation, message, audit, RAG, or agent memory data without a separate approved procedure.
- Phase 13 Admin Security Center exposes compliance/security metrics, but broader automated tenant-isolation regression tests across every router remain a recommended QA suite before scaling public tenants.
- Phase 15.1A/15.1B/15.1C/15.2/15.3 local analysis and offline intake of `external-repos/agency-agents/` is complete, but the folder is not a standalone nested Git repo and exact upstream commit/tag remains unverified. Generated files under `docs/phase15_1/` are disabled metadata/playbook/eval artifacts only. Do not import them into DB, run scripts, map external tool declarations directly, claim runtime compatibility, or activate agents/workflows until a secret scan, Admin review flow, attribution decision, certification workflow and import ADR exist.
- Phase 18 Workflow Composer is code-operational as a safe control-plane. Activation currently creates `composer_only` materializations and does not deploy executable triggers, flows, campaigns, Meta messages, CRM writes or agent handoffs; add a separate ADR/materialization path before advertising runtime workflow deployment.
- Phase 22 Trust AI is code-operational as a governance/control-plane. Policies, risks, model cards, incidents, reports and audits are records and decision support; they are not legal certification and do not automatically enforce runtime changes across agents, workflows, models, plugins, Meta, CRM or billing.
- Phase 22 cross-domain risk scans are metadata-based. Before commercial compliance claims, run legal/security review, real audit sampling, incident response rehearsal, data retention approval and tenant-specific policy attestation.
- Phase 16 Real-Time Intelligence is code-operational as a PostgreSQL-first live control-plane. It intentionally uses polling plus bounded SSE instead of Kafka/NATS/Redis Streams/WebSockets; high-volume tenants still need capacity tests before committing low-latency SLAs.
- Phase 16 realtime alerts are advisory only. Do not sell them as autonomous remediation or make them mutate Meta, CRM, campaigns, billing, workflows, agents, Trust AI or model rollout without a separate approved runtime design.
- Phase 24.2 Voice Intelligence is code-operational for Inbox audio analysis, but production acceptance still needs real tenant Gemini credentials, real WhatsApp/local audio samples, quota/cost review and privacy wording before broad rollout.
- Phase 24.2 currently supports real audio analysis through the Google/Gemini gateway path only. Do not advertise Mistral/OpenRouter/Kimi/Groq audio analysis until their adapter payloads and model support are validated.
- Phase 24.2 stores transcript/summary/classification output. Treat voice output as sensitive customer conversation data and keep tenant filters, auth and retention policy intact.
- Phase 24.3 Vision Intelligence is code-operational for explicit Inbox image/document analysis, but production acceptance still needs real tenant Google/OpenRouter/Kimi credentials, real media samples, quota/cost review and privacy wording before broad rollout.
- Phase 24.3 supports OCR-style extraction only for existing tenant media. It does not perform web search, web image retrieval, image sending, agent media tools or multimodal model training.
- Vision output can include extracted document/customer text. Treat it as sensitive customer conversation data and keep tenant filters, auth and retention policy intact.
- Phase 24.4 Web/Image Search Intelligence is code-operational for explicit external search with sources and human approval, but production acceptance still needs real tenant Tavily/Brave/SerpAPI credentials, quota/cost review, source-quality review and copyright/licensing policy before broad rollout.
- Phase 24.4 does not send search results/images to customers, crawl result URLs, execute agent tools, mutate CRM, launch campaigns or train models. Keep it approval-first until a separate customer-send design is approved.
- External web/image results can contain inaccurate, copyrighted, unsafe or stale content. Human review is mandatory before using links/images in customer conversations.
- Phase 24.5 Agent Multimodal Tools is code-operational for agent-scoped voice, vision and web/image-search tool runs, but production acceptance still needs real tenant media, real provider/search credentials, quota/cost review, operator training and source approval policy.
- Phase 24.5 tool runs are advisory/contextual only. They do not send messages, mutate CRM, execute workflows, launch campaigns, assign agents, train models or bypass approval of external sources.
- Agent runtime consumes web/image search output only after individual results are approved and not blocked; failed or pending search runs must not be treated as factual context.
- Phase 24.6 Multimodal Memory & Training Events is code-operational for sanitized memory/RAG/training-signal capture, but production acceptance still needs real tenant media/search samples, reviewed privacy wording, retention policy, operator workflow training and cost/quota review.
- Phase 24.6 does not train models automatically. Training-ready events are only signals for later ML pipelines and require `multimodal_training_events`, `ml_predictions`, or `ai_premium`.
- Phase 24.7 Inbox UX is code-operational for analysis panels and approved-reference use/send actions, but production acceptance still needs real tenant visual-reference samples, source/copyright policy review, operator training and Meta outbound smoke with a real connected channel.
- Phase 24.7 sends only through the existing CRM outbound endpoint after human click/confirmation. Do not add AI/agent/worker automatic reference sending without a separate approval, privacy and copyright design.
- Phase 24.8 Admin & Premium Gating is code-operational for tenant/plan feature modes, provider policies, request quotas and estimated costs. Production acceptance still needs pricing metadata review for every provider/model, quota policy review, real-credential smoke and billing/legal alignment before using cost estimates commercially.
- Phase 24.8 provider policy defaults intentionally allow existing providers. To block or cap usage, Admin must configure explicit global/plan/tenant policies; zero quota/cost limit means "unlimited/not enforced", not "blocked".
- Phase 24.9 Observability is code-operational for aggregate cost/latency/error/quality/source metrics, but production acceptance still needs real provider pricing metadata and real multimodal traffic before using cost, quality or error-rate reports commercially.
- Phase 24.10 Safe Rollout is code-operational and default-off. Runtime enforcement applies only with rollout feature access plus an explicit enabled policy; acceptance still needs real tenant canary/demo/off rehearsal with real voice/vision/search samples before broad rollout.
- Phase 24.10 rollout events are audit/control metadata only. Do not make rollout decisions mutate CRM, campaigns, billing, Meta runtime, agent ownership or provider credentials without a separate ADR and staging evidence.
- Phase 19 Autonomous Revenue Engine is code-operational and validation passed, but it is intentionally control-plane only. Real customer revenue attribution still requires ecommerce/order/payment data from tenant systems before forecasts/opportunity value can be used commercially.
- Phase 19 revenue opportunity execution does not send customer messages, mutate CRM, launch campaigns/workflows, call payment providers or charge customers. Do not convert it into autonomous revenue actions without ADR, approvals, rollback and real-channel staging smoke.
- Phase 19 policy hardening now enforces allowed playbook action types and monthly control-plane execution caps. Active Docker/API/Swagger smoke for the latest local hardening still needs rerun when Docker Desktop is reachable.
- Phase 20 AI Enterprise Memory Network is code-operational with policy enforcement, audited export/import/delete and tenant UI controls. Prompt/RAG runtime consumption should still use reviewed/published tenant nodes only. Do not expose candidate/private customer memory in prompts or cross-tenant intelligence.
- Phase 20 stores bounded summaries/metadata/hashes, not raw media. Any future memory graph expansion needs lineage and privacy review, and must preserve import-as-candidate plus access logging.
- Phase 17 Federated Learning is code-operational at repository level, but active Docker migration/API/Swagger/worker smoke through `068` and clean PostgreSQL bootstrap `001`-`068` still need rerun in an available Docker runtime.
- Phase 17 federated signals require multiple opted-in tenants with enough samples in the same/general cohort. Until real tenant cohorts are rehearsed, treat aggregate/global signals as candidate decision-support, not production ML proof.
- Phase 17 aggregation is weighted statistical aggregation over safe packages, not advanced secure-aggregation or differential-privacy math beyond policy metadata. Do not make stronger privacy/ML claims without a separate implementation and review.
- Customer-content materialization from voice/vision analysis into Knowledge/RAG or collective memory requires explicit operator approval; do not bypass this check for convenience.
- Remaining proposed phases 21, 23 and 25 are roadmap recommendations, not implemented features. Each phase still needs an ADR, feature flags, acceptance criteria, rollout plan and risk review before runtime work.
- Groq `http_403: error code: 1010` was mitigated by adding explicit provider HTTP headers and refreshing static model fallbacks. If the provider still rejects calls, treat it as a Groq/Cloudflare project/IP/fingerprint block and keep OpenRouter, Google, Mistral or Kimi configured as fallback.
- Humanized AI replies now reduce output size and split long replies into multiple outbound messages while preserving CRM/memory/RAG context. This improves naturalness but can increase monthly message usage because each fragment is queued and billed as a separate outbound message.
- WhatsApp typing indicators are best-effort and depend on Meta Cloud accepting the inbound provider message id, connected `meta_cloud`/`whatsapp_cloud` dispatch mode and current Graph behavior. Do not treat "escribiendo..." as guaranteed delivery-state telemetry.

## Agent Cautions

- Do not use root `backend/`, root `frontend/`, Android, or `ai-service` as active architecture context.
- Do not "fix" issues listed here unless user asks for implementation.
- When documenting a future issue, include file path, observed behavior, risk, and whether it is verified or inferred.
