# OpoAlert v0.6 — BOP Valencia automático (Android + GitHub)

OpoAlert identifica **plazas, oposiciones y bolsas de empleo público** a partir
del BOP de Valencia. Es un proyecto independiente y los anuncios deben
confirmarse siempre en el boletín oficial. La aplicación Android es nativa
(Kotlin) y mantiene los favoritos en el teléfono.

## Estado del proyecto

- **Lector del BOP 0.5.2:** se ha verificado desde un PC Windows la recuperación
  completa del 29/09 al 28/10/2026: 21 boletines, 54 páginas, 1.270 anuncios
  leídos y 50 fichas de empleo clasificadas. El archivo está en
  `docs/convocatorias.json`, como conjunto inicial de datos públicos.
- **Automatización 0.6:** dos workflows de GitHub: una publicación inicial que
  NO consulta la web, y un rastreo diario que reconstruye el histórico y SOLO
  publica si supera las auditorías. Las pruebas locales de software han pasado,
  pero **la ejecución real en los servidores de GitHub está pendiente**.
- **Android:** ya permite indicar una URL HTTPS con el botón «Fuente de datos».
  No necesita recompilarse para cambiar al feed de GitHub Pages. WorkManager
  comprueba las novedades aproximadamente cada seis horas, sujeto a las
  restricciones de Android.

## Primeros pasos

Lee **`INSTRUCCIONES_GITHUB_060.txt`**. Contiene todos los pasos: copiar el
parche en Windows, comprobar los datos, publicar el repositorio con GitHub
Desktop, activar GitHub Pages, publicar la primera captura y configurar la app.

En Windows, tras descomprimir el parche en la carpeta OpoAlert:

```bat
COMPROBAR_Y_PREPARAR_GITHUB_060.bat
```

### Flujos de GitHub

- `.github/workflows/publicar-inicial.yml`: publica el JSON de 50 anuncios ya
  auditados; útil para comprobar GitHub Pages antes de probar el rastreo web.
- `.github/workflows/revisar-bop.yml`: ejecuta diariamente el lector del último
  boletín, la búsqueda de 30 días, la validación estricta del feed, y publica
  en Pages solo si todo funciona. Se puede ejecutar manualmente en «Actions».

La revisión programada tiene lugar sobre las **09:43 UTC** cada día, sujeta
al servicio de GitHub. Esto equivale a 10:43 o 11:43 en la España peninsular,
según la época del año. **No es un sistema de alertas en tiempo real.**

### Fuente de datos de Android

Una vez publicado Pages, introduce en «Fuente de datos» una URL de este tipo:

`https://TUUSUARIO.github.io/OpoAlert/convocatorias.json`

Pulsa refrescar. La primera sincronización con un feed nuevo **no genera un
aluvión de avisos antiguos**; en las siguientes se notifican los identificadores
nuevos. Los favoritos están almacenados en el teléfono, no en GitHub.

### Seguridad y límites

- GitHub Pages con cuenta gratuita exige repositorio **público**. Los datos
  del JSON son anuncios públicos del BOP; no subas documentos privados.
- No se suben entornos `.venv`, datos de trabajo `data/` ni diagnósticos HTML
  (pueden contener información temporal de sesión del portal).
- Si falla la lectura o la validación, el paso de publicación NO se ejecuta.
  Queda el feed anterior de Pages accesible, con su antigua fecha de consulta.
- Los periodos de 30 días son calendarios, ajustados a las fechas con edición
  del BOP. El lector no declara cobertura si falta una fecha de publicación.
- La clasificación incluye modificaciones de bases o trámites de procesos
  selectivos: no todos equivalen a una convocatoria con plazo abierto.
- La app es gratuita y no depende de publicar el APK en Play Store, pero hay
  que habilitar en el teléfono la instalación del APK ya compilado.

## Arquitectura

```text
BOP de Valencia
   |
   +--> Python/Playwright (ultimo boletin + calendario de 30 dias)
              |
              +--> Auditoria de paginacion, ventanas y fechas
              |
              +--> backend/validar_feed.py (control final)
                          |
                          v
              docs/convocatorias.json en GitHub Pages
                          |
                          v
              OpoAlert Android (HTTPs / cache / favoritos / avisos)
```
