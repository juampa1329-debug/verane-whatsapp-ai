# SECURITY_COMPLIANCE

Scope: SaaS security/compliance surfaces, including Phase 13 MFA/privacy and Phase 22 AI Trust.

## Purpose

Phase 13 adds enforceable email OTP MFA and tenant-scoped compliance workflows without changing Meta, CRM, billing, worker or AI runtime behavior.

## MFA Flow

```mermaid
sequenceDiagram
  participant UI as "Tenant/Admin UI"
  participant API as "Auth API"
  participant DB as "PostgreSQL"
  participant SMTP as "SMTP"
  UI->>API: "POST login"
  API->>API: "captcha + rate limit + password verify"
  API->>API: "check user setting and role-required MFA"
  API->>DB: "insert saas_mfa_challenges with hashed OTP"
  API-->>SMTP: "send OTP when configured"
  API-->>UI: "mfa_required + challenge_token"
  UI->>API: "POST login/verify-otp"
  API->>DB: "verify hash, expiry, attempts, context"
  API-->>UI: "MFA-verified JWT"
```

## Compliance Flow

```mermaid
flowchart TB
  User["Tenant user"] --> ExportMe["GET /compliance/me/export"]
  User --> ExportCustomer["GET /compliance/customers/{conversation_id}/export"]
  User --> DeleteRequest["POST /compliance/customers/{conversation_id}/delete-request"]
  ExportMe --> TenantFilter["Auth context + tenant filter"]
  ExportCustomer --> TenantFilter
  DeleteRequest --> TenantFilter
  TenantFilter --> DB["PostgreSQL"]
  DeleteRequest --> Review["saas_privacy_requests review queue"]
  Review --> AdminOps["Manual/legal fulfillment procedure"]
```

## Admin Security Center

```mermaid
flowchart LR
  Admin["Platform admin"] --> Security["Admin Security View"]
  Security --> Metrics["GET /admin/security/compliance"]
  Security --> MFA["GET/PATCH /admin/auth/security"]
  Security --> Audit["GET /admin/audit/export.csv"]
  Metrics --> DB["users, platform admins, webhooks, security events, privacy requests"]
```

## Safety Boundaries

- Email OTP is the only implemented MFA method.
- OTPs and reset tokens are stored as hashes, not raw secrets.
- Production MFA requires SMTP; dev OTP exposure is local-only.
- Compliance delete requests are non-destructive records.
- Customer exports are tied to tenant-scoped conversation IDs.
- Admin audit CSV is a review export, not immutable external archival.
- Secret rotation and TOTP are future scoped work, not hidden behavior in Phase 13.

## Phase 22 AI Trust Boundary

Phase 22 adds AI governance records under `/trust-center` and `/admin/trust-center`.

- Policies, attestations, risk assessments, model cards, incidents, reports and audits are tenant-scoped.
- Risk scans inspect AI metadata but do not enforce runtime changes.
- Compliance reports are evidence snapshots, not legal certification.
- Admin Trust AI overview is read-only and must not expose raw tenant content across tenants.
