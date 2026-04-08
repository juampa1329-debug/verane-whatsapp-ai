# Verane Mobile Android

Base Android nativa para el proyecto `verane-whatsapp-ai`, pensada para paridad funcional progresiva con la app web.

## Estado actual

- Configuracion inicial de entorno desde la app (API base, token opcional, URL web).
- Dashboard nativo:
  - overview (`/api/dashboard/overview`)
  - funnel (`/api/dashboard/funnel`)
  - campaign metrics (`/api/dashboard/campaigns`)
  - remarketing summary (`/api/dashboard/remarketing`)
  - control/tick de engines (`/api/campaigns/engine/*`, `/api/remarketing/engine/*`)
- Inbox multicanal:
  - listar conversaciones (`/api/conversations`)
  - ver historial (`/api/conversations/{phone}/messages`)
  - marcar leido (`/api/conversations/{phone}/read`)
  - enviar texto (`/api/messages/ingest`)
  - adjuntar archivo y enviar media (`/api/media/upload` + `/api/messages/ingest`)
  - takeover (`/api/conversations/takeover`)
- Clientes:
  - listar (`/api/customers`)
  - detalle (`/api/customers/{phone}`)
  - editar (`PATCH /api/customers/{phone}`)
- Marketing nativo:
  - templates (`/api/templates`)
  - segmentos (`/api/customers/segments`)
  - campanas (`/api/campaigns`, `POST /api/campaigns`, `POST /api/campaigns/{id}/launch`)
  - triggers (`/api/triggers`, `PATCH /api/triggers/{id}`)
  - remarketing flows/steps/enrollments (`/api/remarketing/flows*`)
  - dispatch manual flow/step (`/api/remarketing/flows/{id}/dispatch`, `/api/remarketing/steps/{id}/dispatch`)
- Ajustes:
  - guardar API/web/token
  - activar o desactivar sync background cada 15 minutos (WorkManager)
  - prueba de notificaciones locales
- Base para push real con Firebase Messaging (`VeraneFirebaseMessagingService`).

## Requisitos de software

- Android Studio (ultima version estable).
- Android SDK Platform 34.
- Build Tools de Android.
- JDK 17 (Android Studio ya incluye JBR compatible).
- Emulador Android o dispositivo fisico con depuracion USB.
- Git.
- Docker Desktop (para levantar backend local si lo necesitas).

## Como abrir y ejecutar

1. Abre Android Studio.
2. `File > Open` y selecciona: `C:\verane-whatsapp-ai\mobile-android`.
3. Deja que Android Studio sincronice Gradle.
4. Crea/selecciona un emulador.
5. Ejecuta la app (`Run`).
6. En primera pantalla ajusta:
   - `API Base URL`: por ejemplo `https://backend.perfumesverane.com` o tu backend local
   - `Web App URL`: `https://app.perfumesverane.com`
   - `Security Bearer Token` solo si tu backend exige auth en endpoints de seguridad

Puedes ejecutar una verificacion rapida de entorno con:

```powershell
cd C:\verane-whatsapp-ai\mobile-android
.\check_env.ps1
```

## Firebase (push real)

Para push FCM en produccion:

1. Crea proyecto en Firebase.
2. Agrega app Android con `applicationId = com.verane.mobile`.
3. Descarga `google-services.json` y colocalo en `mobile-android/app/`.
4. (Siguiente fase) activar plugin `com.google.gms.google-services` en Gradle.
5. En backend, implementar endpoint para registrar token FCM por usuario/dispositivo.

## Notas

- Esta base ya cubre operacion movil real con Dashboard + Inbox + Clientes + Marketing.
- Siguiente fase para paridad 1:1 total:
  - editores avanzados de templates/triggers/flows
  - Ads Manager nativo
  - seguridad administrativa avanzada en UI nativa
