# API_FLOW

Scope: SaaS only.

## Request Flow

```mermaid
flowchart LR
  Browser["React app"] --> Nginx["Nginx/static server"]
  Browser --> API["FastAPI /saas/v1"]
  API --> Middleware["request metadata + CORS guard"]
  Middleware --> Router["domain router"]
  Router --> Auth["auth dependency if protected"]
  Auth --> SQL["SQLAlchemy raw SQL"]
  SQL --> DB["PostgreSQL"]
  Router --> Response["Pydantic/JSON response"]
```

## Router Mounting

`app_saas.main` mounts domain routers with prefix `/saas/v1`.

Important router groups:

- auth/admin/tenants
- verticals
- CRM/campaigns/broadcasts/ads/social
- integrations/internal/webhooks/media
- billing
- api-credentials/ai-gateway/ai/agents/advisor/knowledge
- intelligence
- compliance
- diagnostics/health
- admin observability/dead-letter/operations

## Observability Flow

```mermaid
flowchart LR
  Admin["Admin Salud view"] --> Health["/admin/observability/health"]
  Admin --> Dead["/admin/observability/dead-letter/*"]
  Admin --> Ops["/admin/operations/*/process"]
  Health --> DB["DB health + queue snapshots + worker heartbeats"]
  Dead --> Queues["Retry/resolve queue source rows"]
  Ops --> Workers["Run queue processors on demand"]
```

## Reliability Phase 12 API Flow

```mermaid
flowchart LR
  Admin["Admin Performance view"] --> Overview["GET /admin/reliability/overview"]
  Admin --> Snapshot["POST /admin/reliability/snapshot"]
  Admin --> Drills["POST /admin/reliability/drills/{type}"]
  Admin --> Retention["POST /admin/reliability/retention/run"]
  Admin --> Process["POST /admin/operations/reliability/process"]
  Overview --> SLO["SLO policies + observability health"]
  Overview --> Backpressure["queue_snapshot + backpressure policies"]
  Overview --> IndexAudit["pg_indexes + pg_stat_user_tables"]
  Drills --> DrillDB["saas_reliability_drills"]
  Snapshot --> Snapshots["saas_reliability_snapshots"]
  Retention --> CleanupRuns["saas_reliability_cleanup_runs"]
  Process --> Worker["workers.reliability"]
```

- Reliability APIs are platform-admin scoped and control-plane first.
- Retention defaults to dry-run; destructive cleanup is role-gated and allowlisted by backend service code.

## Security/Compliance Phase 13 API Flow

```mermaid
flowchart LR
  TenantAuth["/auth/login"] --> TenantMFA["/auth/login/verify-otp"]
  AdminAuth["/admin/auth/login"] --> AdminMFA["/admin/auth/login/verify-otp"]
  TenantSettings["Tenant Settings"] --> Security2FA["/auth/security/2fa"]
  TenantSettings --> Compliance["/compliance/*"]
  AdminSecurity["Admin Security"] --> AdminSecurityApi["/admin/auth/security + /admin/security/compliance"]
  AdminSecurity --> AuditExport["/admin/audit/export.csv"]
  TenantMFA --> MFAStore["saas_mfa_challenges"]
  AdminMFA --> MFAStore
  Compliance --> Privacy["saas_privacy_requests"]
```

- MFA and compliance APIs are backend-authoritative and tenant/platform role scoped.
- Delete requests are workflow records; no automatic hard-delete API was added.

## Inbox API Flow

```mermaid
flowchart LR
  UI["Inbox UI"] --> List["GET /conversations?channel&queue&search"]
  UI --> Thread["GET /conversations/{id}/messages"]
  UI --> Send["POST /conversations/{id}/messages"]
  UI --> Assign["PATCH /customers/{id} assigned_user_id"]
  UI --> CRMConfig["GET /crm/config"]
  UI --> Timeline["GET /conversations/{id}/timeline"]
  UI --> Dedupe["GET /customers/{id}/dedupe-candidates"]
  Dedupe --> Merge["POST /customers/{id}/merge"]
  UI --> Comment["/social/comments/*"]
  Send --> Outbound["saas_outbound_messages"]
  Workers["workers.dispatch / workers.ingest"] --> Status["saas_message_status_events"]
  Status --> UI
```

