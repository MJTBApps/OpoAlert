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
| SA | **Salamanca — CERRADA** | Aunque la sede BOP no responde, el espejo oficial www.lasalina.es/documentacion/bop/2026/ ofrece 22 índices PDF n.º 189–210 y los 327 originales CVE. 8 candidatas, filtradas resoluciones finales y presupuestos. Auditoría independiente: https://github.com/MJTBApps/OpoAlert/actions/runs/40900088560 . Instantánea privada para APK 1.29. |
| SG | **Segovia — CERRADA** | El calendario oficial de septiembre y octubre permite recuperar 13 ediciones consecutivas, del BOP n.º 117 (30/09) al 129 (28/10). Se comprobaron sus 13 PDF originales y los 274 anuncios de los sumarios: 14 candidatas. La auditoría independiente está aprobada: https://github.com/MJTBApps/OpoAlert/actions/runs/40897405178 . Copia únicamente en APK privada 1.28, sin actualización diaria automática. |
| VD | Valladolid | `bop.sede.diputaciondevalladolid.es` y web provincial ConnectTimeout. |
| AS | Asturias | `miprincipado.asturias.es` y `sede.asturias.es` ConnectTimeout. `www.asturias.es/bopa/` da 404, no es el índice BOPA. |
| CB | Cantabria | `boc.cantabria.es`, `boc.gobcantabria.es` y `www.cantabria.es/web/boc` ConnectTimeout. |
| NA | Navarra | `bon.navarra.es` y `www.navarra.es` ConnectTimeout. Lexnavarra normativa HTTP 200, pero no publica el sumario íntegro de los anuncios locales del BON. Tiene vigilancia específica. |
| CE | Ceuta | `www.ceuta.es/ceuta/bocce`, archivo anual jDownloads y `sede.ceuta.es` ConnectTimeout. Portales periodísticos no son fuente oficial íntegra. |

## Estado efectivo
- Fuentes nuevas verificadas en esta fase: **Segovia y Salamanca (2)**. Quedan **10** ámbitos pendientes de los 12 iniciales. Las demás fuentes con errores siguen excluidas.
- Base acumulativa vigente: **OpoAlert 1.29** con La Rioja, Segovia y Salamanca, https://github.com/MJTBApps/OpoAlert/actions/runs/40900571011/artifacts/12908917537. Las versiones 1.27 y 1.28 siguen archivadas.
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

## APK privada OpoAlert 1.28 (verificada)

- Workflow Android: https://github.com/MJTBApps/OpoAlert/actions/runs/40897857532 — **success**, todas las pruebas Kotlin y validaciones de fuentes superadas.
- Descarga ZIP: https://github.com/MJTBApps/OpoAlert/actions/runs/40897857532/artifacts/12908441114
- Dentro del ZIP: `OpoAlert-Espana-1.28.0-PRUEBA.apk`, versionCode 41, versionName 1.28.0-privada, paquete de pruebas `es.opoalert.app.melilla`.
- SHA-256 APK: `055c89643c7b68f292f78477829772020c13c6dec6e07b4f0dc53d74e444700e`.
- Archivo `assets/verified/SG.json` comprobado dentro de la APK junto con `RI.json` de La Rioja y demás fuentes anteriores. Ediciones, avisos y PDF corresponden al período 30/09-29/10/2026, **instantánea privada**, no sincronización automática.

## Cierre adicional: Salamanca BOP (29/10/2026)

- Acceso alternativo del organismo editor: https://www.lasalina.es/documentacion/bop/2026/.
- **22 índices PDF n.º 189–210** (30 septiembre–29 octubre, incluidos), con comprobación de fechas y numeración.
- **327 CVE** cotejados uno a uno con sus PDF originales; **8 posibles convocatorias** extraídas del índice oficial y cotejadas con el PDF correspondiente.
- Incluye el boletín extraordinario n.º 197 del 12 de octubre; la edición n.º 210 del 29 octubre tiene un anuncio con un PDF de 116 páginas.
- Validación independiente: https://github.com/MJTBApps/OpoAlert/actions/runs/40900088560 ; artefacto `salamanca-bop-auditado-30dias`, ID `12908991286`.
- Código: `backend/salamanca_bop.py` y `backend/validar_apk_salamanca.py`.
- En Android: `Castilla y León > Salamanca`, snapshot `assets/verified/SA.json` en APK privada 1.29, compilada y validada, sin sincronización diaria automática.

