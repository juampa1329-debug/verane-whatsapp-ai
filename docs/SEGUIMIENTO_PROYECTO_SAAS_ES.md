# Seguimiento del Proyecto SaaS Scentra +AI

Alcance: solo `saas-version/`.
Fecha de corte: 2026-05-28.
Fuente: inspeccion del codigo real del SaaS y validaciones locales disponibles.

## Resumen Ejecutivo

Scentra +AI SaaS es una plataforma multi-tenant para CRM conversacional, Inbox, campanas, triggers, remarketing, integraciones Meta, billing, observabilidad, Knowledge/RAG, agentes IA, inteligencia predictiva visible en producto, AI Ecosystem, Enterprise AI Network vertical, Federated Learning privacy-safe, Autonomous Revenue Engine supervisado, AI Enterprise Memory Network tenant-scoped, Product Ops con base de localizacion, una ruta documentada para ampliar agentes externos mediante Fase 15.1, un AI Workflow Composer premium-gated para disenar/simular/aprobar workflows AI, y un Trust AI Center para gobierno, riesgos, model cards, incidentes, auditoria y reportes de compliance AI.

Las fases 1 a 14 estan cerradas a nivel de codigo/repositorio. La Fase 11 ya tiene una base operativa de Scentra Intelligence Engine con eventos, feature store, predicciones baseline, recomendaciones con gating premium separado, grants premium, cuotas, API tenant, API Admin, vista tenant `Inteligencia`, vista Admin `AI Predictivo`, integracion de contexto predictivo en Advisor, worker automatico para eventos/features/predicciones, base ModelOps para feedback/metricas de modelos, registro/gobierno de rollout de modelos desde Admin, canary routing deterministico, captura inline limitada para eventos criticos de CRM/Billing, infraestructura ML real opcional, una capa visible de Predictive Intelligence en Dashboard/Inbox/CRM/floating Advisor, un Multi-Agent Operating System para coordinar agentes especializados, Autonomous Operational Intelligence supervisada, un AI Platform Ecosystem para marketplace/plugins/tools/SDK/developer apps e integraciones AI gobernadas, y Enterprise AI Network con benchmarks verticales anonimizados, playbooks, advisors sectoriales y knowledge network. La Fase 12 agrega un control-plane Admin de performance/reliability con SLOs, backpressure, auditoria de indices, retention dry-run, backup readiness y worker reliability sin modificar runtime Meta/WhatsApp/Instagram. La Fase 13 agrega MFA por email OTP para tenant/admin, Security Center Admin, export CSV de auditoria, compliance exports y solicitudes de borrado revisables. La Fase 14 agrega catalogos locales `es-CO`, normalizacion de copy critico y gates de Product Ops para release.

El bootstrap limpio Docker/PostgreSQL de Fase 11 fue validado con proyecto temporal `codexsaasmltrain`, volumen PostgreSQL nuevo, perfil opcional `ml` y migraciones `001` a `050`. Pasaron API health, Swagger, Admin, worker, ML service, MLflow, Qdrant, auto-labeling, feature pipelines, build de dataset, entrenamiento autolabel, prediccion, drift, entrenamiento desde Admin, registro en model registry y smoke de inferencia shadow. Despues de integrar Predictive Intelligence + Advisor, Agent OS, Autonomous Operations, AI Platform Ecosystem, Enterprise AI Network, Fase 12 Performance/Reliability, Fase 13 Security/Compliance, Fase 14 Localization/Product Ops y Fase 18 Workflow Composer, el stack SaaS fue reconstruido con Docker Compose, aplico/salto migraciones hasta `057`, inicio API/worker/admin/PostgreSQL, respondio API health y Swagger `/docs`, paso builds tenant/Admin, clean bootstrap temporal `001` a `057`, smoke API del Composer y smoke browser del panel Composer. En Fase 22 pasaron compileall backend, builds tenant/Admin, Docker rebuild API/worker/Admin, migracion activa hasta `058`, bootstrap PostgreSQL limpio aislado `001` a `058`, API health, Swagger, Admin health, OpenAPI Trust, smoke tenant Trust y smoke Admin Trust. En Fase 16 pasaron compileall backend, builds tenant/Admin, Docker rebuild API/worker/Admin, migracion activa hasta `059`, bootstrap PostgreSQL limpio aislado `001` a `059`, API health, Swagger, Admin health, OpenAPI realtime, smokes tenant/Admin realtime, log scans y browser smoke de `AI Inteligencia`. En Fase 24.2 pasaron py_compile backend, build tenant, Compose config, Docker rebuild API/worker, migracion activa hasta `060`, compileall backend en contenedor, API health, Swagger, OpenAPI voice endpoint y check PostgreSQL de tabla/feature flag. En Fase 24.3 pasaron py_compile backend, builds tenant/Admin, SQL scans, Compose config, Docker rebuild API/worker/Admin, migracion activa hasta `061`, API health, Swagger, Admin health, OpenAPI vision endpoint, DB check de tabla/flags, compileall en contenedor, log scan, browser smoke y bootstrap PostgreSQL limpio `001` a `061`. En Fase 24.4 pasaron py_compile backend, builds tenant/Admin, SQL scans, Compose config, Docker rebuild API/worker/Admin, migracion activa hasta `062`, API health, Swagger, Admin health, OpenAPI web/image search, DB check de tablas/flags, compileall en contenedor, smoke autenticado con fallo seguro sin credencial de busqueda, browser smoke Swagger y bootstrap PostgreSQL limpio `001` a `062`. En Fase 24.5 pasaron py_compile backend, build tenant, Compose config, SQL scans, Docker rebuild API/worker, migracion activa hasta `063`, API health, Swagger, OpenAPI endpoints de herramientas multimodales de agentes, DB check de migracion/flags, compileall en contenedor, smoke autenticado de herramienta con fallo seguro sin credencial de busqueda, browser smoke de Agent OS y bootstrap PostgreSQL limpio `001` a `063`. En Fase 24.6 pasaron py_compile/import backend, builds tenant/Admin, SQL scans, Compose config, Docker rebuild API/worker/Admin, migracion activa hasta `064`, API health, Swagger, OpenAPI endpoints de memoria multimodal, DB check de tabla/flags, smoke autenticado de sync/materializacion, browser smoke de Agent OS y bootstrap PostgreSQL limpio `001` a `064`. En Fase 24.7 pasaron py_compile backend, build tenant, Docker rebuild API/worker, API health, OpenAPI del endpoint de referencia aprobada y smoke browser del frontend sin errores de consola. En Fase 24.8 pasaron py_compile backend, build Admin, Compose config, SQL scans, Docker rebuild API/worker/Admin, migracion activa hasta `065`, API health, Swagger, Admin health, OpenAPI Phase 24.8, smoke autenticado Admin premium-gating/provider-policy, log scan, browser smoke Admin login y bootstrap PostgreSQL limpio `001` a `065`. En Fases 19 y 20 pasaron py_compile backend, builds tenant/Admin, Compose config, SQL scans, Docker rebuild API/worker/Admin, migracion activa `066`, API health, Swagger, OpenAPI Revenue/Memory Network, DB check de 10 tablas, smoke autenticado full-mode con tenant temporal para revenue opportunities/approve/execute y memory sync/publish, browser smoke Admin sin errores y bootstrap PostgreSQL limpio aislado `001` a `066`. En Fase 24.9/24.10 pasaron py_compile backend, builds tenant/Admin, Compose config, SQL scans, tracked diff whitespace y scan manual de whitespace en archivos tocados; la migracion/API/Swagger/bootstrap Docker hasta `067` queda pendiente porque Docker no estuvo accesible desde la ultima sesion.

## Tecnologia Detectada

- Backend: FastAPI en `saas-version/backend/app_saas`.
- API base: `/saas/v1`.
- Base de datos: PostgreSQL 16.
- Acceso DB: SQLAlchemy Core/raw SQL.
- Migraciones: SQL en `saas-version/migrations`, ejecutadas por `app_saas.tools.migrate`.
- Frontend cliente: React 19 + Vite en `saas-version/frontend`.
- Frontend admin: React 19 + Vite en `saas-version/admin-frontend`.
- Workers: Python en `app_saas.workers`, con worker embebido en API y servicio standalone.
- Deploy local/prod: `saas-version/docker-compose.saas.yml`.
- Integraciones principales: WhatsApp Cloud, Instagram Business, Facebook/Meta, WooCommerce, Stripe, MercadoPago, Wompi, proveedores IA.
- Infraestructura ML opcional: perfil Docker `ml` con MLflow, ML service FastAPI/BentoML image, XGBoost, LightGBM, scikit-learn y Qdrant. Apagada por defecto.

## Progreso Por Fases

