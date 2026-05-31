# FRONTEND

Scope: SaaS only. Active frontends live under `saas-version/frontend` and `saas-version/admin-frontend`.

## Client App

Path: `saas-version/frontend`.

Core files:

- `src/App.jsx`: main SaaS shell, auth/recovery/reset/security-settings flow, dashboard/settings/nav orchestration.
- `src/CrmPanel.jsx`: customer CRM workflow plus custom-field and pipeline configuration.
- `src/LabelsPanel.jsx`: label management.
- `src/CampaignsPanel.jsx`: campaign/template/segment/trigger views.
- `src/SaasTriggerBuilderPanel.jsx`: trigger builder UI.
- `src/BroadcastPanel.jsx`: broadcast/template/report workflows.
- `src/AdsPanel.jsx`: ad accounts/campaigns/leads/comments workflows.
- `src/AiAgentsPanel.jsx`: AI agent operations.
- `src/AiEcosystemPanel.jsx`: AI marketplace, plugin center, tool registry, developer console, integrations and AI apps.
- `src/styles.css` and component CSS files: styling.

Runtime config:

- `VITE_API_BASE`: required API base URL.
- `VITE_CAPTCHA_ENABLED`: optional Turnstile UI toggle.
- `VITE_TURNSTILE_SITE_KEY`: Turnstile site key when captcha is enabled.

Auth UX:

- Login/register/recovery/reset forms share an in-flight guard so the submit button is disabled while the request is being processed.
- API auth errors are translated into Spanish user-facing messages for invalid credentials, rate limits, temporary lockout, CAPTCHA failures, MFA/reset-token problems, membership issues and database saturation. Login copy explains the cause and next safe action without revealing whether a specific email exists. Keep this mapping in `formatApiError` when adding new backend auth error codes.
- General frontend errors still keep backend machine codes for support, but tenant/Admin users see Spanish modal copy with a likely cause, suggested next action and collapsible technical detail. Keep new user-facing errors mapped through `friendlyApiError`/`readableErrorNotice` instead of rendering raw endpoint codes.
- Auth/nav branding uses the public Scentra assets already used in transactional emails: `https://scentra-ai.online/favicon.png` and `https://scentra-ai.online/logo-blanco.png`.

Timezone UX:

- Tenant UI defaults to `America/Bogota` and stores the selected profile timezone in `scentra_user_timezone`.
- `todayLabel`, conversation time labels, diagnostics, Intelligence date labels and compact date/time helpers format through the selected timezone.
- Settings profile sends `timezone` to `/auth/profile`; backend stores it in `saas_users.profile_json.timezone`.
- If a stored timezone is unsupported by the browser, the UI falls back to Colombia time.

Internal notification UX:

- Tenant system notifications load from `/saas/v1/notifications` with unread plus recent history.
- Unread notifications can appear as a top popup after login/navigation and as pinned pseudo-items above the Inbox conversation list.
- Read notifications lose the pin but remain visible in the Inbox/history list, ordered by age with the rest of the conversation preview surface.
- Notification pseudo-items are marked `Interno`/`Sin respuesta`; they do not open a customer thread and cannot be replied to.
- `Marcar leída` calls `/saas/v1/notifications/{recipient_id}/read` and removes the popup/pin.
- Tenant Settings includes real profile save and team user management backed by `/auth/profile` and `/auth/team*`.

Local storage keys:

- `scentra_ai_access_token`
- `scentra_ai_refresh_token`
- `scentra_user_timezone`

Navigation surfaces detected in `App.jsx`:

- dashboard
- inbox
- customers
- labels
- campaigns
- broadcast
- ads
- agents
- intelligence
- ecosystem
- settings

Provider choices visible in the UI:

- AI: `gemini`, `groq`, `mistral`, `openrouter`, `kimi`
- TTS: `elevenlabs`, `google_tts`, `piper`
- Search: `tavily`, `brave_search`, `serpapi`
- Channels/integrations: `whatsapp_cloud`, `instagram_business`, `woocommerce`

Groq UI note:

- `src/App.jsx` Groq reference models now show `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, `openai/gpt-oss-20b`, and `openai/gpt-oss-120b`.
- Runtime model selection should still prefer the models returned by `/saas/v1/api-credentials/groq/models` for the tenant credential.

## Admin App

Path: `saas-version/admin-frontend`.

Core files:

- `src/AdminApp.jsx`: platform admin shell, auth/recovery/reset, tenant/admin operations.
- `src/styles.css`: admin styling.

Runtime config:

- `VITE_API_BASE`: required API base URL.
- `VITE_CLIENT_APP_BASE`: client app base URL; default in code is `http://localhost:5174`.
- `VITE_CAPTCHA_ENABLED`: optional Turnstile UI toggle.
- `VITE_TURNSTILE_SITE_KEY`: Turnstile site key when captcha is enabled.
- `VITE_ADMIN_BOOTSTRAP_ENABLED`: optional local bootstrap UI toggle; production should keep it disabled and use the seed command/service.

