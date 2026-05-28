# Informe Scentra: Fase 15.1, Entrenamiento ML Fase 11 y Roadmap 16-25

Alcance: solo `saas-version/`.
Fecha: 2026-05-27.
Fuente externa inicial: `D:\Juan Pablo\Descargas\README.md`.
Fuente local completa analizada: `external-repos/agency-agents/`.

## 1. Resumen Ejecutivo

Este informe agrega tres decisiones de seguimiento:

- Fase 15.1: aprovechar el repositorio externo de agentes como fuente de taxonomia, templates y rubricas, no como runtime ejecutable.
- Fase 11: explicar como se entrenan y promueven modelos ML reales dentro de Scentra sin romper el runtime actual.
- Roadmap 16-25: evaluar si las nuevas fases son viables y en que orden conviene ejecutarlas.

Conclusion principal:

Scentra ya tiene una base fuerte de SaaS, AI Agents, Intelligence Engine, ML opcional, Agent OS, AI Ecosystem, Enterprise AI Network, seguridad, performance, Product Ops, Workflow Composer, Trust AI y Real-Time Intelligence. Tras analizar la repo completa, lo siguiente debe avanzar con disciplina: mantener los templates externos como intake gobernado, usar Composer/Trust/Realtime como control-planes seguros y despues avanzar a voz/multimodal y fases de mayor autonomia.

## 2. Analisis de la Repo Externa

La repo local analizada corresponde a `agency-agents`, llamada "The Agency" en el README.

Lo detectado:

- Es una libreria de agentes Markdown/personas/prompts.
- El archivo `LICENSE` local es MIT.
- El inventario local detecta 184 agentes validos con frontmatter.
- Tambien hay 16 documentos estrategicos/playbooks sin frontmatter de agente.
- Los agentes estan organizados en 14 categorias de agentes mas docs de estrategia.
- Los archivos suelen incluir identidad, personalidad, mision, reglas, workflows, entregables y metricas.
- Incluye scripts de conversion/instalacion para Claude Code y otras herramientas.
- No se presenta como backend SaaS, cola, base de datos, sandbox seguro, billing, observabilidad o runtime productivo.
- La carpeta local no fue detectada como subrepo Git independiente, asi que commit/tag upstream sigue sin verificar.

Valor para Scentra:

- Taxonomia de agentes por rol.
- Plantillas de personalidad y mision para agentes de fabrica.
- Rubricas de evaluacion por tipo de agente.
- Inspiracion para marketplace de agentes.
- Inspiracion para Agent OS, equipos multiagente y Workflow Composer.
- NEXUS/playbooks/handoffs como base para handoff contracts, QA gates, runbooks y evals.
- Agentes internos utiles para QA de Scentra: Code Reviewer, Security Engineer, Evidence Collector, Reality Checker, Database Optimizer y Technical Writer.

Riesgo:

- Los scripts no son runtime SaaS y no deben ejecutarse dentro de Scentra.
- Las claims de "production-ready" deben validarse con archivos reales y pruebas.
- Una libreria de prompts no reemplaza el runtime actual de Scentra.
- Importar prompts sin revision puede introducir permisos inseguros, mala marca, prompt injection o comportamiento no compatible con tenants.

## 3. Fase 15.1 Propuesta

Nombre:

Agent Template Intake & Taxonomy Mapping.

Objetivo:

Convertir el repositorio externo en una fuente revisada de templates, categorias, rubricas y packs de agentes para Scentra, manteniendo aislamiento multi-tenant, premium gating y aprobacion humana.

Entregables:

- Intake read-only del repo completo. Estado: completado a nivel documental.
- Revision de licencia y atribucion. Estado: LICENSE MIT detectado; commit/tag y modificacion local siguen pendientes.
- Parser de inventario de agentes. Estado: completado como script offline.
- Mapeo categoria externa -> rol/industria Scentra. Estado: completado como artefactos offline.
- Esquema de normalizacion de templates. Estado: completado en JSON offline.
- Mapeo a factory agents, custom agents, marketplace, Agent OS, herramientas y memoria.
- Matriz de riesgos por agente/categoria.
- Importacion piloto de 5-10 templates como drafts deshabilitados.
- Rubricas de evaluacion para agentes QA.
- ADR antes de importar contenido al producto.

Criterios de cierre:

- Ningun script externo fue ejecutado.
- Ningun agente fue instalado globalmente en Codex/Claude.
- Ningun plugin externo corre dentro de API/worker.
- Los templates importados quedan disabled/draft hasta aprobacion.
- Las herramientas son explicitas y approval-first.
- Se conserva la regla actual: una conversacion solo tiene un dueno IA activo.

