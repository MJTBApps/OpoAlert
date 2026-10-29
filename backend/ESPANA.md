# OpoAlert España — cobertura real

Actualización: 29 de octubre de 2026.

El catálogo incluye 50 provincias y Ceuta/Melilla. Una fuente activa no
equivale a cobertura exhaustiva de todos los boletines del territorio.

## Fuentes verificadas

- Valencia, Alicante y Castellón: tres lectores de BOP provinciales, con
  comprobación del histórico móvil de 30 días.
- BOE nacional, sección II.B de oposiciones y concursos. No sustituye a
  los BOP ni a los diarios oficiales de las comunidades autónomas.
- CIDO, Diputación de Barcelona: API oficial de procesos selectivos para
  Barcelona, Girona, Lleida y Tarragona. La descarga de 30 días y la
  paginación completa se auditan. Es un catálogo de empleo municipal,
  **no la lectura exhaustiva de los cuatro BOP**. La fecha es la de
  última actualización del proceso, no necesariamente su primera convocatoria.
- BOP Tarragona, Barcelona y Girona: tres lectores independientes de CIDO,
  con 30 días auditados, acceso a los PDF originales y publicación automática.
  Se seleccionan como BOP provinciales, diferenciados de sus catálogos CIDO.
- BOP Lleida: pendiente; el portal eBOP no respondió a las pruebas técnicas,
  por lo que no puede darse por cubierto. CIDO sí proporciona procesos selectivos.

## Próximas integraciones

- Portal estatal administracion.gob.es: el buscador ofrece exportación XML
  oficial. Hay que verificar territorio, fechas y enlaces antes de activar.
- Diarios autonómicos y boletines provinciales restantes: incorporar con
  lector y calendario oficial propio. Su estado sigue pendiente hasta la
  auditoría real, nunca se presenta cobertura inventada.

## Reglas de publicación

1. Identificador estable, institución, fecha, título y enlace verificado.
2. Auditoría de 30 días, paginación completa, contadores y calendario.
3. Ante cualquier fallo se conserva el feed anterior, sin publicar parciales.
4. No inventar plazos, requisitos, vacantes ni enlaces de inscripción.
5. Distinguir BOP, BOE y catálogos agregados como CIDO.
6. OpoAlert es independiente de las Administraciones públicas.

## Tareas programadas

- revisar-bop.yml — BOP Valencia.
- revisar-provincias.yml — BOP Alicante y Castellón.
- revisar-boe.yml — BOE II.B.
- revisar-cido.yml — API CIDO, cuatro feeds de Cataluña.
- revisar-tarragona.yml — 30 días del BOP Tarragona, PDF oficial y feed separado.
- revisar-barcelona.yml, revisar-girona.yml — nuevos BOP catalanes.
- revisar-huesca.yml, revisar-teruel.yml y revisar-zaragoza.yml — fuentes provinciales de Aragón.
- revisar-cadiz.yml — BOP Cádiz con historico y PDF originales.

GitHub Actions puede retrasar ejecuciones. La app sólo consume datos
verificados desde GitHub Pages.


## Aragón — primera fuente provincial validada (28/10/2026)

- **BOP Huesca**: lector de la sede oficial `https://bop.dphuesca.es/publica/consulta-de-bops/`.
  En la auditoría de 30 días se analizaron **22 ediciones, 544 anuncios y 22 candidatos
  a convocatoria** (29/09/2026 al 28/10/2026). El sistema valida todas las páginas,
  correlación de fechas y numeración de los BOP, entidad anunciadora y PDF oficial individual.
  La exportación JSON del portal está mal formada; se consulta el HTML, no se inventan datos.
  Evidencia: https://github.com/MJTBApps/OpoAlert/actions/runs/40694818774