Admin user/notification UX:

- `Usuarios` manages the platform admin profile/password, platform admins, tenant users and role/status changes through `/saas/v1/admin/users/*`.
- `Usuarios` is grouped by tabs: `Mi perfil`, `Admins plataforma`, and `Usuarios empresa`; tenant users include search by name/email/company/role/status.
- `Mi perfil` includes `Zona horaria`; Admin date labels use `scentra_admin_timezone` and default to `America/Bogota`.
- `Notificaciones` loads target tenants/users/roles, prepares a template-assisted Spanish draft, sends targeted internal notifications and optionally sends email copies.
- `Notificaciones` makes the internal-app delivery explicit, supports `Para todos` versus selected audience, target search, and aligned compact recipient checkboxes.
- Admin notification history displays human labels for severity/category and recipient/read/email counts; it must not show raw table names or internal IDs as user-facing labels.
- Admin billing provider settings show payment brand logo chips for Wompi, Mercado Pago, Visa and Mastercard. The chips load public logo URLs with text fallback; provider credentials remain stored/handled by backend provider settings.
- Admin errors use the same friendly modal pattern as the tenant app: Spanish explanation, suggested action and collapsible technical detail.

Local storage key:

- `scentra_admin_access_token`
- `scentra_admin_timezone`

Admin views detected:

- overview
- tenants
- plans
- subscriptions
- billing
- operations
- observability
- audit
- intelligence
- performance
- trust/security/product operations surfaces when enabled by current code

## Build/Serve

- Both apps use React 19, Vite 7, and `@vitejs/plugin-react`.
- Dockerfiles use Node 20 and Nginx.
- `docker-compose.saas.yml` now includes `admin-frontend` for `admin.scentra-ai.online`.
- `dist/` directories exist in the working tree; verify whether they are intentional artifacts before committing.

## Phase 2 Admin UI

- Admin UI exposes overview, tenants, plans, subscriptions, billing, operations, observability, and audit.
- Tenant detail shows effective feature flags from plan/default/trial plus tenant overrides; changes create admin overrides.
- Admin bootstrap UI is hidden outside localhost unless explicitly enabled by `VITE_ADMIN_BOOTSTRAP_ENABLED`.
- Support impersonation opens the client app with a short-lived support token through `VITE_CLIENT_APP_BASE`.
- Admin `Usuarios` now provides real profile/password editing, platform admin creation/listing and tenant user creation/role/status management in tabbed sections.
- Admin `Notificaciones` can send internal notices to all users or selected users, roles and tenants, with optional email copies. Tenant frontend shows unread notices as login popups and pinned Inbox pseudo-items, not as customer conversations.

## Phase 3 Admin Observability UI

- `AdminApp.jsx` observability view shows API, DB, worker, Meta, AI Gateway, backlog, errors, integration, queue, channel, dead-letter, and Meta error-history panels.
- Operations view can manually process webhooks, outbound, triggers, AI pending replies, remarketing, agent orchestration, and Meta token refreshes.
- Dead-letter rows include diagnosis, correlation ID, attempts/retry metadata, resolve, and retry actions.
- Browser smoke on the local admin build confirmed login and the `Salud` view render without console errors.

## Phase 4 Client Inbox UI

- `frontend/src/App.jsx` owns the operational Inbox for DMs and comments.
- DM inbox supports channel/queue/search filtering, unread queues, mine/unassigned filters, SLA overdue, hot leads, human takeover, AI queue, message read state, and status-event timeline.
- The Inbox filter controls render in the top area of the conversation/thread panel, not inside the left preview list, so the preview list keeps more vertical room for conversation cards.
- Comment inbox is separated from DMs and uses `social/comments` APIs for Meta-style comment preview, AI suggestion, reply, and reaction.
- Composer supports text, media upload, document/audio/video/image attachments, voice note recording, emojis, and WooCommerce product cards.
- WooCommerce product cards use a two-row layout with isolated image and opaque body sections so transparent product photos cannot overlap product title, price, chips or CTA text.
- Polling is visibility-aware and lightweight: active Inbox refreshes the selected conversation about every 12 seconds, the list about every 18 seconds, and hidden tabs about every 60 seconds. Poll ticks avoid overlapping refreshes and skip heavy optional reads such as memory, dedupe, search runs, multimodal events, comments and agents unless the user opens/forces that context.
- Notifications are split into in-app sound and browser notifications; browser notifications require explicit permission and are stored under `scentra_browser_notifications`.
- Conversation assignment is operable from the Inbox through assign-to-me and release actions.

## Phase 5 Client CRM UI

