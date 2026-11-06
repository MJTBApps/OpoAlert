# Aviso silencioso con Firebase (OpoAlert 1.54.0)

Sin esto, Android e iOS deciden cuándo revisar en segundo plano y las alertas
suelen llegar al abrir la app. Con Firebase, al publicar convocatorias nuevas
GitHub manda un aviso silencioso al tema `convocatorias`; el móvil descarga los
feeds y compara con sus alertas, que **nunca salen del teléfono**.

Código: `backend/aviso_fcm.py` (paso final de `publicar-web.yml`; avisa si cambian
los anuncios y han pasado 20 minutos desde el último), `app/.../Push.kt` y
`ios/OpoAlert/Push.swift`. Sin los datos de abajo todo sigue funcionando como antes.

## Pasos (una vez)

1. https://console.firebase.google.com → **Crear proyecto** «OpoAlert» (Google Analytics: no).
2. **Añadir app Android**, paquete `es.opoalert.app`. Descarga `google-services.json`
   (no se sube al repositorio). De ahí salen:
   - `appId` = `client[0].client_info.mobilesdk_app_id`
   - `apiKey` = `client[0].api_key[0].current_key`
   - `projectId` = `project_info.project_id`
   - `senderId` = `project_info.project_number`
3. **Añadir app iOS**, bundle `es.opoalert.app`. Descarga `GoogleService-Info.plist`
   (no se sube): `GOOGLE_APP_ID`, `API_KEY`, `GCM_SENDER_ID`, `PROJECT_ID`.
4. Apple: en developer.apple.com → Keys, crea una clave con **Apple Push Notifications
   service (APNs)** y descarga el `.p8` (guárdalo en `~/OpoAlert-claves/`). En
   Identifiers → `es.opoalert.app` activa **Push Notifications**. En Firebase →
   Configuración del proyecto → Cloud Messaging → app iOS, sube esa clave
   (ID de la clave y Team ID).
5. Firebase → Configuración del proyecto → Cuentas de servicio → **Generar nueva
   clave privada** (JSON). Es una clave secreta: solo en GitHub y en `~/OpoAlert-claves/`.
6. GitHub → Settings → Secrets and variables → Actions, secretos nuevos:
   - `FIREBASE_SERVICE_ACCOUNT`: el JSON completo del paso 5.
   - `FIREBASE_ANDROID_PROPERTIES`: cuatro líneas `appId=…`, `apiKey=…`, `projectId=…`, `senderId=…`.
   - `FIREBASE_IOS_APP_ID`, `FIREBASE_IOS_API_KEY`, `FIREBASE_IOS_SENDER_ID`, `FIREBASE_PROJECT_ID`.
7. En el iMac, `~/OpoAlert-claves/firebase.properties` con las mismas cuatro líneas
   de Android (para el AAB de Google Play).
8. Compilar de nuevo: la APK web (Actions), el AAB de Play (`bundlePlayRelease`) y
   iOS (`ios-testflight.yml`).
