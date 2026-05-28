# ADR-037 Phase 13 Security, 2FA & Compliance

Date: 2026-05-27

## Status

Accepted.

## Context

Scentra SaaS already had CAPTCHA, rate limits, lockout, password reset and 2FA preparation fields from Phase 1. Phase 13 needed enforceable MFA and compliance workflows without destabilizing tenant auth, platform admin auth, Meta webhooks, CRM, workers or AI runtime.

## Decision

Implement Phase 13 as backend-enforced email OTP MFA plus non-destructive privacy/compliance control-plane:

- Add forward migration `056_saas_phase13_security_compliance.sql`.
- Store MFA login challenges in `saas_mfa_challenges` with hashed OTPs, expiry, attempts, context and status.
- Use email OTP as the only supported MFA method for tenant and platform admin login.
- Add tenant `/auth/login/verify-otp` and admin `/admin/auth/login/verify-otp` verification endpoints.
- Add role-based mandatory MFA configuration through environment variables.
- Add tenant `/compliance/*` endpoints for current-user export, selected-customer export, privacy delete request creation and request listing.
- Add Admin Security Center APIs for current admin 2FA state, compliance metrics and audit CSV export.
- Keep delete requests as review records instead of automatic hard deletes.

## Safety Constraints

- Do not store or log raw OTPs.
- Production MFA requires SMTP; dev OTP exposure is local-only.
- TOTP/authenticator-app support is intentionally out of scope until separately designed.
- Privacy delete requests must not hard-delete CRM, conversation, message, audit, RAG, billing or agent memory data automatically.
- Existing Meta/WhatsApp/Instagram/webhook runtime is not modified.

## Consequences

- Tenant and platform admin auth now have real MFA enforcement using existing email infrastructure.
- Admins gain a Security Center for MFA/compliance visibility and audit export.
- Tenants gain export/delete-request workflows with tenant-scoped data boundaries.
- Production still needs SMTP/Turnstile/secrets/CORS configuration and legal/retention procedure before public compliance operations.