## APK 1.29 verificada

- Compilación y tests Android: **success** en https://github.com/MJTBApps/OpoAlert/actions/runs/40900571011
- Artifact ZIP (contiene `OpoAlert-Espana-1.29.0-PRUEBA.apk`): https://github.com/MJTBApps/OpoAlert/actions/runs/40900571011/artifacts/12908917537
- `applicationId=es.opoalert.app.melilla`, `versionCode=42`, `versionName=1.29.0-privada`. Instalación de prueba paralela, no Play Store.
- SHA-256 del APK: `e2ac09867a6f6f7865d8ce0425ec6be0e4ded0f1dd3eef87913ca39f2d22f891`.
- El ZIP contiene el paquete de pruebas, y la APK verificó `assets/verified/SA.json`, `SG.json`, `RI.json` y todos los archivos privados anteriores.
- **Restan diez** ámbitos territoriales de los doce que faltaban al empezar el 29/10/2026.

## Segundo ciclo de recuperación: Jaén, Málaga, Albacete y Valladolid (29/10/2026)

**Albacete y Valladolid.** Diagnóstico multi-OS https://github.com/MJTBApps/OpoAlert/actions/runs/40903633597 :
- Windows y Linux confirman `ConnectTimeout` para `bop.dipualba.es` y `bop.sede.diputaciondevalladolid.es` incluso en rutas de boletín completo; repositorios antiguos de Albacete HTTP 503 (seguridad F5), PDF alternativo 2026 HTTP 404.
- Sedes de Diputaciones sí devuelven HTTP 200, pero carecen de sumarios BOP. La ruta `www.sede.diputaciondevalladolid.es/web/guest/ov/bop` redirige a inicio de sesión. En ausencia de la serie de 30 días no publicar.
- El runner macOS está en cola; no suponer su resultado.

**Jaén.** Se han contrastado los dos archivos oficiales de Pandora, `bophistorico.dipujaen.es` y `www.dipujaen.es/hemerotecadigital`, con idéntico total (**41.781** ejemplares), fechas e IDs en las cuatro páginas finales. https://github.com/MJTBApps/OpoAlert/actions/runs/40904626611 . **No recupera los BOP #198, #199, #201**. La petición al formulario `tools/setQuery.vm` devuelve JS a `index.vm`; al seguirlo con misma sesión se muestra índice genérico de actas, sin hallar ejemplar oficial nuevo: https://github.com/MJTBApps/OpoAlert/actions/runs/40904378182 . No declarar 30 días completos.

**Málaga.** El sitio `www.bopmalaga.es` ha vuelto a responder HTTP 200 desde GitHub. Prueba: https://github.com/MJTBApps/OpoAlert/actions/runs/40904841573 . La auditoría estricta https://github.com/MJTBApps/OpoAlert/actions/runs/40904996219 verificó el BOP #188 de 30/09 y #189 de 01/10 (10 edictos, 2 posibles candidatas el 01/10); **se detuvo correctamente en 02/10 por pantalla oficial de verificación interactiva, no eludida**. El selector del servidor también puede devolver la portada del 29/10 aunque se solicite una fecha anterior; se coteja siempre `h2 time[datetime]`, número y enlace de PDF, y nunca se acepta respuesta de fecha incorrecta. No marcar Málaga completa, no publicar feed parcial. El PDF directo `verificacion.php` requiere validación humana según portal editor.

**Resultado del segundo ciclo:** 0 nuevos territorios terminados. **APK 1.29 sigue siendo la última versión validada** (Segovia, Salamanca, La Rioja y anteriores), artifact https://github.com/MJTBApps/OpoAlert/actions/runs/40900571011/artifacts/12908917537. Siguen pendientes 10 zonas.

### Auditoría Málaga con limitación de tráfico (29/10/2026)

