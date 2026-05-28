# FRONTEND_BACKEND_FLOW

Scope: SaaS only.

## Client App Flow

```mermaid
flowchart TB
  App["frontend/src/App.jsx"] --> Auth["/saas/v1/auth/*"]
  App --> Dashboard["/saas/v1/dashboard/overview"]
  App --> Panels["CRM Campaigns Broadcast Ads Agents Settings"]
  Panels --> API["/saas/v1 domain endpoints"]
  API --> DB["PostgreSQL"]
```

## Phase 4 Inbox Flow

```mermaid
flowchart LR
  Inbox["Client Inbox"] --> Filters["channel/search/queue filters"]
  Filters --> Conversations["GET /conversations"]
  Inbox --> Messages["GET/POST /conversations/:id/messages"]
  Inbox --> Read["POST /conversations/:id/read"]
  Inbox --> Assignment["PATCH /customers/:id assigned_user_id"]
  Inbox --> Status["GET /conversations/:id/status-events"]
  Inbox --> CRMConfig["GET /crm/config"]
  Inbox --> Timeline["GET /conversations/:id/timeline"]
  Inbox --> Dedupe["GET /customers/:id/dedupe-candidates + POST merge"]
  Inbox --> Comments["GET/POST /social/comments/*"]
  Conversations --> DB["saas_conversations"]
  Messages --> MessageDB["saas_messages + outbound queue"]
  Status --> StatusDB["saas_message_status_events"]
  CRMConfig --> CRMDB["saas_crm_custom_fields + pipeline stages"]
  Timeline --> CRMEvents["messages/tasks/status/timeline events"]
  Dedupe --> MergeAudit["saas_crm_merge_events"]
  Comments --> SocialDB["social_comments/social_posts"]
```

## Admin App Flow

```mermaid
flowchart TB
  AdminDomain["admin.scentra-ai.online"] --> AdminNginx["admin-frontend Nginx"]
  AdminNginx --> AdminApp["admin-frontend/src/AdminApp.jsx"]
  AdminApp --> AdminAuth["/saas/v1/admin/auth/*"]
  AdminApp --> AdminAPI["/saas/v1/admin/*"]
  AdminApp --> Salud["Observability Salud view"]
  Salud --> Health["/admin/observability/health"]
  Salud --> Dead["/admin/observability/dead-letter/*"]
  Salud --> QueueOps["/admin/operations/*/process"]
  AdminAPI --> DB["PostgreSQL"]
  AdminAPI --> Ops["queues observability billing audit"]
```

## Phase 6 Knowledge UI Flow

```mermaid
flowchart LR
  Settings["Client Ajustes > IA"] --> Sources["GET /knowledge/sources"]
  Settings --> Health["GET /knowledge/health"]
  Settings --> Upload["POST /knowledge/upload PDF/TXT/CSV"]
  Settings --> Crawl["POST /knowledge/url"]
  Settings --> Search["POST /knowledge/search"]
  Settings --> Eval["POST /knowledge/evaluate"]
  Settings --> EvalList["GET /knowledge/evaluations"]
  Search --> Citations["citations + vector score"]
  Eval --> Quality["quality score + pass/fail"]
```

## Phase 7 Campaigns UI Flow

```mermaid
flowchart LR
  Campaigns["CampaignsPanel"] --> Quiet["Global quiet hours"]
  Campaigns --> CampaignPreflight["Campaign preflight"]
  Campaigns --> FlowPreflight["Flow preflight"]
  Campaigns --> FlowAB["Flow A/B report"]
  Builder["SaasTriggerBuilderPanel"] --> TriggerPreflight["Trigger preflight"]
  Builder --> Sim["Trigger simulator"]
  Builder --> Versions["Version history + restore"]
  Builder --> TriggerAB["Trigger A/B report"]
  Quiet --> API["/saas/v1/campaigns/*"]
  CampaignPreflight --> API
  FlowPreflight --> API
  Builder --> API
  API --> DB["PostgreSQL campaign tables"]
```

## Phase 8 Agents UI Flow

