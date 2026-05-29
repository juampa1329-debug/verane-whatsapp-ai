# WORKER_FLOW

Scope: SaaS only.

## Worker Execution

```mermaid
flowchart TB
  APIStartup["FastAPI startup"] -->|if enabled| Embedded["Embedded worker loop"]
  DockerWorker["docker compose worker"] --> Runner["app_saas.workers.runner"]
  Embedded --> Jobs["Due job processors"]
  Runner --> Jobs
  Jobs --> DB["PostgreSQL queues/status tables"]
  Jobs --> Heartbeats["saas_worker_heartbeats"]
  Jobs --> Providers["Meta / AI / other providers"]
```

## Processors Detected

- due webhook events
- scheduled trigger messages
- remarketing flows
- AI replies
- agent orchestration
- outbound messages
- billing lifecycle
- intelligence event derivation, feature recompute and prediction generation
- revenue opportunity analysis and enterprise memory sync inside the Intelligence pipeline
- reliability snapshots, SLO checks and retention dry-runs
- Meta token refreshes

## Safety Model

- Assume duplicate/concurrent execution is possible.
- Status transitions must be retry-safe.
- Provider calls must handle partial failure.
- Admin operation endpoints can manually process queues.
- Worker liveness is recorded in `saas_worker_heartbeats` for embedded and standalone workers.
- Webhook ingestion uses per-event savepoints so failed SQL in one event does not abort the whole batch.
- Optional agent orchestration enqueue is isolated with a savepoint when called from ingestion.

## Phase 7 Campaign Worker Flow

```mermaid
flowchart LR
  Inbound["Inbound message/comment"] --> Triggers["execute_triggers_for_message"]
  Triggers --> Quiet["global + trigger quiet hours"]
  Triggers --> Conditions["conditions: words/tags/stage/status/intent/schedule"]
  Conditions --> Actions["template/tag/status/schedule actions"]
  Actions --> AB["A/B variant + saas_campaign_ab_events"]
  Actions --> Outbound["saas_outbound_messages"]
  Triggers --> BlockAI["block_ai controls AI scheduling"]
  FlowTick["remarketing tick"] --> FlowQuiet["global + flow quiet hours"]
  FlowQuiet --> FlowAB["flow A/B variant/event"]
  FlowAB --> Outbound
```

- Scheduled trigger messages requeue during global quiet hours instead of failing permanently.
- Remarketing enrollments pause/reschedule during global or flow-local quiet hours.
- Outbound dispatch revalidates approved Meta template status for queued/retried template messages.

## Phase 8 Agent Ownership Worker Flow

```mermaid
flowchart LR
  Inbound["Inbound conversation event"] --> Orchestrator["agent orchestration queue"]
  Orchestrator --> Select["select best active agent"]
  Select --> Assign["persist assigned_ai_agent_id"]
  Assign --> Runtime["conversation AI runtime"]
  Runtime --> Budget["agent budget hard stop"]
  Runtime --> Memory["agent memory + collective memory"]
  Budget --> Gateway["AI Gateway"]
  Gateway --> ModelFallback["retryable model fallback"]
  ModelFallback --> ProviderFallback["provider fallback chain"]
  ProviderFallback --> Provider["AI provider"]
```

- Orchestrator assignment makes the selected agent the conversation AI owner.
- Assigned inactive agents block general fallback until a human releases/reassigns the conversation.
- AI Gateway handles retryable model/provider failures for the assigned agent runtime. If every attempt fails with retryable provider errors, the AI pending reply remains retryable through the existing worker flow.

## Phase 9 Billing Worker Flow

```mermaid
flowchart LR
  Tick["embedded/standalone worker tick"] --> Lock["billing advisory lock"]
  Lock --> Lifecycle["sync_billing_lifecycle"]
  Lifecycle --> Trials["expire trials/subscriptions"]
  Lifecycle --> PastDue["past_due grace + suspension"]
  Lifecycle --> Invoices["create/open/age invoices"]
  Lifecycle --> Notices["one-time email notices"]
  PastDue --> Tenant["tenant status/plan sync"]
```