- Para respetar el portal se añadió una pausa de **5 segundos entre consultas HTTP** en `backend/malaga_bop.py` y un corte explícito ante verificación humana.
- Ejecución: https://github.com/MJTBApps/OpoAlert/actions/runs/40905293386 . El lector pudo verificar 30/09/2026 BOP 188 (6 anuncios, 0 candidatas) y 01/10/2026 BOP 189 (10 anuncios, 2 candidatas).
- El 02/10/2026 la web devuelve `Verificación de seguridad` incluso con pausas; se detuvo, sin intentar superar la prueba. **Málaga sigue pendiente**. El validador independiente `backend/validar_apk_malaga.py` está listo, pero no se declara ejecutado ni aprobado porque no existe `MA.json` completo.
- No enviar tráfico masivo ni repetir auditorías indiscriminadas mientras el editor requiera verificación interactiva. Buscar feed/API oficial o autorización del editor antes de nuevo intento.

## Red oficial comprobada desde tres arquitecturas GitHub (29/10/2026)

Ejecución: https://github.com/MJTBApps/OpoAlert/actions/runs/40912346085 .
Los runners `ubuntu-22.04`, `ubuntu-24.04` y `ubuntu-24.04-arm` (arquitecturas x86 y ARM) muestran el mismo patrón:
- **Ceuta, Burgos, Asturias (BOPA y datos abiertos), Cantabria, Valladolid, Albacete y Navarra**: `ConnectTimeout` a los servidores oficiales comprobados.
- **Cuenca**: HTTP 403 en el acceso de boletines.
- **Jaén**: HTTP 500 en el portal BOP principal.
- **Málaga**: timeout en x86 y página de verificación humana en ARM.
- **Controles Salamanca y Segovia**: responden; Salamanca devuelve cabecera `%PDF-` de un índice original. El test no es un problema general de Internet de los runners.

Las investigaciones de nuevos dominios oficiales tampoco aportaron los PDF:
- Burgos: 10 hosts institucionales y varios números, sin acceso al BOP completo. https://github.com/MJTBApps/OpoAlert/actions/runs/40912063189
- Ceuta: portada, sede, archivo octubre y PDF oficial BOCCE n.º 6657 del 02/10 sin respuesta; `ceuta.com` no equivale al editor oficial `ceuta.es`. https://github.com/MJTBApps/OpoAlert/actions/runs/40912147384

**Sin fuentes nuevas certificadas** en esta tanda: quedan diez ámbitos pendientes; la última APK validada es la **1.29**.

### Diagnóstico portátil desde una red española

Se ha preparado una herramienta de **solo lectura** para ejecutar desde una conexión local, con el fin de diagnosticar si el bloqueo está limitado a los rangos IP de los servidores GitHub. La ejecución local **no es prueba de 30 días** ni publica nada.

- Script transparente, sin dependencias: `scripts/diagnostico_bop_local.py`
- Documentación: `backend/DIAGNOSTICO-LOCAL-BOP.md`
- Ejecución y pruebas de Windows: https://github.com/MJTBApps/OpoAlert/actions/runs/40912645131
- Ejecutable ZIP portátil compilado y probado: https://github.com/MJTBApps/OpoAlert/actions/runs/40912645131/artifacts/12914671966
- El informe se almacena solo en `Documentos/OpoAlert` del usuario y contiene exclusivamente URLs públicas, códigos HTTP y errores. No toma IP, no instala tareas ni remite datos automáticamente.
- Si aparece una fuente accesible desde Windows local, el siguiente paso será **auditar con su propio lector** el histórico oficial y los originales; no basta con un resultado verde del diagnóstico.


## Cataluña DOGC autonómico y APK privada 1.30 (29/10/2026)

