# ADR-001 SaaS Workspace As Authoritative Scope

Status: Detected in code and confirmed by user.

## Context

The repository contains multiple systems, but current memory/development context is for `saas-version/` only.

## Decision

Treat `saas-version/` as the authoritative active product boundary for this memory system.

## Consequences

- Agents must inspect `saas-version/` before answering or editing SaaS work.
- Root `backend/`, root `frontend/`, `ai-service/`, and `mobile-android/` are out of scope unless explicitly requested.
- Docs and memory should not merge non-SaaS architecture into SaaS decisions.

## Evidence

- User clarification: only SaaS version is in scope.
- SaaS entrypoints exist under `saas-version/backend`, `saas-version/frontend`, `saas-version/admin-frontend`, and `saas-version/migrations`.

