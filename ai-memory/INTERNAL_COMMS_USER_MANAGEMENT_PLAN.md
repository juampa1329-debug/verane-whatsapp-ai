# INTERNAL_COMMS_USER_MANAGEMENT_PLAN

Scope: SaaS only.

Status: implemented baseline runtime. Keep this file as product memory and extension guide.

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

- Tenant Settings profile/team management persists through `/auth/profile` and `/auth/team*`.
- Tenant password change and email OTP 2FA are already real backend flows.
- Admin `Usuarios` supports Admin profile/password, platform admins, tenant users and role/status changes.

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

Implemented tenant APIs:

- `GET /saas/v1/notifications`
- `POST /saas/v1/notifications/{recipient_id}/read`
- `POST /saas/v1/notifications/read-all`

Implemented admin APIs:

- `GET /saas/v1/admin/notifications`
- `GET /saas/v1/admin/notifications/targets`
- `POST /saas/v1/admin/notifications/draft-ai`
- `POST /saas/v1/admin/notifications`

Safety requirements:

- Preserve tenant isolation in every read/write.
- Creation/send must be platform-admin role gated.
- Tenant users can only read their assigned recipient rows.
- All sends and read acknowledgements should be auditable.
- Email delivery should be optional and use the existing SMTP helper.
- AI drafting must not auto-send.
- AI drafting must not include tenant secrets, customer private content or decrypted provider keys.

## Implemented Baseline

1. Durable schema and backend notification APIs were added in migration `075`.
2. Tenant notification popup and pinned Inbox pseudo-row were added.
3. Admin notification center was added with human approval before send.
4. Optional email copy uses SMTP and branded Spanish templates.
5. Draft generation is currently template-assisted and explicitly marked as non-autonomous.
6. Profile/user-management CRUD and welcome/alert email flow were added.

## Future Extension Recommendation

1. Add a real AI Gateway-backed draft option after deciding which tenant/provider credentials should fund platform notification drafting.
2. Add notification recipient filters by plan/segment when product needs it.
3. Add notification history/search page in the tenant app beyond the unread pinned Inbox behavior.

## Risk Notes

- Mixing system notifications into CRM conversations would risk AI/triggers treating them as customers.
- Sending one notification to many users needs per-recipient rows or the system cannot track read/pinned state safely.
- Email delivery should not block the main notification transaction if SMTP is slow or temporarily unavailable.
