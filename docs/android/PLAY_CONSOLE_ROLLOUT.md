# Rollout Android por tracks (Play Console)

## Prerequisitos

- Keystore de release configurado en Android Studio/Gradle.
- `google-services.json` en `mobile-android/app/`.
- Firebase project con FCM y Crashlytics activos.
- Backend con `firebase-admin` instalado y credenciales FCM (`FCM_SERVICE_ACCOUNT_FILE` o `FCM_SERVICE_ACCOUNT_JSON`).

## Build de release

```powershell
cd C:\verane-whatsapp-ai\mobile-android
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
.\gradlew.bat :app:bundleRelease
```

Artefacto:

- `mobile-android/app/build/outputs/bundle/release/app-release.aab`

## Secuencia recomendada de despliegue

1. `Internal testing`:
   - Subir `app-release.aab`.
   - Validar login, inbox, marketing, seguridad, AI, push y crash test.
2. `Closed testing`:
   - Abrir a equipo extendido/QA.
   - Verificar métricas Crashlytics por version.
3. `Production (staged rollout)`:
   - Iniciar en 5%.
   - Subir a 20% / 50% / 100% segun estabilidad.

## Checklist de smoke test antes de promover

- App inicia sin crashes en Android 10+.
- Registro de token FCM exitoso (`/api/mobile/push/register`).
- Push real llega para:
  - `message_in`
  - `takeover_changed`
  - `security_alert`
- Eventos aparecen en `/api/mobile/push/state`.
- Crashlytics recibe eventos de la version publicada.
