# Blueprint Tecnico SaaS (version inicial)

## 1) Objetivo
Convertir el sistema actual (single-tenant) a una plataforma SaaS multi-tenant segura, escalable y operable.

## 2) Enfoque recomendado
1. Mantener la aplicacion actual operativa.
2. Crear una version SaaS en paralelo dentro de `saas-version/`.
3. Migrar por fases con compatibilidad temporal.
4. Activar hardening de seguridad y aislamiento de datos por tenant.

## 3) Arquitectura objetivo
1. Web/API:
   - `api` (FastAPI, endpoints SaaS).
   - `webhook-ingest` (recepcion webhooks con verificacion estricta).
2. Procesamiento async:
   - `worker-ingest`, `worker-campaigns`, `worker-remarketing`, `worker-billing`.
   - Cola con DLQ (`SQS`/`Rabbit`/`Redis streams` segun stack final).
3. Datos:
   - PostgreSQL administrado.
   - Objeto storage para archivos/media (S3 compatible).
   - Cache opcional (Redis administrado).
4. Seguridad:
   - JWT/OIDC para usuarios.
   - secretos por tenant (secret manager).
   - WAF/rate limit/firma webhooks obligatoria.
5. Observabilidad:
   - logs estructurados.
   - trazas OpenTelemetry.
   - metricas y alertas SLO.

## 4) Estrategia de aislamiento multi-tenant
1. Modelo por defecto: `single database + tenant_id + RLS`.
2. Modelo enterprise opcional: `tenant aislado en database/schema dedicado`.
3. Decision runtime:
   - tenants SMB/Pro: shared DB con RLS.
   - tenants Enterprise: opcion isolated.

## 5) Modelo de datos SaaS (nuevo)
Tablas base propuestas (creadas en `saas-version/migrations/001_saas_core.sql`):

1. `saas_tenants`
   - metadatos del tenant, plan, estado.
2. `saas_users`
   - identidad global (correo, password hash, status).
3. `saas_memberships`
   - relacion usuario-tenant con rol (`owner|admin|supervisor|agent|viewer`).
4. `saas_integrations`
   - configuracion por tenant y canal (whatsapp/meta/instagram/facebook/tiktok/woo).
5. `saas_webhook_endpoints`
   - endpoint key por tenant y canal, estado y ultima actividad.
6. `saas_billing_customers`
   - relacion tenant con cliente en Stripe.
7. `saas_billing_subscriptions`
   - suscripcion, periodo, estado, cancelacion.
8. `saas_plan_limits`
   - limites por plan.
9. `saas_usage_counters`
   - consumo agregado por periodo.
10. `saas_audit_events`
   - auditoria de acciones SaaS.
11. `saas_outbound_messages`
   - cola transaccional para respuestas y mensajes salientes por tenant.

## 6) Tenantizacion de tablas actuales (concreta)
Migracion no destructiva inicial en `saas-version/migrations/002_tenant_columns_non_breaking.sql`.

Tablas impactadas:
1. `conversations`
2. `messages`
3. `campaigns`
4. `campaign_recipients`
5. `automation_triggers`
6. `trigger_executions`
7. `trigger_scheduled_messages`
8. `remarketing_flows`
9. `remarketing_steps`
10. `remarketing_enrollments`
11. `social_webhook_events`
12. `social_comments`
13. `meta_lead_events`

### Nota critica de diseno
`conversations` hoy usa `phone` como PK global. Para SaaS real se requiere cortar a esquema multi-tenant:
1. Crear llave compuesta por tenant.
2. O crear PK surrogate y `UNIQUE (tenant_id, phone)`.
3. Script de corte propuesto: `saas-version/migrations/003_conversations_cutover.sql`.

## 7) Contrato API SaaS v1 (propuesto)
Todos bajo prefijo `/saas/v1`.

### Auth y sesion
1. `POST /auth/login`
2. `POST /auth/refresh`
3. `POST /auth/logout`
4. `GET /auth/me`
5. `POST /auth/switch-tenant`

