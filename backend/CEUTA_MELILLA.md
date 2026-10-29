# Ceuta y Melilla: fuentes oficiales y cierre parcial (29/10/2026)

## Melilla — verificado y empaquetado en fase APK 1.26
- Diario: **Boletín Oficial de la Ciudad Autónoma de Melilla (BOME)**, portal oficial designado por la propia Ciudad: https://bomemelilla.es/
- Histórico 30/09/2026–29/10/2026, calendario verificado en https://bomemelilla.es/bomes/2026 .
- **14 boletines** completos, **8 ordinarios n.º 6419–6426** y **6 extraordinarios n.º 43–48**; último 27/10/2026. No hubo publicación posterior identificada a la fecha de la auditoría.
- **133 artículos**, con sus 133 PDF originales individualizados CVE `BOME-A-2026-xxxx` o `BOME-AX-2026-xxx`, más los 14 PDF completos y 14 sumarios. Todos comprobaron formato PDF real y procedencia del dominio oficial.
- **16 posibles anuncios de empleo**, no equivalentes al número de plazas o inscripciones con plazo abierto. Las exclusiones del clasificador pueden dejar fuera procedimientos ya iniciados o fases de nombramiento.
- Auditoría completada: https://github.com/MJTBApps/OpoAlert/actions/runs/40879256732 . Código `backend/melilla_bome.py`, validación independiente `backend/validar_apk_melilla.py`.
- Interfaz en Android: `Ciudad Autónoma de Melilla > Melilla > BOME`. Los documentos en la ficha abren el PDF original de cada anuncio.

## Ceuta — fuente oficial inaccesible, NO marcar como cubierta
- Portal del **Boletín Oficial de la Ciudad de Ceuta (BOCCE)**: https://www.ceuta.es/ceuta/bocce y archivo del año 2026: https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1965-2026?Itemid=534
- La sede original `www.ceuta.es`, la variante `ceuta.es` y `sede.ceuta.es` fallaron por **ConnectTimeout**, incluyendo las rutas públicas de jDownloads `/component/jdownloads/finish/...`. Existen resultados de buscadores para números antiguos y medios que reproducen resúmenes recientes, pero **no sustituyen** una auditoría completa de todos los boletines y de sus PDFs oficiales originales de los 30 días.
- Se intentó el portal original por HTTPS/HTTP, dominio alternativo y puerta de entrada de la sede; las alternativas públicas de traducción/proxy tampoco ofrecen una exportación fiable de los PDF originales.
- Última verificación de accesos por plataformas heterogéneas: `.github/workflows/probe-ceuta-runners.yml`. No se publica feed ni se muestra Ceuta como fuente completada en la APK, hasta que sea posible corroborar sin huecos todas las ediciones y originales.
- Información no oficial (solo para orientar búsquedas): `https://www.elperiodicodeceuta.es/ayudas-oposiciones-ceuta/`. **Prohibido usarla como prueba de autenticidad o de integridad del archivo.**

## Límites de la versión privada
El instalador acumulativo `OpoAlert Melilla 1.26` contiene sólo fuentes que han aprobado su validación. Preserva todas las fuentes anteriores (incluidas Canarias y Baleares). El contenido BOME es una instantánea **de 29/10/2026**, no se actualiza diariamente por sí solo.

Al recuperar acceso al portal oficial de Ceuta: listar las ediciones desde el 30/09, revisar ordinarias y extraordinarias, descargar todos los PDF originales, extraer y comprobar sumarios y convocatorias, ejecutar auditoría de 30 días y solo entonces añadir un origen BOCCE a la app y generar nueva APK.
