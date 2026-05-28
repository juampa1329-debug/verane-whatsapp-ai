# Roadmap Scentra SaaS: Fases Restantes

Alcance: solo `saas-version/`.
Fecha: 2026-05-28.

## Estado General

Fases cerradas a nivel de codigo/repositorio:

- Fases 1 a 14.
- Fase 16: AI Real-Time Intelligence Layer.
- Fase 17: Federated Learning & Global Intelligence.
- Fase 18: AI Workflow Composer.
- Fase 19: Autonomous Revenue Engine.
- Fase 20: AI Enterprise Memory Network.
- Fase 22: AI Trust, Compliance & Governance.
- Fase 24.1 a 24.10: Voice & Multimodal Intelligence.

Fase 15 esta al 60% porque existe como intake offline seguro del repositorio externo de agentes, pero aun no se importaron templates a DB/Admin ni se activaron agentes de marketplace.

## Fases Que Quedan

### Fase 21: Scentra AI Cloud Platform

Objetivo: convertir las capacidades AI de Scentra en plataforma cloud extensible.

Entregables sugeridos:

- Public/developer APIs versionadas.
- Auth externa para developer apps.
- SDKs oficiales.
- Portal de documentacion API.
- Rate limits por app/tenant/plan.
- API keys con scopes, rotacion y auditoria.
- Gateway de integraciones externas.
- Webhooks salientes firmados.
- Sandbox para desarrolladores.

Dependencias previas:

- Fase 22 Trust AI.
- Fase 24 provider gating.
- Fase 23 sandbox/marketplace si se exponen plugins.
- Politica comercial y legal de APIs.

Riesgos:

- Superficie publica nueva.
- Abuso de APIs.
- Necesidad de soporte y observabilidad externa.

### Fase 23: AI Marketplace Economy

Objetivo: monetizar agentes, playbooks, workflows, plugins y AI packs.

Entregables sugeridos:

- Marketplace real tenant/Admin.
- Review/certificacion de items.
- Versionado y changelog.
- Ratings/reviews.
- Revenue share.
- Billing hooks.
- Sandbox de plugins.
- Abuse monitoring.
- Politicas legales y terminos de creadores.

Dependencias previas:

- Fase 15 intake externo.
- Fase 18 Composer.
- Fase 22 Trust/Governance.
- Fase 21 developer platform si hay terceros.

Riesgos:

- Codigo no confiable.
- Prompts inseguros.
- Disputas de monetizacion.
- Responsabilidad por contenido generado por terceros.

### Fase 25: Enterprise Decision Intelligence

Objetivo: convertir Scentra en capa ejecutiva de decision empresarial.

Entregables sugeridos:

- Decision cockpit ejecutivo.
- What-if analysis.
- Recomendaciones priorizadas por ROI/riesgo.
- Arboles de decision y evidencia.
- Simulaciones de negocio.
- Integracion con Revenue, Memory, Federated, Realtime y Trust.
- Reportes ejecutivos por tenant/industria.

Dependencias previas:

- Datos reales suficientes.
- Fase 17 con cohorts aceptados.
- Fase 19 con fuentes reales de revenue.
- Fase 20 con memoria publicada confiable.
- Fase 22 para trazabilidad/gobierno.

Riesgos:

- Decisiones incorrectas por datos incompletos.
- Sobreconfianza en IA.
- Necesidad de explicabilidad y aprobacion humana.

## Acceptance Pendiente De Fases Ya Implementadas

- Fase 17: correr Docker/migracion/API/Swagger/worker hasta `068`, bootstrap limpio `001`-`068`, prueba multi-tenant opt-in, revision privacidad/legal y runbook ModelOps.
- Fase 19: validar con datos reales de pedidos/pagos antes de usar forecasts comercialmente.
- Fase 20: validar prompt/RAG con nodos publicados solamente.
- Fase 24: probar credenciales reales de proveedores, media real, fuentes aprobadas, pricing real y policies off/demo/canary/full.
- Fase 11 ML: entrenar con labels reales revisados antes de promover modelos fuera de shadow/canary.

## Orden Recomendado

1. Acceptance productiva de Fase 17.
2. Acceptance productiva de Fases 19/20/24.
3. Fase 21: AI Cloud Platform.
4. Fase 23: AI Marketplace Economy.
5. Fase 25: Enterprise Decision Intelligence.

## Regla Principal

No avanzar a marketplace publico, APIs externas o decision intelligence comercial sin:

- feature flags apagados por defecto;
- gating por tenant/plan;
- auditoria;
- rollback;
- sandbox;
- politicas legales;
- validacion con datos reales;
- documentacion sincronizada.
