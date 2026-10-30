# OpoAlert — convocatorias públicas con fuentes verificadas

Aplicación nativa Android que busca convocatorias de empleo público,
bolsas y oposiciones en boletines oficiales y catálogos públicos.
Proyecto gratuito e independiente de las Administraciones públicas.

## Descargar Android

Página pública y última APK: https://mjtbapps.github.io/OpoAlert/

La app avisa cuando hay una APK nueva. Las fuentes nuevas aparecen sin
instalar otra APK cuando la app ya las conoce: la lista de fuentes activas
se lee de la web (`fuentes_activas.json`).

Las compilaciones distribuidas están firmadas para pruebas. Si la firma no
coincide con otra APK instalada, Android puede obligar a desinstalarla
primero, con pérdida de favoritos locales. No se guardan favoritos ni
alertas en un servidor: todo queda en el móvil.

## Fuentes

Más de 60 fuentes, cada una con su lector y validador y una auditoría de
los últimos 30 días que se repite cuatro veces al día:

- **BOE**, sección II.B Oposiciones y concursos.
- **Boletines provinciales (BOP)** de la mayoría de provincias.
- **Diarios autonómicos** (DOGV, DOGC, BOA, BOJA, DOCM, BOCYL, DOE, BORM,
  BOPV, DOG, BOIB, BOC, BOR, BON, BOPA…) y boletines de Ceuta y Melilla.
- **CIDO** (Diputación de Barcelona) para Barcelona, Girona, Lleida y
  Tarragona: catálogo de procesos selectivos municipales, **distinto del
  BOP** de cada provincia.

Algunos portales no responden a los servidores de GitHub. Esos se leen
desde un ordenador en España (el «ejecutor de casa», ver
`EJECUTOR_CASA.md`); si está apagado, esas fuentes conservan su último
feed válido.

El estado detallado de cada fuente está en `backend/fuentes_espana.json`
y `backend/ESPANA.md`. El catálogo no promete cobertura de todos los
boletines de España: una fuente solo aparece cuando su auditoría pasa.

En Android, el botón «Elegir boletines» agrupa las fuentes por comunidad
autónoma y provincia. La búsqueda, las favoritas y las alertas usan las
fuentes seguidas. Los avisos se comprueban periódicamente según Android
y la conexión; no se garantiza notificación instantánea.

## Seguridad y calidad

- Todo anuncio conserva su enlace oficial (PDF o ficha).
- Cada fuente tiene validador de identificación, fechas, paginación,
  contenido y URLs, con las mismas reglas que aplica la app. No se
  publica un archivo parcial: si falla la auditoría, se conserva el anterior.
- «Candidata» no significa plaza confirmada: el filtrado es conservador.
- No se inventan plazos, vacantes ni requisitos.
- OpoAlert no realiza trámites ni sustituye la consulta de las bases.

## Código

- Android (Kotlin): `app/src/main`.
- Backend (Python): `backend/`. Feeds diarios: `backend/feeds_diarios.py`.
- Pruebas: `python -m unittest discover -s backend/tests -q` y
  `python scripts/test_ui_080.py`.
- Workflows: `revisar-*.yml` (feeds), `android-apk.yml` (APK),
  `publicar-apk-*.yml` y `publicar-web.yml` (GitHub Pages).
