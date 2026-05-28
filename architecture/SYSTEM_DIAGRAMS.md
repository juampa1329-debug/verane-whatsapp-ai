# SYSTEM_DIAGRAMS

Scope: SaaS only. Source root: `saas-version/`.

## High-Level Map

```mermaid
flowchart LR
  Client["SaaS Client React/Vite"] --> API["FastAPI app_saas /saas/v1"]
  AdminDomain["admin.scentra-ai.online"] --> Admin["Admin React/Vite + Nginx"]
  Admin --> API
  API --> DB["PostgreSQL"]
  API --> Meta["Meta WhatsApp / Instagram"]
  API --> Woo["WooCommerce"]
  API --> AI["AI/TTS Providers"]
  API --> Billing["Stripe / MercadoPago / Wompi"]
  Webhooks["Provider Webhooks"] --> API
  API --> Queue["DB-backed queues/status tables"]
  Worker["SaaS worker runner"] --> Queue
  Worker --> DB
  Worker --> Heartbeats["Worker heartbeats"]
  Worker --> Meta
  Worker --> AI
  Worker --> BillingLifecycle["Billing lifecycle"]
  Admin --> Observability["Admin observability/dead-letter"]
  Observability --> DB
  Admin --> Reliability["Admin Performance/Reliability"]
  Reliability --> DB
  Client --> Realtime["Tenant Real-Time Intelligence"]
  Admin --> RealtimeAdmin["Admin Realtime Intelligence"]
  Realtime --> DB
  RealtimeAdmin --> DB
```

## Code Map

```mermaid
flowchart TB
  Root["saas-version"] --> Backend["backend/app_saas"]
  Root --> Frontend["frontend"]
  Root --> AdminFrontend["admin-frontend"]
  Root --> Migrations["migrations"]
  Root --> Compose["docker-compose.saas.yml"]
  Backend --> Main["main.py"]
  Backend --> Shared["shared security/secrets/captcha"]
  Backend --> Domains["auth tenants crm campaigns broadcasts ads integrations billing ai agents knowledge intelligence webhooks admin"]
  Backend --> Workers["workers"]
```

## Boundaries

- SaaS API boundary: `/saas/v1`.
- SaaS DB boundary: migrations in `saas-version/migrations`.
- SaaS frontend boundary: `saas-version/frontend` and `saas-version/admin-frontend`.
- Non-SaaS root apps are out of scope.

## Phase 4 Inbox Map

```mermaid
flowchart TB
  Inbox["Client Inbox"] --> DM["DM conversations"]
  Inbox --> CM["Comments tab"]
  DM --> CRM["CRM side panel / assignment / SLA / tasks"]
  DM --> Composer["text media audio product emoji composer"]
  DM --> Status["Meta status events"]
  CM --> CommentAI["comment reply / reaction / AI suggestion"]
  Composer --> Outbound["outbound queue"]
  Webhooks["Meta webhooks"] --> Ingest["workers.ingest"]
  Ingest --> DM
  Ingest --> CM
  Ingest --> Status
```

## Phase 5 CRM Map

```mermaid
flowchart TB
  CRM["Customers / Inbox CRM"] --> Config["/crm/config"]
  Config --> Fields["saas_crm_custom_fields"]
  Config --> Pipeline["saas_crm_pipelines + stages"]
  CRM --> Customer["saas_conversations"]
  Customer --> CustomValues["profile_json.custom_fields"]
  Customer --> Timeline["messages + tasks + status + timeline events"]
  Customer --> Dedupe["dedupe candidates"]
  Dedupe --> Merge["controlled merge"]
  Merge --> Audit["saas_crm_merge_events"]
  AI["Conversation AI"] --> CRMContext["CRM + custom-field context"]
  AI --> Customer
```

## Phase 6 Knowledge/RAG Map

```mermaid
flowchart TB
  KnowledgeUI["Settings Knowledge UI"] --> Sources["saas_knowledge_sources"]
  KnowledgeUI --> Upload["PDF/TXT/CSV upload"]
  KnowledgeUI --> Crawl["Safe URL ingestion"]
  Sources --> Chunks["saas_knowledge_chunks"]
  Chunks --> Vector["vector_json sparse vectors"]
  KnowledgeUI --> Search["RAG search"]
  Search --> Logs["retrieval logs"]
  KnowledgeUI --> Eval["RAG evaluation"]
  Eval --> EvalDB["saas_knowledge_evaluations"]
  AI["Conversation AI"] --> Search
  Search --> Citations["internal citations"]
```