- `App.jsx` loads `/crm/config` for active CRM custom fields and pipeline stages.
- Inbox CRM side panel now renders tenant custom fields, dynamic pipeline stages, duplicate candidates with merge action, predictive intelligence, tasks, AI context and Meta status events. It intentionally does not render a full conversation timeline because the main Inbox thread is the canonical conversation history.
- The predictive intelligence mini-card in the Inbox CRM side panel must span the full CRM mini-form width. Keep `.crm-predictive-card` in the full-width grid selector in `frontend/src/styles.css`; otherwise the card compresses into a narrow half column.
- Conversation list cards must keep natural row height and truncate/wrap badges safely. Preserve `grid-auto-rows: max-content` and full-width `.conversation-item` behavior to avoid cards visually overlapping in narrow Inbox columns.
- Preserve the left Inbox list grid as header plus scrollable list; moving filters back into `.inbox-list` compresses previews and can recreate cramped rows.
- `CrmPanel.jsx` can create tenant custom fields, apply industry pipeline presets, add pipeline stages, and edit customer fichas with custom-field values.
- Custom-field values are sent as `custom_fields` and persisted backend-side into `profile_json.custom_fields`.

## Client Diagnostics UI

- `Configuracion -> Diagnostico` is the tenant operator path for no-inbound/no-AI/no-outbound incidents.
- The panel calls `/saas/v1/diagnostics/overview`, `/saas/v1/diagnostics/run?limit=50`, `/saas/v1/diagnostics/whatsapp/simulate-inbound`, and `/saas/v1/internal/whatsapp/check-subscription`.
- The panel shows server/client diagnostic date-time, current webhook callback URLs, legacy no-key WhatsApp/meta compatibility URLs, endpoint `last_seen_at`, recent webhook received/processed timestamps, and whether a WhatsApp event entered through stale-endpoint fallback.
- The checklist distinguishes "API IA usable" from "API IA guardada": a provider key can be present but unusable when the backend cannot decrypt it with the current `SAAS_SECRET_KEY`.
- The queue panel shows recent AI pending jobs and recent AI Gateway calls/errors so operators can separate "not queued", "credential/model/provider failed", and "outbound failed" cases.
- If a real WhatsApp message is missing from Inbox but `Simular entrada` succeeds, the frontend should guide operators toward Meta callback/WABA `subscribed_apps`/verify-token/fields rather than AI settings.
- Keep this view readable for non-engineers; it is the primary production support surface inside the client app.

## Phase 6 Client Knowledge/RAG UI

- `App.jsx` settings/IA panel manages Knowledge Base sources.
- Upload accepts PDF/TXT/CSV from click or drag/drop and sends files to `/saas/v1/knowledge/upload`.
- Web source ingestion posts to `/saas/v1/knowledge/url`.
- Health cards show active sources, chunks, vectorized chunks, retrieval mode, error count, and RAG quality summary.
- Search UI calls `/saas/v1/knowledge/search` and displays confidence, sparse-vector/lexical mode, vector score, matched terms, content, and internal citations.
- Evaluation UI calls `/saas/v1/knowledge/evaluate` and lists recent `/knowledge/evaluations` results with pass/fail, answerability, quality score, and confidence.
- Source rows show parser metadata, indexing status/error, last indexed time, reindex, and delete actions.

## Phase 7 Client Campaigns UI

- `CampaignsPanel.jsx` exposes global quiet hours, campaign preflight, flow preflight, flow A/B variant configuration, flow A/B reporting, and manual remarketing tick.
- CRM template sequences support text, image, video, audio and document/PDF-style blocks. Document blocks upload through `/media/upload`, store `media_id`, `filename` and optional caption, and preview as document chips in the template chat preview.
- `SaasTriggerBuilderPanel.jsx` exposes trigger simulator, preflight, quiet hours, A/B variants, A/B report, version history, and rollback restore.
- Trigger condition UI supports words, comments, templates, tags, schedules, CRM stage, payment status, customer type, and intent.

## Phase 24.8-24.10 Admin Premium Gating UI

- `admin-frontend/src/AdminApp.jsx` extends the existing `AI Predictivo` view with Phase 24 tenant/plan/provider controls.
- Tenant rows expose Phase 24 voice, vision, web/image search, agent multimodal tool, multimodal memory, observability and rollout feature modes plus monthly quota inputs.
- Plan rows expose plan-level Phase 24 feature mode/quota limits; tenant grants still override these plan limits.
- Provider policy form supports global, plan or tenant scope; AI/search/TTS category; provider code; optional model id; enabled/disabled state; request quota; monthly cost limit; and input/output/request cost metadata.
- The same view shows credential readiness counts and estimated monthly AI/search costs. It never displays decrypted secrets.
- Phase 24.8 itself added no tenant-facing UI; Phase 24.9/24.10 add tenant-facing observability and rollout controls in `IntelligencePanel.jsx`.
- Trigger simulator can set sample message, customer, phone, CRM stage, payment status, and tags before calling `/campaigns/triggers/simulate`.
- Frontend build passed after Phase 7 verification; Vite still reports the existing large-bundle warning only.

