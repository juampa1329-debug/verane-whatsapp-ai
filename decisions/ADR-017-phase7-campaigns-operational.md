# ADR-017: Cierre Operativo De Fase 7 Campanas, Triggers Y Remarketing

Fecha: 2026-05-25

## Estado

Aceptada.

## Contexto

La Fase 7 requeria que campanas, triggers y remarketing fueran simulables, gobernables, compatibles con limites Meta y seguros frente a automatizaciones no deseadas.

El codigo existente ya tenia triggers, flows, cooldown, `block_ai`, preflight parcial, versionado base, quiet hours JSON y A/B JSON. Faltaban piezas de cierre operativo: quiet hours globales centralizadas, reporte A/B, simulator/preflight expuestos completamente, rollback usable, enforcement en workers y validacion de condiciones comerciales por etapa/estado.

## Decision

Se cierra Fase 7 a nivel codigo/repositorio con cambios minimos y compatibles:

- Mantener el modelo existente de FastAPI router + raw SQL + workers.
- Agregar schema forward-only `042_saas_campaigns_phase7_operational.sql`.
- Centralizar quiet hours globales en `saas_campaign_quiet_hours`.
- Registrar eventos A/B en `saas_campaign_ab_events`.
- Exponer endpoints de quiet hours, A/B report, simulator, preflight, versions y restore.
- Bloquear activacion de triggers/flows/campanas cuando preflight falla con severidad alta.
- Enforce de quiet hours/A-B/block_ai en workers, no solo en UI.
- Revalidar plantillas Meta aprobadas en enqueue y dispatch.
- Agregar condiciones comerciales de trigger para `crm_stage`, `payment_status`, `customer_type` e `intent`.

## Consecuencias

Positivas:

- Los operadores pueden simular antes de activar.
- La activacion queda protegida por preflight.
- Quiet hours globales aplican a triggers y flows en runtime.
- A/B tiene trazabilidad consultable.
- Meta templates no se envian si pierden estado aprobado antes del dispatch.
- Triggers pueden responder a etapas y estados comerciales reales del CRM.

Riesgos:

- A/B mide eventos queued/failed; conversion de negocio requiere fase posterior de analytics/ML.
- Validacion clean Docker con PostgreSQL limpio debe repetirse cuando Docker Desktop este disponible.
- Aceptacion final de Meta requiere trafico real o sandbox de proveedor.

## Validacion

- Backend `py_compile`: aprobado.
- Frontend client build: aprobado.
- Admin frontend build: aprobado.
- Compose config: aprobado.
- SQL sin BOM y UTF-8 estricto: aprobado.
- Clean Docker/PostgreSQL: pendiente por daemon Docker no disponible en la sesion.
