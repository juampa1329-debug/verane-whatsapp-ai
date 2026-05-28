# Real-Time Intelligence Layer

Scope: SaaS only. Phase 16.

## Intent

Phase 16 adds a live intelligence control-plane over the existing Phase 11/18/22 data:

- Intelligence events
- feature snapshots
- predictions
- recommendations
- Autonomous Operations anomalies/actions
- Trust AI incidents/risks
- ModelOps metrics

It is PostgreSQL-first and dependency-free. Kafka, NATS, Redis Streams or WebSocket brokers were not added.

## Architecture

```mermaid
flowchart TB
  TenantUI["Tenant Inteligencia<br/>Real-Time AI"] --> TenantAPI["/saas/v1/intelligence/realtime/*"]
  AdminUI["Admin AI Predictivo<br/>Realtime overview"] --> AdminAPI["/saas/v1/admin/intelligence/realtime*"]
  TenantAPI --> Gates["realtime_* feature gates<br/>demo/full mode"]
  Gates --> Sessions["saas_realtime_intelligence_sessions"]
  Gates --> Cursors["saas_realtime_intelligence_cursors"]
  TenantAPI --> Events["saas_intelligence_events"]
  TenantAPI --> Predictions["saas_intelligence_predictions"]
  TenantAPI --> Recs["saas_intelligence_recommendations"]
  TenantAPI --> Ops["saas_ai_operation_anomalies/actions"]
  TenantAPI --> Trust["saas_ai_governance_incidents/risks"]
  AdminAPI --> Metrics["saas_realtime_intelligence_metrics"]
  AdminAPI --> Plans["saas_plan_limits + grants"]
```

## Tenant Flow

```mermaid
sequenceDiagram
  participant UI as "IntelligencePanel"
  participant API as "Realtime API"
  participant Gate as "Feature gates"
  participant DB as "PostgreSQL"
  UI->>API: "POST /realtime/sessions"
  API->>Gate: "realtime_event_stream demo/full"
  API->>DB: "upsert session"
  UI->>API: "GET /realtime/center"
  API->>Gate: "realtime_intelligence_layer demo/full"
  API->>DB: "read events/predictions/recs/ops/trust"
  API-->>UI: "snapshot + alerts + cursor"
  UI->>API: "PATCH /realtime/cursor"
  API->>DB: "upsert user cursor"
```

## Streaming Shape

- Primary tenant UI uses safe polling every 8 seconds.
- Backend also exposes bounded SSE through `GET /intelligence/realtime/stream`.
- SSE connections are capped by `max_seconds` and reopen client-side if needed.
- The stream opens a fresh DB session per snapshot and does not keep a transaction open.

## Data Privacy

- Event payloads are sanitized before returning to UI.
- Keys containing `text`, `message`, `content`, `body`, `email`, `phone`, `token`, `secret`, or `password` are redacted.
- Cross-tenant data is not exposed to tenant endpoints.
- Admin overview aggregates tenant activity but does not return raw event payloads.

## Premium Gating

Feature keys:

- `realtime_intelligence_layer`
- `realtime_event_stream`
- `realtime_ai_alerts`
- `realtime_intelligence_dashboard`

Rules:

- Demo mode can read live previews.
- Full mode is controlled by plan flags, tenant overrides, or explicit Intelligence grants.
- Session creation records usage under `realtime_sessions`.
- Center polling does not consume prediction quota to avoid noisy billing from passive dashboards.

## Safety Boundaries

- No Meta, webhook, CRM, campaign, billing, workflow, agent, model promotion, or Trust enforcement side effects.
- Alerts are advisory and derived from existing records.
- Admin metric refresh writes only `saas_realtime_intelligence_metrics` snapshots.
- Broker-based streaming remains a future scale decision.