## Phase 8 Client AI Agents UI

- `AiAgentsPanel.jsx` supports factory agents and a `Crear Custom Agent` action for tenant-defined agents.
- Agent editor exposes `System prompt rellenable`, base template, variables JSON, rendered prompt preview, tool approvals, memory policy, and budget hard-stop controls.
- Tenant Settings > IA exposes human response controls for compact WhatsApp replies: brief-context style, natural chunking, output-token cap, chunk size/delay, recent-message window, per-message history size and WhatsApp typing indicator toggle.
- The default reply controls favor shorter, more human WhatsApp replies: about 180-character chunks, best-effort typing indicator, and longer spacing between chunks so several outbound fragments do not arrive as one burst.
- `AiAgentsPanel.jsx` now includes the Phase 11 `Agent OS` tab for multi-agent coverage, memory layers, event subscriptions, inter-agent messages, tool-run traces and runtime observability.
- Preflight can be run from the agent panel and activation errors surface as `agent_preflight_not_ready`.
- Budget hard-stop errors surface as `ai_agent_budget_exceeded`.
- `App.jsx` Inbox loads active agents, filters conversations by assigned AI agent, shows assigned-agent badges, and lets users assign/release the AI agent responsible for a conversation.
- CRM side panel includes `Agente IA responsable`; assigning an agent moves the conversation from general AI to that agent.
- Frontend build passed after Phase 8 changes; Vite still reports the existing large-bundle warning only.

## Phase 9 Billing UI

- Tenant `App.jsx` Settings > Plan loads billing overview, plans, checkout sessions, and invoices.
- Tenant billing UI starts checkout for Wompi, MercadoPago, Stripe, or manual pending flows through `/billing/checkout`.
- Tenant invoice rows can download authenticated generated PDFs through `/billing/invoices/{invoice_id}/pdf`.
- Admin billing view lists invoices/credits, can run lifecycle sync, apply manual credits, and download authenticated invoice PDFs through `/admin/billing/invoices/{invoice_id}/pdf`.
- Client and admin builds passed after Phase 9 changes; tenant Vite still reports the existing large-bundle warning only.

## Phase 10 Verticalization UI

- Tenant registration now exposes an industry selector loaded from `/verticals/public-packs` with a local fallback list.
- Tenant `App.jsx` Settings includes an `Industria` tab that shows current pack state, KPI counts, recommended agents, recent applications, and pack application controls.
- Applying a vertical pack calls `/verticals/apply`, reloads vertical state, CRM config, dashboard overview, and session tenant data.
- Optional recommended-agent creation is explicit from the vertical UI; pack application does not auto-activate triggers or flows.
- Company summaries show industry labels where tenant membership data exposes `industry_code`.
- Admin tenant detail now exposes an industry selector; changing it patches the tenant and applies the pack without creating agents.
- Client and admin builds passed after Phase 10 changes; tenant Vite still reports the existing large-bundle warning only.

## Phase 11 Tenant Intelligence UI

- Tenant `App.jsx` now exposes the `Inteligencia` navigation view through `IntelligencePanel.jsx`.
- Tenant `IntelligencePanel.jsx` calls `/saas/v1/intelligence/overview` plus existing `/saas/v1/intelligence/*` APIs for state, feature snapshots, predictions, recommendations, feedback, model metrics and Phase 17 Federated Learning.
- `IntelligencePanel.jsx` renders executive summaries and predictive cards for lead scoring, churn, smart remarketing and operational intelligence.
- `IntelligencePanel.jsx` now includes AI Operations Center and AI Control Center backed by `/saas/v1/intelligence/operations/*`.
- `IntelligencePanel.jsx` now includes Enterprise AI Network surfaces backed by `/saas/v1/intelligence/network/*`: Industry Intelligence Center, Benchmark Dashboard, Industry Insights Panel, Vertical AI Advisors, AI Playbook Marketplace, Industry AI Models and AI Knowledge Network.
- `IntelligencePanel.jsx` now includes Phase 17 Federated Learning surfaces backed by `/saas/v1/intelligence/federated/*`: opt-in policy, privacy mode, local aggregate previews, task selection, manual round/update submission, aggregate preview, aggregate execution and global signal cards.
- Network refresh buttons intentionally separate preview (`dry_run=true`, demo-safe) from persisted refresh (`dry_run=false`, full premium gated).
- Federated Learning buttons intentionally separate preview (`dry_run=true`) from persisted round/update/aggregate operations (`dry_run=false`, full premium gated).
- Tenant users can preview/analyze operational anomalies, tune autonomy level/sensitivity/action limits, and approve/execute/dismiss supervised autonomous action records.
- Demo mode still displays operations previews but backend policy forces auto-remediation and low-risk auto-execute off.
- Tenant users can recompute feature snapshots, trigger gated baseline predictions, submit prediction feedback, and dismiss open recommendations.
- The panel reloads on active tenant changes to avoid showing stale predictive data from the previous company.
- Tenant `App.jsx` renders a predictive strip on Dashboard, predictive badges and a `Churn` filter in Inbox, and a CRM predictive card with conversation-level lead/churn/remarketing prediction actions.
- The floating Advisor now loads `/saas/v1/advisor/briefing` for proactive predictive summaries, insights, recommendations, actions, activity, metrics and memory.
- The AI Agents panel loads `/saas/v1/agents/os` and can call `/saas/v1/agents/os/event-sync`; full event-driven enqueue remains backend-gated, while demo mode shows safe previews.
- Tenant `App.jsx` now exposes the `AI Ecosystem` navigation view through `AiEcosystemPanel.jsx`.
- `AiEcosystemPanel.jsx` calls `/saas/v1/ecosystem/*` to show marketplace items, installations, plugins, tools, event subscriptions, developer apps, SDK manifest, external integrations, AI apps and ecosystem metrics.
- The ecosystem UI allows marketplace install, plugin/tool/developer/integration/app creation only through backend premium gates. Demo mode can show previews but mutation endpoints require full mode.
- Client build and local browser smoke passed after AI Ecosystem UI changes; Vite still reports the existing large-bundle warning only.
- Latest Phase 11 closeout build/browser smoke passed after Enterprise AI Network UI changes for tenant frontend and admin frontend; Vite still reports the existing tenant large-bundle warning only.