## Phase 8 AI Agents Map

```mermaid
flowchart TB
  AgentsUI["AI Agents UI"] --> Registry["saas_ai_agents"]
  AgentsUI --> Preflight["preflight/evals"]
  AgentsUI --> MemoryVault["agent memory vault"]
  AgentsUI --> Collective["collective memory"]
  Inbox["Inbox"] --> Assignment["manual AI agent assignment"]
  Orchestrator["agent orchestrator"] --> Assignment
  Assignment --> Conversation["saas_conversations AI owner"]
  ConversationAI["Conversation AI"] --> Owner["runtime selected agent"]
  Owner --> Prompt["rendered system prompt"]
  Owner --> Collective
  Owner --> Budget["budget hard stop"]
  Budget --> Gateway["AI gateway"]
  Gateway --> ModelFallback["retryable model fallback"]
  ModelFallback --> ProviderFallback["provider fallback"]
  ProviderFallback --> Runs["saas_ai_runs audit"]
```

- The orchestrator selects ownership only; generated replies still pass through Conversation AI and the shared AI Gateway failover path.
- Provider/model failover never changes the assigned AI owner and does not fall back to general AI when an assigned agent is unavailable.

## Phase 24.1 Multimodal Gateway Map

```mermaid
flowchart TB
  FutureCaller["Future media/agent caller"] --> Request["GatewayRequest attachments[]"]
  Request --> Gemini["Gemini inline_data/file_data"]
  Request --> Compat["OpenAI-compatible image_url"]
  Request --> Runs["AI run safe attachment metadata"]
  ApiSettings["Tenant Settings APIs"] --> Tiles["expandable provider tiles"]
  Tiles --> Creds["encrypted credentials + selected model"]
  Creds --> Request
```

- This started as a gateway foundation only; Phase 24.2/24.3 now use it for explicit Inbox audio/image/document analysis, Phase 24.4 adds approval-first web/image search, Phase 24.5 adds read-only agent multimodal tools, Phase 24.6 stores sanitized multimodal memory/training/RAG signals, Phase 24.7 adds human-operated approved-reference UX, Phase 24.8 adds Admin provider/plan gating, and Phase 24.9/24.10 add observability plus safe rollout. Automatic AI/agent customer media sends remain out of scope until a separate approved design.

## Phase 9 Billing Map

```mermaid
flowchart TB
  TenantUI["Tenant Plan UI"] --> Checkout["checkout sessions"]
  TenantUI --> TenantInvoices["invoice list/PDF"]
  AdminUI["Admin Billing UI"] --> Credits["manual credits"]
  AdminUI --> AdminInvoices["manual/list/PDF invoices"]
  Providers["Stripe / MercadoPago / Wompi"] --> Webhook["signed billing webhooks"]
  Webhook --> Events["saas_billing_provider_events"]
  Events --> State["subscriptions/payments/invoices"]
  Lifecycle["billing lifecycle worker"] --> State
  State --> TenantStatus["tenant status/plan"]
  TenantStatus --> WriteGuard["unsafe write guard"]
```

## Phase 10 Verticalization Map

```mermaid
flowchart TB
  Catalog["Industry pack catalog"] --> Apply["verticals.service apply_industry_pack"]
  Register["Tenant registration/create"] --> Apply
  Client["Client Industria settings"] --> Apply
  Admin["Admin tenant industry change"] --> Apply
  Apply --> Tenant["saas_tenants industry_code + vertical snapshot"]
  Apply --> CRM["CRM pipeline/custom fields/labels"]
  Apply --> Campaigns["templates/segments/triggers inactive/flows draft"]
  Apply --> Quiet["quiet-hours defaults"]
  Apply --> Agents["optional recommended agents"]
  Apply --> Audit["saas_vertical_pack_applications"]
```

## Phase 11 Intelligence Map

