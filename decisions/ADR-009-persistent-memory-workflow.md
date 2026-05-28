# ADR-009 Persistent Memory Workflow

Status: Accepted by user instruction.

## Context

SaaS work requires continuity across Codex CLI sessions and context compaction. The project already has root and domain `AGENTS.md` files plus memory/docs under `ai-memory/`, `tasks/`, `docs/`, `architecture/`, and `decisions/`.

## Decision

All future SaaS tasks must follow a permanent memory workflow.

Before any task:

- Read relevant root/domain `AGENTS.md`.
- Read `ai-memory/CURRENT_STATE.md`.
- Read `tasks/TASK_STATE.md`.
- Analyze architectural impact.
- Identify risks.
- Create a short plan before modifying files.

After any change:

- Update `ai-memory/CURRENT_STATE.md`.
- Update `tasks/TASK_STATE.md`.
- Record important decisions in `decisions/`.
- Update affected documentation.
- Record risks.
- Keep code and documentation synchronized.

## Consequences

- Agents spend a small amount of time bootstrapping context before acting.
- Documentation/memory changes become part of the definition of done for SaaS work.
- Risk of hallucination, destructive refactors, and stale context is reduced.
- Non-SaaS paths remain out of scope unless explicitly authorized.

## Evidence

- User instruction: adopt permanent persistent-memory workflow for SaaS version.
- Existing root `AGENTS.md` and domain `AGENTS.md` hierarchy.
- Existing memory files: `ai-memory/CURRENT_STATE.md`, `tasks/TASK_STATE.md`, and `docs/AGENT_RULES.md`.
