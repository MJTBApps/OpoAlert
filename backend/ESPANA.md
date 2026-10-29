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