```mermaid
flowchart TB
  Admin["Admin AI Predictivo"] --> Grants["AI premium grants"]
  Admin --> Process["manual intelligence process"]
  Process --> Worker["workers/intelligence.py"]
  Worker --> Events
  Worker --> FeatureStore
  Worker --> Predict
  Worker --> ModelMetrics["model metrics"]
  MLService["optional ml-service"] --> Predict
  MLService --> MlOps["saas_ml jobs/artifacts/inference/drift"]
  MLService --> MLflow["MLflow"]
  Qdrant["Qdrant optional"] --> MLService
  Admin --> ModelRegistry["model registry + rollout"]
  TenantAPI["Tenant intelligence API"] --> Events["intelligence events"]
  TenantAPI --> FeatureStore["feature values"]
  TenantAPI --> Feedback["prediction feedback"]
  FeatureStore --> Predict["baseline predictions + optional ML shadow/full"]
  Feedback --> ModelMetrics
  ModelMetrics --> ModelRegistry
  Predict --> Recs["recommendations"]
  Grants --> Predict
  Plans["plan + tenant feature flags"] --> Grants
  Recs --> Advisor["Advisor context"]
  Usage["intelligence usage"] --> Admin
  ModelMetrics --> Admin
  ModelRegistry --> Predict
```

## Phase 12 Performance And Reliability Map

```mermaid
flowchart TB
  Admin["Admin Performance"] --> Overview["Reliability overview"]
  Overview --> SLO["SLO metrics"]
  Overview --> Backpressure["Backpressure policies"]
  Overview --> IndexAudit["Index audit"]
  Overview --> Backup["Backup readiness"]
  Admin --> Drills["Reliability drills"]
  Admin --> Retention["Retention dry-run"]
  Worker["workers.reliability"] --> Snapshots["SLO snapshots"]
  Worker --> Retention
  SLO --> Observability["global_health + queue_snapshot"]
  IndexAudit --> PostgresStats["pg_indexes + pg_stat_user_tables"]
  Snapshots --> DB["PostgreSQL"]
  Drills --> DB
  Retention --> DB
```

- Phase 12 is an admin control-plane, not autonomous self-healing.
- Provider throttling, campaign pausing, real backup/restore and destructive cleanup are intentionally outside automatic execution.

## Phase 13 Security And Compliance Map

```mermaid
flowchart TB
  Login["Tenant/Admin login"] --> MFA{"Email OTP required?"}
  MFA -- "no" --> Token["JWT issued"]
  MFA -- "yes" --> Challenge["saas_mfa_challenges"]
  Challenge --> SMTP["SMTP notice"]
  Challenge --> Verify["verify-otp endpoint"]
  Verify --> Token
  TenantUI["Tenant settings"] --> Compliance["/compliance exports + delete requests"]
  Compliance --> Privacy["saas_privacy_requests"]
  AdminUI["Admin Security"] --> Metrics["/admin/security/compliance"]
  AdminUI --> AuditCsv["/admin/audit/export.csv"]
  Metrics --> SecurityEvents["saas_security_events"]
  Metrics --> Privacy
```

- Phase 13 email OTP is enforced by backend auth, not by frontend state.
- Privacy delete requests are non-destructive review records.

## Phase 22 AI Trust Map

```mermaid
flowchart TB
  TenantUI["Tenant Trust AI"] --> TrustAPI["/trust-center/*"]
  AdminUI["Admin Trust AI"] --> AdminTrust["/admin/trust-center/*"]
  TrustAPI --> Gates["demo/full feature gates"]
  TrustAPI --> Policies["policies + attestations"]
  TrustAPI --> Risks["risk assessments"]
  TrustAPI --> Cards["model cards"]
  TrustAPI --> Incidents["incidents"]
  TrustAPI --> Reports["reports"]
  TrustAPI --> Audits["governance audits"]
  Risks --> Signals["agents/workflows/models/tools/plugins/actions metadata"]
  AdminTrust --> Snapshot["tenant risk/source signal overview"]
  Snapshot --> Audits
```

- Phase 22 is a governance control-plane.
- Risk scans and reports do not execute runtime remediation or legal certification.

## Phase 16 Real-Time Intelligence Map

```mermaid
flowchart TB
  TenantUI["Tenant Inteligencia"] --> RealtimeAPI["/intelligence/realtime/*"]
  AdminUI["Admin AI Predictivo"] --> AdminRealtime["/admin/intelligence/realtime*"]
  RealtimeAPI --> Gates["realtime feature gates"]
  Gates --> Sessions["saas_realtime_intelligence_sessions"]
  Gates --> Cursors["saas_realtime_intelligence_cursors"]
  RealtimeAPI --> Events["saas_intelligence_events"]
  RealtimeAPI --> Predictions["saas_intelligence_predictions"]
  RealtimeAPI --> Recs["saas_intelligence_recommendations"]
  RealtimeAPI --> Ops["saas_ai_operation_anomalies/actions"]
  RealtimeAPI --> Trust["saas_ai_governance_incidents/risks"]
  AdminRealtime --> Metrics["saas_realtime_intelligence_metrics"]
```

