# INTEGRATIONS_FLOW

Scope: SaaS only.

## Provider Flow

```mermaid
flowchart LR
  Tenant["Tenant user"] --> UI["SaaS UI settings"]
  UI --> API["/saas/v1/integrations or provider route"]
  API --> Secrets["encrypted credential storage"]
  API --> DB["PostgreSQL"]
  Webhook["Provider webhook"] --> WebhookAPI["/saas/v1/webhooks/*"]
  WebhookAPI --> Events["webhook event records"]
  Worker["worker processors"] --> Events
  Worker --> Provider["Meta/Woo/AI/Billing provider"]
```

## Integration Families

- WhatsApp Cloud through Meta.
- Instagram Business through Meta Graph/OAuth.
- WooCommerce products/integration records.
- AI/TTS provider credentials through API credentials and AI gateway.
- Billing providers through billing webhooks/checkout.
- Turnstile captcha for auth forms when enabled.

## Rules

- Verify signature/token behavior before editing webhooks.
- Keep encrypted credential handling centralized.
- Preserve token health/refresh diagnostics.
- Do not hardcode provider secrets.