| Fase | Area | Progreso | Estado |
| --- | --- | ---: | --- |
| 1 | Seguridad Base | 100% | Operativa a nivel codigo; smoke local previo aprobado |
| 2 | Scentra Admin | 100% | Operativa a nivel codigo; smoke local previo aprobado |
| 3 | Observabilidad y Diagnostico | 100% | Operativa a nivel codigo; smoke local previo aprobado |
| 4 | Inbox Robusto | 100% | Operativa a nivel codigo; build/browser smoke previo aprobado |
| 5 | CRM Comercial | 100% | Operativa a nivel codigo; migracion validada por stack limpio de Fase 6 |
| 6 | Knowledge Base y RAG | 100% | Operativa a nivel codigo; smoke local previo aprobado |
| 7 | Campanas, Triggers y Remarketing | 100% | Cerrada a nivel codigo; validacion local aprobada |
| 8 | AI Agents Enterprise | 100% | Cerrada a nivel codigo; validacion local aprobada |
| 9 | Billing y Monetizacion | 100% | Cerrada a nivel codigo; validacion local aprobada |
| 10 | Verticalizacion | 100% | Cerrada a nivel codigo; validacion local aprobada |
| 11 | ML, Predictive Intelligence, Agent OS, Autonomous Ops, AI Ecosystem & Enterprise AI Network | 100% | Operativa a nivel codigo con event contracts, auto-labeling, feature pipelines, datasets Postgres, MLflow/BentoML image, XGBoost/LightGBM autolabel training, artifacts, Admin controls, drift/inference logs, shadow inference, dashboards predictivos, badges Inbox/CRM, floating Advisor predictivo, Agent OS multiagente, AI Operations supervisado, AI Ecosystem control-plane y Enterprise AI Network con benchmarks verticales anonimizados, advisors, playbooks y knowledge network; acceptance productiva requiere datos reales revisados, ajuste de cohortes y diseno de sandbox antes de plugins ejecutables |
| 12 | Performance, Reliability & Scale | 100% | Operativa y validada localmente con migracion `055`, SLOs, backpressure, auditoria de indices, retention dry-run, backup readiness, worker reliability, endpoints Admin y panel Admin Performance; falta acceptance de carga real y tuning |
| 13 | Security, 2FA & Compliance | 100% | Operativa a nivel codigo con email OTP MFA tenant/admin, Security Center Admin, export CSV de auditoria, exports de privacidad y solicitudes de borrado; acceptance productiva requiere SMTP/Turnstile/secretos/CORS reales y aprobacion legal de retencion |
| 14 | Localization & Product Ops | 100% | Operativa a nivel codigo con catalogos locales tenant/Admin, normalizacion critica de textos, auditoria de copy, release gate, docs/ADR y sin nuevas dependencias |
| 15 | Agent Framework Research & Integration | 60% | Fase 15.1A/15.1B/15.1C/15.2/15.3 completadas como artefactos offline: 184 templates normalizados, 29 drafts evaluados, 7 handoffs, 7 playbooks, 4 runbooks y 6 rubricas generadas; sin importacion DB/runtime |
| 16 | AI Real-Time Intelligence Layer | 100% | Operativa a nivel codigo como control-plane realtime premium: eventos sanitizados, sesiones/cursors, alertas consultivas, vista tenant, overview Admin, metric snapshots y SSE acotado; acceptance productiva requiere pruebas de trafico antes de prometer SLAs realtime |
| 17 | Federated Learning & Global Intelligence | 100% | Operativa a nivel codigo como control-plane federado opt-in, premium-gated y aggregate-only: politicas tenant, paquetes estadisticos locales, rondas federadas, agregados ponderados, signals globales, worker auto-participation bajo opt-in/full gates y UI tenant; acceptance productiva requiere Docker/bootstrap por `068`, prueba multi-tenant, revision privacidad/legal y runbook ModelOps |
| 18 | AI Workflow Composer | 100% | Operativa a nivel codigo como control-plane premium: plantillas, editor de grafo, preflight, simulacion sin efectos, aprobaciones, versiones, rollback y activacion `composer_only`; despliegue runtime a triggers/flows/campanas requiere diseno futuro |
| 19 | Autonomous Revenue Engine | 100% | Operativa y endurecida como control-plane premium: politicas configurables, allowed action types, limite mensual de ejecuciones metadata, oportunidades, forecasts, reportes, playbooks, endpoints tenant, worker integration y UI `Inteligencia`; no envia mensajes, no muta CRM/campanas/workflows y no ejecuta cobros. |
| 20 | AI Enterprise Memory Network | 100% | Operativa y endurecida como grafo de memoria tenant-scoped: politicas, nodos, aristas, sync runs, review/export/import/delete, worker integration, controles UI y enforcement de scopes/retencion/revision de contenido cliente; no comparte contenido crudo entre tenants ni publica memoria candidata sin revision. |
| 22 | AI Trust, Compliance & Governance | 100% | Operativa a nivel codigo como control-plane premium: politicas, attestations, risk assessments, model cards, incidentes, reportes, auditoria, UI tenant Trust AI y vista Admin Trust AI; certificacion legal y enforcement automatico quedan fuera de alcance |
| 24 | Voice & Multimodal Intelligence | 100% | Fase 24.1 a 24.10 cerradas a nivel codigo: adjuntos en AI Gateway, Voice Intelligence, Vision Intelligence, busqueda web/imagen con aprobacion, herramientas multimodales para agentes, memoria/training events, UX Inbox, Admin/Premium Gating, observabilidad de costo/latencia/errores/calidad/fuentes y Safe Rollout con flags apagados por defecto, demo mode y canary. El envio automatico por IA/agentes sigue fuera de alcance. |

## Fases Cerradas 1 a 7

- Fase 1 Seguridad Base: CAPTCHA backend/frontend, rate limit, logs de seguridad, bloqueo temporal, recuperar cuenta, cambio de password y preparacion 2FA.
- Fase 2 Admin: admin frontend deployable, dominio admin configurado en Compose/Traefik, seed seguro de superadmin, gestion de tenants, planes, suscripciones, feature flags, auditoria y colas.
- Fase 3 Observabilidad: health global, worker heartbeat, Meta/AI Gateway, colas, dead-letter, retry, correlation ID, diagnostico por canal e historial de errores Meta.
- Fase 4 Inbox: polling robusto, filtros, asignacion humana, SLA, comentarios separados, adjuntos/audio/emojis/productos, notificaciones y estados.
- Fase 5 CRM: campos personalizados, pipelines configurables, timeline, dedupe/merge, segmentos y actualizacion CRM limitada por politicas IA.
- Fase 6 Knowledge/RAG: upload PDF/TXT/CSV, URL ingestion segura, indexacion visible, busqueda sparse-vector + lexical, citas internas, reindex y evaluaciones de calidad.
- Fase 7 Campanas/Triggers/Remarketing: simulador, preflight, bloqueo de activacion, versiones/rollback, quiet hours globales/locales, A/B, cooldown, `block_ai`, remarketing por flows y validacion Meta template antes de enviar.

## Fase 8 Cerrada: AI Agents Enterprise

Objetivo: que los agentes sean producto premium, medible, gobernable, asignable por conversacion y seguro ante doble respuesta IA.

Implementado:

- Catalogo de agentes de fabrica y Custom Agent.
- Plantillas de system prompt para agentes de fabrica.
- System prompt rellenable con variables JSON y prompt renderizado.
- Creacion de Custom Agent desde UI cliente.
- Preflight obligatorio antes de activar agentes.
- Persistencia de ultimo preflight y registros de eval en `saas_ai_agent_evals`.
- Presupuesto por agente con hard-stop real antes de ejecutar IA.
- Score de salud, metricas runtime, tokens, costo estimado y fallos.
- Tool approvals y acciones sugeridas preservadas.
- Memoria individual por agente y boveda de memorias.
- Importar/exportar/restaurar/borrar memorias.
- Al archivar/eliminar un agente, la memoria se conserva por defecto para poder borrarla despues.
- Memoria colectiva por tenant confirmada e inyectada en el prompt runtime.
- Asignacion manual de agente IA desde Inbox/CRM.
- Filtro de Inbox por agente IA asignado.
- Asignacion automatica por router/orquestador al mejor agente activo.
- Cuando una conversacion queda asignada a un agente, la IA general deja de responder esa conversacion.
- Si el agente asignado esta inactivo/no disponible, el runtime no hace fallback silencioso a IA general; requiere liberar o reasignar.

Archivos clave:

- `saas-version/migrations/043_saas_ai_agents_phase8_operational.sql`
- `saas-version/migrations/044_saas_billing_phase9_operational.sql`
- `saas-version/backend/app_saas/agents/service.py`
- `saas-version/backend/app_saas/agents/router.py`
- `saas-version/backend/app_saas/agents/orchestrator.py`
- `saas-version/backend/app_saas/agents/schemas.py`
- `saas-version/backend/app_saas/ai_agent/service.py`
- `saas-version/backend/app_saas/crm/router.py`
- `saas-version/backend/app_saas/crm/schemas.py`
- `saas-version/frontend/src/AiAgentsPanel.jsx`
- `saas-version/frontend/src/App.jsx`
- `saas-version/frontend/src/styles.css`

Validaciones de Fase 8:

- `python -m py_compile` sobre modulos backend tocados de agents, orchestrator, AI conversation y CRM.
- `npm --prefix saas-version/frontend run build`.
- `npm --prefix saas-version/admin-frontend run build`.
- `docker compose -f saas-version/docker-compose.saas.yml config`.
- Revision SQL BOM: sin BOM.
- Revision UTF-8 estricta SQL: OK.

Pendiente de entorno:

- Las migraciones quedaron cubiertas por el rebuild posterior hasta `054`; falta acceptance con conversaciones reales, presupuesto hard-stop y memoria/vault en staging.

## Fase 9: Billing y Monetizacion

Implementado:

- Checkout con proveedores Stripe, MercadoPago y Wompi.
- Webhooks de pago con verificacion de firma antes de mutar estado.
- Activacion de checkout, invoices/eventos Stripe, pagos MercadoPago y eventos aprobados/fallidos Wompi.
- Creditos manuales desde Admin.
- Facturas/historial y descarga PDF desde cliente y Admin.
- Estados `trial`, `active`, `past_due`, `cancelled`, `suspended`.
- Limites por plan, cuotas y bloqueo central de escrituras sensibles por impago/suspension.
- Job recurrente de lifecycle en worker embebido y standalone.
- Vencimiento de trial/suscripcion, gracia `past_due`, suspension, invoices abiertas/uncollectible y avisos por email.
- Variables Docker para intervalo lifecycle y dias de gracia.

Aceptacion de produccion:

- Probar webhooks reales/sandbox con Wompi, Stripe y MercadoPago usando secretos productivos.
- Confirmar requisitos legales/tributarios de factura PDF por pais antes de usarla como factura fiscal oficial.
- Las migraciones quedaron cubiertas por el rebuild posterior hasta `054`; falta acceptance sandbox/live de proveedores y factura legal.

## Fase 10: Verticalizacion

Implementado:

- Catalogo de agentes por industria.
- Filtros/politicas base por restaurante, hotel, salud, educacion, legal, seguros, inmobiliaria, belleza y mas.
- Agentes verticales de fabrica.
- Migracion `045_saas_verticalization_phase10.sql` para `industry_code`, snapshot del pack vertical y auditoria de aplicaciones.
- Dominio backend `app_saas/verticals` con catalogo, router, schemas, service y reglas locales.
- Packs para general, retail, ecommerce, restaurante, hotel, salud, educacion, inmobiliaria, soporte tecnico, automotriz, servicios financieros, legal, seguros, belleza y servicios.
- Registro y creacion de tenant con seleccion de industria.
- Cambio de industria desde Admin con aplicacion segura del pack.
- Aplicacion idempotente de pipeline CRM, campos personalizados, labels, plantillas CRM, segmentos, triggers inactivos, flows draft, quiet hours base y agentes recomendados opcionales.
- UI cliente en Ajustes > Industria con estado del pack, KPIs, agentes recomendados, historial y boton de aplicacion.
- UI Admin en detalle de tenant con selector de industria y fecha de pack aplicado.

