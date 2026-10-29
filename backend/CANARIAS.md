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
