# ADR-057: Groq Provider HTTP Headers

Status: Accepted

Date: 2026-05-28

Scope: SaaS only, `saas-version/`.

## Context

Production AI Gateway runs showed Groq failures with:

`http_403: error code: 1010`

This is consistent with a provider/Cloudflare-side block of generic Python HTTP client fingerprints. The existing AI Gateway used Python `urllib.request` with authorization headers, but without an explicit product `User-Agent` or `Accept` header.

## Decision

Use explicit provider HTTP headers for AI provider calls and provider model-list calls:

- `User-Agent: ScentraAI/1.0 (+https://scentra-ai.online)`
- `Accept: application/json`

Also refresh Groq static model fallbacks to avoid older fallback entries and prefer documented current options.

## Consequences

- Groq requests no longer present as generic `Python-urllib` traffic.
- The change is provider-compatible and applies to shared AI Gateway HTTP helpers.
- No provider secret handling, tenant isolation, billing gate, route contract or fallback behavior changes.
- If Groq/Cloudflare still blocks the production IP/project, Scentra must rely on configured fallbacks and escalate with Groq using provider logs.

