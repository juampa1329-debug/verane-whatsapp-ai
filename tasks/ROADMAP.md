# ROADMAP

Scope: SaaS only. This is a memory roadmap, not a product commitment.

## Immediate Memory Discipline

1. Keep `ai-memory/CURRENT_STATE.md` synchronized after every SaaS change.
2. Keep `docs/API_REFERENCE.md` synchronized after router changes.
3. Keep `docs/DATABASE.md` and `architecture/DB_FLOW.md` synchronized after migrations/runtime SQL changes.
4. Keep `docs/ENVIRONMENT.md` synchronized after config/compose/frontend env changes.
5. Keep ADRs synchronized when architectural decisions change.

## Safe Development Workflow

1. Identify domain: auth, tenants, CRM, campaigns, broadcasts, ads, integrations, billing, AI, knowledge, admin, workers.
2. Read domain router/schema/service/migrations.
3. Search all references in `saas-version/`.
4. Make minimum scoped change.
5. Run targeted checks when available.
6. Update memory/docs.

## Product-Area Backlog Signals

These are domains visible in code, not requested implementations:

- Tenant onboarding/trials, billing acceptance, and provider payment operations.
- CRM inbox operations and outbound delivery.
- Campaign triggers, flows, preflight, enterprise versions.
- Broadcast template management and reporting.
- Meta/Instagram/WooCommerce integrations.
- AI gateway/provider credentials and AI agent orchestration.
- Knowledge/RAG source ingestion and search.
- Platform admin observability/dead-letter operations.

## Phase Backlog Signals 2026-05-24

