# ADR-053 - Phase 19 Autonomous Revenue Engine

## Status

Accepted.

## Context

Scentra already has CRM, conversations, Intelligence events, predictions, recommendations, Advisor, workflows, campaigns and premium gating. Phase 19 must improve revenue operations without introducing uncontrolled autonomy, automatic sends, billing mutations or campaign activation.

## Decision

Implement Autonomous Revenue Engine as a tenant-scoped, premium-gated control-plane under `/saas/v1/intelligence/revenue/*`.

The engine:

- detects opportunities from real CRM/conversation signals
- stores supervised revenue opportunities, reports, forecasts and experiments
- requires human approval before execution state changes
- records execution as controlled metadata only
- enforces optional policy allowlists for playbook action types
- enforces configured monthly control-plane execution caps
- emits Intelligence events and usage records
- runs from the Intelligence worker only when full premium access allows it

## Safety Boundaries

- No automatic customer messages.
- No automatic charges or billing provider calls.
- No CRM mutation beyond revenue control-plane records.
- No campaign, workflow, trigger or agent activation.
- No fake revenue values; estimated value remains `0` when tenant order/revenue data is unavailable.

## Consequences

Phase 19 is operational as a revenue intelligence layer. Real revenue attribution still requires tenant commerce/order data and acceptance with real workflows before commercial automation.

## Validation

Accepted with active Docker migration `066`, OpenAPI checks, full-mode tenant smoke for opportunity creation/approve/execute, and clean isolated PostgreSQL bootstrap through `001-066`.
