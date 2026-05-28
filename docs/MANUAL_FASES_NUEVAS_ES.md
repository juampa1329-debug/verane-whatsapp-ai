# Manual Operativo: Nuevas Fases AI Scentra

Alcance: solo `saas-version/`.
Fecha: 2026-05-28.

Este manual resume como quedaron las fases nuevas implementadas y como operarlas con seguridad.

## Fase 16: AI Real-Time Intelligence Layer

Que hace:

- Muestra eventos, metricas live, sesiones, cursores y alertas consultivas.
- Usa PostgreSQL polling y SSE acotado.
- No agrega Kafka/NATS/Redis Streams.

Uso:

1. Habilitar features realtime por tenant/plan.
2. Abrir `Inteligencia`.
3. Revisar live feed, alertas y event mix.
4. Marcar cursor visto cuando el operador ya reviso eventos.

Limite:

- Alertas son consultivas. No ejecutan acciones runtime.

## Fase 17: Federated Learning & Global Intelligence

Que hace:

- Permite a tenants hacer opt-in para compartir paquetes estadisticos agregados.
- Genera rondas federadas por tarea/industria.
- Agrega updates ponderados y crea signals globales.

Uso tenant:

1. Admin habilita `federated_learning` o `ai_premium` en modo full.
2. Tenant abre `Inteligencia > Federated Learning`.
3. Activa `Opt-in federado`.
4. Define privacidad, min muestras locales y min tenants de cohorte.
5. Selecciona tareas: lead scoring, churn, remarketing u operaciones.
6. Ejecuta `Preview update`.
7. Si el preview es elegible, ejecuta `Crear ronda + enviar`.
8. En una ronda abierta, puede enviar update o calcular agregado.

Uso worker:

- El worker participa solo si hay full access, opt-in y auto-participation.

Limite:

- No comparte mensajes, conversaciones, media, prompts, secretos ni nombres de tenants.
- No promueve modelos automaticamente.
- Signals federados requieren revision ModelOps antes de afectar produccion.

## Fase 18: AI Workflow Composer

Que hace:

- Permite disenar workflows AI con templates, grafo, preflight, simulacion, aprobaciones, versiones y rollback.

Uso:

1. Habilitar `ai_workflow_composer`.
2. Crear workflow desde template o custom.
3. Ejecutar preflight.
4. Simular sin efectos.
5. Solicitar/aprobar.
6. Activar como `composer_only`.

Limite:

- Activar no despliega triggers/flows/campanas reales todavia.

## Fase 19: Autonomous Revenue Engine

Que hace:

- Detecta oportunidades comerciales desde CRM, predicciones y estados de pago.
- Genera oportunidades, forecasts, reportes y playbooks supervisados.

Uso:

1. Habilitar revenue features o `ai_premium`.
2. En `Inteligencia`, configurar politica: nivel, moneda, meta, max acciones/mes y action types permitidos.
3. Ejecutar `Vista previa`.
4. Ejecutar `Analizar revenue`.
5. Aprobar, ejecutar como metadata o descartar oportunidades.

Limite:

- No envia mensajes, no cobra, no muta CRM/campanas/workflows.

## Fase 20: AI Enterprise Memory Network

Que hace:

- Crea grafo tenant-scoped con memoria colectiva, Knowledge/RAG, multimodal y vertical insights.
- Permite revisar, publicar, archivar, exportar, importar y borrar nodos.

Uso:

1. Habilitar memory features.
2. Configurar politica: privacidad, retencion, scopes, revision cliente, routing multiagente.
3. Ejecutar preview de sync.
4. Ejecutar sync real.
5. Revisar nodos candidate.
6. Publicar solo memoria validada.
7. Exportar/importar JSON si hace falta portabilidad.

Limite:

- Import siempre entra como candidate.
- Nodos privados/candidate no deben entrar a prompts/RAG.

## Fase 22: AI Trust, Compliance & Governance

Que hace:

- Control-plane de politicas, riesgos, model cards, incidentes, auditorias y reportes AI.

Uso:

1. Habilitar Trust AI.
2. Crear o revisar politicas.
3. Ejecutar risk scan.
4. Revisar model cards.
5. Generar reportes.
6. Usar Admin Trust para vista multi-tenant.

Limite:

- No es certificacion legal.
- No aplica enforcement automatico.

## Fase 24: Voice & Multimodal Intelligence

Que hace:

- AI Gateway con adjuntos.
- Analisis de audio.
- Analisis de imagen/documentos.
- Busqueda web/imagen con aprobacion humana.
- Herramientas multimodales para agentes.
- Memoria/training events multimodales.
- UX Inbox para aprobar/usar/enviar referencias.
- Admin/Premium Gating.
- Observabilidad y Safe Rollout.

Uso:

1. Admin configura features, plan limits, provider policies y pricing.
2. Tenant configura credenciales reales por proveedor.
3. Operador analiza audio, imagen/documento o busca referencia externa.
4. Operador aprueba fuentes externas.
5. Operador usa/envia referencia desde Inbox.
6. Observabilidad revisa costo, latencia, errores, calidad y fuentes.
7. Rollout se configura off/demo/canary/full por modalidad/proveedor.

Limite:

- No auto-envia referencias.
- No entrena modelos automaticamente.
- No usa fuentes externas sin aprobacion.

## Manual Fase 11 ML: Entrenar Modelos

Flujo recomendado:

1. Ejecutar con `SAAS_ML_ENABLED=true` solo en staging o entorno controlado.
2. Verificar que MLflow, ML service y Qdrant esten levantados con profile `ml`.
3. Generar auto-labels desde Admin AI Predictivo.
4. Recalcular feature pipelines.
5. Construir dataset Postgres.
6. Entrenar autolabel con LightGBM, XGBoost o sklearn fallback.
7. Revisar metricas offline, distribucion de labels y drift.
8. Registrar modelo en Model Registry en shadow.
9. Habilitar shadow inference para comparar contra baseline.
10. Pasar a canary bajo porcentaje solo con aceptacion humana.
11. Promover a production solo con rollback documentado y evidencia.

Requisitos minimos:

- Datos reales tenant-safe.
- Labels revisados.
- Feature gates por plan/tenant.
- Costos/cuotas definidos.
- Runbook de rollback.

No hacer:

- No entrenar LLMs propios al inicio.
- No usar GPU.
- No vender modelos sinteticos/autolabel como precision productiva.
- No compartir datos crudos entre tenants.

## Operacion En VPS Oracle Cloud Free Tier

Viabilidad:

- El stack base API/worker/Postgres/frontends puede correr para dev o demo pequena si se ajustan recursos.
- No es ideal para todo el perfil ML completo con MLflow, Qdrant, builds, frontends y trafico real simultaneo.

Recomendacion:

- En free tier, usar features ML/AI pesadas apagadas por defecto.
- Ejecutar entrenamientos manuales y pequenos.
- Evitar correr MLflow/Qdrant/ML service continuamente si la RAM es limitada.
- Para produccion real, usar VPS con mas RAM/CPU, backup gestionado y monitoreo.

## Regla De Seguridad

Todas estas fases son feature-flagged, premium-gated y deben mantenerse apagadas por defecto para tenants no autorizados. Cualquier cambio futuro debe actualizar `CURRENT_STATE.md`, `TASK_STATE.md`, docs, riesgos y ADRs.
