# ADR-066: SaaS Dockerfile Startup Gate

## Status

Accepted

## Context

Production Coolify inspection on 2026-05-28 showed the API app configured with base directory `/` and Dockerfile `/backend/Dockerfile`. That builds the legacy non-SaaS backend, whose container runs `uvicorn app.main:app` and does not contain `/app/app_saas` or `/app/migrations`.

The SaaS Compose service already starts the API with:

```bash
python -m app_saas.tools.migrate /app/migrations && python -m app_saas.tools.schema_check /app/migrations && uvicorn app_saas.main:app --host 0.0.0.0 --port 8000
```

Dockerfile-only deployments did not enforce this gate by default.

## Decision

`saas-version/backend/Dockerfile` must use the same startup gate as the Compose API service.

Coolify Dockerfile deployments for the SaaS API must use:

- Base directory: `saas-version`
- Dockerfile location: `/backend/Dockerfile`
- Exposed port: `8000`

The startup command is container-scoped. It must not be treated as a VPS host-shell command.

## Consequences

- Dockerfile-only deployments now fail before Uvicorn if migrations or schema readiness fail.
- A wrong Coolify base directory still needs operator correction, but the documented deploy contract is explicit.
- Compose behavior remains compatible because Compose already overrides the API command with the same gate.
- No application route, worker, webhook, AI runtime, database migration or frontend behavior changes.

