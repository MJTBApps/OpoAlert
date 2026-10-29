# Navarra y La Rioja — OpoAlert, 29/10/2026

## La Rioja: integrada en versión privada 1.27
- Fuente oficial del Gobierno de La Rioja: API XML del BOR `https://ias1.larioja.org/boletin/ExportarBoletinServlet`.
- Especificación pública de la API: `https://ias1.larioja.org/opendata/download?r=Y2Q9MzIxfGNmPTE2` (17 páginas).
- Histórico completo: 30/09/2026–29/10/2026. **22 ediciones 188–209**, calendario oficial cotejado en septiembre y octubre.
- **524 anuncios** de todos los apartados y **26 posibles convocatorias/bolsas** según clasificador conservador. No equivale a 26 nuevas plazas con plazo abierto.
- Cada aviso se coteja contra el documento íntegro original, obtenido por `tipo=2`, verificando fecha, número, organismo, título, cuerpo HTML y referencia estable. La URL pública apunta al XML original oficial, porque el visor PDF resulta intermitente desde GitHub Actions. No se afirma que todos los PDF estén comprobados.
- Código: `backend/rioja_bor.py`, validador independiente `backend/validar_apk_rioja.py`, workflow `.github/workflows/rioja-bor-auditar.yml`.
- Evidencia: https://github.com/MJTBApps/OpoAlert/actions/runs/40889288408
- Archivo validado: `rioja-bor-oficial-30dias`, GitHub artifact ID 12903009317.
- Aplicación: `La Rioja > Diario autonómico > BOR`, archivo empaquetado `assets/verified/RI.json`. La instantánea no se actualiza sola; todavía no hay feed público automatizado.

## Navarra: pendiente, NO cubierta todavía
- Fuente oficial: `https://bon.navarra.es/es/inicio`.
- Pruebas de acceso oficiales desde Linux, Windows, macOS / varios hosts: `ConnectTimeout` para `bon.navarra.es` y `www.navarra.es`. Prueba estricta: https://github.com/MJTBApps/OpoAlert/actions/runs/40886976442
- Datos Abiertos Navarra `https://datosabiertos.navarra.es/` sí responde, pero no proporciona un conjunto equivalente a los 30 días completos del BON.
- `www.lexnavarra.navarra.es` ofrece recopilación normativa, no sumarios exhaustivos del BON ni anuncios locales.
- Índices privados como Boletín Bien / APISpain muestran información de Navarra, pero **no constituyen una auditoría del archivo oficial**: uno es un índice resumido y de suscripción, otro exige alta y clave de API. No se activan como BON íntegro.
- Enlaces a documentos y anuncios originales no se han podido comprobar. El lector BON no se declara activo, la app no mostrará datos falsamente completos.

## Condición para cerrar Navarra
Acreditar acceso fiable al calendario oficial de 30 días, todos los sumarios ordinarios/extraordinarios, títulos, identificadores de anuncios y documentos oficiales; validar independientes y sólo entonces añadir origen BON y compilar una nueva APK privada.

## Integración Android
- Branch `feature/navarra-rioja-20261029`, PR #17.
- La APK 1.27 conserva todos los orígenes privados validados de la 1.26 (Melilla, Canarias, Baleares, Galicia, País Vasco, etc.).
- No se envían anuncios parciales a GitHub Pages, no se prometen actualizaciones automáticas de las fuentes empaquetadas.
