# Autonomous Revenue Engine

Scope: SaaS Phase 19.

## Architecture

```text
CRM conversations/messages
        |
        v
Revenue detector
        |
        +--> saas_ai_revenue_opportunities
        +--> saas_ai_revenue_forecasts
        +--> saas_ai_revenue_reports
        +--> saas_intelligence_events
```

## Runtime Flow

```text
Tenant/Admin grants
  -> /intelligence/revenue/analyze
  -> feature gate: autonomous_revenue_engine or ai_premium
  -> detect candidates from CRM
  -> dry_run returns preview
  -> full mode persists opportunities/report/forecast
  -> policy enforces optional action type allowlist and monthly execution cap
  -> operator approves/dismisses/marks executed
```

## Safety Model

- No automatic outbound messages.
- No payment provider calls.
- No campaign/workflow activation.
- Execution is a control-plane record only.
- Policy `allowed_action_types_json` and `max_monthly_revenue_actions` gate approve/execute status changes when configured.
- Unknown commercial value is stored as `0`, not invented.

## Tables

- `saas_ai_revenue_policies`
- `saas_ai_revenue_opportunities`
- `saas_ai_revenue_forecasts`
- `saas_ai_revenue_experiments`
- `saas_ai_revenue_reports`

## Feature Gates

- `autonomous_revenue_engine`
- `revenue_opportunity_detection`
- `revenue_forecasting`
- `revenue_playbooks`
- `revenue_experiments`
- umbrella: `ai_premium`

## Validation Snapshot

- Migration `066` applied on active Docker stack.
- Clean isolated PostgreSQL bootstrap passed through migrations `001-066`.
- OpenAPI includes `/saas/v1/intelligence/revenue/*`.
- Full-mode tenant smoke created opportunities/reports and approved/executed one opportunity as control-plane metadata.
