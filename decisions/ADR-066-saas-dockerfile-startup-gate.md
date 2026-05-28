# ADR-066: SaaS Dockerfile Startup Gate

## Status

Accepted

## Context

Production Coolify inspection on 2026-05-28 showed the running API container was legacy/non-SaaS: it ran `uvicorn app.main:app` and did not contain `/app/app_saas` or `/app/migrations`.

Follow-up deploy logs showed the connected Coolify source repository is `juampa1329-debug/Scentra-AI`, where the SaaS files are already at repository root. Setting `Base Directory: saas-version` for that direct repo fails because `/saas-version/backend` does not exist in the artifact.

The SaaS Compose service already starts the API with:

```bash
python -m app_saas.tools.migrate /app/migrations && python -m app_saas.tools.schema_check /app/migrations && uvicorn app_saas.main:app --host 0.0.0.0 --port 8000
```

Dockerfile-only deployments did not enforce this gate by default.

## Decision

`saas-version/backend/Dockerfile` must use the same startup gate as the Compose API service.

Coolify Dockerfile deployments for the SaaS API depend on which repository is connected.

When Coolify imports `juampa1329-debug/Scentra-AI`, SaaS files are already at repository root and the API app must use:

- Base directory: `/`
- Dockerfile location: `/backend/Dockerfile`
- Exposed port: `8000`

When Coolify imports the monorepo `juampa1329-debug/verane-whatsapp-ai`, use:

- Base directory: `/saas-version`
- Dockerfile location: `/backend/Dockerfile`
- Exposed port: `8000`

The startup command is container-scoped. It must not be treated as a VPS host-shell command.

## Consequences

- Dockerfile-only deployments now fail before Uvicorn if migrations or schema readiness fail.
- A wrong Coolify base directory still needs operator correction, but the documented deploy contract is explicit.
- Compose behavior remains compatible because Compose already overrides the API command with the same gate.
- No application route, worker, webhook, AI runtime, database migration or frontend behavior changes.
