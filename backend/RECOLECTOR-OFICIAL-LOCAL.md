# Recolector de evidencias oficiales desde una conexión española

El problema identificado en el cierre nacional de OpoAlert 1.29 es que varios
editores de boletines **no responden desde las redes de GitHub Actions**. Un
servicio de seguimiento independiente informó de problemas similares para
Asturias (BOPA) y Cantabria (BOC) desde fuera de España. No se debe afirmar
que se han recuperado los datos hasta comprobar los originales.

## Archivo disponible

Workflow: `.github/workflows/recolector-bop-local-windows.yml` y
script abierto a revisión `scripts/recolector_bop_local.py`.
La acción empaqueta `OpoAlert-Recolector-Oficial.exe` para Windows.

## Uso

1. Descargar el artifact de la última ejecución satisfactoria del workflow,
   descomprimir el ZIP y ejecutar el archivo `.exe` en un equipo personal
   conectado a Internet en España. No debe utilizarse un ordenador municipal
   sin autorización.
2. El programa **no instala nada**, no pide contraseñas ni abre sesiones, no
   ejecuta código JavaScript de las páginas oficiales y no solicita
   privilegios de administrador. Visita únicamente las fuentes públicas
   permitidas. Si Windows SmartScreen alerta por ejecutable sin firma,
   no deshabilitar sus protecciones: revisar el código y ejecutar el script
   Python original es una alternativa.
3. El programa guarda el ZIP
   `Documentos/OpoAlert/OpoAlert_evidencias_oficiales_AAAAMMDD_HHMMSS.zip`.
   **No envía automáticamente** ese archivo ni hace cambios en la APK.
4. Compartir el ZIP en la conversación para analizar los sumarios y validar
   fechas, números, organismos y enlaces originales. Si una web solicita
   CAPTCHA o autenticación, no se intenta superar la verificación.

## Alcance

- Navarra: comprueba el índice del BON y su vista mensual de septiembre, extrae
  solamente enlaces al sumario oficial cuya fecha esté entre el 30/09 y el
  29/10/2026 y comprueba el número del boletín retornado. También contempla
  boletines extraordinarios si están presentes en el índice. No presupone
  que un número ausente del listado sea un día sin publicación.
- Málaga: si abre la portada del BOPMA, recopila por fecha los sumarios
  oficiales del mismo periodo, comprobando que el día mostrado coincide
  exactamente con el solicitado. Espera cinco segundos entre consultas
  y se detiene al encontrar CAPTCHA, errores de acceso o sumario de otro
  día. **No intenta descargar PDFs protegidos ni superar verificaciones.**
- Examina accesos iniciales de las 10 zonas pendientes: Jaén, Málaga,
  Albacete, Cuenca, Burgos, Valladolid, Asturias, Cantabria, Navarra y Ceuta.
- Si Asturias responde, recoge los 30 sumarios diarios oficiales del
  30/09/2026 al 29/10/2026 (incluidos fines de semana para detectar
  publicaciones extraordinarias).
- Si Burgos responde, obtiene una horquilla prudente de números de BOPBUR
  2026, que deben cotejarse con el propio calendario editorial.
- Para Cantabria y Ceuta guarda las entradas oficiales y sus enlaces
  publicados. No asume que los enlaces de la portada constituyen un
  histórico completo.
- Los documentos se reducen a **texto visible y enlaces oficiales**; los
  formularios, scripts, contraseñas, cookies y parámetros de autenticación
  se excluyen de la captura. Los PDF se identifican solo por cabecera en
  esta fase de diagnóstico y deberán auditarse después.
- Nunca se declara cobertura automática ni se generan convocatorias en
  producción con este ZIP. La integración depende de auditoría independiente
  de 30 días y compilación de una nueva APK.

## Pruebas

`python scripts/recolector_bop_local.py --self-test`
o `OpoAlert-Recolector-Oficial.exe --self-test`, sin acceso a Internet.

La herramienta se entrega sin suscripción externa y funciona sin instalar
Python en Windows, al incluirlo en el ejecutable privado generado.
