# OpoAlert: recuperación de las 12 zonas pendientes
**Revisión del 29/10/2026 · rama** `feature/cierre-12-zonas-20261029`, basada en APK privada 1.27 con La Rioja auditada.

## Criterio de cierre
Una zona sólo se declara cubierta si el boletín **oficial** ofrece un calendario continuo de los últimos 30 días, sus sumarios completos (incluidos los extraordinarios), títulos y organismo de cada disposición, y acceso identificable al texto original o PDF de cada candidato; además, una auditoría independiente debe validar el feed y Android debe compilar. Un HTTP 200 de una portada no es evidencia suficiente. Nunca se importa información resumida de portales privados como si fuera íntegra.

## Diagnóstico reproducible
GitHub Actions: https://github.com/MJTBApps/OpoAlert/actions/runs/40893492509
Script: `backend/cierre_12_probe.py`. Comprobó tres URL por zona, cabecera HTTP y redirecciones. **Que este diagnóstico finalice con código cero significa únicamente que pudo documentar los errores**, nunca que un territorio esté completado.

| Código | Territorio | Acceso a diario oficial y bloqueo observado |
|---|---|---|
| JA | Jaén | `bop.dipujaen.es` HTTP 500. Hemeroteca oficial `bophistorico.dipujaen.es` HTTP 200, pero faltan números 198, 199, 201 de octubre (recuperados 19 boletines de 22). Auditoría: https://github.com/MJTBApps/OpoAlert/actions/runs/40894034212 ; falla correctamente por salto 197→200. |
| MA | Málaga | `www.bopmalaga.es` ConnectTimeout desde Linux. Comprobación paralela desde macOS: https://github.com/MJTBApps/OpoAlert/actions/runs/40894056829 . El visor PDF obliga a verificación interactiva oficial. No sortearla. |
| AB | Albacete | `bop.dipualba.es` ConnectTimeout. Portada de la Diputación y sede HTTP 200, sin sumarios BOP completos. |
| CU | Cuenca | `www.dipucuenca.es` HTTP 403 (F5), inclusive ruta PDF y raíz. |
| BU | Burgos | `bopbur.diputaciondeburgos.es` y `www.burgos.es` ConnectTimeout. |
| SA | Salamanca | `sede.diputaciondesalamanca.gob.es/BOP/` ConnectTimeout; portada `www.lasalina.es` accesible, redirige a la sede bloqueada. |
| SG | **Segovia — CERRADA** | El calendario oficial de septiembre y octubre permite recuperar 13 ediciones consecutivas, del BOP n.º 117 (30/09) al 129 (28/10). Se comprobaron sus 13 PDF originales y los 274 anuncios de los sumarios: 14 candidatas. La auditoría independiente está aprobada: https://github.com/MJTBApps/OpoAlert/actions/runs/40897405178 . Copia únicamente en APK privada 1.28, sin actualización diaria automática. |
| VD | Valladolid | `bop.sede.diputaciondevalladolid.es` y web provincial ConnectTimeout. |
| AS | Asturias | `miprincipado.asturias.es` y `sede.asturias.es` ConnectTimeout. `www.asturias.es/bopa/` da 404, no es el índice BOPA. |
| CB | Cantabria | `boc.cantabria.es`, `boc.gobcantabria.es` y `www.cantabria.es/web/boc` ConnectTimeout. |
| NA | Navarra | `bon.navarra.es` y `www.navarra.es` ConnectTimeout. Lexnavarra normativa HTTP 200, pero no publica el sumario íntegro de los anuncios locales del BON. Tiene vigilancia específica. |
| CE | Ceuta | `www.ceuta.es/ceuta/bocce`, archivo anual jDownloads y `sede.ceuta.es` ConnectTimeout. Portales periodísticos no son fuente oficial íntegra. |

## Estado efectivo
- Fuentes nuevas verificadas en esta fase: **Segovia (1)**. Quedan **11** ámbitos pendientes de los 12 iniciales. Las demás fuentes con errores siguen excluidas.
- Base que funciona y conserva La Rioja: **OpoAlert 1.27**, https://github.com/MJTBApps/OpoAlert/actions/runs/40889807797/artifacts/12904466271.
- Bloqueos de red y validación externa están abiertos. Recuperar acceso oficial y **repetir auditoría entera** antes de incorporar provincias y crear nueva APK.
- La cobertura parcial procedente del BOE nacional, DOCM o BOCYL no sustituye los BOP provinciales.

## Acciones siguientes
1. Reintentar las URLs oficiales, pero sólo desencadenar integración si cambia el acceso real.
2. Consultar las sedes responsables para solicitar API, RSS oficial o descarga firmada del archivo en caso de bloqueo prolongado.
3. Completar los números 198, 199 y 201 de Jaén. El n.º 117 de Segovia ya está recuperado y sus 13 ediciones y PDF originales verificados.
4. En Málaga, usar enlaces a ficha/edicto oficiales sin automatizar CAPTCHA. Auditar todas las fechas, evitar declaración de PDF verificado si sólo se llega a verificación interactiva.
5. Ejecutar validadores independientes por cada comunidad y compilación Android acumulativa cuando haya una fuente nueva certificada.

## Cierre adicional: Segovia BOP (29/10/2026)

- **13 boletines** entre 30/09 y 28/10, n.º 117-129, recuperados del índice oficial mediante parámetros de calendario Liferay.
- **274 anuncios** revisados por el sumario original y **14 posibles convocatorias de empleo**; se excluyeron nombramientos y publicaciones de personas aprobadas.
- PDF íntegro y autoría oficial verificados en cada edición; anotación de la página concreta de cada candidato. Auditoría independiente: https://github.com/MJTBApps/OpoAlert/actions/runs/40897405178 . Código `backend/segovia_bop.py` y `backend/validar_apk_segovia.py`.
- OpoAlert 1.28: `Castilla y León > Segovia`, datos locales `assets/verified/SG.json`; no se publica como feed en GitHub Pages.
