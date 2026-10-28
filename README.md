# OpoAlert 1.6 — convocatorias públicas con fuentes verificadas

Aplicación nativa Android que busca convocatorias de empleo público,
bolsas y oposiciones en boletines oficiales y catálogos públicos.
Proyecto gratuito e independiente de las Administraciones públicas.

## Descargar Android

Última versión publicada: desde GitHub Pages, archivo de descarga
OpoAlert-1.6.0.apk (después de comprobar la compilación del proyecto).
Página pública: https://mjtbapps.github.io/OpoAlert/

Las compilaciones distribuidas en esta fase están firmadas para pruebas.
Si la firma no coincide con otra APK instalada, Android puede obligar a
desinstalarla primero, con pérdida de favoritos locales. No se guardan
favoritos ni alertas en un servidor.

## Fuentes disponibles en 1.5

- BOP Valencia, Alicante y Castellón — 30 días auditados.
- BOE, sección II.B Oposiciones y concursos — 30 días auditados.
- CIDO — Barcelona, Girona, Lleida y Tarragona. Catálogo público de
  procesos selectivos municipales, no lectura exhaustiva de los BOP.
- BOP Tarragona, Barcelona y Girona — anuncios provinciales y PDF originales, 30 días auditados.
  Fuente **distinta** de CIDO Tarragona; un mismo proceso puede aparecer
  publicado en ambas.

Total: 11 fuentes independientes. El archivo de catálogo mantiene las 50
provincias, Ceuta y Melilla, pero **no promete cobertura de los boletines
de todo el territorio español** hasta que se conecten y auditen. El BOE
y el buscador estatal no sustituyen los boletines locales/autonómicos.

En Android, toca el selector «Fuentes» para elegir uno o varios boletines.
La búsqueda, favoritas y alertas inteligentes usan las fuentes seguidas.
Los avisos se comprueban periódicamente según Android y la conexión.
No se garantiza notificación instantánea.

## Seguridad y calidad

- Todo anuncio conserva su enlace oficial o, en CIDO, la ficha pública
  del proceso en el catálogo de la Diputación de Barcelona.
- Cada fuente tiene validador de identificación, fechas, paginación,
  contenido y URLs. No se publica un archivo parcial si falla auditoría.
- No se inventan plazos, vacantes ni requisitos no respaldados por el
  anuncio original.
- OpoAlert no realiza trámites ni sustituye la consulta de las bases.

## Código y sincronización

- Android Kotlin: app/src/main.
- Backend Python: backend/.
- Pruebas: python -m unittest discover -s backend/tests -q.
- Pruebas UI: python scripts/test_ui_080.py.
- APK automatizada: .github/workflows/android-apk.yml.
- Publicación de feeds: revisar-bop.yml, revisar-provincias.yml,
  revisar-boe.yml, revisar-cido.yml, revisar-tarragona.yml, revisar-barcelona.yml y revisar-girona.yml.

La expansión geográfica está documentada en backend/ESPANA.md y el estado
de las fuentes se encuentra en backend/fuentes_espana.json.
