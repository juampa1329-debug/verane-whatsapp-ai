# ADR-065: WhatsApp Legacy No-Key Webhook Compatibility

## Status

Accepted.

## Context

Production diagnostics showed that synthetic WhatsApp inbound events could be processed into Inbox records and outbound WhatsApp messages could be delivered, but real inbound messages still did not appear in Scentra.

That narrows the failure mode to Meta callback delivery before Scentra ingestion. One likely production drift case is a Meta Developer callback still pointing to a legacy no-key URL such as `/saas/v1/webhooks/whatsapp` or `/saas/v1/webhooks/meta`, while the canonical SaaS endpoint is `/saas/v1/webhooks/{provider}/{endpoint_key}`.

## Decision

Keep the canonical endpoint-key route as the preferred route, but also accept no-key WhatsApp/meta callback routes:

- `GET|POST /saas/v1/webhooks/whatsapp`
- `GET|POST /saas/v1/webhooks/meta`

No-key GET verification resolves the active endpoint by matching Meta `hub.verify_token` against active WhatsApp/meta endpoint token hashes.

No-key POST delivery reuses the existing WhatsApp payload-asset fallback and resolves the tenant by WABA/Phone Number ID from the Meta payload plus an active connected WhatsApp integration.

Stored webhook headers mark this recovery path as `x-scentra-endpoint-fallback=legacy_no_key_payload_asset`.

## Consequences

- Old Meta callbacks without endpoint key can recover without changing tenant data.
- Diagnostics can show whether traffic used the legacy path.
- The canonical callback URL with endpoint key remains the target operators should configure in Meta Developers.
- This does not solve cases where Meta is not reaching the API domain/path at all, the app is not subscribed to the WhatsApp `messages` field, or WABA/token/app permissions are incorrect.

