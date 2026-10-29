# Canarias: cobertura oficial completa por las dos provincias y el BOC (29/10/2026)

## Alcance
Canarias se cubre mediante tres diarios oficiales independientes:
- **BOC autonómico**: https://www.gobiernodecanarias.org/boc/archivo/2026/ — todas las islas.
- **BOP de Las Palmas**: https://www.boplaspalmas.net/nbop2/main1.php — Gran Canaria, Fuerteventura, Lanzarote y La Graciosa.
- **BOP de Santa Cruz de Tenerife**: https://www.bopsantacruzdetenerife.es/bopsc2/main1.php — Tenerife, La Palma, La Gomera y El Hierro.

La interfaz agrupa la comunidad **Canarias** con las opciones **Las Palmas**, **Santa Cruz de Tenerife** y **Diario autonómico**. No se dispone todavía de filtros independientes para cada isla. Se incluyen los ayuntamientos y cabildos que publican oficialmente en sus BOP.

## Auditoría de 30 días, 30/09/2026–29/10/2026
- **BOC autonómico**: 22 boletines, números correlativos 196–217, incluido el extraordinario 212 (22/10/2026). 361 anuncios, 50 posibles coincidencias de empleo; 50 PDF individuales oficiales de `sede.gobiernodecanarias.org` comprobados. Auditoría: https://github.com/MJTBApps/OpoAlert/actions/runs/40876032718
- **Las Palmas**: 13 BOP provinciales numerados 117–129, 375 anuncios y 35 posibles coincidencias. Todos los PDF completos oficiales de cada edición verificados; los avisos incluyen organismo y título del sumario oficial. Auditoría: https://github.com/MJTBApps/OpoAlert/actions/runs/40876653424
- **Santa Cruz de Tenerife**: 13 BOP 117–129, 522 anuncios y 27 posibles coincidencias. El calendario abreviado de `main1.php` sólo enlaza nueve días y omite cuatro lunes (05, 12, 19 y 26/10), pero sus sumarios oficiales fechados existen, los números coinciden con la secuencia y los PDF íntegros también se verificaron. Auditoría: https://github.com/MJTBApps/OpoAlert/actions/runs/40876653424

**Total:** 48 ediciones oficiales, **1.258 anuncios** revisados y **112 posibles coincidencias de empleo**. No equivale a 112 plazas nuevas ni garantiza que todas estén con plazo abierto. El filtro de títulos no sustituye la lectura de las bases completas.

## Particularidades de la fuente
- La Junta de Canarias (BOC) publica PDF individuales identificados por BOC-A-2026-NNN-XXXX, utilizados en la ficha.
- Los BOP de Las Palmas y Tenerife publican títulos, organismos y calendario en HTML, y **un único PDF para el boletín completo**; las fichas enlazan ese documento oficial completo, no un PDF individual inexistente.
- La auditoría se detiene si faltan números o fechas, si una edición muestra un sumario vacío o si falla la comprobación real del encabezado del PDF.
- Los datos nuevos se incluyen exclusivamente en la APK privada de prueba y corresponden al día 29/10/2026. No se publican como feeds de actualización diaria. Se conservan todas las fuentes anteriormente integradas.

## Archivos
- `backend/canarias_boc.py`
- `backend/canarias_bop_provincial.py`
- `backend/validar_apk_canarias.py`
- `.github/workflows/audit-canarias-boc.yml`
- `.github/workflows/audit-canarias-bop-provincial.yml`
- `.github/workflows/apk-privada-125-canarias.yml`

## APK privada acumulativa 1.25.0 — FINAL

- Workflow con compilación Gradle y todas las pruebas Android **superadas**: https://github.com/MJTBApps/OpoAlert/actions/runs/40877069079
- Instalador dentro del ZIP: https://github.com/MJTBApps/OpoAlert/actions/runs/40877069079/artifacts/12898124310
- APK: `OpoAlert-Canarias-1.25.0-PRUEBA.apk`; package ID `es.opoalert.app.canarias`; etiqueta `OpoAlert Canarias`; versionCode 38.
- SHA-256 APK: `1b464f17fcf57a074e3a9cb24d1f988026a94f8a8d0189d1ac8a37c9c75924f9`.
- La compilación validó y empaquetó `IC.json`, `LP.json`, `TF.json`, así como `IB.json`, `DV.json`, `BJ.json`, `AO.json` y todas las copias previas verificadas. Los tests de UI, fuentes y Android finalizaron con éxito.
- La APK se instala en paralelo sin modificar OpoAlert habitual. Los datos nuevos son copias de fecha 29/10/2026; **no hay actualización diaria automática** para los tres diarios canarios.
