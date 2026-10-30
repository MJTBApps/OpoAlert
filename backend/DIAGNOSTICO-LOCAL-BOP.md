# Prueba de conectividad local de boletines oficiales (OpoAlert)

La APK 1.29 sigue siendo la ultima aplicacion privada auditada. Esta herramienta
permite averiguar si un servidor situado en tu conexion domestica o de trabajo
en Espana recibe los boletines que bloquean el trafico saliente de GitHub.
NO es una nueva APK, no publica convocatorias y no sustituye ninguna auditoria.

## Usar en Windows (sin instalar Python)

1. Descargar el artefacto **OpoAlert-Diagnostico-Local-Windows** de GitHub Actions.
2. Extraer el ZIP en una carpeta de confianza.
3. Revisar el codigo en `scripts/diagnostico_bop_local.py`. El ejecutable
   carece de firma comercial; si Windows lo bloquea por seguridad, NO desactivar
   las protecciones del sistema. Alternativa: ejecutar el script Python original.
4. Ejecutar el archivo `OpoAlert-Diagnostico-Local.exe`.
5. Se crean dos informes, JSON y TXT, en `Documentos/OpoAlert` del perfil Windows.
6. Compartir **solo el JSON** en esta conversacion para saber que portales
   responden desde la red local y decidir que lectores pueden auditarse.

El programa no solicita credenciales ni acceso a carpetas municipales,
no instala tareas programadas, no descubre la IP publica, no toma la ubicacion
del usuario, no abre puertos y no transmite el informe a GitHub ni a OpenAI.
Consulta exclusivamente URLs publicas de los editores oficiales.

## Usar sin EXE

Con Python 3.10+:
```bash
python scripts/diagnostico_bop_local.py
python scripts/diagnostico_bop_local.py --self-test
```

## Significado

- `pdf_reachable`: el PDF original responde en la URL oficial, pero no
  garantiza que las restantes ediciones de los ultimos 30 dias esten presentes.
- `page_reachable`: pagina publica de boletin accesible, no historico completo.
- `blocked` / `connection_error`: bloqueo o problema de red en esa URL.
- `human_verification`: el editor exige validacion humana, no se automatiza.
- `unverified`: contenido no identificado de forma segura.

Los 10 territorios pendientes en este momento son Jaen, Malaga, Albacete,
Cuenca, Burgos, Valladolid, Asturias, Cantabria, Navarra y Ceuta.
Salamanca y Segovia sirven de control de conectividad. **Nunca se activa un
territorio solo por pasar esta prueba**: se requiere la serie completa de
30 dias, los enlaces originales, auditoria independiente y compilacion Android.