```mermaid
flowchart LR
  AgentsPanel["AiAgentsPanel"] --> Catalog["GET /agents/catalog"]
  AgentsPanel --> Custom["POST /agents Custom Agent"]
  AgentsPanel --> Prompt["PATCH /agents/{id} prompt variables"]
  AgentsPanel --> Preflight["GET /agents/{id}/preflight"]
  AgentsPanel --> Activate["POST /agents/{id}/activate"]
  Inbox["App.jsx Inbox"] --> AgentList["GET /agents active"]
  Inbox --> Filter["GET /conversations?agent_id"]
  Inbox --> Assign["PATCH /conversations/{id}/ai-agent"]
  Assign --> Owner["assigned_ai_agent_id / ai_owner_mode"]
  Owner --> Runtime["Conversation AI owner"]
```

## Phase 9 Billing UI Flow

```mermaid
flowchart LR
  Plan["Client Settings > Plan"] --> Overview["GET /billing/overview"]
  Plan --> Checkout["POST /billing/checkout"]
  Plan --> Invoices["GET /billing/invoices"]
  Invoices --> Pdf["GET /billing/invoices/{id}/pdf"]
  Admin["Admin Billing"] --> AdminInvoices["GET /admin/billing/invoices"]
  Admin --> Credits["POST /admin/billing/credits"]
  Admin --> Lifecycle["POST /admin/billing/lifecycle/sync"]
  AdminInvoices --> AdminPdf["GET /admin/billing/invoices/{id}/pdf"]
```

## Phase 10 Verticalization UI Flow

```mermaid
flowchart LR
  Register["Client register form"] --> PublicPacks["GET /verticals/public-packs"]
  Settings["Client Settings > Industria"] --> State["GET /verticals/state"]
  Settings --> Apply["POST /verticals/apply"]
  Apply --> Refresh["reload vertical state + CRM config + dashboard + session"]
  Admin["Admin tenant detail"] --> Industry["PATCH /admin/tenants/{id} industry_code"]
  Industry --> Pack["backend applies pack without auto agents"]
```

## Phase 11 Intelligence Admin Flow

```mermaid
flowchart LR
  Client["Tenant Inteligencia"] --> State["GET /intelligence/state"]
  Client --> Features["GET/POST /intelligence/features"]
  Client --> Predict["POST /intelligence/predict"]
  Client --> Predictions["GET /intelligence/predictions"]
  Client --> Feedback["POST /intelligence/predictions/{id}/feedback"]
  Client --> Recs["GET/POST /intelligence/recommendations"]
  Admin["Admin AI Predictivo"] --> Catalog["GET /admin/intelligence/catalog"]
  Admin --> Tenants["GET /admin/intelligence/tenants"]
  Admin --> Toggle["PATCH /admin/intelligence/tenants/{id}/features"]
  Admin --> Premium["GET /admin/intelligence/premium-gating"]
  Admin --> PlanLimit["PATCH /admin/intelligence/plans/{plan}/features"]
  Admin --> ProviderPolicy["PATCH /admin/intelligence/provider-policies"]
  Admin --> ModelOps["GET/POST /admin/intelligence/model-metrics"]
  Admin --> Registry["GET/PATCH /admin/intelligence/models"]
  Admin --> Process["POST /admin/operations/intelligence/process"]
  Toggle --> Grants["saas_intelligence_feature_grants"]
  PlanLimit --> PlanLimits["saas_intelligence_plan_feature_limits"]
  ProviderPolicy --> ProviderPolicies["saas_ai_provider_policies"]
  Premium --> ProviderCosts["provider costs + credential summaries"]
  Process --> Worker["workers/intelligence.py"]
  Catalog --> FeatureUI["disabled/demo/full controls"]
  Tenants --> Metrics["predictions 30d + usage + recommendations"]
  ModelOps --> Quality["sample + feedback + accuracy + drift"]
  Registry --> Rollout["status + shadow/canary/production + readiness"]
  State --> Grants["tenant grants + quotas"]
  Predict --> PredictionsDb["saas_intelligence_predictions"]
  Feedback --> ModelMetrics["saas_intelligence_model_metrics"]
  Recs --> Recommendations["saas_intelligence_recommendations"]
```