## Phase 11 Admin Intelligence UI

- Admin `AdminApp.jsx` now includes the `AI Predictivo` view.
- The view calls `/saas/v1/admin/intelligence/catalog`, `/saas/v1/admin/intelligence/tenants`, `/saas/v1/admin/intelligence/model-metrics`, `/saas/v1/admin/intelligence/models`, `/saas/v1/admin/intelligence/training-dataset`, and `/saas/v1/admin/intelligence/mlops`.
- Admin can inspect predictions 30d, open recommendations, monthly AI-predictive usage, demo mode, and per-feature mode per tenant.
- Admin can inspect ModelOps metrics: model key, prediction type, sample count, feedback count, accuracy and drift baseline.
- Admin can inspect, register and patch model registry rollout mode/status from `Model Registry & Rollout`.
- The model registration form records metadata and rollout controls. The optional ML training form can call `/saas/v1/admin/intelligence/ml-training/synthetic` when `SAAS_ML_ENABLED=true` and register the resulting artifact in shadow mode.
- The Data Intelligence panel can generate auto-labels, recompute feature pipelines, build Postgres ML datasets, and train autolabel models through `/auto-labels/generate`, `/feature-pipelines/recompute`, `/ml-datasets/build`, and `/ml-training/autolabel`.
- The ML Infrastructure panel shows ML enablement, shadow/auto-train flags, ML service URL, MLflow URI, Qdrant URL, jobs, artifacts, inference runs and drift snapshots.
- The Training readiness panel shows labeled feedback counts plus auto-label counts/readiness by tenant/model/prediction type.
- Feature modes are controlled through `/saas/v1/admin/intelligence/tenants/{tenant_id}/features`.
- Model metrics can be recalculated through `/saas/v1/admin/intelligence/model-metrics/recompute`.
- `AI Predictivo`, `Operacion`, and `Salud` can trigger `/saas/v1/admin/operations/intelligence/process` for manual event derivation, feature recompute, and gated predictions.
- Plan editor and tenant feature flag catalog include the new premium AI feature keys.

## Phase 16 Real-Time Intelligence UI

- Tenant `IntelligencePanel.jsx` now includes `AI Real-Time Intelligence Layer` inside `Inteligencia`.
- The tenant panel calls `/saas/v1/intelligence/realtime/center`, registers a live session through `/realtime/sessions`, updates user cursors through `/realtime/cursor`, and closes the session when possible.
- Tenant UI uses polling every 8 seconds by default and merges new sanitized events by id; backend bounded SSE exists for future clients but is not required by the current UI.
- Tenant surfaces include realtime status, session/cursor state, events 15m/1h, recent predictions, open recommendations, operational anomalies, Trust AI signals, advisory alerts, live event feed and event mix.
- Admin `AI Predictivo` now also calls `/saas/v1/admin/intelligence/realtime` and can refresh snapshots through `/saas/v1/admin/intelligence/realtime/metrics/refresh`.
- Admin realtime overview shows tenant activity, active sessions and per-feature modes for `realtime_intelligence_layer`, `realtime_event_stream`, `realtime_ai_alerts`, and `realtime_intelligence_dashboard`.
- No frontend realtime view sends messages, mutates CRM, changes campaigns, runs workflows, promotes models or triggers remediation.

## Phase 19/20 Intelligence UI