## Knowledge/RAG API Flow

```mermaid
flowchart LR
  UI["Settings Knowledge UI"] --> Upload["POST /knowledge/upload"]
  UI --> URL["POST /knowledge/url"]
  UI --> Search["POST /knowledge/search"]
  UI --> Eval["POST /knowledge/evaluate"]
  Upload --> Sources["saas_knowledge_sources"]
  URL --> Sources
  Sources --> Chunks["saas_knowledge_chunks vector_json"]
  Search --> Chunks
  Search --> Logs["saas_knowledge_retrieval_logs"]
  Eval --> Evals["saas_knowledge_evaluations"]
  AI["Conversation AI"] --> Context["knowledge_context_for_query"]
  Context --> Search
```

## Billing Phase 9 API Flow

```mermaid
flowchart LR
  Client["Tenant Plan UI"] --> Checkout["POST /billing/checkout"]
  Client --> Invoices["GET /billing/invoices + PDF"]
  Admin["Admin Billing UI"] --> AdminOps["/admin/billing/*"]
  Provider["Stripe / MercadoPago / Wompi"] --> Webhook["POST /billing/webhooks/{provider}"]
  Webhook --> Verify["provider signature verification"]
  Verify --> State["checkout/payment/invoice/subscription state"]
  Worker["billing lifecycle worker"] --> State
  State --> Tenant["tenant plan/status"]
  Tenant --> Guard["unsafe write block when non-operational"]
```

## Verticalization Phase 10 API Flow

```mermaid
flowchart LR
  Public["Register/onboarding"] --> PublicPacks["GET /verticals/public-packs"]
  Client["Tenant Settings Industria"] --> Packs["GET /verticals/packs"]
  Client --> State["GET /verticals/state"]
  Client --> Apply["POST /verticals/apply"]
  Admin["Admin tenant detail"] --> Patch["PATCH /admin/tenants/{id} industry_code"]
  Register["POST /auth/register"] --> Apply
  Apply --> Tenant["saas_tenants industry state"]
  Apply --> CRM["pipeline/custom fields/labels"]
  Apply --> Campaigns["templates/segments/triggers draft/flows draft"]
  Apply --> Agents["optional recommended agents"]
  Apply --> Audit["saas_vertical_pack_applications + audit"]
```

## Campaigns Phase 7 API Flow

```mermaid
flowchart LR
  UI["Campaigns + Trigger Builder"] --> Quiet["GET/PATCH /campaigns/settings/quiet-hours"]
  UI --> Preflight["/campaigns/items|triggers|flows preflight"]
  UI --> Sim["POST /campaigns/triggers/simulate"]
  UI --> Versions["GET/POST trigger versions restore"]
  UI --> AB["GET /campaigns/ab-report"]
  Preflight --> Checks["tenant/template/audience/actions/quiet/A-B checks"]
  Sim --> Runtime["workers.triggers simulate_trigger_draft"]
  Runtime --> DB["PostgreSQL tenant data"]
  AB --> Events["saas_campaign_ab_events"]
```

## AI Agents Phase 8 API Flow

```mermaid
flowchart LR
  AgentsUI["AiAgentsPanel"] --> Agents["/agents"]
  AgentsUI --> Preflight["GET /agents/{id}/preflight"]
  AgentsUI --> Activate["POST /agents/{id}/activate"]
  Inbox["Inbox"] --> Assign["PATCH /conversations/{id}/ai-agent"]
  Inbox --> Filter["GET /conversations?agent_id"]
  Assign --> Conversation["saas_conversations assigned_ai_agent_id"]
  Activate --> Checks["preflight + plan + prompt + budget checks"]
  AI["Conversation AI"] --> Runtime["runtime_agent_for_conversation"]
  Runtime --> Conversation
  Runtime --> Memory["agent memory + collective memory"]
  Runtime --> Budget["assert_agent_budget_available"]
  Budget --> Gateway["AI provider gateway"]
  Gateway --> Policy["provider/model policy check"]
  Policy --> Models["retryable model fallback"]
  Models --> Providers["provider fallback chain"]
  Providers --> Runs["saas_ai_runs attempts"]
```

