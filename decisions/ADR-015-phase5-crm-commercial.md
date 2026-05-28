# ADR-015: Phase 5 Commercial CRM

Status: Accepted

Date: 2026-05-25

## Context

Phase 5 needed to close the gap between the existing SaaS CRM and a commercial CRM that can feed campaigns, AI, and follow-up. The code already had tenant conversations/customers, labels, tasks, lead score, assignments, saved segments, and AI CRM updates. Missing product surfaces were tenant custom fields, configurable pipeline, unified timeline, and duplicate merge.

## Decision

- Add forward migration `040_saas_crm_commercial_phase5.sql`.
- Store custom-field definitions in `saas_crm_custom_fields`.
- Store custom-field values inside `saas_conversations.profile_json.custom_fields` to preserve existing customer and conversation response contracts.
- Add default tenant pipeline and stages with industry presets through `saas_crm_pipelines` and `saas_crm_pipeline_stages`.
- Add CRM timeline events and merge audit through `saas_crm_timeline_events` and `saas_crm_merge_events`.
- Keep `crm_stage` as the conversation-facing stage value for backward compatibility.
- Gate AI custom-field updates to configured field keys and runtime agent `crm.update` plus `can_update_crm`.

## Consequences

- Existing CRM consumers remain compatible because primary customer/conversation fields are unchanged.
- Custom-field values remain query-light for the existing CRM UI, but analytics over custom fields require JSONB-aware queries or later materialization.
- Customer merge is available but should be rehearsed with staging/backup data before bulk operational use.
- Clean Docker/PostgreSQL bootstrap must be rerun when Docker is available to validate migration `040` end to end.
