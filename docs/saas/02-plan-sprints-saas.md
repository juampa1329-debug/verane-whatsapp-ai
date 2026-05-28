# Plan de ejecucion por sprints (SaaS)

## 1) Supuestos de planificacion
1. Sprint de 2 semanas.
2. Equipo base:
   - 1 Tech Lead backend.
   - 1 Fullstack backend/frontend.
   - 1 Frontend.
   - 1 QA (compartido).
3. Meta: MVP SaaS funcional en 12-16 semanas.

## 2) Resumen por sprint
1. Sprint 0: setup SaaS paralelo y baseline tecnico.
2. Sprint 1: identidad SaaS y tenant model.
3. Sprint 2: tenantizacion de datos core y API v1.
4. Sprint 3: webhooks multi-tenant + cola + workers.
5. Sprint 4: integraciones por tenant + hardening de seguridad.
6. Sprint 5: billing, planes y limites.
7. Sprint 6: observabilidad, performance y readiness productiva.

## 3) Backlog priorizado por sprint

## Sprint 0 (Semanas 1-2)
### Objetivo
Crear base de trabajo SaaS en paralelo sin romper produccion.

### Historias P0
1. Crear carpeta `saas-version/` y convenciones de arquitectura.
2. Definir migraciones SQL iniciales SaaS core.
3. Crear contrato API `/saas/v1` y reglas de auth.
4. Definir pipeline CI minima (lint + tests + sql check).

### Historias P1
1. Definir IaC inicial (plantillas infra).
2. Preparar entorno `dev/staging` con DB aislada.

### Entregables
1. Estructura SaaS inicial en repo.
2. Scripts de migracion versionados.
3. Documento de arquitectura y checklist de release.

### Estimacion
1. 22-28 puntos.

## Sprint 1 (Semanas 3-4)
### Objetivo
Habilitar auth SaaS y membresias por tenant.

### Historias P0
1. Implementar tablas: `saas_tenants`, `saas_users`, `saas_memberships`.
2. Login/refresh/logout y switch tenant.
3. Middleware de contexto tenant.
4. RBAC por rol (`owner/admin/supervisor/agent/viewer`).

### Historias P1
1. Pantallas iniciales de tenant selector.
2. Admin de miembros basico.

### Historias P2
1. Invite por email (stub).

### Entregables
1. Auth SaaS operativa.
2. Endpoints de tenants y memberships en `/saas/v1`.
3. Pruebas de permisos basicas.

### Estimacion
1. 30-36 puntos.

## Sprint 2 (Semanas 5-6)
### Objetivo
Tenantizar datos core sin corte destructivo.

### Historias P0
1. Agregar `tenant_id` a tablas core (fase no destructiva).
2. Adaptar consultas `conversations/messages` a tenant context.
3. Agregar indices compuestos por tenant.
4. QA de no-regresion en inbox y CRM.

### Historias P1
1. Dual-read para detectar diferencias.
2. Reporte de inconsistencias.

### Entregables
1. API core funcionando por tenant.
2. Datos legacy asignados a tenant "legacy".

### Estimacion
1. 34-42 puntos.

## Sprint 3 (Semanas 7-8)
### Objetivo
Separar ingestion y automatizaciones del proceso web.

### Historias P0
1. Cola principal + DLQ.
2. Worker ingest y worker dispatch.
3. Reintentos con backoff e idempotencia.
4. Endpoint webhook multi-tenant por `endpoint_key`.

### Historias P1
1. Worker de campaigns.
2. Worker de remarketing.

### Entregables
1. Webhooks y jobs en arquitectura async.
2. API web mas estable bajo carga.

### Estimacion
1. 34-44 puntos.

## Sprint 4 (Semanas 9-10)
### Objetivo
Integraciones por tenant y seguridad fuerte.

### Historias P0
1. `saas_integrations` y secret rotation.
2. Firma webhook obligatoria por canal.
3. Desactivar modo abierto en SaaS.
4. RLS en tablas tenantizadas.

### Historias P1
1. Migrar hashing de password a Argon2id.
2. Auditoria SaaS enriquecida.

### Entregables
1. Integraciones aisladas por tenant.
2. Seguridad minima aceptable para SaaS.

### Estimacion
1. 32-40 puntos.

## Sprint 5 (Semanas 11-12)
### Objetivo
Lanzar monetizacion y control de limites.

### Historias P0
1. Integracion Stripe Checkout + Billing Portal.
2. Webhook Stripe y sincronizacion de estado.
3. `saas_plan_limits` + enforcement en API/worker.
4. Dashboard de uso basico por tenant.

### Historias P1
1. Trial y grace period.
2. Dunning basico.

### Entregables
1. Suscripciones activas por tenant.
2. Plan gating funcional.

### Estimacion
1. 28-36 puntos.

## Sprint 6 (Semanas 13-14)
### Objetivo
Preparar go-live productivo.

### Historias P0
1. Observabilidad completa (logs, metricas, trazas, alertas).
2. Testing de carga y chaos basico.
3. Runbooks de incidentes y rollback.
4. Endurecimiento de backups y DR.

### Historias P1
1. Mejoras UX de onboarding.
2. Afinacion de costos.

### Entregables
1. Readiness checklist aprobada.
2. Go-live controlado por cohortes.

### Estimacion
1. 26-34 puntos.

## 4) Dependencias criticas
1. Definicion de proveedor auth (Cognito/Auth0/Clerk o propio).
2. Definicion de proveedor billing (Stripe recomendado).
3. Definicion de proveedor cola (SQS/Rabbit/Redis streams).
4. Definicion de estrategia RLS (strict vs gradual).

## 5) Riesgos y mitigaciones
1. Riesgo: regresion por cambio de llave en `conversations`.
   - Mitigacion: fase no destructiva + cutover controlado + shadow reads.
2. Riesgo: duplicados webhook.
   - Mitigacion: idempotency key por tenant/evento + DLQ.
3. Riesgo: fuga de datos cross-tenant.
   - Mitigacion: middleware tenant estricto + RLS + pruebas de seguridad.
4. Riesgo: sobrecosto operativo.
   - Mitigacion: limites por plan + autoscaling + alertas de costo.

## 6) KPIs de ejecucion
1. Lead time por historia.
2. Defectos P0/P1 por sprint.
3. Error rate 5xx en API SaaS.
4. Tiempo de procesamiento en workers.
5. Tasa de eventos a DLQ.
6. Tasa de activacion de tenants (onboarding completado).

## 7) Definicion de Done por sprint
1. Codigo mergeado en main.
2. Migraciones aplicadas en staging.
3. Pruebas unitarias + integracion en verde.
4. Documentacion actualizada.
5. Checklist de seguridad validada.