- Conversation AI, assigned/custom agents and Advisor use the same `generate_with_gateway` resilience path.
- Retryable model/provider failures can fall through to another allowed model/provider; provider policies, missing credentials and agent budget checks are still enforced before calls.

## Phase 24.1 Multimodal Gateway Flow

```mermaid
flowchart LR
  Caller["Future AI/media caller"] --> Gateway["generate_with_gateway"]
  Gateway --> Request["GatewayRequest + attachments[]"]
  Request --> Gemini["Gemini multimodal parts"]
  Request --> Compat["OpenAI-compatible text/image parts"]
  Gateway --> Runs["saas_ai_runs safe metadata"]
  Settings["Settings > APIs"] --> Creds["/api-credentials"]
  Creds --> Models["/api-credentials/{provider}/models"]
```

- Existing text-only gateway callers keep the same contract.
- Attachments are internal only in 24.1; no public media-analysis endpoint was added.
- Run logs never store raw base64 or media bytes.

## Phase 24.2 Voice Intelligence API Flow

```mermaid
flowchart LR
  Client["Inbox audio card"] --> Analyze["POST /media/messages/{message_id}/voice/analyze"]
  Analyze --> Role["tenant role gate"]
  Role --> Feature["voice feature gate + demo/full mode"]
  Feature --> Message["tenant audio message lookup"]
  Message --> Source["local media or WhatsApp media"]
  Source --> Gateway["generate_with_gateway attachments"]
  Gateway --> Gemini["Google/Gemini"]
  Gemini --> VoiceDb["saas_voice_intelligence_analyses"]
  VoiceDb --> MessagePayload["saas_messages.payload_json.voice_intelligence"]
  VoiceDb --> Event["message.audio.analyzed"]
```

- The endpoint analyzes existing tenant audio messages only.
- Cached completed analysis is reused unless `force=true`.
- Output is advisory and does not mutate CRM, campaigns, agents, workflows or outbound messaging.

## Phase 24.3 Vision Intelligence API Flow

```mermaid
flowchart LR
  Client["Inbox image/document card"] --> Analyze["POST /media/messages/{message_id}/vision/analyze"]
  Analyze --> Role["tenant role gate"]
  Role --> Feature["vision feature gate + demo/full mode"]
  Feature --> Message["tenant visual/document message lookup"]
  Message --> Source["local media or WhatsApp media"]
  Source --> Gateway["generate_with_gateway attachments"]
  Gateway --> Provider["Gemini image/document path<br/>OpenRouter/Kimi image path"]
  Provider --> VisionDb["saas_vision_intelligence_analyses"]
  VisionDb --> MessagePayload["saas_messages.payload_json.vision_intelligence"]
  VisionDb --> Event["message.visual.analyzed"]
```

- The endpoint analyzes existing tenant image/document/file messages only.
- Cached completed analysis is reused unless `force=true`.
- Output is advisory and does not search the web, send media, mutate CRM, campaigns, agents, workflows or outbound messaging.

## Phase 24.4 Web/Image Search Intelligence API Flow

```mermaid
flowchart LR
  Client["Inbox search card"] --> Search["POST /media/search"]
  Client --> Runs["GET /media/search/runs"]
  Client --> Review["POST /media/search/results/{id}/approval"]
  Search --> Role["tenant role gate"]
  Role --> Feature["web/image/external source feature gate"]
  Feature --> Context["optional conversation/message ownership check"]
  Context --> Creds["encrypted tenant provider credential"]
  Creds --> Provider["Tavily / Brave Search / SerpAPI"]
  Provider --> Safety["public URL safety screening"]
  Safety --> RunDb["saas_web_search_intelligence_runs"]
  Safety --> ResultDb["saas_web_search_intelligence_results"]
  Review --> ResultDb
  ResultDb --> Events["external_search.* events"]
```

