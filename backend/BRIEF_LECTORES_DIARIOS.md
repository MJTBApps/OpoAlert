# Encargo: convertir un lector de instantánea en lector diario

Proyecto: `C:\Users\PC-02\Desktop\APP\OpoAlert` (lee primero `CLAUDE.md`, sección «Feeds diarios de España»).
Python: `C:\Users\PC-02\Desktop\APP\OpoAlert\.venv\Scripts\python.exe` (ya tiene requests, bs4, pymupdf, pypdf, defusedxml, tzdata, playwright).
Ejecuta los scripts con la carpeta `backend` como directorio de trabajo, o con `sys.path` apuntando a ella.

## Qué hay que conseguir
Los lectores asignados se escribieron para una instantánea fija (30/09–29/10/2026) y tienen fechas, meses, rangos de números de boletín o recuentos esperados escritos a mano. Hay que dejarlos funcionando **cualquier día**:

1. `audit(today=None)` con `end = today or date.today()` y la ventana `end-29 … end`; CLI `--output FICHERO`. Sin fechas, años, meses ni números de boletín fijos.
2. Fines de semana y festivos: la primera y la última edición pueden caer hasta 3 días dentro de la ventana.
3. Cambio de año: la numeración vuelve a 1 en enero (usa `clm_common.numbering_ok([(fecha, número), ...])`). Los anuncios pueden llevar el año de registro anterior (o el siguiente a final de diciembre). Si el calendario del portal es mensual o anual, pide los meses o años que toque. Solo si el portal de verdad no ofrece el año anterior, la ventana de enero empieza el 1 de enero: `clm_common.publish_audit(..., start=date(end.year,1,1))` (ver `murcia_borm.py`).
4. Mínimos de ediciones compatibles con la Navidad (unas 15 en 30 días para diarios de lunes a viernes; menos para boletines de 2-3 días por semana).
5. Salida en el formato de `clm_common.publish_audit` (schemaVersion 1, coverage, historyCoverage, notices). Las reglas de la app están en `app/src/main/java/es/opoalert/app/Province.kt` (busca tu código): `province` = etiqueta, `source` = expectedSource **exacto**, enlaces `https` al host oficial con la ruta que empieza por el prefijo, `id` que encaje en el Regex.
6. **Nunca inventar datos ni publicar parciales**: si algo no cuadra, el lector falla (excepción). Sé respetuoso con los portales: como mucho 3 hilos a la vez, timeouts y reintentos moderados.

## Cómo probar (obligatorio, contra los portales reales)
```python
import sys,json; sys.path.insert(0,r"C:\Users\PC-02\Desktop\APP\OpoAlert\backend")
from datetime import date; import feeds_diarios as fd
fd.SOURCES["XX"]=("tu_lector.py",[],"nombre_feed.json")   # nombre de Province.kt feedUrl
data=modulo.audit(today=date(...)); open(f,"w",encoding="utf-8").write(json.dumps(data,ensure_ascii=False))
print(fd.validate("XX",f,today=date(...)))
```
Prueba con: hoy (`date.today()`), `date(2026,10,15)` (cruce de mes) y `date(2026,1,15)` (cruce de año, ventana 17/12/2025–15/01/2026). Si el portal no permite consultar fechas pasadas, dilo y explica por qué la lógica es correcta para enero.
Ejecuta también `python -m unittest discover -s backend/tests -q`: no puede romperse nada.

## Límites
- Edita **solo** tus lectores y sus pruebas (`backend/tests/test_<lector>.py`, si existen o los creas). Puedes leer cualquier archivo.
- **No edites** archivos compartidos (`clm_common.py`, `provincial_common.py`, `galicia_common.py`, `zaragoza_bop.py`, `feeds_diarios.py`, `Province.kt`, `SourceCatalog.kt`, workflows). Si necesitas un cambio en uno de ellos, descríbelo exacto en tu informe.
- No hagas commits ni uses git para cambiar ramas.
- En Windows PowerShell 5.1 no edites archivos con Get-Content/Set-Content: estropea los acentos. Usa la herramienta de edición.

## Informe final (breve)
Para cada lector: archivos cambiados, resultado de las 3 fechas (ediciones, anuncios y candidatas, o el error), la línea para `SOURCES` (`"XX":("lector.py",[args],"feed.json")`), cambios necesarios en archivos compartidos y cualquier límite real del portal.
