# Setup local Android (Windows)

## 1) Software a instalar

- Android Studio (version estable actual, incluye JBR/JDK 17).
- Android SDK Platform 34.
- Android SDK Build-Tools 34.x.
- Android Emulator + una imagen API 34 (x86_64) con Google APIs.
- Git.
- Docker Desktop (para levantar backend local).

## 2) Levantar backend local

Desde la raiz del repo:

```powershell
docker-compose up -d
```

### Variables recomendadas para push FCM en backend

Define una de estas opciones:

- `FCM_SERVICE_ACCOUNT_FILE` con ruta absoluta al JSON de service account de Firebase.
- `FCM_SERVICE_ACCOUNT_JSON` con el JSON completo (string).

Y habilita push:

- `PUSH_FCM_ENABLED=true`

Backend esperado en local:

- API: `http://10.0.2.2:8000` (si usas emulador Android).
- API: `http://<IP_LOCAL_PC>:8000` (si usas dispositivo fisico).

## 3) Abrir y ejecutar app Android

1. Abre `C:\verane-whatsapp-ai\mobile-android` en Android Studio.
2. Espera Sync de Gradle.
3. Crea/inicia un emulador API 34.
4. Coloca `google-services.json` en `C:\verane-whatsapp-ai\mobile-android\app\google-services.json`.
5. Ejecuta `app` (Run).

## 4) Build por terminal (opcional)

```powershell
cd C:\verane-whatsapp-ai\mobile-android
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
.\gradlew.bat :app:assembleDebug -x lint
```

APK generado:

- `C:\verane-whatsapp-ai\mobile-android\app\build\outputs\apk\debug\app-debug.apk`

Para release (AAB):

```powershell
cd C:\verane-whatsapp-ai\mobile-android
$env:JAVA_HOME='C:\Program Files\Android\Android Studio\jbr'
.\gradlew.bat :app:bundleRelease
```

Bundle generado:

- `C:\verane-whatsapp-ai\mobile-android\app\build\outputs\bundle\release\app-release.aab`

## 5) Configuracion inicial dentro de la app

En pantalla de Setup:

- `API Base URL`: `http://10.0.2.2:8000` (emulador) o IP local (dispositivo fisico).
- `Security Token`: token configurado en backend.
- `Web App Base`: URL de tu panel web.
- `Rol activo`: `admin/supervisor/agente` segun el token que uses.
- `Actor`: nombre para auditoria (opcional, recomendado).