Validaciones:

- Backend `compileall` aprobado para verticals, main, auth, tenants, admin y agents service.
- `npm run build` aprobado en frontend cliente.
- `npm run build` aprobado en admin frontend.
- `docker compose -f saas-version/docker-compose.saas.yml config --quiet` aprobado.
- SQL sin BOM y UTF-8 estricto OK.
- `git diff --check` limitado al scope SaaS/docs aprobado.

Aceptacion pendiente:

- Las migraciones quedaron cubiertas por el rebuild posterior hasta `054`.
- Probar cada pack vertical en staging con datos reales antes de aplicarlo a tenants productivos maduros.
- Activar triggers/flows solo despues de revision y preflight humano.

## Fase 11: ML & Predictive Intelligence / Scentra Intelligence Engine

Implementado:

- Migracion `046_saas_intelligence_engine_phase11.sql`.
- Migracion `047_saas_intelligence_modelops_phase11.sql`.
- Migracion `048_saas_intelligence_model_rollouts_phase11.sql`.
- Migracion `049_saas_ml_infrastructure_phase11.sql`.
- Migracion `050_saas_ml_training_strategy_phase11.sql`.
- Migracion `051_saas_multi_agent_operating_system_phase11.sql`.
- Migracion `052_saas_autonomous_operational_intelligence_phase11.sql`.
- Migracion `053_saas_ai_platform_ecosystem_phase11.sql`.
- Migracion `054_saas_enterprise_ai_network_phase11.sql`.
- Event store multi-tenant: `saas_intelligence_events`.
- Feature store base: `saas_intelligence_feature_values`.
- Predicciones: `saas_intelligence_predictions`.
- Recomendaciones: `saas_intelligence_recommendations`.
- Grants/licencias premium AI: `saas_intelligence_feature_grants`.
- Usage/quota: `saas_intelligence_usage`.
- Model registry base: `saas_intelligence_model_registry`.
- Feedback de predicciones: `saas_intelligence_prediction_feedback`.
- Metricas por tenant/modelo: `saas_intelligence_model_metrics`.
- Gobierno de rollout de modelos: columnas de rollout en `saas_intelligence_model_registry` y eventos en `saas_intelligence_model_rollout_events`.
- Jobs de entrenamiento ML: `saas_ml_training_jobs`.
- Artifacts de modelos ML: `saas_ml_model_artifacts`.
- Runs de inferencia ML: `saas_ml_inference_runs`.
- Snapshots de drift ML: `saas_ml_drift_snapshots`.
- Contratos de eventos: `saas_intelligence_event_contracts`.
- Cursores de replay: `saas_intelligence_event_replay_cursors`.
- Auto-labels: `saas_ml_auto_labels`.
- Feature sets: `saas_ml_feature_sets`.
- Runs de pipelines de features: `saas_ml_feature_pipeline_runs`.
- Datasets de entrenamiento: `saas_ml_training_datasets`.
- Evaluaciones offline de modelos: `saas_ml_model_evaluations`.
- Mensajes inter-agente: `saas_ai_agent_messages`.
- Traces runtime de agentes: `saas_ai_agent_runtime_traces`.
- Tool runs con aprobacion: `saas_ai_agent_tool_runs`.
- Subscripciones event-driven: `saas_ai_agent_event_subscriptions`.
- Politicas de operaciones AI: `saas_ai_operation_policies`.
- Playbooks de operaciones AI: `saas_ai_operation_playbooks`.
- Anomalias operacionales AI: `saas_ai_operation_anomalies`.
- Acciones autonomas supervisadas: `saas_ai_operation_actions`.
- Reportes operacionales AI: `saas_ai_operation_reports`.
- Marketplace AI: `saas_ai_marketplace_items`.
- Instalaciones de marketplace: `saas_ai_marketplace_installations`.
- Plugins AI tenant-scoped: `saas_ai_plugins`.
- Tool registry central: `saas_ai_tool_registry`.
- Suscripciones de eventos ecosystem: `saas_ai_ecosystem_event_subscriptions`.
- Developer apps: `saas_ai_developer_apps`.
- Integraciones AI externas metadata-only: `saas_ai_external_integrations`.
- AI apps tenant-scoped: `saas_ai_apps`.
- Traces y metricas ecosystem: `saas_ai_ecosystem_traces`, `saas_ai_ecosystem_metrics`.
- Modelos verticales por industria: `saas_ai_vertical_industry_models`.
- Benchmarks anonimizados por industria: `saas_ai_vertical_benchmarks`.
- Comparaciones tenant vs industria: `saas_ai_vertical_tenant_benchmarks`.
- Insights verticales tenant-scoped: `saas_ai_vertical_insights`.
- Playbooks AI verticales: `saas_ai_vertical_playbooks`.
- Knowledge network agregado: `saas_ai_knowledge_network`.
- Metric snapshots de red: `saas_ai_network_metrics`.
- Dominio backend `app_saas/intelligence`.
- Servicio ML opcional `app_saas/ml_service`.
- Endpoints tenant `/saas/v1/intelligence/*`.
- Endpoints tenant `/saas/v1/ecosystem/*`.
- Endpoints tenant `/saas/v1/intelligence/network/*`.
- Endpoint tenant `GET /saas/v1/intelligence/overview` para resumen ejecutivo, cards predictivas, agregados CRM, recomendaciones abiertas y observabilidad ModelOps.
- Endpoints Admin `/saas/v1/admin/intelligence/*`.
- Endpoints internos ML `/health`, `/models`, `/train/synthetic`, `/predict`, `/drift/evaluate`, `/metrics`.
- Endpoints internos ML `/datasets/build` y `/train/autolabel`.
- Vista Admin `AI Predictivo`.
- Feature flags premium/demo en billing y Admin.
- Predicciones baseline para lead scoring, churn, smart remarketing y anomalia operativa.
- Worker `app_saas/workers/intelligence.py` para derivar eventos canonicos desde tablas existentes.
- Recomputo automatico de features por tenant desde worker embebido/standalone/Admin.
- Generacion automatica de predicciones baseline con gating, cuotas y cooldown.
- Registro de feedback de predicciones desde API tenant.
- Recalculo de metricas de modelos desde API/Admin y worker.
- Admin `AI Predictivo` muestra ModelOps predictivo: muestras, feedback, accuracy y drift baseline.
- Admin `AI Predictivo` permite registrar modelos y muestra `Model Registry & Rollout`: estado, shadow/canary/production, porcentaje de trafico, feedback agregado, accuracy, drift y readiness.
- El runtime de predicciones bloquea modelos deshabilitados/pausados y selecciona modelos canary activos de forma deterministica por tenant/prediccion/sujeto/ventana y porcentaje de trafico.
- El output de prediccion usa `baseline_rules` por defecto; si `SAAS_ML_ENABLED=true` y hay artifact listo, puede llamar el ML service.
- La inferencia shadow corre en paralelo cuando `SAAS_ML_SHADOW_INFERENCE_ENABLED=true`, sin cambiar el resultado baseline de negocio.
- El output registra `ml_inference` con estado, modelo, version, score, label, latencia y error si aplica.
- Shadow/canary no aprobado se persiste como `shadow` y no genera recomendaciones automaticas.
- La persistencia de recomendaciones esta separada del permiso de prediccion: una prediccion demo puede generarse con `intelligence_demo`, pero escribir `saas_intelligence_recommendations` requiere `predictive_recommendations` habilitado y con cuota.
- El output de la prediccion incluye `recommendation_gate` para auditar si la recomendacion fue solicitada, habilitada, creada o bloqueada.
- UI tenant `Inteligencia` en `saas-version/frontend/src/IntelligencePanel.jsx`.
- UI tenant `AI Ecosystem` en `saas-version/frontend/src/AiEcosystemPanel.jsx`.
- UI tenant `Inteligencia` ahora incluye Industry Intelligence Center, Benchmark Dashboard, Industry Insights Panel, AI Playbook Marketplace, Industry AI Models y AI Knowledge Network.
- La vista tenant `Inteligencia` muestra summaries diario/semanal/operacional y tarjetas para lead scoring, churn, smart remarketing y anomalias operativas.
- El tenant puede ver grants/uso, feature snapshots, predicciones, recomendaciones, feedback y metricas de modelos.
- El tenant puede recalcular features, generar predicciones baseline con gating, registrar feedback y descartar recomendaciones usando APIs existentes `/saas/v1/intelligence/*`.
- Dashboard tenant muestra una franja predictiva con ultimas predicciones y recomendaciones abiertas.
- Inbox muestra badges predictivos y filtro `Churn` para conversaciones con riesgo alto.
- CRM/conversaciones exponen `predictive_intelligence` con lead score, conversion probability, engagement score, temperature, churn risk, retention priority, best channel/window/frequency y accion recomendada.
- CRM permite ejecutar predicciones conversation-level de lead scoring, churn y smart remarketing desde el panel lateral.
- Admin Operations expone `/admin/operations/intelligence/process`.
- `AI Predictivo`, `Operacion` y `Salud` pueden ejecutar Intelligence manualmente.
- `intelligence/capture.py` registra eventos inline seleccionados con transaccion anidada para no romper la escritura de negocio.
- El envio outbound desde CRM registra `message.sent` con replay key `message:{id}`.
- Billing registra `billing.subscription.changed` al activar checkout pago y al cambiar estado de suscripcion.
- Advisor recibe predicciones/recomendaciones recientes como contexto.
- Endpoint `GET /saas/v1/advisor/briefing` alimenta el floating Advisor con overview predictivo, insights proactivos, recomendaciones, acciones, actividad, metricas y memoria.
- El floating Advisor muestra briefing predictivo persistente sin auto-ejecutar acciones.
- Endpoint `GET /saas/v1/agents/os` expone cobertura core de agentes, capas de memoria, subscripciones, mensajes, tool runs, traces, routing de modelos, estado premium/demo y orquestador.
- Endpoints `GET|POST /saas/v1/agents/os/messages`, `POST /saas/v1/agents/os/event-sync` y `GET|POST /saas/v1/agents/{agent_id}/tool-runs` agregan comunicacion inter-agente, sync de senales predictivas y trazas de herramientas.
- Agent OS puede convertir predicciones/recomendaciones recientes en jobs del orquestador solo cuando el tenant tiene modo premium full; en demo devuelve candidatos sin encolar.
- Tool runs de Agent OS crean action drafts aprobables por humano y no ejecutan efectos de negocio directamente.
- UI tenant `AI Agents` agrega pestana `Agent OS` con cobertura, memoria, event-driven subscriptions, mensajes, tool runs y observabilidad.
- Endpoint `GET /saas/v1/intelligence/operations/center` expone AI Operations Center con policy, niveles de autonomia, snapshot, anomalias, acciones, reportes y playbooks.
- Endpoints `PATCH /saas/v1/intelligence/operations/control`, `POST /saas/v1/intelligence/operations/analyze`, `GET /saas/v1/intelligence/operations/actions`, y approve/execute/dismiss agregan AI Control Center y flujo supervisado de acciones autonomas.
- `intelligence/operations.py` detecta anomalias de webhooks, outbound, dead-letter, Meta subscription drift, campanas, triggers, inactividad, oportunidades comerciales y worker degradation.
- Autonomous Operations soporta niveles 0 a 4. En demo permite preview/analisis, pero fuerza `auto_remediation_enabled=false` y `low_risk_auto_execute=false`.
- La ejecucion actual de acciones autonomas registra resultado controlado/auditable y no muta directamente Meta, colas, campanas, CRM o billing.
- Worker de Intelligence ejecuta analisis autonomo en transaccion anidada y reporta totales `autonomous_anomalies` y `autonomous_actions`.
- UI tenant `Inteligencia` agrega AI Operations Center, AI Control Center, acciones autonomas y reportes operacionales.
- Feature flags premium nuevas: `autonomous_operations`, `ai_self_healing`, `ai_control_center`.
- AI Platform Ecosystem expone Marketplace, Agent Store, Plugin Center, Tool Registry, Event Subscriptions, Developer Console, Integrations Center y AI Apps.
- Las features ecosystem (`ai_marketplace`, `ai_plugin_center`, `ai_developer_console`, `ai_tool_registry`, `ai_app_framework`) quedan apagadas por defecto y disponibles por full premium/`ai_premium`.
- Las features Enterprise AI Network (`enterprise_ai_network`, `vertical_ai_intelligence`, `industry_ai_models`, `benchmark_intelligence`, `cross_tenant_intelligence`, `vertical_ai_advisors`, `ai_playbook_library`) quedan apagadas por defecto y disponibles por full premium/`ai_premium`.
- Enterprise AI Network comparte solo metricas agregadas y anonimizadas; no comparte mensajes crudos, conversaciones completas, nombres de tenants ni contenido sensible.
- Los benchmarks requieren muestra minima de 3 tenants por industria/metrica antes de publicarse como agregado.
- Los playbooks verticales son recomendaciones/drafts; no activan triggers, flows ni campanas automaticamente.
- En demo se puede previsualizar estado/catalogos; instalar/crear/actualizar requiere full mode.
- Plugins, tools, integraciones externas y AI apps son metadata/control-plane; no se ejecuta codigo no confiable dentro del API/worker.
- Developer apps guardan API keys hasheadas y muestran la key cruda solo una vez.
- Kimi verificado como proveedor oficial existente en AI Gateway; no se duplico proveedor.
- `requirements-ml.txt` instala MLflow, BentoML, XGBoost, LightGBM, scikit-learn, pandas/numpy, joblib y Prometheus client solo para la imagen ML.
- `Dockerfile.ml` aisla el runtime ML para no cargar dependencias pesadas en API/worker por defecto.
- Compose agrega perfil opcional `ml` con `mlflow`, `ml-service` y `qdrant`; todas las flags ML quedan apagadas por defecto en API/worker.
- Entrenamiento inicial soporta datasets sinteticos/autolabel para lead scoring, churn prediction, smart remarketing y operational anomaly detection.
- Auto-labeling operativo a partir de datos reales del SaaS: conversiones CRM/pago, inactividad, engagement negativo, resultados de campanas/broadcasts y fallos operativos.
- Feature pipelines operativos para `lead_scoring`, `churn_prediction`, `smart_remarketing` y `operational_anomaly`, con `feature_set_key`, version y metadata de calidad.
- Build de datasets desde Postgres: une `saas_ml_auto_labels` con `saas_intelligence_feature_values`, genera CSV/manifiesto y registra `saas_ml_training_datasets`.
- Entrenamiento autolabel operativo: LightGBM, XGBoost o sklearn fallback desde datasets Postgres, logging MLflow/BentoML cuando esta disponible, evaluacion offline y registro opcional como candidato shadow.
- Worker de Intelligence puede preparar labels/features solo si `SAAS_ML_AUTO_TRAIN_ENABLED=true`; por defecto sigue apagado para no alterar runtime Meta/WhatsApp/Instagram.
- Admin `AI Predictivo` muestra readiness de datasets, estado de infraestructura ML, jobs/artifacts/inference/drift y boton de entrenamiento sintetico cuando ML esta habilitado.

