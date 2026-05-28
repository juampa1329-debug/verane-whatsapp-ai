# ADR-020: Phase 10 Verticalization Packs

Status: accepted

Date: 2026-05-25

## Context

Scentra +AI SaaS needed Phase 10 verticalization so tenants can start with industry-specific CRM, campaign, automation, and agent baselines instead of a generic workspace.

Existing code already had pieces in separate domains:

- CRM pipeline presets in `app_saas/crm/router.py`.
- Factory AI agent templates and industry policy presets in `app_saas/agents/service.py`.
- Campaign templates, segments, triggers, flows, quiet-hours, and preflight runtime from Phase 7.
- Tenant/admin/client flows in `auth`, `tenants`, `admin`, and React apps.

The missing piece was a tenant-level industry state and an idempotent pack application layer that coordinates these existing domains safely.

## Decision

Add a dedicated SaaS backend domain:

- `saas-version/backend/app_saas/verticals/catalog.py`
- `saas-version/backend/app_saas/verticals/service.py`
- `saas-version/backend/app_saas/verticals/router.py`
- `saas-version/backend/app_saas/verticals/schemas.py`

Add migration `045_saas_verticalization_phase10.sql` with:

- `saas_tenants.industry_code`
- `saas_tenants.vertical_pack_version`
- `saas_tenants.vertical_pack_json`
- `saas_tenants.vertical_pack_applied_at`
- `saas_vertical_pack_applications`

Vertical packs are applied idempotently per tenant and seed:

- CRM default pipeline stages
- CRM custom fields
- labels
- CRM message templates
- saved segments
- trigger drafts
- remarketing flow drafts
- quiet-hours defaults
- optional recommended factory agents

Trigger resources from packs are created inactive and flow resources are created as draft. Recommended agents are not auto-created during registration, tenant creation, or admin industry changes; the tenant UI can explicitly request them.

## Consequences

- Tenant onboarding can now select an industry and receive an operational baseline.
- Admin can change a tenant industry and apply the same backend pack path.
- Pack application writes across tenants, CRM, campaigns, and agents, so future edits must preserve tenant filters, idempotency, and plan-limit behavior.
- Applying a pack updates the tenant default CRM pipeline; staging review is required before changing mature production tenants.
- Clean Docker/PostgreSQL bootstrap must be rerun through migration `045` when Docker Desktop is available.

## Safety Rules

- Do not activate seeded triggers or flows automatically.
- Do not create agents unless the caller explicitly requests it.
- Do not store secrets in `vertical_pack_json`.
- Preserve `/saas/v1/verticals` compatibility.
- Reuse existing CRM/campaign/agent schemas and preflight workflows instead of introducing a separate automation runtime.