- Phase 16 is a live intelligence control-plane over existing events/signals.
- Default transport is polling; bounded SSE is available for future clients.
- Alerts are advisory and no realtime endpoint mutates Meta, CRM, campaigns, billing, workflows, agents or model rollout state.

## Phase 24.2 Voice Intelligence Map

```mermaid
flowchart TB
  Audio["Tenant audio message"] --> MediaAPI["/media/messages/{id}/voice/analyze"]
  MediaAPI --> Gates["role + voice feature gates"]
  MediaAPI --> Source["local media asset or WhatsApp media bytes"]
  Source --> AIGateway["AI Gateway attachments"]
  AIGateway --> Gemini["Google/Gemini audio model"]
  Gemini --> Analysis["saas_voice_intelligence_analyses"]
  Analysis --> Payload["message payload compact result"]
  Analysis --> Event["Intelligence inline event"]
  Payload --> Inbox["Inbox Voice Intelligence card"]
```

- Phase 24.2 analyzes audio only when a user explicitly requests it from an existing tenant message.
- It does not send responses, mutate CRM, launch campaigns, execute agents, run OCR or search the web.

## Phase 24.3 Vision Intelligence Map

```mermaid
flowchart TB
  Media["Tenant image/document/file message"] --> MediaAPI["/media/messages/{id}/vision/analyze"]
  MediaAPI --> Gates["role + vision feature gates"]
  MediaAPI --> Source["local media asset or WhatsApp media bytes"]
  Source --> AIGateway["AI Gateway attachments"]
  AIGateway --> Provider["Gemini/OpenRouter/Kimi vision model"]
  Provider --> Analysis["saas_vision_intelligence_analyses"]
  Analysis --> Payload["message payload compact result"]
  Analysis --> Event["Intelligence inline event"]
  Payload --> Inbox["Inbox Vision Intelligence card"]
```

- Phase 24.3 analyzes image/document media only when a user explicitly requests it from an existing tenant message.
- It does not search the web, send references, mutate CRM, launch campaigns, execute agents or train models.

## Phase 24.4 Web/Image Search Intelligence Map

```mermaid
flowchart TB
  Query["Explicit user query"] --> MediaAPI["/media/search"]
  MediaAPI --> Gates["role + web/image feature gates"]
  MediaAPI --> Creds["encrypted tenant search credential"]
  Creds --> Providers["Tavily / Brave Search / SerpAPI"]
  Providers --> Safety["public URL safety screen"]
  Safety --> Runs["saas_web_search_intelligence_runs"]
  Safety --> Results["saas_web_search_intelligence_results"]
  Results --> Approval["human approval status"]
  Approval --> Inbox["Inbox source cards"]
  Results --> Event["Intelligence inline event"]
```

- Phase 24.4 searches external providers only when a user explicitly requests it.
- Results are source references with approval state; they are not sent to customers automatically.
- It does not crawl result URLs, mutate CRM, launch campaigns or train models.

## Phase 24.5 Agent Multimodal Tools Map

```mermaid
flowchart TB
  AgentOS["AI Agents > Agent OS"] --> Execute["/agents/{agent_id}/multimodal-tools/execute"]
  Execute --> Policy["agent tools_json + feature gate"]
  Policy --> ToolRun["saas_ai_agent_tool_runs"]
  ToolRun --> Voice["existing voice analysis"]
  ToolRun --> Vision["existing vision analysis"]
  ToolRun --> Search["existing web/image search"]
  Search --> Approval["source approval"]
  Approval --> Context["approved source prompt context"]
  Voice --> Context
  Vision --> Context
```

- Phase 24.5 tools are agent-scoped and contextual.
- External sources reach prompts only after approval and only when not blocked.
- It does not send messages, mutate CRM, launch campaigns, execute workflows, assign agents or train models.

## Phase 24.6 Multimodal Memory Map

