# OpoAlert: lectura con control de cobertura del BOP de Valencia

**Fase de auditoría, no integrada todavía con la app Android 0.2.**

Hasta ahora la app lee el HTML de portada de `bop.dival.es`. Ese portal
puede presentar **solo una página de resultados**; la versión 0.2 no
recorre la paginación ni accede a fechas pasadas.

`bop_full.py` usa Chromium mediante Playwright para navegar como un usuario,
recorrer las páginas de la **última edición publicada** y recoger todos los
anuncios antes de filtrar los relacionados con plazas y bolsas.

## En Windows, sin Android Studio

Ejecuta desde la carpeta principal `PROBAR_LECTOR_BOP.bat`. Requiere Python 3.
El primer uso descarga un Chromium dedicado a las pruebas. No necesita
Android Studio ni que se compile un APK. Es un test del **motor**, no del móvil.

Si prefieres PowerShell:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe -m unittest discover -s backend\tests -v
.\.venv\Scripts\python.exe backend\bop_full.py --output data\convocatorias.json
```

En `data/convocatorias.json`, el campo `coverage` incluye:

- `bulletin`: número de la edición leída.
- `pagesVisited`: páginas visitadas.
- `announcementsRead`: número **total** de anuncios extraídos de esas páginas,
  incluidos anuncios que no son empleo público.
- `opportunities`: plazas o bolsas detectadas.
- `complete`: si el navegador identificó el final de la paginación.
- `status`: método de confirmación o causa de cobertura dudosa.

Si el HTML no presenta un paginador identificable, el lector **no declarará
falsamente** que ha revisado todo el boletín. Guardará diagnóstico HTML/PNG
para adaptar el lector a la web real. No se modifica el feed válido anterior.

**Nota**: `complete=true` confirma fin del paginador reconocido, pero se debe
contrastar el número total de anuncios con el sumario oficial antes de hacer
promesas de cobertura exhaustiva. El sistema clasifica por título y puede
producir falsos negativos. También hay suplementos y anuncios de nuevas
convocatorias cuyos plazos se anuncian después en el BOE.

## Ejecución gratuita en GitHub Actions (fase posterior)

`.github/workflows/revisar-bop.yml` incluye una comprobación automatizada
tres veces al día laborable. Para activarla hay que crear un repositorio
de GitHub con estos archivos, habilitar Actions y (si se quiere servir un
JSON a la app) GitHub Pages desde `/docs`. La programación puede retrasarse,
y la gratuidad depende del plan/uso de GitHub; comprobar límites actuales.

El workflow **no** modifica los datos existentes cuando la auditoría falla.
Conserva el histórico de los números de registro que haya leído en ediciones
anteriores, pero **no puede recuperar por sí solo una fecha perdida** cuando
el proceso ha estado apagado. La consulta por fechas queda para la siguiente
fase; no afirmamos que se lea ya el histórico completo del BOP.

## Datos y propiedad

Todo el código es del proyecto OpoAlert y los enlaces remiten al BOP oficial.
Antes del despliegue público hay que verificar condiciones de reutilización,
modales/cookies, límites de acceso y el resultado de la navegación real.