## 4. Lo Que Sigue Necesitando Confirmacion

La repo local ya esta disponible. Para pasar de analisis a importacion segura todavia falta confirmar:

- Source URL oficial.
- Commit hash o release tag upstream.
- Si la carpeta local tiene cambios privados.
- Confirmacion de licencia MIT o compatible con SaaS comercial.
- Reglas de atribucion si existen.
- Carpetas prioritarias.
- Confirmacion de que no hay secretos, tokens, datos de clientes o prompts privados.

Fases 15.1B/15.1C/15.2/15.3 ya completadas sin tocar runtime:

- `saas-version/scripts/phase15-agent-template-intake.mjs`.
- `saas-version/scripts/phase15-nexus-eval-harness.mjs`.
- `docs/phase15_1/agent_template_inventory.json`.
- `docs/phase15_1/agent_template_inventory.csv`.
- `docs/phase15_1/agent_template_drafts.json`.
- `docs/phase15_1/agent_template_risk_report.md`.
- `docs/phase15_1/nexus_handoff_contracts.json`.
- `docs/phase15_1/nexus_playbooks.json`.
- `docs/phase15_1/agent_eval_rubrics.json`.
- `docs/phase15_1/agent_eval_results.json`.
- `docs/phase15_1/phase15_2_15_3_report.md`.

Resultado 15.2/15.3:

- 7 contratos de handoff NEXUS.
- 7 playbooks de fase.
- 4 runbooks de escenario.
- 6 rubricas de evaluacion Scentra.
- 29 drafts evaluados, todos bloqueados para activacion hasta revision humana.

## 5. Como Se Entrenan los Modelos de Fase 11

Scentra no debe iniciar con entrenamiento pesado ni GPU. La estrategia correcta es incremental, tabular, explicable, multi-tenant y apagada por defecto.

Flujo operativo:

1. Capturar eventos estructurados.
2. Generar auto-labels desde eventos reales.
3. Recomputar features por tenant/sujeto/modelo.
4. Construir dataset desde Postgres.
5. Entrenar LightGBM, XGBoost o sklearn fallback.
6. Evaluar offline.
7. Registrar modelo en registry.
8. Ejecutar shadow inference.
9. Hacer canary con bajo porcentaje.
10. Promover a produccion solo con aceptacion humana.

Infraestructura ya preparada:

- `saas_intelligence_events`
- `saas_ml_auto_labels`
- `saas_intelligence_feature_values`
- `saas_ml_training_datasets`
- `saas_ml_model_evaluations`
- `saas_intelligence_model_registry`
- MLflow opcional.
- BentoML image opcional.
- XGBoost, LightGBM y scikit-learn en imagen ML.
- Qdrant opcional, no conectado aun al RAG productivo.

Flags importantes:

- `SAAS_ML_ENABLED=false` por defecto.
- `SAAS_ML_SHADOW_INFERENCE_ENABLED=true` en staging para comparar sin afectar negocio.
- `SAAS_ML_AUTO_TRAIN_ENABLED=false` inicialmente.
- `SAAS_ML_SERVICE_URL=http://ml-service:8090`.
- `SAAS_MLFLOW_TRACKING_URI=http://mlflow:5000`.

Modelos iniciales:

- Lead Scoring V1: probabilidad de conversion y temperatura.
- Churn Prediction V1: riesgo de abandono.
- Smart Remarketing V1: mejor canal, hora, frecuencia y segmento.
- Operational Anomaly V1: degradacion de webhooks, colas y APIs.

Datos minimos recomendados:

- Lead scoring: 500 a 1,000 leads etiquetados; mejor 5,000+.
- Churn: 300 a 500 ejemplos; mejor 2,000+.
- Remarketing: 1,000+ resultados de campanas/triggers.
- Anomalias: suficiente trafico normal y eventos de incidente.

Lo que no se necesita inicialmente:

- GPU.
- Entrenar LLMs propios.
- Kafka/NATS en el stack default.
- Training distribuido.
- Datasets externos privados.

## 6. Reglas de Seguridad ML

- No vender modelos bootstrap como precision productiva.
- No compartir mensajes crudos entre tenants.
- No compartir telefonos, nombres, conversaciones o documentos privados.
- Los modelos cross-tenant solo pueden usar features anonimizadas/agregadas.
- Revisar distribucion de labels antes de entrenar.
- Mantener fallback `baseline_rules`.
- Shadow no debe cambiar decisiones de negocio.
- Canary debe iniciar bajo y medirse con accuracy, drift, latencia, costo y quejas.
- Produccion requiere rollback documentado.