- The endpoint searches external providers only after an explicit user query.
- Results are persisted as pending/rejected/approved source records.
- Blocked/unsafe results cannot be approved.
- Output is advisory and does not crawl result pages, send links/images, mutate CRM, campaigns, agents, workflows or outbound messaging.

## Phase 24.5 Agent Multimodal Tools API Flow

```mermaid
flowchart LR
  AgentUI["AI Agents > Agent OS"] --> Execute["POST /agents/{agent_id}/multimodal-tools/execute"]
  Execute --> Role["tenant role gate"]
  Role --> Agent["tenant agent + tools_json check"]
  Agent --> Feature["agent multimodal feature gate"]
  Feature --> ToolRun["saas_ai_agent_tool_runs"]
  ToolRun --> Media["existing media/search endpoint"]
  Media --> Output["completed/failed compact output"]
  Output --> Prompt["assigned-agent prompt context"]
```

- Voice/vision tools require an existing tenant Inbox message id.
- Web/image search results still require per-source approval before agent prompt use.
- The endpoint records traces only; it does not send messages, mutate CRM, launch campaigns or execute workflows.

## Phase 24.6 Multimodal Memory API Flow

```mermaid
flowchart LR
  AgentUI["AI Agents > Agent OS"] --> List["GET /agents/multimodal-memory/events"]
  AgentUI --> Sync["POST /agents/multimodal-memory/sync"]
  AgentUI --> Materialize["POST /agents/multimodal-memory/events/{id}/materialize"]
  Sync --> Role["tenant role gate"]
  Role --> Feature["multimodal memory feature gate"]
  Feature --> Sources["voice/vision/approved search/tool-run sources"]
  Sources --> Memory["saas_multimodal_memory_events"]
  Memory --> Features["conversation ML feature values"]
  Materialize --> Approval["customer-content explicit approval"]
  Approval --> Knowledge["Knowledge/RAG source"]
  Approval --> Collective["collective agent memory"]
```

- Sync stores sanitized text/features only; no raw media/base64 is persisted.
- Training-ready flags require `multimodal_training_events`, `ml_predictions`, or `ai_premium`.
- Materialization can write to Knowledge/RAG and/or collective memory only after operator action.
- The API does not send customer messages, mutate CRM, launch campaigns, execute workflows, assign agents or train models automatically.

## Phase 24.8 Admin Premium Gating API Flow

```mermaid
flowchart LR
  Admin["Admin AI Predictivo"] --> Overview["GET /admin/intelligence/premium-gating"]
  Admin --> PlanPatch["PATCH /admin/intelligence/plans/{plan_code}/features"]
  Admin --> ProviderPatch["PATCH /admin/intelligence/provider-policies"]
  PlanPatch --> PlanLimits["plan feature mode/quota"]
  ProviderPatch --> Policies["provider availability/quota/cost"]
  Gateway["AI Gateway"] --> PolicyCheck["provider policy check"]
  Search["POST /media/search"] --> PolicyCheck
  PolicyCheck --> External["provider call if allowed"]
```

- Admin routes are platform-admin scoped; plan/provider mutations require platform/billing admin roles.
- Tenant grants remain more specific than plan limits.
- Provider policies can block provider/model usage or enforce positive monthly request/cost limits before external calls.
- The API returns credential readiness counts and estimated costs only; decrypted secrets are never returned.

## Phase 19/20 Revenue And Memory API Flow

