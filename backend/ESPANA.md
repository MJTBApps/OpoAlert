# OpoAlert España — arquitectura y despliegue progresivo

## Cobertura real (no promesas de cobertura)

El catálogo `backend/fuentes_espana.json` incluye **50 provincias y Ceuta/Melilla**.
Su función es identificar territorio, comunidad autónoma, tipo de diario y estado
de conexión. **El catálogo NO significa que el lector esté operativo**.

- `active`: fuente con 30 días auditados y feed validado. Actualmente BOP
  Valencia, Alicante y Castellón.
- `pilot`: fuente en auditoría; no se ofrece a los usuarios.
- `pending`: territorio todavía sin lector verificado.

La API oficial BOE `https://www.boe.es/datosabiertos/api/boe/sumario/{fecha}`
permite consultar la sección **II.B: Oposiciones y concursos** de ámbito estatal.
**No sustituye** a los BOP provinciales ni a los diarios oficiales de comunidades
autónomas y ciudades autónomas.

## Contrato de un lector

Cada lector debe emitir el esquema: `source`, `province`,
`lastCheckedUTC`, `coverage.complete`, `historyCoverage.complete`
(con rango diario exacto, fechas publicadas y sin publicar, números y contadores),
y `notices` (id único, title, entity, date, bulletin, type, url, province).
Los enlaces deben apuntar al sitio oficial y cada objeto debe validar
identificador, fecha, boletín y documento.

**Si una jornada falla, no publicar ningún fichero de esa fuente.**
Conservar el feed anterior y registrar el fallo. El lector de BOE de 30 días
se ejecuta primero en una rama sin publicación.

## Plan escalable

1. Verificar BOE 30 días, publicar como fuente **de ámbito estatal separada**.
2. Incorporar BOP cercanos (Tarragona, Albacete, Cuenca, Teruel, Murcia
   mediante su diario autonómico), uno a uno, con su propia auditoría.
3. Selección múltiple por comunidades y provincias únicamente para fuentes
   activadas. Guardar favoritos de manera independiente a la selección.
4. Aumentar la capacidad del feed con manifiesto de fuentes y descarga
   por lotes/comunidad autónoma, manteniendo caché y notificaciones por
   identificador estable. Evitar consultar 52 URLs en serie.
5. Asociar publicaciones relativas al mismo proceso selectivo y distinguir
   convocatorias nuevas de listas, subsanaciones y nombramientos.

No inferir plazos, vacantes, grupos ni enlaces de inscripción que no se
hayan verificado en la publicación oficial. Indicar siempre que OpoAlert
es un proyecto independiente no gubernamental.