- **BOP Teruel**, validado el 28/10/2026: 30 días de histórico (29/09–28/10), **22 ediciones (BOP 186–207), 46 páginas, 358 anuncios y 9 candidatos**, desde `https://bender.dpteruel.es/dpt/bopt.nsf/inicio.xsp`. El buscador XPages devuelve 10 anuncios por página y puede repetir números de anuncio; OpoAlert conserva el identificador único del documento de cada anuncio. Los documentos originales son HTML íntegros del portal oficial; el PDF reside en otro servidor inaccesible desde la auditoría, por lo que no se ofrece como acceso principal. Lector y validador independiente aprobados: https://github.com/MJTBApps/OpoAlert/actions/runs/40724272627.
- **BOP Zaragoza**: auditoría superada del 29/09/2026 al 28/10/2026: **26 boletines oficiales (224–249), 750 anuncios completos, 58 candidatas y 84 PDF originales verificados**, incluidas las secciones I-VII y no oficiales. La Diputación no respondió en GitHub Actions, pero el Gobierno de Aragón proporciona los mismos edictos provinciales a través de `https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI` con `BASE=BZHT`, `SECC-C=zaragoza` y exportaciones JSON+XML. Se comprueban dos exportaciones de los 30 días completos y se coteja cada identificador, organismo, fecha y enlace PDF. Se recuperaron incluso el boletín 246 del 24/10 y los documentos cuyos caracteres escapados estaban mal formados en JSON, mediante contraste estricto con XML. Prueba: https://github.com/MJTBApps/OpoAlert/actions/runs/40729482210.
- **Lleida** continúa pendiente; la existencia de CIDO no equivale a BOP completo.

Las provincias futuras se añaden únicamente cuando su lector y sus documentos
oficiales superan auditoría real de 30 días. Los fallos nunca publican archivos parciales.

## Andalucía — BOP Cádiz incorporado (28/10/2026)

El BOP de Cádiz tiene portal oficial https://www.bopcadiz.es/ con índice completo por edición y enlace a los PDFs originales. El lector valida el calendario oficial, la correlación entre fecha HTML y PDF, los 30 días y las ediciones consecutivas, con organismo emisor, código de anuncio y enlace PDF con número de página cuando consta. **Auditoría superada: 21 boletines (188–208), 359 anuncios y 41 candidatos** del 29/09/2026 al 28/10/2026. Evidencia: https://github.com/MJTBApps/OpoAlert/actions/runs/40782858099. Almería dispone de un buscador ZK que se ha podido consultar con Playwright y aún requiere lector de histórico validado. Córdoba, Granada, Huelva, Jaén, Málaga y Sevilla pendientes de incorporación.

## Andalucía — Almería y Jaén (29/10/2026)

**Almería**, validada: 21 ediciones (BOP 189–209), 305 edictos y 61 candidatas en el intervalo 30/09–29/10/2026. Fuente oficial https://app.dipalme.org/pandora/ y PDFs individuales en app.dipalme.org/bop/services/manager/edicto/. El lector comprueba 30 días, correlación de sumario y anuncios del texto íntegro OCR facilitado por la Diputación, numeración consecutiva y PDFs. Evidencia: https://github.com/MJTBApps/OpoAlert/actions/runs/40824575998.

**Jaén pendiente**, no integrado en la APK. Su hemeroteca https://bophistorico.dipujaen.es/ es accesible, pero faltan los boletines 198, 199 y 201 de octubre de 2026 en el índice consultado; el portal bop.dipujaen.es devuelve HTTP 500 en las comprobaciones. Se ha construido un lector preliminar; es imprescindible completar los huecos y validar el histórico antes de declarar cobertura.

La expansión autónoma programada en ChatGPT ha quedado desactivada por petición del usuario. Los flujos periódicos de actualización de las fuentes ya publicadas de GitHub Actions son distintos de esa automatización de desarrollo.


## Andalucía — nuevos BOP Granada y Sevilla (29/10/2026)

Los índices publicados por las diputaciones de Granada y Sevilla permiten
consultar las 30 fechas naturales y distinguir días sin boletín mediante
numeración consecutiva y PDF oficiales de cada edición. Sus lectores verifican
el número, la fecha, el total de anuncios y el enlace PDF original de cada
candidata, y un validador independiente rechaza feeds parciales.

