# ADR-007 React Vite Client And Admin Apps

Status: Detected in code.

## Context

SaaS ships two frontend applications: tenant client app and platform admin app.

## Decision

Use React + Vite frontends:

- `saas-version/frontend` for tenant users.
- `saas-version/admin-frontend` for platform admins.

## Consequences

- Tenant session storage and admin session storage are separate.
- Both apps depend on `VITE_API_BASE`.
- Admin app uses `/saas/v1/admin/*`; client app uses tenant endpoints.
- Shared API changes must be checked against both apps.

## Evidence

- `saas-version/frontend/package.json`
- `saas-version/frontend/src/App.jsx`
- `saas-version/admin-frontend/package.json`
- `saas-version/admin-frontend/src/AdminApp.jsx`