- Tenant `IntelligencePanel.jsx` now includes `Autonomous Revenue Engine`.
- The tenant panel calls `/saas/v1/intelligence/revenue/center`, `/revenue/analyze`, and opportunity action endpoints for approve/execute/dismiss.
- Revenue UI shows access mode, policy controls, CRM/revenue metrics, detected opportunities, forecasts, reports and playbooks.
- Tenant operators can configure autonomy level, currency, revenue goal, monthly action cap and optional playbook action-type allowlist from the Intelligence panel.
- Revenue actions are explicit human clicks and update only control-plane opportunity status.
- Tenant `IntelligencePanel.jsx` now includes `AI Enterprise Memory Network`.
- The memory panel calls `/saas/v1/intelligence/memory-network/center`, `/memory-network/sync`, `/memory-network/policy`, `/memory-network/export`, `/memory-network/import`, node review and node delete endpoints.
- Memory UI shows graph node counts, edge counts, sync runs, routing guidance, policy controls, export/import JSON controls and review buttons for publish/reject/archive/delete.
- Policy controls cover privacy mode, retention days, allowed scopes, customer-content review, cross-agent retrieval and auto-capture preference. Backend remains authoritative for feature gates and policy enforcement.
- Imported memory JSON enters as reviewable `candidate` nodes; delete requires an explicit human confirmation in the browser.
- Admin `AI Predictivo` inherits Phase 19/20 feature keys through the existing feature catalog/defaults; no separate Admin page was added.
- No UI path sends customer messages, mutates CRM, activates campaigns/workflows/triggers, calls payment providers, publishes cross-tenant memory or bypasses backend premium gating.

## Phase 24.1 API Settings UI

- Tenant Settings > APIs now uses compact provider tiles for AI, TTS and channel/commerce credentials.
- Unsaved providers are shown as "Anadir" tiles instead of full credential cards.
- Clicking a provider tile expands the credential/model controls for that provider.
- Saved credentials or saved selected models remain visible automatically, preserving existing tenant setup.
- AI provider reference lists now include cost/role guidance for Gemini Flash Lite, Groq low-latency classification, Mistral short tasks, OpenRouter fallback and Kimi reasoning/vision-capable models.
- No frontend flow uploads media to AI yet; Inbox media remains under the existing composer/media upload behavior.

## Phase 24.2 Voice Intelligence UI

- Tenant Settings > IA now includes `Analisis de audios`.
- The Voice Intelligence selector is intentionally restricted to providers with a validated audio path; current runtime support is Google/Gemini.
- The linked model card shows the selected Gemini model and whether an encrypted credential exists.
- Inbox audio message bubbles include a `Voice Intelligence` panel.
- Audio panels can call `POST /saas/v1/media/messages/{message_id}/voice/analyze` for analyze/reanalyze.
- Results are displayed from `payload_json.voice_intelligence`:
  - summary.
  - sentiment.
  - intent.
  - urgency.
  - confidence.
  - recommended action.
  - expandable transcript.
- The UI updates only the local message payload after analysis. It does not auto-create CRM tasks, send replies, launch campaigns, or hand off agents.

## Phase 24.3 Vision Intelligence UI

- Tenant Settings > IA now includes `Vision Intelligence`.
- The selector offers Google/Gemini, OpenRouter and Kimi for image analysis; documents remain routed by the backend to Gemini in this phase.
- The linked model card shows the selected image/document model and whether an encrypted credential exists.
- Inbox image, document and file message bubbles include a `Vision Intelligence` panel.
- Vision panels call `POST /saas/v1/media/messages/{message_id}/vision/analyze` for analyze/reanalyze.
- Results are displayed from `payload_json.vision_intelligence`:
  - summary.
  - visual description.
  - extracted text.
  - document type.
  - intent.
  - urgency.
  - confidence.
  - topics.
  - recommended action.
- The UI updates only the local message payload after analysis. It does not search the web, send media, mutate CRM records, launch campaigns or hand off agents.

## Phase 24.4 Web/Image Search Intelligence UI

- Tenant Settings > APIs includes compact provider tiles for Tavily, Brave Search API and SerpAPI.
- Tenant Settings > IA includes a `Busqueda web/imagen` provider selector and shows whether the selected provider credential exists.
- The Inbox CRM side panel includes a `Web/Image Search Intelligence` card for the selected conversation.
- Search supports `Mixta`, `Web` and `Imagen` modes, a query box, provider selector and bounded result loading.
- Recent runs are loaded with the selected conversation messages through `/saas/v1/media/search/runs`.
- Result cards show source title, provider, snippet, URL, optional image/thumbnail, license/source metadata when available, safety status and approval status.
- Human review buttons call `/saas/v1/media/search/results/{result_id}/approval` for approve/reject.
- The UI does not auto-send external links/images, create CRM records, launch campaigns, execute workflows or hand off agents from search results.

## Phase 24.5 Agent Multimodal Tools UI

