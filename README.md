# OpoAlert 1.12 — convocatorias públicas con fuentes verificadas

Aplicación nativa Android que busca convocatorias de empleo público,
bolsas y oposiciones en boletines oficiales y catálogos públicos.
Proyecto gratuito e independiente de las Administraciones públicas.

## Descargar Android

Última versión para esta rama: OpoAlert 1.12.0 con BOP Almería. La descarga pública se activará solo después de superar la compilación Android y comprobar la publicación.
Página pública: https://mjtbapps.github.io/OpoAlert/

Las compilaciones distribuidas en esta fase están firmadas para pruebas.
Si la firma no coincide con otra APK instalada, Android puede obligar a
desinstalarla primero, con pérdida de favoritos locales. No se guardan
favoritos ni alertas en un servidor.

## Fuentes incluidas en 1.12

- BOP Valencia, Alicante y Castellón — 30 días auditados.
- BOE, sección II.B Oposiciones y concursos — 30 días auditados.
- CIDO — Barcelona, Girona, Lleida y Tarragona. Catálogo público de
  procesos selectivos municipales, no lectura exhaustiva de los BOP.
- BOP Tarragona, Barcelona y Girona — anuncios provinciales y PDF originales, 30 días auditados.
  Fuente **distinta** de CIDO Tarragona; un mismo proceso puede aparecer
  publicado en ambas.

- BOP Huesca (Aragón) — 30 días y 22 ediciones auditados, 544 anuncios revisados y acceso al PDF individual oficial.

- BOP Teruel (Aragón): lector del boletín de la Diputación con anuncios individuales HTML oficiales y paginación XPages. Auditoría completa de 30 días aprobada el 28/10/2026: https://github.com/MJTBApps/OpoAlert/actions/runs/40724272627.

- BOP Zaragoza: archivo de la provincia completo a través de la exportación oficial de datos abiertos del Gobierno de Aragón (incluye todas las secciones, no solo la sexta). Descarga XML/JSON de 30 días, cotejo de anuncios y PDF originales. Auditoría de 30 días, 26 ediciones y 750 anuncios aprobada: https://github.com/MJTBApps/OpoAlert/actions/runs/40729482210.

- BOP Almería (Andalucía): 30 días auditados (30/09–29/10/2026), 21 ediciones oficiales, 305 edictos y 61 posibles convocatorias. Hemeroteca oficial de la Diputación con cotejo de códigos del sumario, OCR original y enlaces directos a PDF. Auditoría: https://github.com/MJTBApps/OpoAlert/actions/runs/40824575998.

- BOP Cádiz (Andalucía): 30 días auditados entre el 29/09 y 28/10/2026. **21 ediciones oficiales, 359 anuncios y 41 candidatas**, índice completo con fechas y organismos y enlaces directos al PDF original del BOP. Auditoría independiente: https://github.com/MJTBApps/OpoAlert/actions/runs/40782858099.

Total: 16 fuentes independientes. El archivo de catálogo mantiene las 50
provincias, Ceuta y Melilla, pero **no promete cobertura de los boletines
de todo el territorio español** hasta que se conecten y auditen. El BOE
y el buscador estatal no sustituyen los boletines locales/autonómicos.

En Android, toca el botón «Elegir boletines». Las fuentes aparecen agrupadas por comunidad autónoma y provincia; puedes desplegar cada comunidad y seleccionar BOP o CIDO por separado, además del BOE nacional.
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
  revisar-boe.yml, revisar-cido.yml, revisar-tarragona.yml, revisar-barcelona.yml, revisar-girona.yml, revisar-huesca.yml, revisar-teruel.yml, revisar-zaragoza.yml revisar-cadiz.yml y revisar-almeria.yml.

La expansión geográfica está documentada en backend/ESPANA.md y el estado
de las fuentes se encuentra en backend/fuentes_espana.json.

**Jaén** continúa pendiente. La hemeroteca oficial accesible omite los BOP 198, 199 y 201 de octubre de 2026. No está disponible como fuente en esta APK.
