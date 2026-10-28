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
- BOP Tarragona: se ha desarrollado además un lector independiente
  de CIDO, auditado en piloto con 30 días completos; todavía no está
  integrado como segunda fuente de Tarragona en la app.

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

GitHub Actions puede retrasar ejecuciones. La app sólo consume datos
verificados desde GitHub Pages.