## Phase 16 Real-Time Intelligence UI Flow

```mermaid
flowchart LR
  Tenant["IntelligencePanel"] --> Center["GET /intelligence/realtime/center"]
  Tenant --> Session["POST /intelligence/realtime/sessions"]
  Tenant --> Cursor["PATCH /intelligence/realtime/cursor"]
  Tenant --> Poll["8s polling merge"]
  Admin["Admin AI Predictivo"] --> Overview["GET /admin/intelligence/realtime"]
  Admin --> Snapshot["POST /admin/intelligence/realtime/metrics/refresh"]
  Center --> LiveCards["status + alerts + event feed + event mix"]
  Session --> SessionState["live session"]
  Cursor --> CursorState["last seen event"]
  Overview --> AdminCards["tenant activity + feature modes"]
```

- Tenant UI reads sanitized live signals only.
- Admin UI reads aggregate per-tenant live activity and writes metric snapshots only.
- Neither UI can execute realtime alerts or mutate provider/customer runtime from Phase 16.

## Phase 24.1 API Settings Flow

```mermaid
flowchart LR
  Settings["Settings > APIs"] --> Tiles["Provider tiles"]
  Tiles --> Expanded["Expanded credential/model card"]
  Expanded --> Save["POST /api-credentials"]
  Expanded --> Models["GET /api-credentials/{provider}/models"]
  Save --> Encrypted["Encrypted tenant credential"]
  Models --> Selected["selected_model metadata"]
  Selected --> Gateway["AI Gateway model resolution"]
```

- Unsaved providers stay collapsed until the tenant clicks "Anadir".
- Saved credentials or selected models remain visible automatically.
- Model loading still uses the existing credential/model endpoints.

## Phase 24.2 Voice Intelligence UI Flow

```mermaid
flowchart LR
  Settings["Settings > IA"] --> Provider["Voice analysis provider"]
  Provider --> Credential["selected Gemini model/credential state"]
  Inbox["Inbox audio message"] --> Button["Analizar voz / Reanalizar"]
  Button --> API["POST /media/messages/{id}/voice/analyze"]
  API --> Payload["payload_json.voice_intelligence"]
  Payload --> Card["summary + sentiment + intent + transcript"]
```

- Voice analysis updates the local message payload after the API returns.
- The UI does not create CRM tasks, send replies or trigger automations from the voice card.

## Phase 24.3 Vision Intelligence UI Flow

```mermaid
flowchart LR
  Settings["Settings > IA"] --> Provider["Vision Intelligence provider"]
  Provider --> Credential["selected vision model/credential state"]
  Inbox["Inbox image/document/file message"] --> Button["Analizar media / Reanalizar"]
  Button --> API["POST /media/messages/{id}/vision/analyze"]
  API --> Payload["payload_json.vision_intelligence"]
  Payload --> Card["summary + OCR text + intent + visual description"]
```

- Vision analysis updates the local message payload after the API returns.
- The UI does not search the web, send images/documents, create CRM tasks, trigger automations or hand off agents from the vision card.

## Phase 24.4 Web/Image Search Intelligence UI Flow

```mermaid
flowchart LR
  SettingsAPI["Settings > APIs"] --> SearchCreds["Tavily / Brave / SerpAPI credentials"]
  SettingsAI["Settings > IA"] --> Provider["Web/Image Search provider"]
  Inbox["Inbox CRM side panel"] --> Query["Search query + type"]
  Query --> Search["POST /media/search"]
  Inbox --> Runs["GET /media/search/runs"]
  Runs --> Cards["source cards + optional image preview"]
  Cards --> Review["approve / reject"]
  Review --> API["POST /media/search/results/{id}/approval"]
```

- Search runs are scoped to the active tenant and optional selected conversation.
- Result cards are advisory source references and require human review.
- The UI does not auto-send links/images, mutate CRM, launch campaigns, execute workflows or hand off agents from search results.

## Phase 24.5 Agent Multimodal Tools UI Flow

