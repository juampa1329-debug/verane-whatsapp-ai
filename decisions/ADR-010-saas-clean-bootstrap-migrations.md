# ADR-010 SaaS Clean Bootstrap Migrations

Status: Accepted
Date: 2026-05-24
Scope: SaaS only

## Context

The SaaS app uses SQL migrations under `saas-version/migrations` executed by `app_saas.tools.migrate`.

The project works in an existing environment, but a clean PostgreSQL bootstrap exposed migration failures:

- UTF-8 BOM in `022_instagram_business_integration.sql`.
- Ambiguous `max_memory_archives` reference in `030_saas_ai_agent_memory_vault_limits.sql`.
- `036_saas_knowledge_rag_phase8.sql` altered `saas_knowledge_sources` before creating it.
- Early legacy bridge migrations assumed root legacy tables existed.

## Decision

Normalize historical SaaS migrations for reproducible clean installs because the user explicitly requested clean Docker/PostgreSQL bootstrap.

Accepted migration policy for this repair:

- Keep changes minimal and schema-compatible.
- Do not refactor app logic.
- Preserve SaaS-only scope.
- Guard legacy root-table operations with `to_regclass`.
- Create SaaS tables before ALTER when the migration owns the table.
- Qualify ambiguous columns in `UPDATE ... FROM`.
- Keep SQL files strict UTF-8 without BOM.

## Consequences

Positive:

- Clean SaaS PostgreSQL bootstrap is more reproducible.
- Migration runner no longer depends on BOM-tolerant SQL parsing.
- Knowledge/RAG schema aligns better with runtime `knowledge/router.py`.
- Legacy migration steps no longer fail when root legacy tables are absent.

Risks:

- Historical migration edits must be verified against staging/production migration history before applying to an already-migrated database.
- Runtime validation passed later on 2026-05-24 with a temporary clean Docker/PostgreSQL stack.

## Verification

Completed in this session:

- SQL BOM scan: no BOM remains.
- Strict UTF-8 decode: all SQL files pass.
- Static order/FK heuristic: no unguarded order issue detected.
- Docker Compose config: valid.
- Later validation on 2026-05-24: clean Docker/PostgreSQL bootstrap applied migrations `001` through `039`, FastAPI health passed, standalone/embedded worker heartbeat passed, admin frontend started, and Swagger `/docs` returned 200.

Runtime note:

- Compose requires external network `coolify`; avoid running multiple temporary SaaS Compose projects on that same external network unless service aliases are isolated.
