# Phase 15.1B/15.1C Agent Template Intake Report

Scope: SaaS only. Generated from `external-repos/agency-agents/` in read-only mode.

## Summary

- License detected: MIT.
- Normalized agent templates: 184.
- Strategy/playbook docs detected: 16.
- Disabled draft candidates generated: 29.
- Runtime import: none.
- External scripts executed: none.
- Database writes: none.

## Counts By Risk

- high: 155
- medium: 14
- restricted: 15

## Counts By Surface

- defer: 31
- internal_admin_eval: 68
- tenant_marketplace_draft: 85

## Counts By Category

- academic: 5
- design: 8
- engineering: 29
- finance: 5
- game-development: 20
- marketing: 30
- paid-media: 7
- product: 5
- project-management: 6
- sales: 8
- spatial-computing: 6
- specialized: 41
- support: 6
- testing: 8

## Draft Candidates

| Item key | Name | Surface | Risk | Industry | Source |
| --- | --- | --- | --- | --- | --- |
| external.agency_agents.marketing_marketing_content_creator.v1 | Content Creator | agent_store | restricted | general | marketing/marketing-content-creator.md |
| external.agency_agents.marketing_marketing_instagram_curator.v1 | Instagram Curator | agent_store | high | general | marketing/marketing-instagram-curator.md |
| external.agency_agents.paid_media_paid_media_paid_social_strategist.v1 | Paid Social Strategist | agent_store | restricted | general | paid-media/paid-media-paid-social-strategist.md |
| external.agency_agents.paid_media_paid_media_ppc_strategist.v1 | PPC Campaign Strategist | agent_store | restricted | general | paid-media/paid-media-ppc-strategist.md |
| external.agency_agents.paid_media_paid_media_tracking_specialist.v1 | Tracking & Measurement Specialist | agent_store | restricted | general | paid-media/paid-media-tracking-specialist.md |
| external.agency_agents.sales_sales_discovery_coach.v1 | Discovery Coach | agent_store | high | general | sales/sales-discovery-coach.md |
| external.agency_agents.sales_sales_outbound_strategist.v1 | Outbound Strategist | agent_store | high | general | sales/sales-outbound-strategist.md |
| external.agency_agents.sales_sales_pipeline_analyst.v1 | Pipeline Analyst | agent_store | high | general | sales/sales-pipeline-analyst.md |
| external.agency_agents.specialized_customer_service.v1 | Customer Service | agent_store | high | general | specialized/customer-service.md |
| external.agency_agents.specialized_healthcare_customer_service.v1 | Healthcare Customer Service | agent_store | high | healthcare | specialized/healthcare-customer-service.md |
| external.agency_agents.specialized_hospitality_guest_services.v1 | Hospitality Guest Services | agent_store | high | hospitality | specialized/hospitality-guest-services.md |
| external.agency_agents.specialized_legal_client_intake.v1 | Legal Client Intake | agent_store | high | legal | specialized/legal-client-intake.md |
| external.agency_agents.specialized_real_estate_buyer_seller.v1 | Real Estate Buyer & Seller | agent_store | high | real_estate | specialized/real-estate-buyer-seller.md |
| external.agency_agents.specialized_retail_customer_returns.v1 | Retail Customer Returns | agent_store | high | retail_ecommerce | specialized/retail-customer-returns.md |
| external.agency_agents.specialized_sales_outreach.v1 | Sales Outreach | agent_store | high | general | specialized/sales-outreach.md |
| external.agency_agents.support_support_support_responder.v1 | Support Responder | agent_store | high | general | support/support-support-responder.md |
| external.agency_agents.engineering_engineering_database_optimizer.v1 | Database Optimizer | internal_eval | medium | general | engineering/engineering-database-optimizer.md |
| external.agency_agents.engineering_engineering_incident_response_commander.v1 | Incident Response Commander | internal_eval | high | general | engineering/engineering-incident-response-commander.md |
| external.agency_agents.engineering_engineering_security_engineer.v1 | Security Engineer | internal_eval | high | general | engineering/engineering-security-engineer.md |
| external.agency_agents.engineering_engineering_sre.v1 | SRE (Site Reliability Engineer) | internal_eval | high | general | engineering/engineering-sre.md |
| external.agency_agents.engineering_engineering_technical_writer.v1 | Technical Writer | internal_eval | high | general | engineering/engineering-technical-writer.md |
| external.agency_agents.specialized_agentic_identity_trust.v1 | Agentic Identity & Trust Architect | internal_eval | high | general | specialized/agentic-identity-trust.md |
| external.agency_agents.specialized_agents_orchestrator.v1 | Agents Orchestrator | internal_eval | high | general | specialized/agents-orchestrator.md |
| external.agency_agents.specialized_automation_governance_architect.v1 | Automation Governance Architect | internal_eval | high | general | specialized/automation-governance-architect.md |
| external.agency_agents.specialized_specialized_workflow_architect.v1 | Workflow Architect | internal_eval | high | general | specialized/specialized-workflow-architect.md |
| external.agency_agents.testing_testing_api_tester.v1 | API Tester | internal_eval | high | general | testing/testing-api-tester.md |
| external.agency_agents.testing_testing_evidence_collector.v1 | Evidence Collector | internal_eval | high | general | testing/testing-evidence-collector.md |
| external.agency_agents.testing_testing_performance_benchmarker.v1 | Performance Benchmarker | internal_eval | medium | general | testing/testing-performance-benchmarker.md |
| external.agency_agents.testing_testing_reality_checker.v1 | Reality Checker | internal_eval | medium | general | testing/testing-reality-checker.md |

## Mandatory Guardrails

- Keep every generated item disabled until Admin/security review.
- Do not map external tool declarations directly to Scentra tools.
- Keep outbound/customer-facing behavior as suggest-only until explicit approval.
- Preserve tenant isolation, premium gating, preflight, budgets, memory governance and one-AI-owner behavior.
- Confirm upstream URL/commit/tag and run a formal secret scan before commercial use.
