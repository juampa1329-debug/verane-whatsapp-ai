# ADR-069 - Internal Notifications And Transactional Email

## Status

Accepted.

## Context

Scentra needs password recovery, welcome emails, account/role alerts, Admin-originated notifications, and in-app announcements without mixing system communications with customer conversations.

Customer conversations are processed by Inbox, CRM, triggers, remarketing, AI replies and agent orchestration. Reusing those tables for platform announcements would risk AI responding to system notices or showing them as customer messages.

## Decision

Implement a dedicated internal notification domain:

- Store system communications in `saas_system_notifications`.
- Store per-user delivery/read/email state in `saas_system_notification_recipients`.
- Show tenant notifications as non-replyable popups and pinned Inbox pseudo-items while unread.
- Keep internal notifications outside customer conversation/message tables.
- Use branded Spanish HTML emails from `app_saas.shared.email` for reset password, welcome, access/role alerts and optional notification copies.
- Send bulk notification email copies after in-app notification rows are committed so SMTP does not hold a PostgreSQL transaction.

## Consequences

- Customer AI, triggers, remarketing, CRM automation and agent orchestration stay isolated from platform notifications.
- In-app delivery works even when SMTP is down or not configured.
- Admin can target notifications by tenant, role or user while keeping copy human-readable.
- Future notification work should extend this domain, not create synthetic customer conversations.