Validaciones:

- Backend `compileall` aprobado para modulos tocados.
- `npm --prefix saas-version/frontend run build` aprobado para la UI tenant `Inteligencia`.
- `npm --prefix saas-version/admin-frontend run build` aprobado.
- Ultima validacion frontend de la capa producto predictiva: `npm.cmd run build` en `saas-version/frontend` aprobado con advertencia Vite existente de chunk grande.
- Ultima validacion backend de la capa producto predictiva: `docker compose -f saas-version/docker-compose.saas.yml exec -T api python -m compileall -q app_saas` aprobado dentro del contenedor API reconstruido.
- `docker compose -f saas-version/docker-compose.saas.yml config --quiet` aprobado.
- SQL sin BOM y UTF-8 estricto OK.
- `git diff --check` limitado al scope SaaS/docs aprobado.
- Docker/PostgreSQL limpio aplico migraciones hasta `054`; API health, Swagger, OpenAPI, Admin health, API worker y worker standalone iniciaron correctamente.
- Ultimo rebuild SaaS actual: `docker compose -f saas-version/docker-compose.saas.yml up -d --build` aplico migraciones `001` a `054`; API `/saas/v1/health` y Swagger `/docs` respondieron 200; API/admin/worker/PostgreSQL quedaron healthy/running.
- Validacion Agent OS: `docker compose ... exec -T api python -m compileall -q app_saas` aprobado, tablas `saas_ai_agent_messages`, `saas_ai_agent_runtime_traces`, `saas_ai_agent_tool_runs` y `saas_ai_agent_event_subscriptions` existen, frontend build aprobado.
- Validacion Autonomous Operations: ultimo rebuild SaaS aplico migracion `052`; existen tablas `saas_ai_operation_policies`, `saas_ai_operation_playbooks`, `saas_ai_operation_anomalies`, `saas_ai_operation_actions` y `saas_ai_operation_reports`; OpenAPI contiene `/intelligence/operations/*`; API health y Swagger OK; smoke tenant demo/control aprobado.
- Validacion AI Platform Ecosystem: ultimo rebuild SaaS aplico migracion `053`; existen tablas ecosystem; OpenAPI contiene `/ecosystem/*`; API compileall, frontend build, API health y Swagger OK; smoke tenant demo bloqueo mutaciones sin full; smoke premium marketplace install/plugin/tool/developer-app aprobado; browser smoke local cargo `AI Ecosystem` sin errores de consola.
- Validacion Enterprise AI Network: ultimo rebuild SaaS aplico migracion `054`; existen tablas vertical network; OpenAPI contiene `/intelligence/network/center`, `/refresh` y `/playbooks`; API compileall, frontend/admin build, API health y Swagger OK; smoke tenant demo cargo center/preview; refresh full bloqueo sin permiso; refresh full con grant premium persistio 8 insights y 7 benchmarks tenant; browser smoke local cargo cliente y admin sin errores de consola.
- Smoke Admin autenticado aprobado para listar modelos, evaluar readiness, hacer PATCH de modelo, registrar evento de rollout y registrar auditoria admin.
- Smoke tenant aprobado para registro, cliente CRM, envio outbound y evento inline `message.sent`.
- Smoke billing aprobado para cambio de estado de suscripcion y evento inline `billing.subscription.changed`.
- Smoke predictivo extendido aprobado en Docker/PostgreSQL limpio: registro de tenant, clientes CRM semilla, recomputo de features, grant deshabilitado de `predictive_recommendations`, prediccion demo `lead_scoring` sin recomendacion persistida, prediccion full `smart_remarketing` con recomendacion persistida, feedback, metricas de modelo y descarte de recomendacion.
- Smoke canary aprobado en Docker/PostgreSQL limpio: login admin, registro de tenant, grant premium, registro de modelo, recomputo de features, canary `100%`, fallback `0%` y metadata `baseline_rules`.
- Smoke ML opcional aprobado en Docker/PostgreSQL limpio con migraciones `001` a `049`: MLflow healthy, ML service healthy, Qdrant ready, entrenamiento sintetico LightGBM, prediccion, drift, training XGBoost desde Admin, registro shadow en model registry y MLops overview.
- Smoke ML training strategy aprobado en Docker/PostgreSQL limpio con migraciones `001` a `050`: generacion de auto-labels, recomputo de feature pipelines, build de dataset, entrenamiento autolabel, registro de evaluacion, prediccion directa y drift.
- Smoke de inferencia shadow aprobado: prediccion baseline de churn queda como salida autorizada y el modelo entrenado retorna `ml_inference.ok = true` bajo `baseline_rules+ml_shadow`.
- Escaneo estricto de logs recientes de API, ML service y worker sin `Traceback`, `UserWarning`, excepciones no manejadas ni `ERROR:`.
- Browser smoke aprobado para Scentra Admin servido desde Docker sin errores de consola.
- Browser smoke visual del cliente tenant para la capa producto predictiva quedo pendiente: la politica del Browser bloqueo `file://` y el dev server Vite local no quedo alcanzable en esta sesion de Windows. La validacion frontend de esta parte queda a nivel build.
- PDF de seguimiento en espanol regenerado: `docs/Scentra_SaaS_Project_Status.pdf`.

Pendiente para acceptance productiva total de Fase 11:

- Ampliar emision inline mas alla de CRM outbound y cambios de suscripcion cuando un dominio necesite fanout casi realtime.
- Revisar calidad/distribucion de auto-labels por tenant con datos reales antes de promover modelos productivos.
- Promover modelos desde shadow/canary/full con revision humana, no con artifacts sinteticos o auto-labels sin validar.
- Profundizar drift, precision, recall, latencia, costo por prediccion, alertas y rollback operativo.
- Decidir si Qdrant se conectara al RAG productivo; por ahora esta preparado en el perfil ML pero el Knowledge/RAG actual sigue usando Postgres sparse-vector + lexical.
- Kafka/NATS no fueron agregados al stack default; event streaming externo debe entrar solo cuando el volumen lo justifique.
- Mantener Autonomous Operations en modo supervisado hasta que cada playbook de self-healing tenga evidencia en staging, rollback ensayado y aprobacion explicita para efectos reales.
- Disenar sandbox/plugin runtime y gateway externo antes de habilitar plugins ejecutables o autenticacion publica con developer keys.
- Ajustar cohortes, definicion de KPIs y mensajes comerciales de benchmark con datos reales antes de vender comparativas sectoriales como referencia definitiva.
- Ajustar thresholds de anomalias y politicas de autonomia con trafico real antes de habilitar Level 3/4 ampliamente.
- Ampliar acceptance con trafico real de tenants/proveedores y volumenes mayores.
- Validar en staging los textos/claims visibles de inteligencia predictiva antes de venta enterprise para no presentar modelos bootstrap/autolabel como precision productiva certificada.

## Fase 12 y 13 Cerradas, Fases Recomendadas 14 a 15

Fase 12 Performance, Reliability & Scale:

- Implementada con migracion `055`, SLO policies, backpressure policies, retention policies, cleanup runs, snapshots, drills e indices esperados para tablas de alto volumen.
- Backend `app_saas/reliability/service.py` calcula SLOs, backpressure, auditoria de indices PostgreSQL, retention dry-run, backup readiness y drills.
- Worker reliability corre desde API embedded y worker standalone; registra snapshots y dry-runs sin mutar colas/proveedores.
- Admin expone `Performance` con SLOs, colas, indices, retention, cleanup runs, drills, snapshots y acciones seguras.
- No ejecuta auto-throttling, no pausa campanas, no repara Meta automaticamente y no borra datos por defecto.
- Validacion local: build frontend/admin, py_compile backend, Compose config, BOM scan, Docker rebuild, migracion `055`, API health, Swagger, OpenAPI, API compileall, smoke autenticado Admin reliability, retention dry-run de 6 politicas, log scan y PDF regenerado.
- Pendiente de acceptance productiva: pruebas de carga reales, tuning de thresholds, pruebas reales de backup/restore y politica legal/operativa de retencion.

Fase 13 Security, 2FA & Compliance:

- Implementada con migracion `056_saas_phase13_security_compliance.sql`, tabla `saas_mfa_challenges` y tabla `saas_privacy_requests`.
- Tenant login y Admin login soportan challenge MFA por email OTP cuando el usuario lo activa o cuando el rol esta configurado como obligatorio.
- Los JWT emitidos despues de OTP llevan verificacion MFA y refresh bloquea sesiones que requieren MFA sin haberlo completado.
- Ajustes de seguridad tenant/admin permiten activar/desactivar 2FA email; en produccion requiere SMTP configurado.
- Emails de seguridad para reset/cambio de password y cambios 2FA quedan detras de `SAAS_SECURITY_NOTIFY_ENABLED`.
- Tenant app puede exportar datos de cuenta, exportar datos de una conversacion/cliente seleccionado y registrar solicitud de borrado sin hard-delete automatico.
- Admin app agrega `Security` con metricas de 2FA, admins sin 2FA, webhooks firmados, eventos de seguridad, solicitudes de privacidad, estado SMTP y export CSV de auditoria.
- Validacion local: compileall backend, build frontend/admin, Docker rebuild API/worker/admin, migraciones hasta `056`, health, Swagger, smoke tenant MFA, smoke admin MFA, smoke compliance export, smoke Admin Security Compliance y logs API/worker sin errores actuales.
- TOTP/app authenticator no se implemento; el metodo aprobado en esta fase es email OTP para minimizar riesgo y reutilizar SMTP existente.

Fase 14 Localization & Product Ops:

- Implementada con catalogos locales sin dependencias: `frontend/src/i18n.js` y `admin-frontend/src/i18n.js`.
- Locale base `es-CO`; overrides opcionales `VITE_APP_LOCALE` y `VITE_ADMIN_LOCALE`.
- Normalizados textos criticos de navegacion tenant/Admin, titulos de paginas, tabs de ajustes, conexion Meta/Facebook, plantillas Broadcast, Agentes IA, Ecosistema IA, benchmarks de Inteligencia y Admin Rendimiento.
- Scripts Product Ops:
  - `node saas-version/scripts/phase14-copy-audit.mjs`
  - `node saas-version/scripts/phase14-release-check.mjs`
- Package scripts tenant/Admin: `phase14:copy-audit` y `phase14:release-check`.
- Documentacion/arquitectura/ADR agregadas: `docs/LOCALIZATION_PRODUCT_OPS.md`, `architecture/LOCALIZATION_PRODUCT_OPS.md`, `decisions/ADR-038-phase14-localization-product-ops.md`.
- No cambia APIs, DB, auth, billing, workers, Meta ni runtime ML/IA.
- Pendiente evolutivo: mover copy largo de panels especificos a catalogos conforme se modifiquen esos modulos y agregar E2E real cuando se apruebe un framework de testing.

Fase 15 Agent Framework Research & Integration:

- Fase 15.1A analizo la repo local completa en `external-repos/agency-agents/`, usando el README externo inicial solo como contexto.
- La repo es una libreria MIT de agentes Markdown/personas/prompts, no un runtime SaaS listo para ejecutar.
- Se detectaron 184 agentes validos con frontmatter, 16 documentos estrategicos/playbooks sin frontmatter de agente, 14 categorias de agentes, docs NEXUS, ejemplos, integraciones y scripts de instalacion/conversion/lint.
- La carpeta local no fue detectada como subrepo Git independiente; falta confirmar source URL, commit/tag upstream y si hay cambios privados.
- Lo aprovechable para Scentra es taxonomia, estructura de persona, misiones, reglas criticas, workflows, handoffs NEXUS, entregables, metricas de exito, playbooks y rubricas de evaluacion.
- No se aprueba ejecutar scripts externos, instalar agentes globales ni correr plugin code dentro de API/worker.
- Fase 15.1B/15.1C se implementaron sin afectar runtime: `saas-version/scripts/phase15-agent-template-intake.mjs` genero inventario, CSV, drafts deshabilitados y reporte en `docs/phase15_1/`.
- Fase 15.2/15.3 se implementaron sin afectar runtime: `saas-version/scripts/phase15-nexus-eval-harness.mjs` genero 7 contratos de handoff, 7 playbooks, 4 runbooks, 6 rubricas y evals para 29 drafts.
- Documentacion creada/actualizada: `docs/PHASE15_1_AGENCY_AGENTS_RESEARCH.md`, `architecture/AGENT_TEMPLATE_INTAKE.md`, `decisions/ADR-039-phase15-1-agency-agents-research.md`, `decisions/ADR-040-phase15-1b-1c-offline-agent-template-intake.md`, `decisions/ADR-041-phase15-2-15-3-nexus-eval-harness.md`.
- Para avanzar hace falta confirmar upstream Git URL/commit/tag, decidir atribucion, ejecutar secret scan formal, escoger categorias definitivas y aprobar importacion real a Admin/DB.
- Se mantienen las reglas actuales: una conversacion solo puede tener un dueno IA activo a la vez, memoria individual/colectiva sigue tenant-scoped, y herramientas quedan approval-first.

Fase 16 AI Real-Time Intelligence Layer:

- Implementada como control-plane premium realtime sobre la inteligencia existente.
- Migracion nueva: `saas-version/migrations/059_saas_realtime_intelligence_phase16.sql`.
- Backend nuevo: `saas-version/backend/app_saas/intelligence/realtime.py`.
- Tablas nuevas: `saas_realtime_intelligence_sessions`, `saas_realtime_intelligence_cursors` y `saas_realtime_intelligence_metrics`.
- Endpoints tenant: `/saas/v1/intelligence/realtime/center`, `/events`, `/sessions`, `/cursor`, `/sessions/{id}/close` y `/stream`.
- Endpoints Admin: `/saas/v1/admin/intelligence/realtime` y `/saas/v1/admin/intelligence/realtime/metrics/refresh`.
- Feature flags: `realtime_intelligence_layer`, `realtime_event_stream`, `realtime_ai_alerts`, `realtime_intelligence_dashboard`.
- UI tenant en `IntelligencePanel.jsx`: estado live, sesiones, cursor, metricas, alertas, feed de eventos sanitizados y mezcla de eventos.
- UI Admin en `AdminApp.jsx`: overview por tenant, sesiones activas, eventos recientes, predicciones, recomendaciones y modos por feature.
- Transporte actual: polling seguro cada 8 segundos en UI tenant y SSE acotado para clientes futuros.
- Seguridad: no agrega Kafka/NATS/Redis Streams/WebSockets, no instala dependencias, no envia mensajes, no cambia CRM/campanas/billing/Meta/workflows/agentes/modelos y no ejecuta remediacion.
- Validacion: compileall backend, build tenant, build Admin, Compose config, SQL BOM/UTF-8, Docker rebuild API/worker/Admin, migraciones hasta `059`, bootstrap PostgreSQL limpio `001` a `059`, health API, Swagger, health Admin, OpenAPI realtime, smoke tenant con evento sanitizado/sesion/cursor/cierre, smoke Admin con refresh de metricas, log scan API/worker y browser smoke de tenant/Admin/Swagger.
- Pendiente productivo: pruebas de trafico/capacidad antes de prometer latencia realtime contractual y definir politica comercial por plan/tenant.

Fase 24 Voice & Multimodal Intelligence:

- Fase 24.1 implementada como fundacion de compatibilidad para voz, imagen, video y documentos.
- Backend: `GatewayAttachment`, `GatewayRequest.attachments` y `generate_with_gateway(..., attachments=...)`.
- Gemini adapter puede enviar partes `inline_data` o `file_data`; OpenAI-compatible puede enviar imagenes como `image_url` cuando el modelo lo soporte.
- Los logs de `saas_ai_runs` solo registran metadata segura de adjuntos: conteo, tipos, MIME y origen; no guardan base64 ni bytes.
- Catalogo ampliado con `gemini-2.5-flash-lite` y `moonshot-v1-8k-vision-preview`; Kimi queda marcado como multimodal-capable para modelos compatibles.
- UI tenant Ajustes > APIs ahora muestra tiles "Anadir" y expande solo proveedores configurados o seleccionados, reduciendo la pagina larga.
- Fase 24.2 Voice Intelligence implementada para audios existentes del Inbox.
- Migracion nueva: `saas-version/migrations/060_saas_voice_intelligence_phase24.sql`.
- Tabla nueva: `saas_voice_intelligence_analyses`.
- Feature flags: `voice_intelligence`, `voice_transcription`, `voice_sentiment_intent`.
- Endpoint tenant: `POST /saas/v1/media/messages/{message_id}/voice/analyze`.
- Capacidades: transcripcion, resumen, sentimiento, score, intencion, urgencia, idioma, confianza, accion recomendada, action items y hints CRM.
- Fuentes de audio: `saas_media_assets` local y audio inbound de WhatsApp por los helpers existentes de Meta Graph.
- Provider actual para audio real: Google/Gemini via AI Gateway attachments.
- UI tenant Ajustes > IA permite seleccionar provider de analisis de audio y muestra modelo/credencial vinculada.
- UI Inbox muestra tarjetas Voice Intelligence en mensajes de audio con Analizar/Reanalizar, resumen, sentimiento, intencion y transcript expandible.
- Fase 24.3 Vision Intelligence implementada para imagenes, documentos y archivos existentes del Inbox.
- Migracion nueva: `saas-version/migrations/061_saas_vision_intelligence_phase24.sql`.
- Tabla nueva: `saas_vision_intelligence_analyses`.
- Feature flags: `vision_intelligence`, `image_understanding`, `document_ocr`.
- Endpoint tenant: `POST /saas/v1/media/messages/{message_id}/vision/analyze`.
- Capacidades: descripcion visual, texto extraido/OCR-style, resumen, tipo de documento, sentimiento, intencion, urgencia, idioma, confianza, entidades, temas, pistas de producto y accion recomendada.
- Fuentes de media: `saas_media_assets` local y media inbound de WhatsApp por los helpers existentes de Meta Graph.
- Provider actual para documentos/OCR: Google/Gemini via AI Gateway attachments; imagenes pueden solicitar Google, OpenRouter o Kimi cuando el modelo/credencial lo soporte.
- UI tenant Ajustes > IA permite seleccionar provider de Vision Intelligence y muestra modelo/credencial vinculada.
- UI Inbox muestra tarjetas Vision Intelligence en mensajes de imagen/documento/archivo con Analizar/Reanalizar, resumen, tipo documental, intencion, descripcion visual y texto extraido expandible.
- Fase 24.4 Web/Image Search Intelligence implementada para busqueda externa con fuentes y aprobacion humana.
- Migracion nueva: `saas-version/migrations/062_saas_web_image_search_intelligence_phase24.sql`.
- Tablas nuevas: `saas_web_search_intelligence_runs` y `saas_web_search_intelligence_results`.
- Feature flags: `web_search_intelligence`, `image_search_intelligence`, `external_source_assist`.
- Endpoints tenant: `POST /saas/v1/media/search`, `GET /saas/v1/media/search/runs` y `POST /saas/v1/media/search/results/{result_id}/approval`.
- Providers soportados: Tavily, Brave Search API y SerpAPI mediante credenciales tenant cifradas.
- Resultados guardan fuente, snippet, URL, imagen/thumbnail opcional, score/rank, estado de seguridad, estado de aprobacion y metadata.
- Resultados inseguros/internos/privados quedan bloqueados y no se pueden aprobar.
- UI tenant Ajustes > APIs agrega tiles compactos para providers de busqueda.
- UI tenant Ajustes > IA permite seleccionar provider de busqueda web/imagen y ver estado de credencial.
- UI Inbox CRM side panel muestra tarjetas de fuentes con preview visual cuando existe y acciones aprobar/rechazar.
- Fase 24.5 Agent Multimodal Tools implementada para agentes.
- Migracion nueva: `saas-version/migrations/063_saas_agent_multimodal_tools_phase24.sql`.
- Feature flags: `agent_multimodal_tools`, `agent_voice_tools`, `agent_vision_tools`, `agent_external_search_tools`.
- Backend nuevo: `saas-version/backend/app_saas/agents/multimodal_tools.py`.
- Endpoints tenant: `GET /saas/v1/agents/multimodal-tools/catalog`, `GET /saas/v1/agents/{agent_id}/multimodal-tools/runs` y `POST /saas/v1/agents/{agent_id}/multimodal-tools/execute`.
- Herramientas: `media.voice_analyze`, `media.vision_analyze` y `media.web_image_search`.
- Los agentes deben tener la herramienta declarada en `tools_json` y pasar gating premium/demo antes de ejecutar.
- Los tool runs se registran en `saas_ai_agent_tool_runs`; busqueda externa sigue usando aprobacion humana por resultado.
- El runtime de conversacion del agente puede leer contexto multimodal compacto; fuentes externas solo entran al prompt si estan aprobadas y no bloqueadas.
- UI tenant AI Agents > Agent OS muestra herramientas multimodales, formulario de ejecucion, runs recientes y aprobacion/rechazo de fuentes.
- Fase 24.6 Multimodal Memory & Training Events implementada para guardar resultados utiles en ML/RAG/memoria.
- Migracion nueva: `saas-version/migrations/064_saas_multimodal_memory_training_events_phase24.sql`.
- Tabla nueva: `saas_multimodal_memory_events`.
- Feature flags: `multimodal_memory_events`, `multimodal_training_events`, `multimodal_rag_materialization`, `multimodal_agent_memory`.
- Backend nuevo: `saas-version/backend/app_saas/agents/multimodal_memory.py`.
- Endpoints tenant: `GET /saas/v1/agents/multimodal-memory/events`, `POST /saas/v1/agents/multimodal-memory/sync` y `POST /saas/v1/agents/multimodal-memory/events/{event_id}/materialize`.
- Captura senales sanitizadas desde analisis de voz, analisis de vision, fuentes web/imagen aprobadas y tool runs multimodales completados.
- Actualiza features conversacionales en `saas_intelligence_feature_values`: conteo multimodal, fuentes externas aprobadas, confianza, sentimiento, urgencia y volumen de texto.
- La marca `eligible_for_training` requiere `multimodal_training_events`, `ml_predictions` o `ai_premium`; memoria sin ese gate no autoriza entrenamiento.
- Los operadores pueden materializar eventos a Knowledge/RAG, memoria colectiva de agentes o ambos; contenido de clientes requiere aprobacion explicita.
- UI tenant AI Agents > Agent OS muestra `Memoria y training multimodal`, conteos, eventos, sincronizacion y botones de materializacion.
- Seguridad: no guarda bytes/base64, no muta CRM, no crea tareas/tickets, no lanza campanas, no ejecuta workflows, no asigna agentes, no crawlea resultados, no entrena modelos automaticamente y no envia mensajes.
- Validacion: py_compile/import backend, builds tenant/Admin, Compose config, SQL scans, Docker rebuild API/worker/Admin, migracion activa hasta `064`, compileall backend en contenedor, API health, Swagger, OpenAPI multimodal memory endpoints, check DB de migracion/flags, smoke autenticado de sync/materializacion, browser smoke de Agent OS despues de serializar DDL runtime, log scan API/worker sin nuevos 500/deadlock/traceback y bootstrap PostgreSQL limpio `001` a `064`.
- Fase 24.7 Inbox UX implementada para panel de analisis, referencias visuales aprobadas y aprobar/usar/enviar.
- No requiere migracion nueva; reutiliza tablas de Web/Image Search, memoria multimodal y CRM/outbound.
- Endpoint tenant: `POST /saas/v1/media/search/results/{result_id}/reference`.
- El endpoint prepara texto de referencia solo desde resultados aprobados y no bloqueados; revalida URL publica y conversacion opcional.
- El envio real al cliente sigue usando `POST /saas/v1/conversations/{conversation_id}/messages`, conservando cuota, cola outbound, estados Meta y auditoria `message.sent`.
- UI Inbox CRM side panel muestra `Panel de analisis Inbox` con voz, vision, memoria multimodal, conteos de referencias aprobadas/pendientes, refresco y sincronizacion de memoria.
- Las referencias visuales aprobadas tienen acciones `Usar` y `Enviar`; las fuentes pendientes seguras tienen `Aprobar y usar` y `Aprobar y enviar`.
- `Enviar` requiere click humano y confirmacion del navegador.
- Seguridad: no hay envio automatico por IA/agentes/workers, no se usan fuentes bloqueadas, no se bypassa aprobacion, no se crawlean resultados, no se entrena modelo y no se muta CRM/campanas/workflows/Meta/billing.
- Validacion: py_compile backend, build tenant, Docker rebuild API/worker, API health, OpenAPI reference endpoint y browser smoke frontend sin errores.
- Fase 24.8 Admin & Premium Gating implementada para activar/controlar Phase 24 por tenant, plan, proveedor y costo.
- Migracion nueva: `saas-version/migrations/065_saas_multimodal_admin_gating_phase24.sql`.
- Tablas nuevas: `saas_intelligence_plan_feature_limits` y `saas_ai_provider_policies`.
- Endpoints Admin: `GET /saas/v1/admin/intelligence/premium-gating`, `PATCH /saas/v1/admin/intelligence/plans/{plan_code}/features` y `PATCH /saas/v1/admin/intelligence/provider-policies`.
- Backend nuevo: `saas-version/backend/app_saas/intelligence/premium.py`.
- Admin puede configurar modo `off/demo/full` y cuota mensual para features Phase 24 por tenant o por plan.
- Admin puede configurar proveedor AI/search/TTS por scope global/plan/tenant, modelo opcional, estado enabled/disabled, cuota de requests, limite de costo mensual y costos input/output/request.
- AI Gateway y Web/Image Search verifican provider policy antes de llamar proveedores externos.
- UI Admin `AI Predictivo` muestra resumen de costos, credenciales listas, politicas activas, tenant gating y plan gating.
- Seguridad: valores cero de cuota/costo no bloquean; se interpretan como sin limite configurado. Las politicas por defecto permiten compatibilidad hasta que Admin configure bloqueo/cupo/costo.
- Validacion: py_compile backend, build Admin, Compose config, SQL scans, Docker rebuild API/worker/Admin, migracion activa hasta `065`, API health, Swagger, Admin health, OpenAPI Phase 24.8, smoke autenticado de premium-gating/provider-policy, compileall en contenedor, log scan sin nuevos errores y bootstrap PostgreSQL limpio `001` a `065`.
- Fase 24.9 Observability implementada para costo por media, latencia, errores, calidad y fuentes usadas.
- Migracion nueva: `saas-version/migrations/067_saas_multimodal_observability_rollout_phase24.sql`.
- Tabla nueva: `saas_multimodal_observability_snapshots`.
- Feature flags default-off: `multimodal_observability`, `multimodal_cost_observability` y `multimodal_quality_monitoring`.
- Backend nuevo: `saas-version/backend/app_saas/intelligence/multimodal_observability.py`.
- Endpoints tenant: `GET /saas/v1/intelligence/multimodal/observability/center` y `POST /saas/v1/intelligence/multimodal/observability/refresh`.
- Observabilidad agrega datos desde AI Gateway runs, Voice Intelligence, Vision Intelligence, Web/Image Search, Agent tool runs y memoria multimodal.
- Reporta requests, costo estimado, latencia promedio/P95, errores, calidad/confianza, proveedores y fuentes usadas/aprobadas/bloqueadas.
- El costo usa pricing configurado por Admin en provider policies; costo cero significa pricing no configurado, no uso gratis ni factura real.
- Fase 24.10 Safe Rollout implementada con flags apagados por defecto, demo mode y canary.
- Tablas nuevas: `saas_multimodal_rollout_policies` y `saas_multimodal_rollout_events`.
- Feature flags default-off: `multimodal_safe_rollout` y `multimodal_canary`.
- Endpoints tenant: `GET /saas/v1/intelligence/multimodal/rollout/center` y `PATCH /saas/v1/intelligence/multimodal/rollout/policy`.
- Modos soportados: `off`, `demo`, `canary` y `full`.
- El canary es deterministico por tenant/user/subject y puede degradar a demo cuando la policy lo permite.
- Runtime aplicado en Voice Intelligence, Vision Intelligence y Web/Image Search antes de ejecutar proveedores externos.
- Seguridad: no hay bloqueo implicito; se requiere feature access y policy explicita habilitada. No muta CRM, campanas, workflows, billing, Meta runtime ni ownership de agentes.
- UI tenant `Inteligencia` muestra paneles Phase 24.9 y Phase 24.10 con metricas, providers, fuentes, policies y eventos de rollout.
- UI Admin `AI Predictivo` incluye los nuevos flags para tenant/plan gating.
- Validacion: py_compile backend, build tenant, build Admin, Compose config, SQL scans, tracked diff whitespace y scan manual de whitespace en archivos tocados. Pendiente Docker runtime/API/Swagger/bootstrap hasta `067` por Docker no accesible en la ultima sesion.