- DOGC completo 30/09–29/10/2026: 23 números principales #9761–9783, 3 anexos, 20 suplementos oficiales, 46 sumarios, 2.111 documentos y 499 candidatos conservadores de empleo. No equivalen a 499 plazas abiertas.
- Fuente oficial: API del propio DOGC (calendarDOGC, summaryDOGC, documentDOGC, summarySuplement), TLS 1.2 con cadena CA validada, sumarios exhaustivos y textos originales autenticados con CVE. No se afirma que todos los PDF estén descargados.
- Auditoría con validador independiente y resultado success: https://github.com/MJTBApps/OpoAlert/actions/runs/40964593861 ; artifact cataluna-dogc-oficial-30dias (ID 12938075943).
- Nueva fuente independiente CATALUNA_DOGC, código DC, en Cataluña > Diario autonómico. El BOP provincial de Lleida continúa sin cobertura íntegra.
- APK privada 1.30.0 acumulativa con todas las fuentes anteriores y DC.json: https://github.com/MJTBApps/OpoAlert/actions/runs/40965207029/artifacts/12937217739 ; Android y validadores success en https://github.com/MJTBApps/OpoAlert/actions/runs/40965207029
- Paquete es.opoalert.app.melilla; versionCode 43; versionName 1.30.0-privada. SHA-256 APK: 9c40dcd665851c7f23ec4bab5886da11505113feabf2e4239b740a6974f3a9ab.
- No se publica feed nuevo ni se declara cubierta ninguna de las diez zonas pendientes originales (Jaén, Málaga, Albacete, Cuenca, Burgos, Valladolid, Asturias, Cantabria, Navarra y Ceuta). La copia DOGC es una instantánea privada, no sincronización automática.


## Avance nocturno con evidencias oficiales parciales (29/10/2026)

- **Se conservaron los 19 ejemplares reales de Jaén que ofrece la hemeroteca de la Diputación para 30/09–29/10/2026.** La revisión de Linux y Windows funcionó: https://github.com/MJTBApps/OpoAlert/actions/runs/40966580613 (3 originales cotejados inicialmente).
- Auditoría exhaustiva parcial de Jaén en https://github.com/MJTBApps/OpoAlert/actions/runs/40966786425; artefacto `jaen-ejemplares-originales-parciales-19` ID `12937239393` (19 fechas/IDs/URL, 18 de los 19 PDF completos verificados, con SHA256).
- **El PDF n.º 202 del 15/10/2026, 146 páginas, 18.122.770 bytes**, superaba el tope inicial de 15 MB y se cotejó aparte con un límite ajustado; fecha/número del texto original verificados y SHA256 `d09ec8fbd21737ba0e33b9b670d39e74032e4f621ddd8cba4e7a83632bca4230`. https://github.com/MJTBApps/OpoAlert/actions/runs/40967181299; artefacto `jaen-original-grande-2026-10-15` ID `12937678697`.
- **Jaén: 19/19 originales archivados actualmente verificados, faltan los números de boletín 198, 199 y 201**. La cobertura sigue INCOMPLETA (19 de las 22 ediciones que presupone el rango); no hay feed JA, no se ha modificado la APK. Los manifiestos parciales se guardan como artefactos separados; combinar los dos artefactos para reproducir la evidencia.
- Ruta alternativa oficial Albacete `https://www.dipualba.es/WebBop` detectada mediante el redirect del BOP antiguo; `WebBop`, `default.aspx` y RSS de esta ruta responden 503; la sede da 200 pero no el índice de todos los BOP. https://github.com/MJTBApps/OpoAlert/actions/runs/40966951230 . La fuente AB sigue bloqueada.
- Diagnóstico de otras zonas, con dos redes (Linux/Windows), artifact JSON por sistema operativo: https://github.com/MJTBApps/OpoAlert/actions/runs/40966580613. Las portadas 200 en Albacete, Cuenca y Navarra NO acreditan índices originales completos; el resto de hosts ensayados no recuperan boletines 2026.
- Seguimiento nocturno programado 30/10/2026, cada hora entre 00:00 y 07:00 en Europe/Madrid; usar esta sección y sus links para no repetir las descargas de 19 PDF. Enviar aviso solo por nuevo territorio COMPLETO y auditado. Informe matinal programado para las 08:00.
- Última APK acumulativa certificada: 1.30.0, https://github.com/MJTBApps/OpoAlert/actions/runs/40965207029/artifacts/12937217739 . Sin modificaciones ni nueva APK hasta fuente añadida con auditoría independiente.


### Otro método ensayado: catálogo oficial abierto de Navarra

