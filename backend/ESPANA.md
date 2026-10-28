# OpoAlert España — cobertura real

Actualización: 28 de octubre de 2026.

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