```mermaid
flowchart TB
  Voice["voice analysis"] --> Sync["multimodal memory sync"]
  Vision["vision analysis"] --> Sync
  Search["approved search result"] --> Sync
  ToolRun["completed agent tool run"] --> Sync
  Sync --> Memory["saas_multimodal_memory_events"]
  Memory --> Features["ML feature values"]
  Memory --> Prompt["assigned-agent context"]
  Memory --> Mat["operator materialization"]
  Mat --> RAG["Knowledge/RAG"]
  Mat --> Collective["collective memory"]
```

- Phase 24.6 captures sanitized text/features/labels only.
- Training-ready events require a specific ML/training premium gate.
- Customer content needs explicit approval before Knowledge/RAG or collective-memory materialization.
- It does not store raw media/base64, auto-train models, send messages or mutate operational domains.

## Phase 24.8 Admin Premium Gating Map

```mermaid
flowchart TB
  Admin["Admin AI Predictivo"] --> Gating["premium-gating overview"]
  Admin --> PlanLimits["plan feature limits"]
  Admin --> ProviderPolicies["provider policies"]
  Gating --> CostSummary["AI/search monthly cost estimate"]
  PlanLimits --> TenantState["effective Intelligence feature state"]
  ProviderPolicies --> Gateway["AI Gateway provider check"]
  ProviderPolicies --> Search["Web/Image Search provider check"]
  Gateway --> ExternalAI["external AI provider"]
  Search --> ExternalSearch["external search provider"]
```

- Phase 24.8 is an Admin control-plane over existing gates and provider calls.
- Provider disablement, request quota and cost limit enforcement happens before external calls.
- It does not expose decrypted secrets, auto-charge billing, train models or alter Meta/CRM/campaign/workflow runtime.

## Phase 24.9-24.10 Multimodal Observability And Rollout Map

```mermaid
flowchart TB
  Runtime["Voice/Vision/Search runtime"] --> Rollout["Safe rollout helper"]
  Rollout --> Policies["rollout policies"]
  Rollout --> Decisions["rollout events"]
  Runtime --> Observability["observability collector"]
  Tools["Agent multimodal tools"] --> Observability
  Memory["Multimodal memory"] --> Observability
  Observability --> Snapshots["observability snapshots"]
  Pricing["provider policy pricing"] --> Observability
  UI["Tenant Inteligencia"] --> Observability
  UI --> Policies
```

- Phase 24.9 tracks cost, latency, errors, quality and sources used from existing multimodal tables.
- Phase 24.10 keeps rollout disabled unless a tenant has rollout access and an explicit enabled policy.
- Rollout decisions can block, downgrade to demo, canary-select or allow full execution without mutating CRM, campaigns, billing, Meta or agent ownership.

## Phase 19/20 Revenue And Memory Map

```mermaid
flowchart TB
  CRM["CRM/conversations"] --> Revenue["Autonomous Revenue Engine"]
  Predictions["Intelligence predictions"] --> Revenue
  Revenue --> Opportunities["Revenue opportunities"]
  Revenue --> Forecasts["Revenue forecasts/reports"]
  Collective["Collective memory"] --> Memory["Enterprise Memory Network"]
  Knowledge["Knowledge/RAG"] --> Memory
  Multimodal["Multimodal memory"] --> Memory
  Vertical["Vertical insights"] --> Memory
  Memory --> Graph["Tenant memory graph nodes/edges"]
  Graph --> Policy["scope/privacy/retention policy"]
  Graph --> Review["human review: publish/archive/reject/delete"]
  Graph --> Portability["audited export/import"]
```

- Revenue is supervised and records control-plane opportunities only.
- Enterprise Memory Network is tenant-scoped and stores bounded summaries/metadata/hashes.
- Enterprise Memory Network import creates candidate nodes only; export/import/delete are tenant-scoped and access-logged.
- Neither system sends messages, mutates CRM/campaign/workflow runtime, charges payments or shares raw tenant content.

## Phase 17 Federated Learning Map

```mermaid
flowchart TB
  Tenant["Tenant opt-in policy"] --> Local["Local aggregate update package"]
  Worker["Intelligence worker"] --> Local
  Local --> Round["Federated round"]
  Round --> Update["Tenant update"]
  Update --> Aggregate["Privacy-safe aggregate"]
  Aggregate --> Signal["Global signal / benchmark"]
  Signal --> ModelOps["Manual ModelOps review only"]
```

- Phase 17 is opt-in and premium-gated.
- Local packages are aggregate/statistical and tenant-owned.
- Aggregates do not promote models, send messages, mutate CRM, activate campaigns/workflows or alter Meta/billing/provider runtime.