### Tenants y membresias
1. `POST /tenants`
2. `GET /tenants`
3. `GET /tenants/{tenant_id}`
4. `PATCH /tenants/{tenant_id}`
5. `POST /tenants/{tenant_id}/members`
6. `PATCH /tenants/{tenant_id}/members/{user_id}`
7. `DELETE /tenants/{tenant_id}/members/{user_id}`

### Integraciones y webhooks
1. `GET /integrations`
2. `POST /integrations/{provider}/connect`
3. `PATCH /integrations/{provider}`
4. `POST /integrations/{provider}/rotate-secret`
5. `GET /webhooks/endpoints`
6. `POST /webhooks/endpoints`
7. `POST /webhooks/{provider}/{endpoint_key}`

### Inbox y CRM
1. `GET /conversations`
2. `GET /conversations/{phone}/messages`
3. `POST /messages/ingest`
4. `POST /conversations/takeover`
5. `POST /crm`
6. `GET /crm/{phone}`

### Billing y plan
1. `GET /billing/subscription`
2. `POST /billing/checkout-session`
3. `POST /billing/portal-session`
4. `POST /billing/webhook/stripe`
5. `GET /limits`
6. `GET /usage`

### Admin y auditoria
1. `GET /audit/events`
2. `GET /health`
3. `GET /ready`
4. `POST /admin/reindex`

## 8) Webhooks multi-tenant (propuesta operativa)
1. URL por endpoint key:
   - `/saas/v1/webhooks/whatsapp/{endpoint_key}`
   - `/saas/v1/webhooks/meta/{endpoint_key}`
2. Resolver tenant por `endpoint_key` + firma valida.
3. Rechazar si:
   - endpoint inactivo,
   - firma invalida,
   - replay detectado.
4. Insert idempotencia:
   - `provider_event_id + tenant_id` unico.

## 9) Workers y colas (propuesta)
Queues:
1. `q.webhooks.ingest`
2. `q.messages.outbound`
3. `q.campaigns.dispatch`
4. `q.remarketing.tick`
5. `q.billing.events`
6. `q.deadletter`

Workers:
1. `worker_ingest` consume webhooks y normaliza eventos.
2. `worker_dispatch` envia mensajes salientes.
3. `worker_campaigns` agenda y ejecuta lotes.
4. `worker_remarketing` avanza etapas.
5. `worker_billing` sincroniza estado de suscripcion.

## 10) Seguridad obligatoria en SaaS
1. Sin modo abierto en produccion.
2. Auth obligatoria en todos los endpoints de negocio.
3. Firma webhook obligatoria por provider.
4. Password hashing robusto (Argon2id recomendado).
5. Secretos fuera de DB y env plano.
6. Auditoria de acciones criticas con actor, tenant, diff y IP.
7. RLS en tablas tenantizadas (`saas-version/migrations/004_rls_policies.sql`).
8. Rate limit por tenant y por endpoint.

## 11) Migraciones concretas incluidas
1. `saas-version/migrations/001_saas_core.sql`
2. `saas-version/migrations/002_tenant_columns_non_breaking.sql`
3. `saas-version/migrations/003_conversations_cutover.sql`
4. `saas-version/migrations/004_rls_policies.sql`
5. `saas-version/migrations/005_saas_webhook_events.sql`
6. `saas-version/migrations/006_saas_crm_core.sql`
7. `saas-version/migrations/007_webhook_signature_hardening.sql`
8. `saas-version/migrations/008_outbound_messages.sql`

## 12) Estrategia de despliegue
1. `dev`: validar migraciones y contrato SaaS.
2. `staging`: migrar dump anonimo y correr pruebas E2E.
3. `prod fase A`: dual-write opcional y tenant legacy.
4. `prod fase B`: cutover de conversaciones.
5. `prod fase C`: activar RLS estricto.

## 13) Criterios de aceptacion del MVP SaaS
1. Cada usuario pertenece a >=1 tenant con rol.
2. No existe lectura cruzada entre tenants.
3. Integraciones y webhooks configurables por tenant.
4. Billing activo con cambio de plan.
5. Background jobs fuera del proceso web.
6. Auditoria y alertas basicas en funcionamiento.
