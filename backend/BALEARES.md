# Illes Balears — BOIB oficial (29/10/2026)

## Fuente y alcance
- Portal oficial del Govern: https://www.caib.es/eboibfront/es
- Único BOIB común a **Mallorca, Menorca, Ibiza y Formentera**; incorpora también publicaciones de ayuntamientos y consejos insulares. No hay que inventar cuatro BOP provinciales por isla.
- Navegación Android: comunidad `Illes Balears`, territorio `Todas las islas`, fuente `Illes Balears (BOIB)`. No se ofrece aún un filtro individual de islas: los avisos son de cobertura regional y municipal mezclada.
- Histórico: últimos 30 días, del 30/09/2026 al 29/10/2026. La primera publicación ordinaria del intervalo ocurrió el 01/10/2026.

## Auditoría oficial realizada
- 16 ediciones numeradas correlativamente del BOIB **123 a 138**, incluidas las 3 extraordinarias **124 (01/10)**, **129 (12/10)** y **134 (21/10)**, descubiertas desde el calendario oficial `/eboibfront/es/2026/mes/9` (mes índice 0).
- Revisión de **todas las secciones publicadas** en cada número, incluidas autoridades y personal, actos administrativos, normativa, procedimientos judiciales y anuncios. No se asume que la primera sección mostrada en el índice contenga todos los avisos.
- **1.076 anuncios**, **158 posibles convocatorias de empleo**, **158 PDF oficiales originales verificados**. Son coincidencias del clasificador, no un número confirmado de plazas disponibles.
- Identificadores: `IB-2026-<numero de registro o edicto>`. URL PDF original del dominio `www.caib.es` en `/eboibfront/pdf/es/2026/<boib>/<id>` o `/eboibfront/eli/.../dof/spa/pdf`. El navegador valida host HTTPS, ruta e ID, antes de aceptar un aviso.
- Evidencia del lector y auditoría: https://github.com/MJTBApps/OpoAlert/actions/runs/40873448718 ; artefacto `baleares-boib-oficial-30dias` de fecha 29/10/2026.
- Código `backend/baleares_boib.py`, validador independiente `backend/validar_apk_baleares.py` y workflow `.github/workflows/audit-baleares-boib.yml`.

## Seguridad y actualizaciones
Las copias de los nuevos boletines se integran sólo en la **APK privada de pruebas** y no se suben a GitHub Pages como datos actualizados automáticamente. La fecha de las fuentes debe mostrarse para no inducir a confusión. Un fallo de sección, un número discontinuo, PDF que no sea PDF o contenido falso detiene la auditoría sin publicar una cobertura ficticia.

Se conserva el resto de fuentes verificadas en el instalador acumulativo, sin sustituirlo ni eliminar la aplicación habitual. El filtro de isla, los plazos exactos de inscripción y el cierre de otras provincias bloqueadas no están acreditados por esta auditoría y no se infieren.

## APK privada acumulativa 1.24.0 — comprobada

- Compilación GitHub Actions: https://github.com/MJTBApps/OpoAlert/actions/runs/40873873310 (**success**).
- Descargar ZIP con APK: https://github.com/MJTBApps/OpoAlert/actions/runs/40873873310/artifacts/12896933104
- Archivo: `OpoAlert-Baleares-1.24.0-PRUEBA.apk`; paquete `es.opoalert.app.baleares`; etiqueta `OpoAlert Baleares`.
- SHA-256 del APK: `c46800c27a91a809b6308b4cba081d1b47e7e464f193f30523a33c84c119e67a`.
- Compilación y todas las pruebas Android superadas; validadores independientes de BOIB, DOGV, BOA, BOJA, Galicia, Euskadi, Murcia, Extremadura, Castilla y León y fuentes anteriores aprobados.
- Se instala **junto a la versión anterior** (no reemplaza la aplicación OpoAlert habitual), con datos de BOIB fechados al 29/10/2026 y sin actualización automática de ese boletín.
