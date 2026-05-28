# AUTH_FLOW

Scope: SaaS only.

## Tenant User Auth

```mermaid
sequenceDiagram
  participant UI as Client App
  participant API as /saas/v1/auth
  participant DB as PostgreSQL
  UI->>API: POST /register or /login
  API->>API: optional captcha + rate limit
  API->>DB: user + membership + tenant checks
  API->>API: Argon2 password verify/hash
  API->>API: if email OTP required, create hashed MFA challenge
  API-->>UI: either MFA challenge or access token + refresh token
  UI->>API: POST /login/verify-otp when challenged
  API->>DB: verify hashed OTP + expiry + attempts
  API->>UI: MFA-verified access token + refresh token
  UI->>API: Bearer access token
  API->>API: get_current_user validates JWT/role/tenant
```

## Password Recovery

```mermaid
sequenceDiagram
  participant UI as Client/Admin App
  participant API as /saas/v1/auth
  participant DB as PostgreSQL
  participant SMTP as SMTP server
  UI->>API: POST /password/forgot email + optional captcha
  API->>API: rate limit by endpoint/email/IP
  API->>DB: supersede old tokens + store hashed single-use token
  API-->>SMTP: send reset link when SMTP is configured
  UI->>API: POST /password/reset token + new password
  API->>DB: validate hash/status/expiry
  API->>DB: update password hash + clear lockout + mark token used
```

## Account Lockout

```mermaid
flowchart TB
  BadLogin["Invalid tenant/admin login"] --> Counter["Increment saas_users.failed_login_count"]
  Counter --> Threshold{"Count >= SAAS_LOGIN_LOCK_FAILED_ATTEMPTS"}
  Threshold -- "no" --> Reject["401 invalid credentials"]
  Threshold -- "yes" --> Lock["Set locked_until = now + SAAS_LOGIN_LOCK_MINUTES"]
  Lock --> Block["423 account_temporarily_locked"]
  GoodLogin["Valid login after lock expires"] --> Clear["Clear failed_login_count and locked_until"]
```

## Platform Admin Auth

```mermaid
sequenceDiagram
  participant Admin as Admin App
  participant API as /saas/v1/admin/auth
  participant DB as PostgreSQL
  Admin->>API: POST /login
  API->>DB: saas_users + saas_platform_admins
  API->>API: verify role/status
  API->>API: if email OTP required, create hashed MFA challenge
  API-->>Admin: either MFA challenge or platform token
  Admin->>API: POST /login/verify-otp when challenged
  API->>DB: verify hashed OTP + expiry + attempts
  API->>Admin: MFA-verified platform token
  Admin->>API: Bearer platform token
  API->>API: get_current_platform_admin
```

## First Platform Admin Seed

```mermaid
sequenceDiagram
  participant Ops as Operator
  participant Seed as platform-admin-seed / create_platform_admin
  participant DB as PostgreSQL
  Ops->>Seed: SAAS_ADMIN_EMAIL + strong password + role
  Seed->>DB: upsert saas_users + saas_platform_admins
  Seed-->>Ops: user_id + email + platform_role
```

## Rules

- Tenant roles and platform roles are separate.
- Tenant JWT must include tenant context.
- Platform admin privileges must not imply tenant membership unless impersonation flow explicitly handles it.
- Password hashing uses Argon2.
- JWT uses HS256 with configured issuer/secret.
- CAPTCHA is enforced server-side when enabled; frontend widgets are not trusted alone.
- Phase 13 supports email OTP MFA challenges for tenant/admin login. TOTP/authenticator apps are not implemented.
- HTTP admin bootstrap is local-only; production first-admin creation must use the seed tool/service.
