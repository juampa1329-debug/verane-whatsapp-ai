# ADR-059: AI Gateway Model And Provider Resilience

## Status

Accepted.

## Context

SaaS conversation AI, assigned/custom agents and Advisor use `generate_with_gateway` for provider calls. The gateway already accepted a provider chain, but a transient model outage such as `http_503` high demand could still leave a pending customer reply without a generated answer if every configured provider attempt failed.

## Decision

Keep resilience in `app_saas/ai_gateway/service.py` as the shared layer.

- Retry retryable model failures inside the same provider before moving to the next provider.
- Treat `408`, `409`, `425`, `429`, `500`, `502`, `503`, `504`, unavailable/timeout/high-demand/temporary/empty-output signals as retryable.
- Build model candidates from the selected credential model, optional `settings.metadata_json.model_fallbacks_json`, provider default model and provider static models.
- Enforce Admin provider policy for each candidate model before any external call.
- Record each skipped/failed/success attempt in `saas_ai_runs` with safe metadata only.
- Map all-retryable gateway exhaustion in conversation AI to `ai_generation_error` so the existing `saas_ai_pending_replies` worker retry path remains active.

## Consequences

- Conversation AI, assigned/custom agents, Agent OS runtime paths and Advisor inherit fallback without duplicating logic.
- A single customer message can create multiple AI run rows when fallback is used.
- Missing credentials, disabled providers/models and quota/cost policy blocks remain configuration/operator issues and are not bypassed.
- No DB migration, dependency, route contract, Meta runtime, billing-limit or tenant-isolation change is required.

