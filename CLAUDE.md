# OpoAlert — contexto del proyecto

App Android nativa (Kotlin) que muestra convocatorias de empleo público, bolsas y oposiciones sacadas de boletines oficiales (BOE, BOP provinciales y el catálogo CIDO). Proyecto gratuito e independiente de las Administraciones.

- Repositorio **público**: `https://github.com/MJTBApps/OpoAlert` (rama `main`).
- Web y descargas: `https://mjtbapps.github.io/OpoAlert/` (GitHub Pages desde `docs/`).
- Se trabaja con **GitHub Desktop** en `C:\Users\PC-02\Desktop\APP\OpoAlert`. No hay `git` en el PATH; el de GitHub Desktop está en `%LOCALAPPDATA%\GitHubDesktop\app-*\resources\app\git\cmd\git.exe`.
- El proyecto se desarrolla también con ChatGPT. Este archivo es la referencia común: si cambian las reglas, actualízalo.

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
  - Versión: `versionCode` / `versionName` en `app/build.gradle.kts` (ahora 27 / 1.14.0). `applicationId` = `es.opoalert.app` (no cambiarlo).
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

- `main` publica la **1.14.0** con 19 fuentes. La rama `integracion/espana-20261030` prepara la **1.34.0**: une el trabajo de las ramas `feature/*` de ChatGPT (APK privada 1.33) y pasa **24 fuentes nuevas** a feed diario (Madrid, Huelva, Castilla-La Mancha, Castilla y León, Extremadura, Murcia, Bizkaia, Gipuzkoa, BOPV, Galicia salvo Lugo, DOGV).
- **Ocultas hasta tener lector diario** (`pendingDailyFeed`): sus lectores tienen las fechas del 30/09–29/10 fijas o dependen de recoger datos desde un PC en España: Salamanca, Segovia, Álava, Lugo, La Rioja, Melilla, Canarias (BOC y dos BOP), Baleares, BOJA, DOGC, BOA, Navarra, Asturias y Ceuta, además de Albacete y Cuenca.
- Sin lector: Jaén (huecos en la hemeroteca), Málaga (verificación anti-robots en los PDF: no eludirla), Burgos, Valladolid, Cantabria y BOP Lleida. Muchos de estos portales **no responden desde GitHub Actions pero sí desde este PC** (IP española).
- **Cambio de año**: muchos lectores y patrones de `Province.kt` llevan `2026` fijo (rutas de PDF, identificadores). Hay que generalizarlo antes del 1/1/2027.
- La expansión autónoma programada desde ChatGPT está **desactivada** por decisión del usuario.
- Por limpiar: unos 200 workflows `probe-*`, `diag-*`, `audit-*`, `apk-privada-*` de investigación; `README.md` desactualizado; `INSTRUCCIONES_GITHUB_060.txt` con la ruta antigua `C:\Users\Informatica\...`.

## Antes de dar un cambio por terminado

1. Pasar las pruebas de Python (y `scripts/test_ui_080.py` si se toca la app).
2. Si se toca la app, comprobar que compila (en local o en Actions).
3. Dejar el cambio listo para commit en GitHub Desktop y decir al usuario qué archivos han cambiado.