- La API pública del Gobierno de Navarra `https://datosabiertos.navarra.es/es/api/3/action/package_search` funciona y devuelve JSON CKAN auténtico. Búsqueda de "BON" y "diario oficial" da **cero datasets de boletín**; "boletin" devuelve solo un dataset estadístico ajeno, y "Boletín Oficial de Navarra" trae coincidencias inespecíficas (toponimia, carreteras, turismo), no sumarios originales. No existe así archivo BON completo demostrado.
- Resultado y metadatos guardados: https://github.com/MJTBApps/OpoAlert/actions/runs/40967296319, artifact `navarra-catalogo-datos-abiertos-bon-parcial`. Se mantiene BON Navarra pendiente; no generar feed ni APK por una API de catálogo que solo prueba conectividad.


## Navarra BON: instantánea cerrada hasta el 29/10 y APK privada 1.31 — 30/10/2026

- El usuario ejecutó el recolector Windows desde red española y aportó dos ZIP adicionales de auditoría (`OpoAlert_auditoria_local_v2_20261030_091758.zip` y `OpoAlert_avance_navarra_20261030_091701.zip`). La auditoría contrastó con el ZIP inicial (`OpoAlert_evidencias_oficiales_20261030_081751.zip`) y comprobó SHA256 de cadena de evidencias.
- Índice editorial octubre + septiembre: **24 ediciones consecutivas BON n.º 194–217**, 30/09 a 29/10/2026; extraordinarios 202, 203 y 217. Se recuperó el BON 194 del índice oficial de septiembre, con 29 edictos sin convocatorias, omitido inicialmente al mirar solo octubre.
- **1.163 anuncios** indexados en las 24 ediciones; URLs de anuncio oficial 0..N-1 sin saltos por edición. **52 candidatas** con originales HTML del editor recuperados y con título, número y fecha cotejados. Los textos de 12 originales muy extensos se almacenaron solo hasta 40.000 caracteres, pero la ficha de origen se comprobó y los enlaces oficiales quedan en el feed.
- Filtrado conservador: 11 candidatas descartadas por tratarse de modificaciones de la OPE, propuestas de contratación, resultados, traslados o tribunal. **41 convocatorias/bolsas válidas** incluidas en `NA.json`. El texto original es `https://bon.navarra.es/es/anuncio/-/texto/2026/<numero>/<indice>`, nunca un agregador.
- Procedencia e integridad: `backend/snapshots/NA_20261029.json.gz.b64`, SHA256 de `NA.json` `e369c9fdf50cdae604d3f105acaf85145df5ae82891911dbcd702b2d4673452f`; validador independiente `backend/validar_apk_navarra.py`. Auditoría GitHub Actions **success**: https://github.com/MJTBApps/OpoAlert/actions/runs/41026179435 ; artifact `navarra-bon-auditado-30dias` ID 12963149069.
- **APK acumulativa privada OpoAlert 1.31.0** compilada y comprobada (tests de interfaz, Kotlin, validadores existentes y auditoría Navarra): https://github.com/MJTBApps/OpoAlert/actions/runs/41026314338 ; ZIP de instalación https://github.com/MJTBApps/OpoAlert/actions/runs/41026314338/artifacts/12963562341, contiene `OpoAlert-Espana-1.31.0-PRUEBA.apk`.
- `applicationId=es.opoalert.app.melilla`, `versionCode=44`, `versionName=1.31.0-privada`, SHA256 APK `3eba7b0cb4be170deb0e3934d7a3169e110f1cf379d311905cc99754650a67e3`. Se conserva toda fuente previa de 1.30 y se añade en `Comunidad Foral de Navarra > Navarra`, paquete local `assets/verified/NA.json` sin feed nuevo público.
- **Precisión temporal esencial:** se cierra el período histórico 30/09–29/10/2026, pero el BON **218 del 30/10/2026 ya está publicado**, con 67 anuncios enlazados y dos posibles candidatas (índices 35 y 36) cuyos originales NO se han cotejado. No declarar actualización automática a 30/10 ni desactivar vigilancia diaria Navarra hasta verificar originales del 218. El BOPA Asturias recuperado contiene 22 ediciones y 917 enlaces PDF oficiales, pero los PDF individuales tampoco están auditados aún.
- El BON Navarra sale de la lista de fuentes bloqueadas **para el histórico concluido hasta 29/10**. Quedan pendientes la actualización del 30/10 y las otras nueve zonas originales con bloqueo, más el BOP provincial de Lleida.