- Billing lifecycle is interval-throttled by `SAAS_BILLING_LIFECYCLE_INTERVAL_MINUTES`.
- Past-due suspension grace is controlled by `BILLING_PAST_DUE_GRACE_DAYS`.
- The lifecycle processor must remain idempotent because API embedded workers and standalone workers can both run.
- Compose defaults the API embedded worker off when the standalone worker service is present. Single-container deployments can still enable the embedded worker explicitly.

## Phase 11 Intelligence Worker Flow

```mermaid
flowchart LR
  Tick["embedded/standalone/admin tick"] --> Lock["intelligence advisory lock"]
  Lock --> Derive["derive canonical events"]
  Derive --> Events["saas_intelligence_events"]
  Events --> Features["recompute tenant feature snapshot"]
  Features --> Gate["feature flags + grants + quota"]
  Gate --> Predict["baseline predictions with cooldown"]
  Predict --> Recs["recommendations for Advisor/Admin"]
  Predict --> Metrics["model metrics recompute"]
  Gate --> Revenue["revenue analysis if full-enabled"]
  Gate --> Memory["enterprise memory sync if full-enabled"]
```

- `workers/intelligence.py` derives events idempotently from existing SaaS tables rather than changing every producer path at once.
- Derived sources currently include conversations, messages, webhooks, outbound messages, trigger executions, campaign A/B events, remarketing enrollments, AI Gateway runs and billing subscriptions.
- The processor uses `pg_try_advisory_xact_lock(hashtext('scentra:intelligence:pipeline'))` to avoid duplicate concurrent runs.
- Automatic predictions stay behind plan/grant/demo/full gating and monthly quota checks.
- Revenue Engine and Enterprise Memory Network run in nested transactions and skip tenants without full feature access. Memory sync also applies tenant memory policy before upserting candidates.
- Revenue/memory worker paths do not send messages, mutate CRM/campaign/workflow runtime, call payment providers, publish prompts or share raw cross-tenant content.
- Model metrics recompute after each tenant pipeline and remain tenant/model scoped.
- Runtime knobs: `SAAS_INTELLIGENCE_WORKER_INTERVAL_MINUTES`, `SAAS_INTELLIGENCE_EVENT_LIMIT`, `SAAS_INTELLIGENCE_LOOKBACK_HOURS`, and `SAAS_INTELLIGENCE_PREDICTION_COOLDOWN_MINUTES`.

## AI Outbound Fragment Flow

```mermaid
flowchart LR
  AI["AI Gateway response"] --> Split["natural chunk split"]
  Split --> Queue["saas_outbound_messages with staggered next_attempt_at"]
  Queue --> Batch["outbound worker batch"]
  Batch --> Typing["best-effort WhatsApp typing indicator"]
  Typing --> Meta["Meta Cloud send"]
  Batch --> Defer["defer extra chunks for same conversation"]
  Defer --> Queue
```

- Conversation AI still makes one model call with CRM, memory, Knowledge/RAG, collective memory and recent transcript context.
- Message fragmentation happens after generation, in the outbound queue, so context is not lost between fragments.
- The outbound worker sends at most one multi-chunk AI fragment per conversation per batch and nudges additional due fragments forward to avoid burst delivery after backlog.
- WhatsApp typing indicators are best-effort and require the original inbound Meta provider message id.

## Phase 12 Reliability Worker Flow

```mermaid
flowchart LR
  Tick["embedded/standalone/admin tick"] --> Gate["15 minute snapshot throttle"]
  Gate --> Snapshot["record SLO/backpressure snapshot"]
  Snapshot --> Tables["saas_reliability_snapshots"]
  Tick --> Retention["enabled retention dry-run only"]
  Retention --> Runs["saas_reliability_cleanup_runs"]
  Admin["Admin Performance"] --> Drills["load_smoke / backup_readiness / retention_dry_run"]
  Drills --> Audit["saas_reliability_drills + audit"]
```

- `workers/reliability.py` opens its own DB session and delegates to `reliability.service.process_due_reliability`.
- The processor records snapshots and dry-run cleanup telemetry; it does not call Meta, pause campaigns, mutate queues or delete data automatically.
- Destructive retention remains an explicit admin API action with platform-admin role checks and backend allowlisted SQL.