```mermaid
flowchart LR
  AgentOS["AI Agents > Agent OS"] --> Catalog["GET /agents/multimodal-tools/catalog"]
  AgentOS --> Runs["GET /agents/{agent_id}/multimodal-tools/runs"]
  AgentOS --> Execute["POST /agents/{agent_id}/multimodal-tools/execute"]
  Execute --> Media["voice / vision / search backend"]
  Runs --> Cards["tool run cards"]
  Cards --> Review["approve/reject search source"]
  Review --> SearchApproval["POST /media/search/results/{id}/approval"]
```

- The UI requires real Inbox ids for voice/vision tools and a query for web/image search.
- Agent tool output is shown as run history; it does not auto-send customer messages or mutate CRM.
- Search source approval remains human-in-the-loop before any agent prompt can use external source context.

## Phase 24.6 Multimodal Memory UI Flow

```mermaid
flowchart LR
  AgentOS["AI Agents > Agent OS"] --> Events["GET /agents/multimodal-memory/events"]
  AgentOS --> Sync["POST /agents/multimodal-memory/sync"]
  AgentOS --> Materialize["POST /agents/multimodal-memory/events/{id}/materialize"]
  Events --> Cards["memory/training/RAG event rows"]
  Sync --> Cards
  Cards --> Confirm["customer-content confirmation"]
  Confirm --> Materialize
  Materialize --> Refresh["reload memory events"]
```

- The UI shows counts for memory events, training-ready rows, RAG candidates and materialized rows.
- Operators explicitly choose whether to send a row to Knowledge/RAG or collective memory.
- The UI does not auto-send references, mutate CRM, launch campaigns, execute workflows or start model training.

## Phase 24.8-24.10 Admin Premium Gating UI Flow

```mermaid
flowchart LR
  Admin["Admin AI Predictivo"] --> Overview["GET /admin/intelligence/premium-gating"]
  Overview --> TenantCards["tenant Phase 24 modes/quotas"]
  Overview --> PlanCards["plan Phase 24 modes/quotas"]
  Overview --> ProviderCards["provider policies + cost summary"]
  TenantCards --> TenantGrant["PATCH /admin/intelligence/tenants/{id}/features"]
  PlanCards --> PlanPatch["PATCH /admin/intelligence/plans/{plan}/features"]
  ProviderCards --> ProviderPatch["PATCH /admin/intelligence/provider-policies"]
```

- Admin sees tenant grants, plan limits, provider policies, credential readiness and estimated monthly AI/search cost in one view.
- The UI never displays decrypted provider secrets.
- Cost controls are metadata-driven and require reviewed provider pricing before commercial reporting.

## Phase 24.9-24.10 Tenant Observability And Rollout UI Flow

```mermaid
flowchart LR
  Tenant["Tenant Inteligencia"] --> Obs["GET /intelligence/multimodal/observability/center"]
  Tenant --> Refresh["POST /intelligence/multimodal/observability/refresh"]
  Tenant --> Rollout["GET /intelligence/multimodal/rollout/center"]
  Tenant --> Patch["PATCH /intelligence/multimodal/rollout/policy"]
  Obs --> Cards["cost/latency/errors/quality/source cards"]
  Refresh --> Cards
  Rollout --> Form["safe rollout policy form"]
  Patch --> Form
```

- Observability panels read aggregate/safe metadata only.
- Rollout controls remain backend-authoritative and require feature access plus explicit policy enablement.

## Session Storage

- Client access token: `scentra_ai_access_token`
- Client refresh token: `scentra_ai_refresh_token`
- Admin access token: `scentra_admin_access_token`

## Env Boundary

- Both frontends require `VITE_API_BASE`.
- Admin can use `VITE_CLIENT_APP_BASE`.
- Captcha UI uses `VITE_CAPTCHA_ENABLED` and `VITE_TURNSTILE_SITE_KEY`.
- Admin local bootstrap UI uses `VITE_ADMIN_BOOTSTRAP_ENABLED` or localhost runtime detection; production uses the seed command/service instead.