```mermaid
flowchart LR
  TenantUI["Tenant Inteligencia"] --> RevenueCenter["GET /intelligence/revenue/center"]
  TenantUI --> RevenueAnalyze["POST /intelligence/revenue/analyze"]
  TenantUI --> RevenueActions["POST /intelligence/revenue/opportunities/{id}/approve|execute|dismiss"]
  TenantUI --> MemoryCenter["GET /intelligence/memory-network/center"]
  TenantUI --> MemorySync["POST /intelligence/memory-network/sync"]
  TenantUI --> MemoryPolicy["PATCH /intelligence/memory-network/policy"]
  TenantUI --> MemoryExport["GET /intelligence/memory-network/export"]
  TenantUI --> MemoryImport["POST /intelligence/memory-network/import"]
  TenantUI --> MemoryReview["POST /intelligence/memory-network/nodes/{id}/review"]
  TenantUI --> MemoryDelete["DELETE /intelligence/memory-network/nodes/{id}"]
  RevenueAnalyze --> RevenueGate["revenue feature gates"]
  RevenueActions --> RevenueGate
  MemorySync --> MemoryGate["memory feature gates"]
  MemoryPolicy --> MemoryGate
  MemoryExport --> MemoryGate
  MemoryImport --> MemoryGate
  MemoryReview --> MemoryGate
  MemoryDelete --> MemoryGate
  RevenueAnalyze --> RevenueTables["saas_ai_revenue_*"]
  MemorySync --> MemoryTables["saas_enterprise_memory_*"]
  MemoryExport --> MemoryTables
  MemoryImport --> MemoryTables
  MemoryDelete --> MemoryTables
```

- Demo mode can preview center/dry-run data; full mode is required for persistence and status changes.
- Revenue actions are control-plane records only and do not send messages, charge customers or mutate CRM/campaign/workflow runtime.
- Memory review changes graph node status only; prompt/RAG consumers should read published tenant nodes after routing review.

## Phase 24.9-24.10 Multimodal Observability And Rollout API Flow

```mermaid
flowchart LR
  TenantUI["Tenant Inteligencia"] --> ObsCenter["GET /intelligence/multimodal/observability/center"]
  TenantUI --> ObsRefresh["POST /intelligence/multimodal/observability/refresh"]
  TenantUI --> RolloutCenter["GET /intelligence/multimodal/rollout/center"]
  TenantUI --> RolloutPatch["PATCH /intelligence/multimodal/rollout/policy"]
  ObsCenter --> ObsGate["multimodal observability gates"]
  ObsRefresh --> ObsGate
  RolloutCenter --> RolloutGate["safe rollout gates"]
  RolloutPatch --> RolloutGate
  ObsRefresh --> Snapshots["saas_multimodal_observability_snapshots"]
  RolloutPatch --> Policies["saas_multimodal_rollout_policies"]
  MediaRuntime["voice/vision/search endpoints"] --> RolloutHelper["apply_multimodal_safe_rollout"]
  RolloutHelper --> Policies
  RolloutHelper --> Events["saas_multimodal_rollout_events"]
```

- Observability reads aggregate metrics and optional snapshots only.
- Rollout mutation is tenant-scoped and role-gated through the existing Intelligence router/auth path.
- Runtime enforcement is opt-in: no explicit enabled policy means compatibility behavior.

## Phase 17 Federated Learning API Flow

```mermaid
flowchart LR
  TenantUI["Tenant Inteligencia"] --> Center["GET /intelligence/federated/center"]
  TenantUI --> Policy["PATCH /intelligence/federated/policy"]
  TenantUI --> Prepare["POST /intelligence/federated/rounds/prepare"]
  TenantUI --> Submit["POST /intelligence/federated/rounds/{id}/submit-update"]
  TenantUI --> Aggregate["POST /intelligence/federated/rounds/{id}/aggregate"]
  Center --> ReadGates["demo/global/federated gates"]
  Policy --> FullGates["full federated gates + role"]
  Prepare --> FullGates
  Submit --> FullGates
  Aggregate --> FullGates
  Prepare --> Updates["aggregate tenant update package"]
  Submit --> Updates
  Updates --> AggregateRows["weighted aggregate rows"]
  AggregateRows --> Signals["global intelligence signals"]
```