Fase 18 AI Workflow Composer:

- Implementada como control-plane premium para disenar workflows AI sin efectos externos durante pruebas.
- Backend nuevo: `saas-version/backend/app_saas/workflow_composer/`.
- Migracion nueva: `saas-version/migrations/057_saas_ai_workflow_composer_phase18.sql`.
- UI tenant nueva: `saas-version/frontend/src/WorkflowComposerPanel.jsx`.
- Endpoints bajo `/saas/v1/workflow-composer`.
- Feature flags: `ai_workflow_composer` para operaciones full y `workflow_composer_templates` para plantillas/demo.
- Capacidades: plantillas seguras, editor de grafo, nodos/edges, preflight, simulacion sin efectos, aprobaciones, versiones, rollback y activacion `composer_only`.
- Validacion: build frontend/Admin, compileall backend, Docker rebuild, API health, Swagger, worker, bootstrap temporal limpio `001` a `057`, smoke API autenticado y smoke browser del panel Composer.
- Pendiente intencional: despliegue runtime a triggers/flows/campanas/agentes. Requiere futuro diseno de materializacion, ADR, aprobacion humana, preflight y smoke staging.

Fase 22 AI Trust, Compliance & Governance:

- Implementada como control-plane premium para gobierno AI, no como enforcement automatico.
- Backend nuevo: `saas-version/backend/app_saas/trust_center/`.
- Migracion nueva: `saas-version/migrations/058_saas_ai_trust_compliance_governance_phase22.sql`.
- UI tenant nueva: `saas-version/frontend/src/TrustCenterPanel.jsx`.
- Vista Admin nueva: `Trust AI` en `saas-version/admin-frontend/src/AdminApp.jsx`.
- Endpoints tenant bajo `/saas/v1/trust-center`.
- Endpoints Admin bajo `/saas/v1/admin/trust-center`.
- Feature flags: `ai_trust_center`, `ai_governance_policies`, `ai_risk_assessments`, `ai_model_cards`, `ai_compliance_reports`, `ai_audit_exports`.
- Capacidades: politicas, attestations, risk scan preview/persist, mitigacion de riesgos, model cards, incidentes, auditoria y reportes de compliance AI.
- Validacion: compileall backend, build frontend tenant, build Admin, Docker rebuild, migracion activa hasta `058`, bootstrap PostgreSQL limpio aislado `001` a `058`, API health, Swagger, Admin health, OpenAPI Trust, smoke tenant Trust y smoke Admin Trust.
- Pendiente productivo: revisar lenguaje legal/compliance, hacer muestreo de auditoria real y definir politica de planes/tenants para full mode.

## Fases 19 y 20 Cerradas

Fase 19 Autonomous Revenue Engine:

- Migracion nueva: `saas-version/migrations/066_saas_revenue_memory_network_phase19_20.sql`.
- Backend nuevo: `saas-version/backend/app_saas/intelligence/revenue.py`.
- Endpoints tenant bajo `/saas/v1/intelligence/revenue/*`.
- Tablas: politicas, oportunidades, forecasts, experimentos y reportes de revenue AI.
- Detecta oportunidades desde senales reales CRM/conversacion/prediccion: lead hot, pago pendiente, etapa propuesta/cotizacion e inactividad de leads warm.
- UI tenant `Inteligencia` muestra metricas, politica configurable, oportunidades, forecasts, reportes y playbooks.
- La politica de revenue permite definir nivel de autonomia, moneda, meta, limite mensual de ejecuciones control-plane y action types permitidos para approve/execute.
- Seguridad: no envia mensajes, no cobra, no llama proveedores de pago, no muta CRM, no activa campanas/workflows/triggers y no modifica runtime Meta.
- Validacion: Docker activo aplico `066`, OpenAPI contiene endpoints, smoke autenticado full-mode creo oportunidades/report y ejecuto approve/execute como metadata control-plane.
- Hardening posterior: py_compile backend, builds tenant/Admin, Compose config y SQL UTF-8/BOM scans pasaron; Docker Desktop no estuvo accesible para rerun activo de API/Swagger en esta sesion.

Fase 20 AI Enterprise Memory Network:

- Misma migracion `066_saas_revenue_memory_network_phase19_20.sql`.
- Backend nuevo: `saas-version/backend/app_saas/intelligence/memory_network.py`.
- Endpoints tenant bajo `/saas/v1/intelligence/memory-network/*` para center, policy, sync, export, import, review y delete.
- Tablas: politicas, nodos, aristas, sync runs y access logs.
- Sincroniza candidatos desde memoria colectiva, Knowledge/RAG, eventos multimodales y vertical insights.
- La policy aplica privacidad, retencion, scopes permitidos y revision de contenido cliente durante sync/import/publish y actualizaciones de nodos existentes.
- Exporta JSON tenant-scoped con summaries/metadata/hashes; importa JSON sanitizado como nodos `candidate`; delete borra nodos tenant-scoped con audit/access log.
- UI tenant `Inteligencia` muestra nodos, aristas, routing, sync runs, controles de politica, export/import y acciones de publicar/rechazar/archivar/borrar.
- Seguridad: tenant-scoped, sin raw media/base64, sin compartir contenido crudo entre tenants y sin publicar memoria candidata a prompts/RAG sin revision.
- Validacion: smoke autenticado full-mode ejecuto sync, creo nodos/aristas y publico un nodo de prueba; el tenant temporal fue eliminado. El ultimo endurecimiento paso py_compile backend, builds tenant/Admin, Compose config y scans SQL; smoke activo export/import/delete queda pendiente porque Docker no estuvo accesible.

## Fase 17 Cerrada: Federated Learning & Global Intelligence

Implementado:

- Migracion nueva: `saas-version/migrations/068_saas_federated_learning_phase17.sql`.
- Backend nuevo: `saas-version/backend/app_saas/intelligence/federated.py`.
- Endpoints tenant bajo `/saas/v1/intelligence/federated/*`.
- Tablas: politicas federadas, rondas, updates agregados tenant, agregados federados y signals globales.
- Feature flags default-off: `federated_learning`, `federated_model_updates`, `privacy_safe_model_aggregation`, `global_intelligence`, `federated_benchmarking`.
- UI tenant `Inteligencia` muestra opt-in, privacidad, thresholds, tareas permitidas, previews locales, rondas, envio de updates, agregacion y signals globales.
- Worker Intelligence participa automaticamente solo si el tenant tiene full access, `opt_in_enabled=true` y `auto_participation_enabled=true`.
- Los paquetes federados contienen solo estadisticas agregadas, resumenes de features, feature importance, calidad, hash y metadata de privacidad.
- Seguridad: no comparte mensajes crudos, conversaciones completas, media/base64, prompts, secretos, payloads de proveedor, nombres de tenants ni contenido privado de clientes entre tenants.
- Los agregados son signals candidate/benchmark; no promueven modelos automaticamente ni mutan CRM/campanas/workflows/billing/Meta/agentes.

Validacion:

- `python -m py_compile` aprobado para modulos backend tocados.
- Build tenant frontend aprobado con warning existente de bundle grande.
- Build Admin frontend aprobado.
- Docker Compose config aprobado.

Pendiente productivo:

- Ejecutar migracion/API/Swagger/worker Docker hasta `068`.
- Ejecutar bootstrap PostgreSQL limpio `001` a `068`.
- Probar con varios tenants opt-in de la misma industria/general para validar thresholds.
- Revisar privacidad/legal antes de claims comerciales de aprendizaje cross-tenant.
- Definir runbook ModelOps antes de usar signals federados para seleccionar modelos productivos.