- **Granada**: 22 BOP, 633 anuncios de todos los tipos y 65 candidatas.
  Fuente: https://bop.dipgra.es/publica/consulta-de-bops/
- **Sevilla**: 21 BOP, 621 anuncios y 44 candidatas.
  Fuente: https://bopsevilla.dipusevilla.es/publica/consulta-de-bops/
- **Evidencia** de las dos auditorías de 30/09 a 29/10/2026:
  https://github.com/MJTBApps/OpoAlert/actions/runs/40832320045

El filtrado de empleo es conservador; candidatos no significa vacantes
confirmadas y se debe contrastar cada anuncio oficial.

**Huelva**, **Málaga** y **Jaén** aún no están activos
como fuentes independientes: Málaga tiene conexiones intermitentes desde
Actions, Huelva todavía requiere una auditoría completa de su archivo y
Jaén presenta huecos de numeración.

## Córdoba — 22 boletines y PDFs verificados (29/10/2026)

- Portal de la Diputación: https://bop.dipucordoba.es/
- Intervalo auditado: 30/09/2026 a 29/10/2026, 22 boletines con números
  consecutivos, **376 anuncios completos y 25 candidatas a convocatoria**.
- Lectura de sumario y anuncios por fecha. En el portal Next.js los
  fragmentos de HTML inicial pueden contener anuncios desconectados del
  organismo emisor; se utiliza Chromium para recuperar el DOM hidratado solo
  en los casos afectados. Las correcciones oficiales BOP-AC no se publican
  como plazas nuevas. Se comprueban sumario oficial y PDF individual.
- Auditoría independiente: https://github.com/MJTBApps/OpoAlert/actions/runs/40833433731


## Madrid — BOCM como fuente autonómica (29/10/2026)

- Fuente: https://www.bocm.es/listado-de-boletines
- Madrid es una comunidad autónoma uniprovincial, por lo que se integra el
  **BOCM** y no se inventa un BOP provincial. Contiene anuncios de la
  Administración autonómica, ayuntamientos y otros organismos.
- Se auditan los 30 días mediante el índice oficial, incluidos boletines
  extraordinarios (p.ej. 258 y 259 del 28/10/2026).
- El portal puede devolver el XML del boletín 258 al solicitar el 259. El
  lector rechaza esa inconsistencia y contrasta la edición extraordinaria
  mediante HTML oficial y metadatos JSON-LD del anuncio; comprueba el PDF
  completo de cada edición y una muestra de PDF individuales por edición.
  Todos los enlaces individuales proceden del sumario oficial, se verifican
  estructuralmente y no se inventan, aunque por límites de acceso no se
  descargan todos durante cada auditoría.
- **El BOAM municipal de Madrid no se da por cubierto**; es una fuente
  independiente que deberá tener su propio lector si se incorpora.


## Extremadura — tres fuentes auditadas, APK privada 1.18 (29/10/2026)

La comunidad autónoma se incorpora al selector territorial con **Badajoz**, **Cáceres** y **DOE** (diario autonómico). No se han publicado los feeds de esta fase en GitHub Pages ni se ha modificado la versión que ya estaba instalada en el móvil. Las tres instantáneas de 30 días se incluyen únicamente en la APK de pruebas, con identificador Android `es.opoalert.app.ext`.