- Federated center can show safe previews in demo/read mode.
- Persisted policy/update/aggregation operations require owner/admin/supervisor and full premium feature access.
- API responses never include raw cross-tenant content, tenant names from other tenants, media/base64, prompts or decrypted secrets.

## Intelligence Phase 11 API Flow

```mermaid
flowchart LR
  Admin["Admin AI Predictivo"] --> AdminAPI["/admin/intelligence/*"]
  Admin --> Ops["/admin/operations/intelligence/process"]
  Tenant["Tenant Inteligencia UI/API"] --> TenantAPI["/intelligence/*"]
  CrmBilling["CRM send + Billing state changes"] --> Inline["record_inline_event"]
  Inline --> Events
  Worker["worker/intelligence.py"] --> Events
  Ops --> Worker
  AdminAPI --> Grants["saas_intelligence_feature_grants"]
  AdminAPI --> Registry["saas_intelligence_model_registry"]
  AdminAPI --> RolloutEvents["saas_intelligence_model_rollout_events"]
  TenantAPI --> Events["saas_intelligence_events"]
  TenantAPI --> Features["feature recompute/read"]
  Features --> Predictions["saas_intelligence_predictions"]
  Predictions --> Feedback["prediction feedback"]
  Feedback --> ModelMetrics["model metrics"]
  ModelMetrics --> Registry
  Registry --> Predictions
  AdminAPI --> ModelMetrics
  Predictions --> Recs["saas_intelligence_recommendations"]
  Recs --> Advisor["advisor_context"]
  Billing["plan flags + tenant flags"] --> Grants
  Billing --> TenantAPI
```

## AI Trust Phase 22 API Flow

```mermaid
flowchart LR
  TenantUI["Tenant Trust AI"] --> TenantAPI["/trust-center/*"]
  AdminUI["Admin Trust AI"] --> AdminAPI["/admin/trust-center/*"]
  TenantAPI --> Gates["premium/demo gates"]
  AdminAPI --> Snapshot["read-only platform snapshot"]
  Gates --> Policies["governance policies + attestations"]
  Gates --> Risks["risk assessments"]
  Gates --> Cards["model cards"]
  Gates --> Incidents["governance incidents"]
  Gates --> Reports["compliance reports"]
  Gates --> Audits["governance audits"]
  Risks --> Signals["agents/workflows/models/tools/plugins/actions metadata"]
  Reports --> Audits
  AdminAPI --> Audits
```

## Real-Time Intelligence Phase 16 API Flow

```mermaid
flowchart LR
  TenantUI["Tenant Inteligencia"] --> Center["GET /intelligence/realtime/center"]
  TenantUI --> Events["GET /intelligence/realtime/events"]
  TenantUI --> Session["POST /intelligence/realtime/sessions"]
  TenantUI --> Cursor["PATCH /intelligence/realtime/cursor"]
  TenantUI --> Stream["GET /intelligence/realtime/stream"]
  AdminUI["Admin AI Predictivo"] --> AdminRt["GET /admin/intelligence/realtime"]
  AdminUI --> Refresh["POST /admin/intelligence/realtime/metrics/refresh"]
  Center --> Gates["realtime_* feature gates"]
  Session --> Gates
  Cursor --> Gates
  Gates --> RtState["sessions + cursors"]
  Center --> Signals["events + predictions + recommendations + ops + trust"]
  Events --> Sanitizer["payload redaction"]
  Refresh --> Snapshots["saas_realtime_intelligence_metrics"]
  AdminRt --> Snapshots
```

- Tenant realtime APIs are tenant-scoped and premium/demo gated.
- Event payloads are sanitized before reaching the tenant UI.
- Admin metric refresh writes only snapshot rows; it does not process queues, send messages, repair Meta, mutate CRM, activate workflows or promote models.

## Compatibility Rule

Any endpoint documented for SaaS must exist under `saas-version/backend/app_saas` and be mounted in `main.py`.
