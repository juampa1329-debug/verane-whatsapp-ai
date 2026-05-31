# ADR-072 - Profile Timezone And Friendly Error UX

Date: 2026-05-30

## Status

Accepted

## Context

Scentra operators need dates and diagnostics to be understandable in Colombia by default, with a profile-level option to change timezone when a user works from another region. Users also see backend/provider machine errors such as raw endpoint codes, Meta sync failures or `churn` labels that are useful for support but confusing in the UI.

The existing SaaS schema already has `saas_users.profile_json` for profile metadata.

## Decision

- Store tenant/Admin timezone preference in `saas_users.profile_json.timezone`.
- Default timezone in tenant and Admin UIs to `America/Bogota`.
- Persist the selected timezone in local browser storage (`scentra_user_timezone` and `scentra_admin_timezone`) so formatting is stable before `/me` finishes loading.
- Format visible dates/times through the selected timezone in the tenant and Admin apps.
- Keep backend machine error codes/details for support, but present Spanish friendly error modals with likely cause, suggested next action and collapsible technical detail.
- Replace user-facing raw `Churn` language with `Riesgo de abandono` / `Abandono`.
- Reuse public Scentra brand assets and public payment logo URLs in UI chips with text fallback.

## Consequences

- No database migration is required, reducing production bootstrap risk.
- The UI can support Colombia time immediately while allowing user preference changes later.
- Support still has access to machine details without exposing raw backend wording as the primary user message.
- Payment logo rendering depends on external public image availability until approved local brand assets are bundled.

## Guardrails

- Do not remove backend machine codes; they are useful for logs, API clients and support.
- Do not hardcode credentials or provider runtime behavior in logo/UI work.
- If future timezone entry becomes free-form, add backend timezone validation before storing.