- **BOP Badajoz**, fuente https://www.dip-badajoz.es/bop/: 22 boletines ordinarios del 30/09 al 29/10 de 2026, 516 anuncios y 45 candidatas a convocatoria. Incluye la edición suplementaria del 21/10 con el mismo número de BOP y los documentos PDF con prefijos de rectificación. Se comprueba identificador, organismo, fecha, archivo PDF y continuidad de números. Auditoría: https://github.com/MJTBApps/OpoAlert/actions/runs/40850935583
- **BOP Cáceres**, fuente https://bop.dip-caceres.es/bop/index.html: 22 boletines, 548 anuncios y 34 candidatas. Se utilizan los servicios JSON oficiales `/bop/services/boletines/bopMesCalendario` y `/bop/services/anuncios/anunciosAnunciantes`, incluidos los históricos de septiembre y octubre, cotejando cada PDF individual y el original completo de cada edición. Auditoría: https://github.com/MJTBApps/OpoAlert/actions/runs/40850591480
- **DOE Extremadura**, fuente https://doe.juntaex.es/: 22 ediciones (incluye la extraordinaria de 28/10), 527 anuncios y 50 candidatas. Índice oficial de 30 días, PDF completo de cada edición y PDF original de cada candidata, incluidos los documentos con identificadores alfanuméricos. Auditoría: https://github.com/MJTBApps/OpoAlert/actions/runs/40850174258

**Total:** 66 ediciones, 1.591 anuncios revisados y 129 anuncios candidatos. No equivalen a 129 plazas confirmadas; no se inventan requisitos, plazos ni enlaces de inscripción. Las instantáneas incluidas en la APK no se actualizan automáticamente, y se indica esto al usuario en el estado de la fuente. Se validan con `backend/validar_apk_ext.py` y pruebas de Android antes de distribuir la APK privada.


## Región de Murcia — BORM auditado, APK privada 1.19 (29/10/2026)

Murcia es una comunidad uniprovincial y **el BORM** es la fuente oficial que contiene tanto los anuncios de la Comunidad Autónoma como los de las entidades locales murcianas. No se duplica como BOP separado. Se incorpora al selector de la app mediante **Región de Murcia → Murcia → BORM**.

- Índice oficial de datos abiertos del BORM: https://transparencia.carm.es/rest-services/services/restFile/BORMIndice.json (contiene título, administración, anunciante, fecha, NPE, PDF original y número de boletín). Portal del original: https://www.borm.es/
- Lectura auditada: últimos 30 días, **30/09/2026–29/10/2026**; **26 ediciones, 593 anuncios y 50 coincidencias conservadoras de empleo público**. Incluye 25 BORM ordinarios (números 226–250) y el extraordinario **2 del 12/10/2026**, etiquetado internamente como 2E. Se contrasta la continuidad de los números de los boletines y el NPE con fecha, anuncio y PDF.
- Los **50 documentos candidatos** se verificaron mediante lectura del encabezado PDF de https://www.borm.es/services/anuncio/{id}/pdf; sin inventar plazas, sedes de inscripción o plazos. Una coincidencia de texto no significa necesariamente una plaza nueva.
- Auditoría satisfactoria: https://github.com/MJTBApps/OpoAlert/actions/runs/40853666976
- Fuente Android: código MU, id `MU-2026-...`; instantánea local privada y versión debug aislada `es.opoalert.app.mur`, con nombre **OpoAlert Murcia** y versión **1.19.0-privada**. Conserva las fuentes verificadas previas. No se publican estos índices en GitHub Pages ni se sustituyen las APK instaladas anteriormente. Los registros incluidos son una fotografía del 29 de octubre y no se actualizan automáticamente.

La compilación privada valida `backend/validar_apk_murcia.py`, los validadores anteriores de Extremadura, Castilla y León, Madrid, Huelva y Castilla-La Mancha, y los test unitarios Android.


## Auditoría del norte: País Vasco, Cantabria y Asturias (29/10/2026)

**País Vasco: las cuatro fuentes oficiales cubiertas (30/09/2026 a 29/10/2026).** Se han verificado los sumarios de cada boletín, identidad de organismos/anuncios, numeración y PDF original para cada posible convocatoria:

- Álava: BOTHA (https://e-s.araba.eus/BOTHA/Inicio/SGBO5001.aspx) 13 boletines del n.º 112 al 124, **301 anuncios, 13 posibles convocatorias**, incluidas carpetas de PDF alternas `pdfni`. Auditoría: https://github.com/MJTBApps/OpoAlert/actions/runs/40865396955
- Bizkaia: BOB (https://www.bizkaia.eus/es/bob) 22 ediciones del n.º 187 al 208, **700 anuncios, 55 posibles convocatorias**. Auditoría: https://github.com/MJTBApps/OpoAlert/actions/runs/40865184369
- Gipuzkoa: BOG (https://egoitza.gipuzkoa.eus/es/bog) 22 ediciones del n.º 186 al 207, **737 anuncios, 32 posibles convocatorias**, descartando las páginas de sábado/domingo sin publicación. Auditoría: https://github.com/MJTBApps/OpoAlert/actions/runs/40865028129
- País Vasco: BOPV (https://api.euskadi.eus/bopv/administrative-acts) 21 ediciones del n.º 187 al 207, **341 anuncios, 33 posibles convocatorias**. Los datos abiertos de la API solo alcanzaban al 28/10; se recuperó la edición del 29/10 (18 anuncios, seis candidatas) del RSS oficial https://www.euskadi.eus/bopv2/datos/Ultimo.xml con verificación de títulos, enlaces y PDF. Los seis registros del día 29 usan en `entity` el aviso transparente «Emisor: consultar anuncio oficial (BOPV)», porque el RSS no identifica inequívocamente al órgano emisor. Auditoría: https://github.com/MJTBApps/OpoAlert/actions/runs/40865761806

**Total País Vasco**: 78 ediciones, 2.079 anuncios y 133 coincidencias potenciales de empleo público. «Posible convocatoria» no significa 133 plazas nuevas y no se calculan fechas ni requisitos que no estén en el anuncio. Las cuatro instantáneas se empaquetan únicamente en la APK privada 1.20 «OpoAlert Euskadi», conservando los datos verificados anteriores. `applicationIdSuffix=.euskadi` evita sobrescribir la versión habitual y las de prueba. Las instantáneas no se actualizan automáticamente.

**Cantabria (BOC): bloqueada, NO auditada ni incorporada.** Fuente oficial https://boc.cantabria.es/boces/. Tanto el host canónico como los alternativos `boc.gobcantabria.es`, `www.cantabria.es` y `sede.cantabria.es` dieron tiempos de espera de conexión desde GitHub Actions, sin recuperar sumarios ni PDF. Comprobación de conectividad documentada en https://github.com/MJTBApps/OpoAlert/actions/runs/40865502697. No hay JSON verificado de 30 días ni feeds publicados.

**Asturias (BOPA): bloqueada, NO auditada ni incorporada.** Fuente oficial https://miprincipado.asturias.es/bopa/; también fallaron `sede.asturias.es` y `descargas.asturias.es` por conexión agotada. `www.asturias.es/bopa/` devolvió 404 y no constituye una fuente sustitutiva. Comprobación: https://github.com/MJTBApps/OpoAlert/actions/runs/40865502697. No hay datos de 30 días verificados ni fuente publicada. Evitar presentar títulos de motores de búsqueda o terceros como un feed oficial completo.

**Pendiente para terminar Cantabria y Asturias**: disponer de acceso HTTP verificable desde el entorno de auditoría a los sitios oficiales, recuperar los 30 días, validar todos los PDF de posibles convocatorias, añadir lectores y fuentes solo tras superar las pruebas, y emitir nueva APK privada sin cambiar la anterior. Los scripts de diagnóstico son `backend/diag_norte_2026.py` y `backend/diag_norte_alt.py`. No confundir el trabajo preparado con una fuente validada.

APK privada 1.20 **construida y probada**: https://github.com/MJTBApps/OpoAlert/actions/runs/40865936657/artifacts/12893417621 (ZIP con `OpoAlert-Euskadi-1.20.0-PRUEBA.apk`). Pruebas Android, validadores de fuentes previas y cotejo de cuatro JSON del País Vasco finalizados satisfactoriamente. SHA-256 del APK: `b647c2691a0c6ebe1b0e20948695585bab68bd8b0ced1977c755c37748591877`. La APK no incluye BOC Cantabria ni BOPA Asturias porque sus auditorías no han podido ejecutarse; no afirmar que las tres comunidades están terminadas.
