# OpoAlert 0.8 — Empleo público, BOP Valencia

Aplicación Android nativa, gratuita, para consultar publicaciones de plazas,
oposiciones y bolsas de empleo del BOP de Valencia. El historial lo recopila y
audita automáticamente un lector Playwright que se ejecuta en GitHub Actions.

## Instalar Android

Descarga la última APK desde **Releases**:

https://github.com/MJTBApps/OpoAlert/releases/tag/v0.8.0

La app trae configurada su fuente pública; no es necesario indicar ninguna URL.
En el primer inicio Android puede solicitar permiso para avisos de nuevas convocatorias.
Puede activarse o desactivarse desde el menú de tres puntos, sin ocupar la portada.

**Aviso de instalación:** la APK descargada desde GitHub Actions es una compilación
de prueba con firma de depuración. Si la versión anterior tiene otra firma,
Android exigirá desinstalarla antes. Al desinstalar se pierden los favoritos
guardados en ese teléfono. Para distribuir futuras actualizaciones sin perder
favoritos será necesario configurar una firma privada estable.

## Interfaz v0.8

- Encabezado compacto: convocatorias recientes, favoritas, última sincronización,
  boletín y estado del histórico.
- Actualizar mediante icono correctamente alineado.
- Se muestran de inmediato Explorar, Favoritas, búsqueda, filtros y la lista.
- Las tarjetas priorizan la descripción de la plaza/bolsa y el organismo;
  el anuncio oficial completo permanece accesible al tocar la tarjeta.
- Los anuncios de trámite identificables se señalan como `TRÁMITE`.
- El usuario no configura la URL ni el filtro redundante de 30 días.

## Datos y actualizaciones

El lector diario utiliza `.github/workflows/revisar-bop.yml`, con calendario
real de publicaciones y auditoría de 30 días antes de publicar.

Feed público: https://mjtbapps.github.io/OpoAlert/convocatorias.json

La comprobación Android utiliza WorkManager aproximadamente cada seis horas,
cuando hay conexión y el sistema operativo lo permite. No es un servicio de
notificaciones instantáneas ni garantiza la hora de entrega.

El archivo oficial del BOP y, cuando proceda, el BOE son las fuentes que
determinan los requisitos y los plazos de solicitud. OpoAlert es una ayuda
para localizar anuncios, no sustituye la lectura del documento oficial.

## Desarrollo

- Código Android Kotlin: `app/src/main/`.
- Extracción Python Playwright: `backend/`.
- Pruebas del lector: `python -m unittest discover -s backend/tests -q`.
- Comprobación de interfaz: `python scripts/test_ui_080.py`.
- Build automatizado de la APK: `.github/workflows/android-apk.yml`.
- Publicación del feed: `.github/workflows/revisar-bop.yml`.

Este proyecto no incluye contraseñas, claves privadas ni datos personales de
usuarios. Los favoritos se guardan localmente en el teléfono.

## Idioma de los anuncios

El portal BOP permite pulsar **CAS** para obtener sus titulares oficiales en
castellano. Los lectores de portada y de historico seleccionan y comprueban
ese idioma antes de extraer las fichas. No se reescriben ni traducen titulos
de manera aproximada; el PDF oficial se abre con el parametro `lang=es`.

Tras actualizar el repositorio es necesario que se complete la siguiente
ejecucion verde del workflow de lectura de BOP para que los titulares del
feed publico cambien de valenciano a castellano.
