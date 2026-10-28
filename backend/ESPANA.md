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
- revisar-huesca.yml, revisar-teruel.yml — fuentes provinciales de Aragón.

GitHub Actions puede retrasar ejecuciones. La app sólo consume datos
verificados desde GitHub Pages.


## Aragón — primera fuente provincial validada (28/10/2026)

- **BOP Huesca**: lector de la sede oficial `https://bop.dphuesca.es/publica/consulta-de-bops/`.
  En la auditoría de 30 días se analizaron **22 ediciones, 544 anuncios y 22 candidatos
  a convocatoria** (29/09/2026 al 28/10/2026). El sistema valida todas las páginas,
  correlación de fechas y numeración de los BOP, entidad anunciadora y PDF oficial individual.
  La exportación JSON del portal está mal formada; se consulta el HTML, no se inventan datos.
  Evidencia: https://github.com/MJTBApps/OpoAlert/actions/runs/40694818774
- **Teruel**: el BOP oficial está en `https://bender.dpteruel.es/dpt/bopt.nsf/inicio.xsp`. Su archivo se consulta con un buscador XPages por fecha, recuperando todas las páginas de resultados (10 anuncios por página) para cada uno de los 30 días. Los anuncios individuales muestran la publicación oficial íntegra en HTML; los PDF del dominio alternativo no son accesibles desde el sistema de validación, por lo que se enlazan únicamente esos anuncios originales. Integración sujeta al resultado exitoso de la auditoría y a su posterior publicación.
- **Zaragoza**: la URL oficial de la Diputación agotó el tiempo de espera en GitHub Actions;
  investigar alternativa oficial antes de activar el feed.
- **Lleida** continúa pendiente; la existencia de CIDO no equivale a BOP completo.

Las provincias futuras se añaden únicamente cuando su lector y sus documentos
oficiales superan auditoría real de 30 días. Los fallos nunca publican archivos parciales.