- `AiAgentsPanel.jsx` now shows an Agent OS section for `Herramientas multimodales para agentes`.
- The section lists `media.voice_analyze`, `media.vision_analyze`, and `media.web_image_search` from `/saas/v1/agents/multimodal-tools/catalog` or the Agent OS overview.
- Users can execute a selected agent tool through `/saas/v1/agents/{agent_id}/multimodal-tools/execute`.
- Voice and vision require a real Inbox `message_id`; search requires a query and can include conversation/message context, provider and limit.
- Recent agent multimodal runs are loaded from `/saas/v1/agents/{agent_id}/multimodal-tools/runs`.
- Search result cards keep approve/reject actions wired to `/saas/v1/media/search/results/{result_id}/approval`.
- The UI explicitly keeps the flow contextual/read-only: it does not send replies, mutate CRM, launch campaigns, execute workflows or train models from tool output.

## Phase 24.6 Multimodal Memory & Training Events UI

- `AiAgentsPanel.jsx` now shows `Memoria y training multimodal` inside Agent OS for the selected agent/runtime overview.
- The UI loads curated events from `/saas/v1/agents/multimodal-memory/events`.
- Operators can run `/saas/v1/agents/multimodal-memory/sync` to capture recent voice, vision, approved search and completed agent tool outputs as sanitized memory events.
- Cards show memory events, training-ready counts, RAG candidates and already materialized events.
- Event rows show source kind, approval state, training/RAG/agent-memory eligibility and compact features.
- Materialization buttons call `/saas/v1/agents/multimodal-memory/events/{event_id}/materialize` to send an event to Knowledge/RAG or collective memory.
- If a row may contain customer content, the UI asks for explicit confirmation before sending it to Knowledge/RAG or collective memory.
- The UI does not auto-send media/references, mutate CRM, execute workflows/campaigns or start model training.

## Phase 24.7 Inbox Multimodal UX

- `App.jsx` Inbox CRM side panel now includes `Panel de analisis Inbox`.
- The panel summarizes conversation-scoped voice analysis, vision analysis, multimodal memory highlights and approved/pending external reference counts.
- The panel can refresh or sync conversation multimodal memory through `/agents/multimodal-memory/events` and `/agents/multimodal-memory/sync`.
- Approved visual references from Web/Image Search appear in a dedicated strip with `Usar` and `Enviar`.
- Web/Image Search result cards now expose `Usar`, `Enviar`, `Aprobar y usar`, and `Aprobar y enviar`.
- `Usar` inserts a prepared approved reference into the existing composer.
- `Enviar` uses the existing CRM message endpoint after human click/confirmation; it does not create a separate outbound path.
- The UI still cannot use blocked sources and does not auto-send from agents or workers.

## Phase 24.9-24.10 Multimodal Observability And Rollout UI

- Tenant `IntelligencePanel.jsx` now loads:
  - `/saas/v1/intelligence/multimodal/observability/center`.
  - `/saas/v1/intelligence/multimodal/rollout/center`.
- `Phase 24.9 Observability` shows multimodal request volume, estimated cost, P95/average latency, error count, quality score, provider rows and recent source usage.
- Operators can preview or persist an observability snapshot through `/saas/v1/intelligence/multimodal/observability/refresh`.
- `Phase 24.10 Safe Rollout` lets authorized tenants configure rollout policy fields: feature key, modality, provider code, mode, canary percent, p95/error/quality thresholds and demo fallback.
- Rollout policy updates call `/saas/v1/intelligence/multimodal/rollout/policy`.
- Recent rollout events are visible in the same panel for audit.
- Admin `AI Predictivo` Phase 24 gating includes the new feature keys for observability, cost observability, quality monitoring, safe rollout and canary by tenant/plan.
- The UI remains backend-authoritative: if the tenant does not have the feature, the panels fail closed/read-empty rather than bypassing gates.

## Phase 12 Admin Performance UI

- Admin `AdminApp.jsx` now includes the `Performance` view backed by `/saas/v1/admin/reliability/overview`.
- The view shows Reliability status, SLO status, backlog, error count, expected index coverage and backup readiness.
- Safe actions available from UI: record SLO snapshot, run load smoke drill, run backup readiness drill, run retention dry-run and process the reliability worker tick.
- Tables show SLO metrics, backpressure by queue, PostgreSQL index audit, retention policies, cleanup runs, drills and snapshots.
- Admin `Operacion` and `Salud` can also run `/saas/v1/admin/operations/reliability/process`.
- The UI intentionally does not expose destructive retention runs; destructive cleanup remains backend-role gated and must be called explicitly.

## Phase 1 Auth UI

