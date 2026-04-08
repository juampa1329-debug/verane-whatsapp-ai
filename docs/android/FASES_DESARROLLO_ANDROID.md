# Fases de desarrollo Android (paridad con app web)

## Fase 0 - Entorno

- Instalar Android Studio + SDK + emulador.
- Verificar ejecucion local de backend (`docker-compose up -d` en raiz del repo).
- Definir `API Base URL` para entorno local/staging/prod.

## Fase 1 - Base movil (completada)

- Proyecto Kotlin + Compose inicial.
- Configuracion persistente de API/token/web en DataStore.
- Notificaciones locales y worker de sync.
- Base de Firebase Messaging para push real.

## Fase 2 - Operacion diaria (completada)

- Inbox funcional con lectura y envio.
- Adjuntos por `media/upload`.
- Toggle takeover.
- Clientes: listado, detalle y edicion CRM.

## Fase 3 - Paridad de negocio (completada)

- Dashboard nativo (KPIs/funnel/campaigns/remarketing) con refresh y ticks manuales de engine.
- Marketing nativo operativo:
  - templates y segmentos
  - campanas (crear y lanzar)
  - triggers (activar/desactivar)
  - remarketing flows/steps/enrollments + dispatch flow/step
- Incluye:
  - CRUD avanzado de templates/triggers/flows/steps con validaciones basicas en UI
  - Filtros operativos por estado/canal y acciones masivas por modulo

## Fase 4 - Seguridad y AI movil (completada)

- Modo seguridad por roles en app (admin/supervisor/agente) con acceso condicional a modulos.
- Gestion de seguridad movil:
  - policy, MFA, alertas
  - usuarios (crear/editar/reset password/2FA)
  - sesiones (revocar individual/masivo)
  - API keys (crear/rotar/revelar/activar-desactivar)
  - auditoria y estado de rotacion
- Ajustes AI operativos:
  - AI settings (LLM/voice/MM)
  - Knowledge base (upload/reindex/delete de archivos)
  - Web sources (crear/sync/toggle/delete)
  - Test QA de process-message y TTS

## Fase 5 - Push real y release (completada)

- Push real end-to-end:
  - registro/desregistro de token FCM en backend (`/api/mobile/push/*`)
  - registro automatico desde Android (startup + refresh de token)
  - envio por eventos: `message_in`, `takeover_changed`, `security_alert`
  - estado y test manual de push desde backend
- Observabilidad release:
  - Crashlytics instrumentado en app
  - custom keys de rol/API/actor para debugging
  - logging de eventos FCM recibidos y errores de registro
- Release hardening:
  - build release con minify + shrink resources
  - reglas ProGuard base para serializacion/Firebase
  - documentacion de rollout por tracks de Play Console