- Account recovery is now Phase 1 code-complete; production readiness depends on SMTP and Turnstile env validation.
- Phase 3 observability is now code-complete; production readiness depends on real Meta/provider credentials, log retention/alerting, and staging traffic validation.
- Phase 4 Inbox is now code-complete; production acceptance depends on live Meta delivery/read webhook validation and Docker clean-stack rerun when Docker is available.
- Phase 5 CRM Comercial is now code-complete at repo level; clean Docker/PostgreSQL bootstrap for migration `040` was covered by the Phase 6 clean stack, while duplicate-merge rehearsal and AI custom-field smoke remain production acceptance work.
- Phase 6 Knowledge Base y RAG is now code-complete and smoke-tested with upload, indexing/vectorization, search, citations, quality evaluation, health, API/worker/bootstrap validation, and client UI support.
- Phase 7 Campanas, Triggers y Remarketing is now code-complete at repo level with simulator, preflight, version rollback, global quiet hours, A/B telemetry/reporting, Meta approved-template dispatch checks, and trigger conditions for CRM stages/status/intent. Clean Docker/PostgreSQL rerun through migration `042` remains pending until Docker Desktop is available.
- Phase 8 AI Agents Enterprise is now code-complete at repo level with preflight-gated activation, runtime budget hard stop, custom agents, fillable system prompts, manual/automatic conversation assignment, and collective-memory prompt injection. Clean Docker/PostgreSQL rerun through migration `043` remains pending until Docker Desktop is available.
- Phase 9 Billing y Monetizacion is now code-complete at repo level with provider signature verification, recurring lifecycle worker, payment-state sync, impago write blocking, notice emails, and invoice PDF download. Clean Docker/PostgreSQL rerun through migration `044` and real provider webhook acceptance remain pending until environment/providers are available.
- Phase 10 Verticalizacion is now code-complete at repo level with industry onboarding, tenant vertical state, CRM pipelines/custom fields/labels, templates, segments, trigger drafts, flow drafts, quiet-hours defaults, recommended agent packs, client UI, and admin tenant controls. Clean Docker/PostgreSQL rerun through migration `045` remains pending until Docker Desktop is available.
- Phase 11 Scentra Intelligence Engine now includes derived-event automation, limited safe inline event capture for CRM outbound and billing subscription changes, feature recompute, gated baseline prediction generation, separated predictive-recommendation gating, prediction feedback, ModelOps metrics, model registration, deterministic canary registry routing through Admin, tenant-facing `Inteligencia` UI, optional real ML infrastructure, event contracts, auto-labeling, feature pipelines, Postgres dataset builds, autolabel training and offline model evaluations. Clean Docker/PostgreSQL rerun through migration `050` passed with Compose profile `ml`; smokes confirmed CRM/Billing events, demo/full predictive grants, feedback/metrics, admin model registration/canary, MLflow, ML service, Qdrant, synthetic training, auto-label generation, feature pipelines, dataset materialization, XGBoost/LightGBM autolabel training, prediction, drift, Admin ML training/registry registration, and tenant shadow inference.
- Phase 12 Performance, Reliability & Scale is code-complete with SLO/backpressure/retention/snapshot/drill schema, reliability service/worker, Admin reliability endpoints, Admin `Performance` view, expected high-volume indexes, retention dry-run defaults and backup-readiness drills. Production acceptance still needs load tests, real backup/restore drills, threshold tuning and retention-policy approval.
- Phase 13 Security, 2FA & Compliance is code-complete with email OTP MFA for tenant/admin login, MFA-required role config, security notices, Admin Security Center, audit CSV export, tenant compliance exports, non-destructive privacy delete requests and Docker/API smokes through migration `056`. Production acceptance still needs SMTP/Turnstile/secret/CORS validation and legal retention workflow approval.
- Phase 14 added Spanish baseline catalogs and Product Ops copy/release gates. Continue moving long-tail module copy into catalogs whenever those modules are touched.
- Expand Phase 11 ML from optional/bootstrap to production only after auto-label quality review, tenant isolation checks, drift/cost alerts, rollback runbooks, shadow/canary acceptance and pricing/plan policy are approved.
- Extend Phase 12 with measured cache/partitioning/load-test work only after bottlenecks are observed in staging/production traffic.
- Add future authenticator-app/TOTP and automated secret-rotation work only after a dedicated security design is approved.
- Phase 15.1A/15.1B/15.1C/15.2/15.3 are now complete as offline intake for `external-repos/agency-agents/`: 184 valid agent templates normalized, 16 strategy/playbook docs counted, 29 disabled draft metadata items generated/evaluated, 7 handoff contracts, 7 playbooks, 4 scenario runbooks and 6 eval rubrics generated. No external scripts executed and no DB/runtime import performed. The folder is not a standalone nested Git repo, so upstream commit/tag remains unverified.
- Phase 18 AI Workflow Composer is now code-operational as a premium-gated control-plane with templates, graph editor, preflight, simulation, approvals, versions, rollback and `composer_only` activation. Runtime trigger/flow/campaign deployment from Composer intentionally requires a future materialization ADR.
- Phase 22 AI Trust, Compliance & Governance is now code-operational as a premium-gated control-plane with policies, attestations, risk assessments, model cards, incidents, reports, audits, tenant Trust AI UI and Admin Trust AI overview. It does not auto-enforce runtime changes or provide legal certification.
- Phase 16 Real-Time Intelligence Layer is now code-operational and smoke-tested as a PostgreSQL-first, premium-gated live control-plane with sanitized event feeds, tenant sessions/cursors, advisory alerts, tenant UI, Admin overview, metric snapshots and bounded SSE. Active Docker validation and clean PostgreSQL bootstrap passed through migration `059`; tenant/Admin realtime smokes, OpenAPI checks, log scans and browser smokes passed. It does not add broker infrastructure or runtime side effects.
- Phase 24.1 through 24.10 are now code-operational for gateway attachments, Voice Intelligence audio analysis, Vision Intelligence image/document analysis, Web/Image Search with sources plus human approval, Agent Multimodal Tools with approved-source prompt context, Multimodal Memory & Training Events for ML/RAG/agent memory capture, Inbox analysis/reference UX, Admin/Premium Gating, multimodal observability/cost/latency/error/quality/source tracking, and safe rollout with default-off flags, demo mode and deterministic canary controls. Active Docker validation previously passed through migration `065`; Phase 24.9/24.10 local checks passed for compile/build/config/SQL scans, but active Docker migration/API/bootstrap validation through `067` remains pending because Docker was not reachable in the latest session. Production acceptance needs real Gemini/OpenRouter/Kimi/Tavily/Brave/SerpAPI credentials, real media/search/reference samples, provider pricing metadata, quota policy review, rollout policy rehearsal, privacy wording, source/copyright policy, operator training and real Meta outbound smoke.
- Phase 19 Autonomous Revenue Engine is now code-operational and hardened with migration `066`, revenue opportunity/control-plane tables, tenant revenue endpoints, worker integration, tenant UI policy controls, allowed action-type enforcement, monthly control-plane execution caps and full-mode authenticated smoke. Production acceptance needs real tenant commerce/order/payment data before using forecasts or opportunity value commercially.
- Phase 20 AI Enterprise Memory Network is now code-operational with migration `066`, tenant memory graph tables, sync/review/export/import/delete endpoints, worker integration, tenant UI policy controls and full-mode authenticated smoke from the original implementation. Latest hardening adds active allowed-scope/retention/customer-review enforcement plus audited JSON portability. Production acceptance still needs prompt/RAG routing acceptance for published nodes only with real tenant samples.
- Phase 17 Federated Learning & Global Intelligence is code-operational at repository level with migration `068`, tenant opt-in policy, aggregate update packages, federated rounds, weighted aggregates, global signals, worker auto-participation behind opt-in/full gates, tenant UI controls and default-off feature flags. Production acceptance needs active Docker migration/API smoke through `068`, multi-tenant sample/cohort rehearsal, privacy review and ModelOps promotion runbook before using signals for production models.
- Recommended next roadmap order after Phase 17: Phase 21 AI Cloud Platform, Phase 23 Marketplace Economy, Phase 25 Decision Intelligence.
- Phase 11 trained ML should move beyond bootstrap only after real tenant-safe labels, label-distribution review, offline eval reports, shadow/canary acceptance, drift/cost alerts, rollback runbooks and plan/tenant commercial policy are approved.

## Do Not Do Automatically

- Do not refactor SaaS architecture.
- Do not merge SaaS with root app.
- Do not update packages.
- Do not clean generated artifacts unless requested.
- Do not implement roadmap items without explicit user request.