- Tenant app supports login, email OTP MFA challenge verification, register/trial creation, password recovery, password reset from `?reset_token=`, password change, 2FA email settings, and privacy export/delete-request actions.
- Admin app supports login, email OTP MFA challenge verification, local bootstrap, password recovery, password reset from `?reset_token=`, and the Phase 13 `Security` view.
- Turnstile widgets are shown on auth/recovery/reset/bootstrap forms when `VITE_CAPTCHA_ENABLED=true` and `VITE_TURNSTILE_SITE_KEY` is present.
- The frontend sends CAPTCHA tokens to the backend; the backend remains the authority when CAPTCHA is enabled.

## Phase 13 Security UI

- Tenant auth can enter an MFA challenge state after `/saas/v1/auth/login`; verification uses `/saas/v1/auth/login/verify-otp`.
- Tenant Settings > Seguridad uses email OTP only; no TOTP/authenticator-app UI is present.
- Tenant Settings exposes JSON exports for current account and selected customer/conversation plus a non-destructive privacy delete request action.
- Admin auth can enter an MFA challenge state after `/saas/v1/admin/auth/login`; verification uses `/saas/v1/admin/auth/login/verify-otp`.
- Admin `Security` uses `/saas/v1/admin/auth/security`, `/saas/v1/admin/security/compliance`, and `/saas/v1/admin/audit/export.csv`.
- Admin `Security` shows MFA state, SMTP state, users/admins with 2FA, webhook signature coverage, security events and privacy-request counts.

## Phase 14 Localization And Product Ops UI

- Tenant app has a local Spanish baseline catalog at `frontend/src/i18n.js`; default locale is `es-CO`, optional override is `VITE_APP_LOCALE`.
- Admin app has a local Spanish baseline catalog at `admin-frontend/src/i18n.js`; default locale is `es-CO`, optional override is `VITE_ADMIN_LOCALE`.
- Critical top-level tenant/admin navigation, auth shell labels, page titles, settings tabs, Meta connection copy, AI Agents, AI Ecosystem and Admin Performance labels were normalized away from mixed English fragments.
- `saas-version/scripts/phase14-copy-audit.mjs` blocks regressions for critical UI terms such as `Dashboard`, `Overview`, `Performance`, `AI Agents`, `AI Ecosystem`, `Facebook Login`, `Footer text` and related strings in active source files.
- `saas-version/scripts/phase14-release-check.mjs` validates Phase 14 memory/docs/files and runs the copy audit before release handoff.
- Frontend package scripts expose `phase14:copy-audit` and `phase14:release-check` without adding dependencies.

## Phase 18 Workflow Composer UI

- Tenant `App.jsx` exposes the `Composer` navigation view through `WorkflowComposerPanel.jsx`.
- `WorkflowComposerPanel.jsx` calls `/saas/v1/workflow-composer/*` for overview, templates, workflow CRUD, preflight, simulation, approval, activation and version rollback.
- UI surfaces include template library, workflow list, graph node/edge editor, config JSON editor, preflight inspector, simulation input/result, governance controls and version history.
- Demo mode keeps the page visible but disables create/update/preflight/simulate/approval/activation when backend access is not full.
- `frontend/src/i18n.js` includes `nav.composer` and `page.composer.*`.
- `frontend/src/styles.css` includes Composer layouts and sidebar overflow handling so the added nav item remains reachable in shorter viewports.

## Phase 22 AI Trust UI

- Tenant `App.jsx` exposes the `Trust AI` navigation view through `TrustCenterPanel.jsx`.
- `TrustCenterPanel.jsx` calls `/saas/v1/trust-center/*` for overview, policies, risk assessments, model cards, incidents, audits and reports.
- UI surfaces include trust overview, feature/mode state, governance controls, policy attestation, risk scan preview/persist, model-card registry, incident workflow, audit history and compliance report generation.
- Demo mode can show read-only/preview trust state; mutation buttons rely on backend full-mode checks.
- Admin `AdminApp.jsx` exposes `Trust AI` backed by `/saas/v1/admin/trust-center/overview` for aggregate tenant risks, incidents, source signals and recent governance audit records.
- `frontend/src/i18n.js` and `admin-frontend/src/i18n.js` include the new navigation labels.

## Billing Provider UI

- Admin `Facturacion` now includes `Pasarelas de pago` cards for Wompi and Mercado Pago.
- Each card has switches for habilitar, modo prueba, proveedor predeterminado and debug temporal.
- Credentials are split into Prueba and Produccion sections. Secret inputs are not prefilled; leaving them blank preserves the encrypted backend value.
- Tenant Settings > Plan now shows a payment trust footer with Wompi, Mercado Pago and accepted payment badges before checkout history.

## Frontend Safety Rules

- Do not change API paths without checking backend routers under `app_saas`.
- Preserve token key names unless intentionally migrating sessions.
- Keep admin auth separate from tenant user auth.
- Do not infer root `frontend/` behavior for SaaS.
- Search for consumers before changing response shapes: `rg "<field-or-endpoint>" saas-version/frontend saas-version/admin-frontend saas-version/backend/app_saas`.
