# AGENT_RULES

Scope: SaaS only. These rules bind future Codex/AI work in this repository unless the user explicitly overrides scope.

## Non-Negotiable Scope

- Active product scope is `saas-version/`.
- Do not modify root `backend/`, root `frontend/`, `ai-service/`, or `mobile-android/` unless the user explicitly asks.
- Do not import assumptions from the non-SaaS app into SaaS documentation or code changes.

## Change Discipline

- Never refactor without authorization.
- Never modify outside the requested scope.
- Never update dependencies automatically.
- Never install packages unless requested.
- Never move, delete, or rename files unless requested.
- Never change architecture because it looks cleaner.
- Always make the smallest compatible change.
- Preserve public API compatibility unless the task is explicitly a breaking change.
- Preserve tenant isolation, auth checks, and billing limits.

## Permanent Memory Workflow

Before any SaaS task:

- Read root/domain `AGENTS.md`.
- Read `ai-memory/CURRENT_STATE.md`.
- Read `tasks/TASK_STATE.md`.
- Analyze architectural impact.
- Identify risks.
- Create a short plan before modifying files.

After any SaaS change:

- Update `ai-memory/CURRENT_STATE.md`.
- Update `tasks/TASK_STATE.md`.
- Record important decisions in `decisions/`.
- Update affected documentation.
- Record risks.
- Keep code and documentation synchronized.

## Required Analysis Before Edits

- Always read root `AGENTS.md` and the nearest SaaS domain `AGENTS.md` before editing.
- Always inspect imports before editing.
- Always review references before editing: `rg "<symbol|path|endpoint>" saas-version`.
- Always inspect frontend consumers before backend response changes.
- Always inspect backend routers/schemas before frontend API changes.
- Always inspect migrations and runtime SQL before DB changes.
- Always check auth role requirements before changing protected behavior.
- Always check worker paths before changing queued workflows.

## Duplication And Patterns

- Do not create duplicated helpers when an existing domain helper exists.
- Follow local module style: routers, schemas, service/helpers, raw SQL patterns.
- Prefer existing provider/integration abstractions.
- Do not introduce a new framework or global abstraction without explicit approval.

## Documentation Synchronization

After any future SaaS code/config change, update as applicable:

- `tasks/TASK_STATE.md`
- `ai-memory/CURRENT_STATE.md`
- `ai-memory/CRITICAL_WARNINGS.md`
- `ai-memory/SAFE_MODIFICATION_GUIDE.md`
- `ai-memory/FILE_MAP.md`
- `ai-memory/BUSINESS_LOGIC.md`
- relevant docs in `docs/`
- relevant diagrams in `architecture/`
- ADRs in `decisions/` when a durable decision changes
- `docs/DEPENDENCIES.md` when dependencies change
- `docs/ENVIRONMENT.md` when env/config changes

## Output Rules For Agents

- State when a fact is derived from code.
- State when a risk is inferred.
- Do not invent endpoints, tables, providers, or env vars.
- If uncertain, search the codebase before answering.
- Keep documentation modular and concise for RAG/token efficiency.
