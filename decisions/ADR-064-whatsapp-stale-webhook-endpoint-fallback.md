# ADR-064: WhatsApp Stale Webhook Endpoint Fallback

Date: 2026-05-28

## Status

Accepted.

## Context

Production reported that real WhatsApp messages stopped appearing in the Inbox while Meta webhook settings had not been manually changed.

The SaaS inbound path resolves tenant by `/saas/v1/webhooks/{provider}/{endpoint_key}` before storing `saas_webhook_events`. If a deployment, DB repair, or endpoint rotation leaves Meta posting to an old endpoint key that no longer exists or is inactive, the POST is rejected before the worker can ingest the message.

## Decision

Keep exact endpoint-key lookup as the primary path.

For Meta-style WhatsApp POST payloads only, if exact endpoint lookup returns 404/inactive, recover tenant routing by matching payload WABA ID or Phone Number ID against an active connected WhatsApp integration and an active webhook endpoint.

Store diagnostic headers that mark the fallback and preserve the originally requested endpoint key.

Do not apply this fallback to GET verification. Meta verification still requires the current callback URL and verify token.

## Consequences

- Existing Meta POST delivery can recover when Meta still calls a stale endpoint key but payload assets match a configured tenant.
- Diagnostics can show `fallback URL antigua`, helping operators update Meta Developers to the current callback URL.
- This does not solve missing `subscribed_apps`, missing active endpoints, invalid Meta tokens, media 403s, or Meta not calling Scentra.
- Signature/token behavior is not weakened beyond the already existing Meta POST acceptance path.
