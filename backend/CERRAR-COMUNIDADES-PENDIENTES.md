# Cierre de las comunidades ya comenzadas — 29/10/2026

**Regla:** no iniciar nuevas comunidades hasta revisar los huecos de las ya tratadas. No se falsifican índices de 30 días ni se incorporan fuentes con PDF, calendario o autoría sin comprobar. Las copias de fuentes nuevas se incluyen únicamente en APK privada de pruebas y no se publican como actualizaciones diarias.

## Cierre conseguido en esta rama

- **Andalucía: BOJA autonómico**. Auditoría de todos los sumarios y secciones del 30/09 al 29/10: 21 ediciones (#190–210), 1.480 anuncios, 390 coincidencias potenciales de empleo público. PDF oficiales autenticados; disposiciones en dos PDF se comprueban completas y cuentan una sola vez. Evidencia: https://github.com/MJTBApps/OpoAlert/actions/runs/40870227064. Archivo `backend/boja_autonomico.py`, lector `ANDALUCIA_BOJA` en Android.
- **Aragón: BOA autonómico**. 21 ediciones (#190–210), 733 anuncios, 123 coincidencias, contrastando los datos abiertos oficiales completos JSON/XML y los PDF de las coincidencias. Fuente https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI con `BASE=BOLE`; no se confunde con el BOP de Zaragoza `BASE=BZHT`. Evidencia: https://github.com/MJTBApps/OpoAlert/actions/runs/40870863143. Archivo `backend/boa_autonomico.py`, lector `ARAGON_BOA` en Android.
- **APK privada acumulativa 1.22.0**: https://github.com/MJTBApps/OpoAlert/actions/runs/40870998173/artifacts/12896136979 con todas las fuentes privadas validadas anteriormente, BOA y BOJA. Paquete exclusivo `es.opoalert.app.cierre`, etiqueta `OpoAlert Cierre`, no altera los favoritos ni las notificaciones de la app habitual. Las copias son del 29/10/2026, no se actualizan automáticamente. Los dos nuevos archivos se cotejan con `backend/validar_apk_cierre.py` durante la compilación.

## Provincias pendientes por recuperar; no declarar completas

| Comunidad previamente trabajada | Fuente pendiente | Comprobación de acceso |
|---|---|---|
| Andalucía | BOP Jaén | Portal moderno `bop.dipujaen.es` HTTP 500; hemeroteca histórica responde, pero presenta huecos en números 198, 199 y 201 de octubre. Exige recuperar los originales y verificar continuidad. |
| Andalucía | BOP Málaga | Sumarios oficiales `www.bopmalaga.es` disponibles desde algunos entornos, pero el PDF oficial pasa por `verificacion.php` con Cloudflare Turnstile. No automatizar CAPTCHA ni usar PDF de terceros. |
| Castilla-La Mancha | BOP Albacete | `bop.dipualba.es` agota la conexión en Ubuntu, macOS y Windows. |
| Castilla-La Mancha | BOP Cuenca | `www.dipucuenca.es` responde HTTP 403 de filtro de acceso; no confundirlo con un boletín sin publicaciones. |
| Castilla y León | BOP Burgos | `bopbur.diputaciondeburgos.es` agota la conexión en las tres redes. |
| Castilla y León | BOP Salamanca | Archivo antiguo de `www.lasalina.es` responde, pero el calendario 2026 no tiene enlaces tras migración; la Sede `sede.diputaciondesalamanca.gob.es/BOP/` agota conexión. |
| Castilla y León | BOP Segovia | `www.dipsegovia.es/bop` devuelve doce ediciones de octubre del n.º 118 al 129 (02–28/10); falta recuperar el boletín del 30/09, n.º 117, con PDF íntegro y anuncios identificados. La navegación simple `?page=2` / `?mes=9&ano=2026` repite las doce ediciones, no sirve para demostrar cobertura histórica. |
| Castilla y León | BOP Valladolid | `bop.sede.diputaciondevalladolid.es` y web de diputación sin acceso desde tres sistemas operativos. |
| Cataluña | BOP Lleida | `ebop.diputaciolleida.cat` sin conexión desde tres sistemas operativos. CIDO proporciona algunas convocatorias pero no sustituye la lectura exhaustiva del BOP. |
| Cantabria | BOC | `boc.cantabria.es` y `boc.gobcantabria.es` sin conexión desde tres sistemas operativos. |
| Asturias | BOPA | `miprincipado.asturias.es` y `sede.asturias.es` sin conexión desde tres sistemas operativos. |

Fuentes autonómicas ya iniciadas aún pendientes: **DOGV Comunidad Valenciana** y **DOGC Cataluña**. Las páginas iniciales responden pero el portal DOGV es una SPA Angular, y el DOGC no ofrece en la primera página un índice completo de 30 días. No activar sin recuperar todas las ediciones y cotejar PDF.

El **BOAM municipal de Madrid** es una publicación diferente del BOCM y no se marca cubierta. El BOE nacional sigue siendo fuente independiente.

## Diagnósticos reproducibles

- Conectividad de 31 URLs oficiales desde tres redes: https://github.com/MJTBApps/OpoAlert/actions/runs/40869432779
- Estructuras y calendario de Segovia y archivo histórico de Salamanca: https://github.com/MJTBApps/OpoAlert/actions/runs/40869542017
- PDF de Segovia y comprobaciones de acceso a septiembre: https://github.com/MJTBApps/OpoAlert/actions/runs/40869856851
- Diagnóstico DOGV / DOGC: https://github.com/MJTBApps/OpoAlert/actions/runs/40871063130

**Estado:** el alcance provincial de España continúa siendo parcial. El desarrollo no avanza a comunidades nuevas hasta completar o documentar los obstáculos de las anteriores. Si cambia la conectividad del portal, repetir auditoría íntegra en vez de generar datos simulados.
