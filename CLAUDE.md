# OpoAlert — contexto del proyecto

App Android nativa (Kotlin) que muestra convocatorias de empleo público, bolsas y oposiciones sacadas de boletines oficiales (BOE, BOP provinciales y el catálogo CIDO). Proyecto gratuito e independiente de las Administraciones.

- Repositorio **público**: `https://github.com/MJTBApps/OpoAlert` (rama `main`).
- Web y descargas: `https://mjtbapps.github.io/OpoAlert/` (GitHub Pages desde `docs/`).
- Se trabaja en dos equipos:
  - **iMac de casa** (macOS 13, Intel x64): `/Users/jordi/Desktop/APP/OpoAlert`. Aquí `git` funciona en la terminal (Xcode Command Line Tools). Python 3.12 de python.org; entorno `~/opoalert-venv` (el mismo que usa el ejecutor de casa). En Mac Intel, `pip install` con `--only-binary=:all:` (las últimas `cryptography` y `pymupdf` ya no traen paquete para Intel y no compilan).
  - **PC Windows**: GitHub Desktop en `C:\Users\PC-02\Desktop\APP\OpoAlert`. No hay `git` en el PATH; el de GitHub Desktop está en `%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\cmd\git.exe`. Lo que sigue sobre `.venv\`, `.bat` y Temurin se refiere a este PC.
- Desde el 30/10/2026 el proyecto se desarrolla **solo con Claude**: ChatGPT dejó unas 25 ramas `feature/*` sin unir y unos 200 workflows de pruebas sueltas (casi todos borrados el 30/10/2026). Su trabajo útil ya está en `main`; no hay que retomar esas ramas. Si cambian las reglas, actualiza este archivo.
- Claude no hace push: hace los commits en local y el usuario pulsa «Push origin» en GitHub Desktop.

## Cómo funciona

1. **Backend Python** (`backend/`): un lector por boletín descarga los **últimos 30 días**, extrae todos los anuncios y marca las posibles convocatorias. Un **validador independiente** comprueba el resultado.
2. **GitHub Actions** (`.github/workflows/revisar-*.yml`): una vez al día ejecuta lector, pruebas y validador. Solo si todo pasa, copia el JSON a `docs/`, hace commit como «OpoAlert Bot» y lanza `publicar-web.yml`, que despliega `docs/` en Pages.
3. **App Android** (`app/`): descarga esos JSON de Pages (`Province.feedUrl`), muestra buscador, favoritas y alertas inteligentes, y revisa avisos con WorkManager (~6 h, sin garantía de inmediatez). Los favoritos y alertas se guardan **solo en el móvil**.

## Dónde está el código

- **Android**: `app/src/main/java/es/opoalert/app/`
  - `Province.kt` — enum con **cada fuente**: código, nombre, URL del feed, web oficial, host y ruta de los PDF, patrón de identificador.
  - `SourceCatalog.kt` — agrupación por comunidad y provincia del selector «Elegir boletines». Solo fuentes auditadas.
  - `MainActivity.kt` (pantalla principal), `NoticeDetailActivity.kt` (ficha), `AlertsActivity.kt` + `AlertRule*.kt` (alertas), `RemoteFeedReader.kt` / `Repository.kt` (lectura de feeds), `BopWorker.kt` + `Notifications.kt` (avisos), `FavoritesStore.kt`.
  - `DemoAds.kt` — anuncios AdMob **solo de demostración**, con consentimiento UMP. No generan ingresos.
  - Pruebas: `app/src/test/java/es/opoalert/app/`.
  - Versión: `versionCode` / `versionName` en `app/build.gradle.kts` (ahora 57 / 1.44.0). `applicationId` = `es.opoalert.app` (no cambiarlo).
- **Backend**: `backend/`
  - Lectores: `bop_full.py` + `history.py` (Valencia), `alicante.py`, `castellon.py`, `province_history.py`, `boe_nacional.py`, `cido_cataluna.py`, `tarragona.py`, `barcelona_bop.py`, `girona_bop.py`, `huesca_bop.py`, `teruel_bop.py`, `zaragoza_bop.py`, `cadiz_bop.py`, `pandora_bop.py` (Almería), `andalucia_opencms_bop.py` (Granada y Sevilla), `cordoba_bop.py`.
  - Validadores: `validar_*.py`, uno por fuente; `validar_feed.py` para el feed de Valencia.
  - `*_probe.py`, `probe_*.py`, `pag_*.py`, `diagnosticar_*.py`: scripts de investigación, no de producción.
  - Estado de la cobertura: `backend/ESPANA.md` y `backend/fuentes_espana.json`.
  - Pruebas: `backend/tests/`.
- **Feeds publicados**: `docs/*.json` (`convocatorias.json` es Valencia). Portada: `docs/index.html`. APK publicados: `docs/OpoAlert-X.Y.Z.apk`.
- **Workflows**: `revisar-*.yml` (diarios, publican feeds), `*-auditar.yml` / `*-pilot.yml` / `probe-*.yml` / `stage-*.yml` (pruebas y pilotos manuales), `android-apk.yml` (compila el APK), `publicar-apk-1XX.yml` (sube el APK a `docs/`), `publicar-web.yml` (despliega Pages).

## Pruebas

```
python -m unittest discover -s backend/tests -q
python scripts/test_ui_080.py
```

Para una sola fuente: `python -m unittest discover -s backend/tests -p test_cordoba_bop.py -v`.
Dependencias: `pip install -r backend/requirements.txt` (Playwright y BeautifulSoup) y `python -m playwright install chromium`. Algunos workflows instalan también `requests`. El entorno local es `.venv\` (no se sube), con Python 3.12 de `%LOCALAPPDATA%\Programs\Python\Python312`; en Windows hace falta además `tzdata` (zona horaria Europe/Madrid).

## Cómo compilar el APK

**Normalmente lo compila GitHub Actions** (`android-apk.yml`: Java 17, Gradle 8.11.1, SDK 35) al subir cambios de `app/` a `main`. El APK queda como artefacto y `publicar-apk-1XX.yml` lo copia a `docs/`.

En local: `COMPILAR_OPOALERT.bat`, o `gradlew.bat assembleDebug` desde la raíz. `gradlew.bat` descarga Gradle 8.11.1 en `.gradle-dist/`. El APK sale en `app\build\outputs\apk\debug\app-debug.apk`.
- El .bat busca Java 17 Temurin. En este PC solo hay **Temurin 21** (`C:\Program Files\Eclipse Adoptium\jdk-21.0.12.101-hotspot`): fija `JAVA_HOME` a ese y llama a `gradlew.bat` con la ruta completa. Con Java 21 compila y pasa `:app:testDebugUnitTest` (comprobado el 30/10/2026).
- SDK de Android: `%LOCALAPPDATA%\Android\Sdk` (lo escribe en `local.properties` si falta).
- **En el iMac** (desde el 30/10/2026): Temurin 17 x64 en `/Library/Java/JavaVirtualMachines/temurin-17.jdk`, SDK en `~/Library/Android/sdk` (cmdline-tools, `platforms;android-35`, `build-tools;35.0.0`, licencias aceptadas por el usuario). Compilar y probar: `JAVA_HOME=/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home sh gradlew --no-daemon :app:testDebugUnitTest assembleDebug` (`gradlew` no tiene permiso de ejecución: llamarlo con `sh`).
- No actualizar el Android Gradle Plugin (8.9.2) ni Kotlin (2.2.20) sin motivo.

## Reglas de publicación (respetarlas siempre)

1. Una fuente solo aparece en la app cuando su lector y su validador superan una **auditoría real de 30 días** (ediciones consecutivas, paginación completa, contadores, fechas y enlaces oficiales).
2. **Nunca publicar un feed parcial.** Si falla la lectura o la validación, se conserva el anterior.
3. **No inventar** plazos, vacantes, requisitos ni enlaces. Todo anuncio conserva su enlace oficial (PDF o ficha).
4. Distinguir BOP, BOE y catálogos agregados como CIDO: no son la misma fuente aunque coincidan anuncios.
5. «Candidata» no significa plaza confirmada: el filtrado es conservador y se avisa al usuario.
6. El repositorio y los datos son **públicos**: no subir claves, tokens ni datos personales.

## Feeds diarios de España (`backend/feeds_diarios.py`)

Desde la 1.34, las fuentes nuevas no llevan un workflow cada una. Todas van en el registro `SOURCES` de `backend/feeds_diarios.py` y las ejecuta **un solo workflow**, `revisar-espana.yml` (diario, 17:30 UTC; un trabajo por fuente, máximo 6 a la vez, `fail-fast: false`).

- `python backend/feeds_diarios.py run XX --out out` ejecuta el lector y lo valida. El validador común lee las reglas de la fuente de **`Province.kt`** (etiqueta, fuente, dominio y ruta del PDF, patrón de identificador), es decir, comprueba lo mismo que la app. También exige el periodo de 30 días que acaba hoy, ediciones ordenadas y sin duplicar, contadores coherentes, y rechaza el feed si trae menos de la mitad de anuncios que el publicado (lectura incompleta).
- Los lectores calculan la ventana desde `date.today()`. **Nunca fijar fechas, números de boletín ni meses en el código**: la primera y la última edición pueden caer hasta 3 días dentro de la ventana (fines de semana y festivos).
- Las fuentes del registro se ven en la app; las que aún no tienen feed diario están en `SourceCatalog.pendingDailyFeed` y se **ocultan**. `backend/tests/test_feeds_diarios.py` comprueba que registro y app coinciden.
- Las 19 fuentes antiguas (VA, AL, CS, BOE, CIDO, BOP Cataluña/Aragón/Andalucía) siguen con sus `revisar-*.yml` propios.

## Añadir una fuente nueva (lista de comprobación)

1. Lector `backend/<fuente>.py` con `--output` y ventana dinámica (ver arriba). Pruebas en `backend/tests/`.
2. Probarlo en local: `.venv\Scripts\python.exe backend\feeds_diarios.py run XX --out out` (y simular un domingo llamando a `audit(today=...)`).
3. Añadirlo a `SOURCES` en `feeds_diarios.py` y quitarlo de `SourceCatalog.pendingDailyFeed`, o crear su entrada en `Province.kt` / `SourceCatalog.territoryOf` si es nueva. Ajustar `SourceCatalogTest`.
4. Subir versión en `app/build.gradle.kts`, `android-apk.yml` y `scripts/test_ui_080.py`, y crear `publicar-apk-1XX.yml` (añadirlo también a `publicar-web.yml`).
5. Actualizar `README.md`, `backend/ESPANA.md` y `backend/fuentes_espana.json`.

## Trabajo con git (importante)

- El bot hace commits en `main` **varias veces al día** (feeds en `docs/`). **Antes de empezar: Fetch/Pull origin.** Al terminar: commit y Push enseguida.
- No modificar a mano los `docs/*.json` ni los APK de `docs/`: los generan los workflows.
- Si un Push choca, no forzarlo (`--force`): traer los cambios y resolver.
- `.gitignore` excluye `data/`, `.venv/`, `build/`, `local.properties` y `*.apk` (los APK de `docs/` se añaden con `git add -f` desde los workflows).

## Estado (30/10/2026)

- App **1.44.0** (31/10/2026): el editor de alertas usa la misma lista por comunidades que «Elegir boletines» (`SourcePicker.kt`, compartido por `MainActivity` y `AlertsActivity`) y se puede desplazar (antes no hacía scroll y no se veían todas las provincias).
- App 1.43.0 (31/10/2026): visor de PDF con zoom continuo como el de una foto (`PdfDocumentView`: pellizco desde el punto entre los dedos hasta 5×, desplazamiento con inercia en cualquier dirección y doble toque 2,5× / ancho de pantalla). Cada página se dibuja una vez al ancho de la pantalla y, al soltar, la zona visible se vuelve a dibujar a la resolución exacta (texto nítido). En el emulador, `sendevent` no consigue simular el pellizco: probarlo en el móvil.
- App 1.42.0 (31/10/2026): `res/xml/network_security_config.xml` añade la raíz pública «Sectigo Public Server Authentication Root R46» (`res/raw/sectigo_r46.pem`, SHA-256 7B:B6:47…F2:5A:06, la de Mozilla) a las del sistema: Android no la trae y sin ella no se abrían dentro de la app los PDF de BOP Alicante, BOP Girona, BOB Bizkaia, BOCCE Ceuta y BOP Segovia. La verificación de certificados sigue activada y solo se admite HTTPS.
- App 1.41.0 (31/10/2026): el PDF oficial se ve dentro de la app (`PdfViewerActivity`: descarga a la caché, `PdfRenderer`, zoom, abre en la página de `#page=N` y, si el enlace no es un PDF, lo abre fuera); la ficha ya no tiene los recuadros de plazas y plazo: el número de plazas sale como etiqueta solo si el título lo dice. Los clasificadores (`scan.py` y `provincial_common.py`) ya no cuentan como plaza de empleo «plaza de toros», «plaza de abastos» o «plazas de garaje/aparcamiento», y descartan «demanial», «venta ambulante» y «puestos de venta».
- App 1.40.0 (31/10/2026): anuncio de apertura y anuncios en la lista (identificadores de PRUEBA de Google), estructura de Premium y ficha con «Ver PDF oficial» arriba. Detalle y pasos pendientes en `PLAN_MONETIZACION_IOS.md`. La 1.39.0 (31/10/2026): icono nuevo, alertas corregidas y mejoras de pantalla. La **1.38.0** (30/10/2026): las 19 fuentes de siempre más **46 con feed diario** en `feeds_diarios.SOURCES`. La 1.38 añade a `Province.kt` Cantabria (CN), Valladolid (VD), Burgos (BU), Jaén (JA) y BOP Lleida (LE), y corrige la web de Cuenca. Las fuentes que la APK no conoce no se muestran aunque estén en `fuentes_activas.json`. La app lee de la web `fuentes_activas.json` (lo genera `publicar-web.yml`), así que **una fuente nueva aparece sin instalar otra APK**.
- **Cuatro actualizaciones al día** para todas las fuentes: 6:30, 9:30, 12:30 y 16:30 en invierno (una hora más en verano), escalonadas 5 minutos. La app 1.37.0 consulta cada hora y avisa de APK nuevas (`version.json`, generado por `feeds_diarios.py manifest` desde las APK de `docs/`).
- `revisar-bop.yml` y `revisar-provincias.yml` pasan solo las pruebas de sus lectores (desde el 31/10/2026; antes pasaban toda la batería, fallaron el 29 y el 30/10 y los feeds de Valencia, Alicante y Castellón se quedaron en el 28/10). El 31/10 Valencia volvió a fallar al guardar: el push chocaba con los commits de otros bots y `revisar-bop.yml` no reintentaba. Ahora usa el mismo bucle de 5 intentos (`fetch` + `rebase` + `push`) que los demás `revisar-*.yml`; cualquier workflow nuevo que publique en `docs/` debe llevarlo.
- **Ejecutor de casa** (`revisar-espana-casa.yml`, guía `EJECUTOR_CASA.md`, etiqueta `opoalert-casa`): lee los portales que no responden a GitHub. `feeds_diarios.HOME_ONLY` = Navarra, Asturias, Ceuta, Albacete, Cantabria, Valladolid, Burgos, Jaén, BOP Lleida y Cuenca (las siete últimas desde el 30/10/2026); `HOME_BACKUP` = La Rioja y Cáceres (también se leen en GitHub). **Instalado el 30/10/2026 en el iMac** (`iMac-de-Jordi`, carpeta `~/actions-runner`, servicio launchd del usuario, `.env` con `OPOALERT_PYTHON=~/opoalert-venv/bin/python`); primera ejecución en verde y Navarra, Asturias y Ceuta publicadas. El servicio arranca al iniciar sesión; el iMac tiene activado el inicio de sesión automático, el reposo desactivado con corriente y el arranque tras corte de luz (`pmset autorestart 1`). Si el iMac está apagado, esas fuentes no se actualizan y la app conserva el último feed.
- Asturias: en los días sin BOPA (fines de semana y festivos) el portal muestra el último boletín sin enlaces a PDF. `asturias_bopa.parse_summary` solo toma su número y su fecha, y el boletín se lee pidiéndolo por su fecha (arreglado el 31/10/2026; el sábado 31/10 falló la lectura).
- Ceuta: ids `CE-AAAA-NNN` (ordinarios) y `CE-AAAA-ENNN` (extraordinarios); `announcementsRead` = edictos leídos de los PDF.
- **Ocultas** (`pendingDailyFeed`): ninguna. Cuenca se activó el 30/10/2026 (desde casa, web `https://www.dipucuenca.es/boletin1`). Si una fuente nueva necesita ocultarse, la lista debe seguir escrita como `setOf(...)` (la lee `test_feeds_diarios.py`).
- Repositorio: en Settings → Actions está activado «Require approval for all external contributors» (protege el ejecutor de casa).
- Los validadores `validar_apk_*.py` son de la antigua instantánea privada y ya no sirven para los feeds diarios.
- Sin lector: Málaga (`https://www.bopmalaga.es/`). Comprobado desde el iMac el 31/10/2026: solo el sumario del día es público; los sumarios anteriores y todos los PDF piden Cloudflare Turnstile (no eludirlo). Opciones: acumular cada día el sumario del día (30 días hasta tener la ventana, enlaces al sumario y no al PDF) o pedir un acceso oficial a la Diputación (CEDMA). Lo decide el usuario. Burgos solo admite TLS 1.0: `burgos_bop.py` usa un adaptador con verificación de certificado y de nombre de host activadas (no quitarla). Jaén devuelve HTTP 429 si no se espera entre peticiones.
- **Cambio de año (hecho el 30/10/2026, app 1.35.0)**: los 24 lectores diarios y `Province.kt` ya no llevan el año fijo. La numeración que vuelve a 1 en enero se comprueba con `clm_common.numbering_ok`. Probado con la ventana real del 17/12/2025 al 15/01/2026: pasan todos los que admiten fechas pasadas. Palencia, Zamora y Madrid leen la lista de los últimos boletines y solo se pueden probar con la fecha de hoy. Murcia y Cádiz solo ofrecen el año en curso, así que en enero su ventana va del 1 de enero a hoy (`publish_audit(start=...)`; el validador común solo lo acepta si empieza el 1 de enero).
- **Pendiente de calendario**: `barcelona_bop.py` tiene los festivos oficiales de Cataluña de 2027 (Ordre EMT/52/2026), pero **faltan las dos fiestas locales de Barcelona de 2027**. A partir del 1/5/2027 el lector se detiene hasta que se añadan (`LOCAL_HOLIDAYS_PENDING_FROM`). En 2028 hará falta el calendario completo de ese año.
- Melilla y Canarias (ocultas) aún llevan `2026` en la dirección de la fuente de `Province.kt`: corregirlo al reescribir sus lectores.
- Workflows de investigación: el 30/10/2026 se borraron 165 `probe-*`, `diag-*`, `diagnosticar-*`, `audit-*` y `apk-privada-*` que solo se lanzaban con push a ramas `feature/*` antiguas (siguen en el historial de git). Quedan 6 porque los citan notas de `backend/*.md`. Por limpiar: `INSTRUCCIONES_GITHUB_060.txt` con la ruta antigua `C:\Users\Informatica\...`.

## Probar la app en el emulador (iMac)

- Emulador y imagen `system-images;android-34;google_apis;x86_64` en `~/Library/Android/sdk`; dispositivo `opoalert` (Pixel 6). Arrancar sin ventana: `~/Library/Android/sdk/emulator/emulator -avd opoalert -no-window -no-audio -gpu swiftshader_indirect` y esperar a `adb shell getprop sys.boot_completed` = 1. Va lento: el primer arranque puede dar «System UI isn't responding» (pulsar «Wait»).
- Instalar: `adb install -r app/build/outputs/apk/debug/app-debug.apk`; capturas con `adb exec-out screencap -p`; elementos con `adb shell uiautomator dump`.
- Probar avisos sin esperar: la imagen admite `adb root`. Quitar anuncios de `entries` y de `seen_notice_ids_v1` en `shared_prefs/opoalert_store.xml` (`run-as es.opoalert.app`), cerrar la app con `am kill` (no `force-stop`, que borra los trabajos programados), adelantar el reloj (`settings put global auto_time 0`; `date @...`) y `cmd jobscheduler run -f es.opoalert.app <n.º>`. WorkManager no adelanta un trabajo periódico antes de su hora. Al acabar, `settings put global auto_time 1`.
- El aro claro alrededor del icono en el escritorio es de las apps sugeridas del lanzador de Pixel, no del icono.

## Publicidad, Premium e iOS

Ver `PLAN_MONETIZACION_IOS.md`. Resumen:
- `DemoAds.kt`: anuncio de apertura (solo al arrancar, nunca la primera vez, máx. uno por hora, se descarta si tarda más de 5 s) y un banner cada 8 convocatorias (máx. 5). Identificadores de PRUEBA hasta que el usuario cree la cuenta de AdMob. **En España no se sirve ningún anuncio hasta publicar el mensaje del RGPD en AdMob** (el gestor UMP no tiene formulario que mostrar). Para verlos en el emulador, compilación temporal con `ConsentDebugSettings` y `DEBUG_GEOGRAPHY_OTHER` (no subirla nunca).
- `Premium.kt`: sin anuncios y alertas desbloqueadas. `BILLING_READY = false` hasta tener Google Play Billing (exige publicar en Google Play); mientras, las alertas son gratis. Las compilaciones de prueba tienen «Activar (pruebas)» en el menú.
- iOS: este iMac (2017, macOS 13) no puede usar Xcode 26, obligatorio para el App Store desde el 28/04/2026. Usar ejecutores macOS de GitHub Actions o un Mac con Apple Silicon.

## App iOS (`ios/`, desde el 31/10/2026)

- SwiftUI, iOS 16+, bundle `es.opoalert.app`, versión 1.0.0. Mismas funciones que Android, sin anuncios ni Premium. Guía: `ios/README.md`.
- `ios/OpoAlertCore/`: paquete Swift con la lógica (equivale a `Province.kt`, `RemoteFeedReader.kt`, `Repository.kt`…). Mismas claves de guardado que Android (`selected_provinces_v1`, `favorites_v2`, `keyword_alert_rules_v1`, `seen_notice_ids_v1`…).
- **`Fuentes.generated.swift` se genera desde Android** con `python scripts/generar_fuentes_ios.py`. Al cambiar `Province.kt`, `SourceCatalog.kt`, las siglas de `RemoteFeedReader.kt` o los nombres de `NoticeDetailActivity.kt`, regenerarlo: `backend/tests/test_fuentes_ios.py` y `ios-app.yml` fallan si no está al día.
- Comprobaciones: `OpoAlertChecks` (pruebas de Android portadas, revisión simulada y validación de todos los `docs/*.json`). En el iMac, SwiftPM no funciona sin Xcode: compilar con `swiftc` como dice `ios/README.md`. Las pantallas solo se compilan en `ios-app.yml` (macOS de GitHub), que guarda capturas del simulador en el artefacto `capturas-ios`.
- `ios/project.yml` es para XcodeGen; el `.xcodeproj` y el `Info.plist` se generan (están en `.gitignore`).
- Icono: `scripts/generar_icono_ios.swift` dibuja el mismo diseño que el de Android.

## Antes de dar un cambio por terminado

1. Pasar las pruebas de Python (y `scripts/test_ui_080.py` si se toca la app).
2. Si se toca la app, comprobar que compila (en local o en Actions).
3. Dejar el cambio listo para commit en GitHub Desktop y decir al usuario qué archivos han cambiado.