## Roadmap Recomendado Fases 21 a 25

Las fases propuestas son viables, pero no conviene tratarlas todas como inmediatas. Tras cerrar Fase 17, la secuencia recomendada es:

1. Fase 21: Scentra AI Cloud Platform.
2. Fase 23: AI Marketplace Economy.
3. Fase 25: Enterprise Decision Intelligence.

Criterio arquitectonico:

- Fase 18 ya aporta el control-plane de composicion segura antes de abrir marketplace amplio o despliegue runtime.
- Fase 22 ya aporta el control-plane de trust/gobierno necesario antes de ampliar autonomia, marketplace, federated learning, APIs externas y decisiones enterprise.
- Fase 16 ya aporta la superficie realtime para convertir eventos, predicciones y gobierno en monitoreo live sin activar acciones automaticas.
- Fase 24 es muy coherente con WhatsApp/Instagram por audios, imagenes y adjuntos.
- Fase 17 ya aporta el control-plane federado aggregate-only; aun requiere acceptance multi-tenant, privacidad y ModelOps antes de uso productivo de signals.
- Fase 21, 23 y 25 son valiosas pero deben esperar mas madurez de datos, sandbox, gobierno, comercializacion y calidad ML.
- Evaluacion detallada: `docs/ROADMAP_PHASES_16_25_EVALUATION.md`.

## Riesgos Restantes

- Produccion requiere SMTP, Turnstile, secretos fuertes, CORS/domains y credenciales reales.
- Billing queda cerrado a nivel codigo; requiere pruebas reales/sandbox de proveedores y validacion legal de factura PDF antes de produccion.
- Live Meta/AI acceptance debe probarse con trafico real o sandbox.
- La asignacion a agente inactivo bloquea fallback por seguridad; operadores deben liberar o reasignar desde Inbox.
- Verticalizacion queda cerrada a nivel codigo; requiere acceptance de packs por industria en staging antes de cambios masivos a tenants productivos.
- Phase 11 ya tiene ML real opcional y apagado por defecto, pero los modelos entrenados actualmente son sinteticos/autolabel para bootstrap tecnico. No deben venderse como precision productiva hasta revisar labels reales/auto-labels, validar drift/calidad/costos y aprobar rollout por tenant/plan.
- Fase 15.1A/15.1B/15.1C/15.2/15.3 ya generaron inventario, clasificacion, drafts, handoffs, playbooks y evals offline, pero falta verificar commit/tag upstream, hacer secret scan formal y revisar cada agente antes de importarlo a DB/Admin.
- Fase 18 queda operativa como control-plane; `composer_only` no debe venderse como despliegue runtime automatico hasta implementar una materializacion segura hacia triggers/flows/campanas/agentes.
- Fase 22 queda operativa como control-plane; sus reportes son evidencia operacional y no certificacion legal.
- Fase 16 queda operativa como control-plane realtime; no debe venderse como bus de eventos enterprise ni auto-remediacion hasta que existan pruebas de capacidad, broker aprobado si aplica y ADR de acciones runtime.
- Fase 24.2 queda operativa para audios, pero acceptance productiva requiere credenciales reales Google/Gemini, audios reales WhatsApp/locales, revision de costos/cuotas y politicas de privacidad/retencion de transcript.
- Fase 24.3 queda operativa para imagenes/documentos existentes, pero acceptance productiva requiere credenciales reales Google/OpenRouter/Kimi, media real WhatsApp/local, revision de costos/cuotas y politicas de privacidad/retencion de texto extraido.
- Fase 24.4 queda operativa para busqueda web/imagen con fuentes y aprobacion, pero acceptance productiva requiere credenciales reales Tavily/Brave/SerpAPI, revision de cuotas/costos, calidad de fuentes y politica de copyright/licencias antes de usar referencias con clientes.
- Fase 24.5 queda operativa para herramientas multimodales agent-scoped, pero acceptance productiva requiere media real, credenciales reales, aprobacion de fuentes, revision de costos/cuotas y entrenamiento de operadores.
- Fase 24.6 queda operativa para memoria/training events multimodales, pero acceptance productiva requiere muestras reales, politica de retencion, revision de privacidad, revision de copyright para fuentes externas y entrenamiento de operadores antes de materializar contenido sensible.
- Fase 24.7 queda operativa para UX Inbox de analisis/referencias aprobadas, pero acceptance productiva requiere muestras reales de referencias visuales, politica de copyright/fuentes, entrenamiento de operadores y smoke Meta outbound con canal real.
- Fase 24.8 queda operativa para Admin/Premium Gating, pero acceptance productiva requiere pricing real por proveedor/modelo, politica comercial de cuotas, smoke con credenciales reales y alineacion legal/billing antes de usar costos como dato comercial.
- Fase 24.9 queda operativa para observabilidad multimodal, pero acceptance productiva requiere pricing real por proveedor/modelo y trafico real antes de usar costo/calidad/error-rate como dato comercial.
- Fase 24.10 queda operativa para safe rollout default-off/demo/canary, pero acceptance productiva requiere ensayar policies `off/demo/canary/full` con muestras reales antes de habilitarlo ampliamente.
- Fase 24.9/24.10 aun necesita migracion/API/Swagger/bootstrap Docker hasta `067` cuando Docker este disponible en la maquina.
- Fase 19 queda operativa como control-plane de revenue; acceptance productiva requiere datos reales de pedidos/pagos/valor comercial por tenant antes de usar forecasts u oportunidad estimada como metrica comercial.
- Fase 20 queda operativa como grafo de memoria tenant-scoped con policy, export/import/delete auditados; acceptance productiva requiere muestras reales y validacion de que solo nodos publicados entren a prompts/RAG.
- Fase 17 queda operativa a nivel codigo, pero no debe venderse como federated learning productivo avanzado hasta probar cohortes reales, privacidad, calidad de labels y promocion ModelOps.
- Las fases restantes 21, 23 y 25 son recomendacion de roadmap, no compromiso implementado; cada una requiere ADR, feature flags, acceptance y riesgos propios antes de tocar runtime.
- Fase 12 queda operativa como control-plane; sus SLOs/backpressure son thresholds iniciales y deben calibrarse con trafico real antes de comprometer SLAs comerciales.
- Fase 13 queda operativa con email OTP; TOTP/app authenticator y rotacion automatizada de secretos quedan fuera del alcance actual hasta diseno/aprobacion especifica.
- Las solicitudes de borrado de privacidad son revisables y no hacen hard-delete automatico; se requiere procedimiento legal/operativo antes de ejecutar eliminaciones reales.
- Retention destructive esta deshabilitado/dry-run por defecto; antes de borrar historicos se requiere backup verificado, ensayo en staging y aprobacion de politica legal/operativa.
- Backup readiness no reemplaza backup/restore real de infraestructura.

## Siguientes Prioridades Recomendadas

1. Ejecutar acceptance de packs verticales en staging con tenants reales o datos semilla.
2. Ejecutar acceptance sandbox/live de billing con Stripe, MercadoPago y Wompi.
3. Mantener Fase 14: ejecutar auditoria de copy/release gate antes de cada entrega frontend/admin y expandir catalogos al tocar nuevos modulos.
4. Ejecutar acceptance de Fase 12: carga real, ajuste de thresholds, backup/restore real y politica de retencion.
5. Ejecutar smoke de Fase 8 en staging con conversaciones reales, asignacion manual/automatica, memoria colectiva y presupuesto hard-stop.
6. Confirmar source URL/commit/tag de `agency-agents`, decidir atribucion y aprobar si los drafts offline pasan a Admin/DB.
7. Definir politica comercial de features predictivas full por plan/tenant antes de venta enterprise.
8. Ejecutar acceptance de Fase 11 ML con datos reales anonimizados o datasets staging tenant-safe antes de activar `SAAS_ML_ENABLED` en produccion.
9. Ejecutar acceptance de Fase 24.2 Voice Intelligence con credenciales reales Google/Gemini, audios reales WhatsApp/locales y revision de privacidad/costos antes de habilitarlo comercialmente.
10. Ejecutar acceptance de Fase 24.3 Vision Intelligence con credenciales reales Google/OpenRouter/Kimi, imagenes/documentos reales y revision de privacidad/costos antes de habilitarlo comercialmente.
11. Ejecutar acceptance de Fase 24.4 Web/Image Search Intelligence con credenciales reales Tavily/Brave/SerpAPI, busquedas reales, revision de fuentes, cuotas/costos y politica de copyright antes de habilitarlo comercialmente.
12. Ejecutar acceptance de Fase 24.5 Agent Multimodal Tools con agentes asignados, media real, busqueda real, fuentes aprobadas y verificacion de que solo contexto aprobado entra al prompt.
13. Ejecutar acceptance de Fase 24.6 Multimodal Memory con eventos reales, materializacion revisada a RAG/memoria colectiva, politicas de retencion y verificacion de que training-ready solo se activa con feature premium.
14. Ejecutar acceptance de Fase 24.7 Inbox UX con fuentes visuales aprobadas, revision de copyright/fuentes, operadores entrenados y envio real por Meta outbound desde el CRM existente.
15. Configurar acceptance de Fase 24.8 con precios reales por proveedor/modelo, cuotas por plan, bloqueo de prueba por tenant y reporte de costos mensual comparado contra consola del proveedor.
16. Ejecutar acceptance de Fase 24.9/24.10 con migracion Docker hasta `067`, health/API/Swagger, clean bootstrap PostgreSQL, precios reales, trafico multimodal real y policies `off/demo/canary/full`.
17. Ejecutar acceptance de Fase 19 con datos reales o staging de pedidos/pagos, validacion comercial de forecasts y definicion de que acciones pueden materializarse en CRM/campanas en una fase futura.
18. Ejecutar acceptance de Fase 20 con muestras reales de memoria colectiva/RAG/multimodal, flujo export/import/delete y validacion de prompt routing solo con nodos publicados.
19. Ejecutar acceptance de Fase 17 con migracion Docker hasta `068`, bootstrap limpio `001` a `068`, varios tenants opt-in, validacion privacidad/legal y runbook ModelOps.
20. Continuar roadmap con Fase 21, luego Fase 23 y Fase 25.
