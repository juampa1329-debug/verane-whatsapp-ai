# ADR-011 Phase 1 Security Hardening

Status: Implemented on 2026-05-24.

## Context

Phase 1 requires auth entrypoints to be protected before scaling users: CAPTCHA, backend validation, rate limiting by endpoint/IP/principal, security logs, temporary lockout, account recovery, and 2FA preparation.

## Decision

Keep security enforcement in the SaaS backend and use the frontends only as token collectors/UX:

- Verify Turnstile in backend when `SAAS_CAPTCHA_ENABLED=true`.
- Use `saas_security_events` for auth attempts, failures, blocks, resets, password changes, and 2FA-prep changes.
- Enforce auth rate limits per event/endpoint with combined IP+principal, principal/email, and IP scopes.
- Store failed login state on `saas_users.failed_login_count` and `saas_users.locked_until`.
- Store password recovery tokens as hashed, expiring, single-use rows in `saas_password_reset_tokens`.
- Send reset links through stdlib SMTP when configured; expose dev tokens only in local mode.
- Persist 2FA preparation fields on `saas_users`, but defer OTP/TOTP login challenge enforcement to a later security phase.

## Consequences

- Tenant and platform admin login share the same lockout primitives while keeping authorization models separate.
- Password reset does not reveal account existence.
- Production account recovery depends on SMTP configuration.
- Production CAPTCHA closure depends on both frontend Turnstile site key and backend Turnstile secret.
- Future full 2FA work must build on the existing persisted fields without claiming Phase 1 already enforces OTP.

## Evidence

- `saas-version/migrations/038_saas_phase1_security_hardening.sql`
- `saas-version/backend/app_saas/auth/router.py`
- `saas-version/backend/app_saas/auth/schemas.py`
- `saas-version/backend/app_saas/admin/router.py`
- `saas-version/backend/app_saas/shared/security.py`
- `saas-version/backend/app_saas/shared/security_events.py`
- `saas-version/backend/app_saas/shared/email.py`
- `saas-version/frontend/src/App.jsx`
- `saas-version/admin-frontend/src/AdminApp.jsx`
