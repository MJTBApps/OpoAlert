# OpoAlert: publicidad, Premium y versión iOS

Estado a 31/10/2026. Lo que ya está hecho en la app Android y lo que falta, con
lo que solo puede hacer el propietario (cuentas, pagos y datos fiscales).

## 1. Publicidad (Android) — hecha en código, con anuncios de prueba

- **Al abrir la app**: anuncio de apertura de AdMob (*App Open*). Solo al
  arrancar la app desde cero, nunca en el primer arranque, como mucho uno por
  hora y solo si carga en menos de 5 segundos (si no, se descarta y no se hace
  esperar). `DemoAds.loadOpenAd()`.
- **En la lista**: un anuncio cada 8 convocatorias, máximo 5
  (`DemoAds.LIST_AD_EVERY`, `MAX_LIST_ADS`), con la etiqueta «PUBLICIDAD».
- **Consentimiento (RGPD)**: lo gestiona la plataforma de Google (UMP). Sin
  consentimiento no se piden anuncios y la app funciona igual.
- Comprobado en el emulador el 31/10/2026 con la geografía de depuración de UMP
  (fuera de la UE): se ven el anuncio de apertura y los de la lista.

**Lo que falta, y solo puede hacerlo el propietario:**
1. Crear la cuenta de **AdMob** (admob.google.com) con los datos fiscales y de
   cobro.
2. Dar de alta la app y crear dos bloques de anuncios: *App open* y *Banner*
   (adaptable). Cambiar los identificadores de prueba en `DemoAds.kt`
   (`BANNER_ID`, `OPEN_AD_ID`) y el `APPLICATION_ID` de `AndroidManifest.xml`.
3. En AdMob → *Privacidad y mensajes*, **publicar el mensaje del RGPD**. Sin él,
   en España el gestor de consentimiento no muestra ningún formulario y **no se
   sirve ningún anuncio** (es lo que pasa hoy con los identificadores de prueba).
4. Publicar `app-ads.txt` en la raíz del dominio de desarrollador que figure en
   Google Play.
5. No pulsar nunca los propios anuncios reales (AdMob suspende la cuenta). Para
   probar, seguir con los identificadores de prueba o registrar el móvil como
   dispositivo de prueba.

## 2. OpoAlert Premium — estructura hecha, sin cobro todavía

- `Premium.kt`: Premium quita toda la publicidad y desbloquea las alertas.
- Menú → «OpoAlert Premium» explica las ventajas. En las compilaciones de
  prueba (las de `docs/`) hay un botón «Activar (pruebas)» para simularlo.
- `Premium.BILLING_READY = false`: mientras no haya cobro, **las alertas siguen
  gratis para todos**. Al ponerlo a `true`, las alertas pasan a ser de Premium.

**Para cobrar hace falta Google Play.** Google Play Billing solo funciona con la
app instalada desde Google Play, no con la APK de GitHub Pages:
1. Cuenta de desarrollador de **Google Play Console** (pago único de 25 USD y
   verificación de identidad).
2. Compilar la versión *release* firmada (AAB) y subir `targetSdk` a 35 (Google
   Play lo exige para apps nuevas y actualizaciones).
3. Crear la suscripción (o compra única) en Play Console.
4. Integrar Google Play Billing (`com.android.billingclient`), verificar la
   compra y poner `BILLING_READY = true`.
5. Ficha de Play Store: política de privacidad, clasificación de contenido y
   formulario de seguridad de los datos (declarar AdMob).

## 3. Versión iOS — estudio

**Este iMac no puede compilar para el App Store.** Es un iMac de 2017
(iMac18,3), cuyo último macOS es Ventura 13. Desde el 28/04/2026 Apple exige
Xcode 26 con el SDK de iOS 26 para subir apps, y Xcode 26 necesita un macOS
más moderno que Ventura.

Opciones:
- **GitHub Actions con macOS** (recomendada para empezar): el repositorio es
  público, así que los ejecutores macOS con Xcode 26 son gratuitos. Sirven
  para compilar, pasar pruebas, sacar capturas del simulador y subir a
  TestFlight.
- **Un Mac con Apple Silicon** (p. ej. un Mac mini), si se quiere trabajar con
  Xcode en local y el simulador en pantalla.

Requisitos del propietario: **Apple Developer Program** (99 USD al año), un
iPhone para probar con TestFlight y, para Premium, el acuerdo de pagos de App
Store Connect.

Enfoque técnico propuesto: **app nativa en SwiftUI** que lee los mismos feeds
JSON de GitHub Pages (`fuentes_activas.json` y un JSON por fuente). El backend
no cambia. Piezas: lista y búsqueda, ficha, favoritas, alertas (con
`BGAppRefreshTask` y notificaciones locales; iOS decide cuándo ejecutarlas),
anuncios con Google Mobile Ads para iOS y Premium con StoreKit 2.

Orden recomendado: (1) AdMob y Play Console para Android, (2) Premium con cobro
en Android, (3) iOS con la misma estructura.
