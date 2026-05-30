# INTERNAL_COMMS_USER_MANAGEMENT_PLAN

Scope: SaaS only.

Status: planning/memory only. No runtime implementation exists yet.

## Captured Operator Context

- The production email/SMTP channel has been configured outside the codebase by the user, using Oracle-hosted mail infrastructure.
- Scentra email is intended for:
  - password recovery
  - MFA/security notifications
  - system alerts
  - transactional system emails
- Existing backend SMTP support is in `saas-version/backend/app_saas/shared/email.py` and env vars are documented in `docs/ENVIRONMENT.md`.

## Product Requirements To Preserve

### Admin/Profile/User Management

The Admin app needs a real profile and user-management area.

Required capabilities:

- Current admin profile:
  - view/update name
  - view/change email with safe verification path
  - change password
  - manage 2FA/email OTP status
- Platform admin user management:
  - create platform admins
  - list admins
  - activate/deactivate admins
  - assign platform roles
- Tenant user management:
  - create tenant users
  - invite users by email
  - assign tenant roles: `owner`, `admin`, `supervisor`, `agent`, `viewer`
  - activate/deactivate tenant memberships
  - audit role changes

Current code notes:

- Tenant Settings has a profile UI in `frontend/src/App.jsx`, but `saveProfileLocal` is local-only and says persistence is missing.
- Tenant password change and email OTP 2FA are already real backend flows.
- Admin Security exists, but there is no complete Admin profile/user-management section yet.

### Internal Notifications / System Inbox

Add an internal communications system for platform/admin-to-tenant/user messages.

Required behavior:

- Admin can send notifications to:
  - one user
  - selected users
  - all users in a tenant
  - all tenants
  - selected tenant roles
  - selected plans or tenant segments later
- Optional AI assistance can draft the notification copy, but the human admin must approve before sending.
- Notifications should appear:
  - as a popup/notice when the user logs in or loads the app
  - as an internal pinned item at the top of the tenant Inbox while unread
  - in a persistent notification inbox/history
- Once read, the notification loses top pinning but remains in history.

Hard boundaries:

- Do not store internal system notifications as customer `saas_conversations` unless explicitly approved.
- Do not send these notifications to WhatsApp/Instagram/Facebook.
- Do not let customer-facing AI, triggers, remarketing, CRM automation, or agent orchestration answer or process these notifications as customer chats.
- Do not show a customer composer/reply box for these internal notifications.
- Do not count internal notifications as customer messages or Meta outbound usage.

Recommended architecture:

- New backend domain: `app_saas/notifications`.
- New migration tables:
  - `saas_system_notifications`
  - `saas_system_notification_recipients`
- Use per-recipient rows for read state, pinning, delivery state and auditability.
- Tenant app should render unread internal notifications as pseudo-items above the Inbox conversation list, not as real CRM conversation rows.
- Admin app should get a new `Notificaciones` or `Comunicaciones` view.

Suggested tenant APIs:

- `GET /saas/v1/notifications`
- `GET /saas/v1/notifications/unread`
- `POST /saas/v1/notifications/{notification_id}/read`

Suggested admin APIs:

- `GET /saas/v1/admin/notifications`
- `POST /saas/v1/admin/notifications/draft-ai`
- `POST /saas/v1/admin/notifications`
- `POST /saas/v1/admin/notifications/{notification_id}/send`

Safety requirements:

- Preserve tenant isolation in every read/write.
- Creation/send must be platform-admin role gated.
- Tenant users can only read their assigned recipient rows.
- All sends and read acknowledgements should be auditable.
- Email delivery should be optional and use the existing SMTP helper.
- AI drafting must not auto-send.
- AI drafting must not include tenant secrets, customer private content or decrypted provider keys.

## Implementation Order Recommendation

1. Add durable schema and backend notification APIs.
2. Add tenant notification popup and pinned Inbox pseudo-row.
3. Add Admin notification center without AI drafting.
4. Add optional email delivery using SMTP.
5. Add AI-assisted draft generation with explicit human approval.
6. Add profile/user-management CRUD and invitation flow.

## Risk Notes

- Mixing system notifications into CRM conversations would risk AI/triggers treating them as customers.
- Sending one notification to many users needs per-recipient rows or the system cannot track read/pinned state safely.
- Email delivery should not block the main notification transaction if SMTP is slow or temporarily unavailable.