## 7. Evaluacion Roadmap Fases 16-25

Las fases son viables, pero deben ordenarse por madurez, riesgo y dependencia. El analisis completo de `agency-agents` cambia el orden: primero conviene construir intake, handoffs y evals para que las fases de workflow, gobierno y autonomia nazcan con reglas claras.

Orden recomendado actualizado despues de implementar Fase 18, Fase 22, Fase 16, Fase 24, Fase 19, Fase 20 y Fase 17:

1. Phase 21: Scentra AI Cloud Platform.
2. Phase 23: AI Marketplace Economy.
3. Phase 25: Enterprise Decision Intelligence.

## 8. Viabilidad Por Fase

Phase 16: AI Real-Time Intelligence Layer.

- Viabilidad: alta.
- Estado: implementada como control-plane PostgreSQL-first.
- Usa eventos, predicciones, recomendaciones, Operations y Trust AI sin mutar runtime.
- Transporte actual: polling inteligente y SSE acotado; Kafka/NATS queda como decision futura por volumen.

Phase 17: Federated Learning & Global Intelligence.

- Viabilidad: media.
- Estado: implementada a nivel codigo como control-plane opt-in, premium-gated y aggregate-only.
- Valor alto, complejidad legal/tecnica alta.
- Ya existe base con politicas tenant, paquetes estadisticos locales, rondas federadas, agregados ponderados y signals globales.
- Aun requiere acceptance multi-tenant real, privacidad/legal y runbook ModelOps antes de usar signals para seleccion de modelos productivos.

Phase 18: AI Workflow Composer.

- Viabilidad: alta.
- Muy buena siguiente fase.
- Debe generar workflows como drafts con simulador, preflight, versionado y rollback.

Phase 19: Autonomous Revenue Engine.

- Viabilidad: alta pero riesgosa.
- Estado: implementada como control-plane supervisado; no ejecuta envios, cobros, mutaciones CRM ni activaciones runtime.
- Acceptance productiva requiere datos reales de pedidos/pagos/valor comercial por tenant.

Phase 20: AI Enterprise Memory Network.

- Viabilidad: media-alta.
- Estado: implementada como grafo tenant-scoped de memoria revisable.
- Acceptance productiva requiere retencion, export/delete, lineage y uso de prompts/RAG solo con nodos publicados.

Phase 21: Scentra AI Cloud Platform.

- Viabilidad: media.
- Mejor despues de APIs estables, SDK, auth gateway, billing y soporte enterprise.

Phase 22: AI Trust, Compliance & Governance Enterprise.

- Viabilidad: muy alta.
- Debe adelantarse o correr en paralelo.
- Habilita ventas enterprise, autonomia segura, auditoria y procurement.

Phase 23: AI Marketplace Economy.

- Viabilidad: media-alta.
- Requiere sandbox, review, revenue share, legal terms, abuse monitoring y certificacion.

Phase 24: Voice & Multimodal Intelligence.

- Viabilidad: alta.
- Encaja con WhatsApp/Instagram por audios, imagenes y documentos.
- Empezar con transcripcion, resumen y clasificacion de adjuntos.

Phase 25: Enterprise Decision Intelligence.

- Viabilidad: alta pero tardia.
- Requiere datos historicos confiables, modelos validados y gobierno maduro.

## 9. Recomendacion Final

Fase 15.1A/15.1B/15.1C/15.2/15.3 ya cuentan con analisis, normalizacion, drafts, handoffs y evals offline. La repo externa queda aprovechada como fuente de templates, blueprints y rubricas, sin activar agentes ni ejecutar scripts externos.

Fase 11 ya puede entrenar modelos reales, pero el valor comercial depende de datos reales, labels revisados, shadow/canary, drift/costo y lenguaje de producto prudente.

Para el roadmap, la siguiente apuesta mas fuerte es:

1. Fase 24 para voz/multimodal sobre WhatsApp, Instagram y adjuntos.
2. Fase 19 para revenue automation approval-first y segura frente a politicas Meta.
3. Fase 20 para memoria enterprise con lineage, permisos y delete/export.
4. Fase 17 debe pasar acceptance multi-tenant/privacy/ModelOps antes de claims productivos.
5. Fase 21/23/25 solo cuando haya mas datos, sandbox, gobierno, capacidad y politicas comerciales maduras.
