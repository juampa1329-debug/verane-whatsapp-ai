# LOCALIZATION_PRODUCT_OPS

Scope: SaaS only.

## Text Flow

```mermaid
flowchart LR
  Env["Vite env\nVITE_APP_LOCALE / VITE_ADMIN_LOCALE"] --> Catalog["Local ES module catalog\nes-CO default"]
  Catalog --> Tenant["Tenant React shell"]
  Catalog --> Admin["Admin React shell"]
  Tenant --> Build["Vite build"]
  Admin --> Build
```

## Product Ops Gate

```mermaid
flowchart TD
  Change["SaaS change"] --> Docs["Update memory/docs"]
  Docs --> CopyAudit["phase14-copy-audit.mjs"]
  CopyAudit --> ReleaseCheck["phase14-release-check.mjs"]
  ReleaseCheck --> FrontendBuild["Tenant/Admin builds"]
  FrontendBuild --> Compose["Docker Compose config"]
  Compose --> Runtime["Docker migrations + health when available"]
  Runtime --> Handoff["Handoff with checks and residual risk"]
```

## Safety Boundaries

- No runtime translation service.
- No DB-backed locale table.
- No new dependency.
- No API contract change.
- No provider enum/value translation.
- No generated runtime mutation.

## External Agent Repository Intake

For Phase 15 research, keep external repositories outside `saas-version/` until an ADR approves integration.

Recommended workspace path:

```text
external-repos/agents-research/
```

Required intake metadata:

- Source URL or zip origin.
- Branch/tag/commit.
- License and reuse permission.
- Install/runtime notes.
- Which parts the user wants evaluated: planner, tools, memory, evals, observability, prompts, SDK, or orchestration.
- Confirmation that secrets and private customer data were removed.

Analysis order:

1. Read-only architecture review.
2. Map concepts to Scentra domains.
3. Record ADR and risks.
4. Prototype behind feature flags only after approval.
