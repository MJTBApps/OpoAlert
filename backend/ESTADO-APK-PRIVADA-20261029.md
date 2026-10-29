# OpoAlert — APK privada 1.16.0 (29-10-2026)

Esta variante no se ha publicado en ninguna tienda, web ni GitHub Pages.
Se compila como `es.opoalert.app.prueba`, con nombre visible
**OpoAlert PRUEBA**, para instalarse en paralelo a la versión normal
`es.opoalert.app`. No exige desinstalar la original, por lo que evita
riesgos para sus favoritos y alertas.

## Datos auditados incluidos en la APK

Cada origen es una copia verificada del 30/09/2026 al 29/10/2026,
empaquetada como JSON en `app/src/main/assets/verified` durante la
compilación privada. NO es una fuente en vivo y NO se publica en Pages.

| Fuente | Ediciones | Anuncios leídos | Posibles convocatorias |
|---|---:|---:|---:|
| Madrid BOCM | 28 | 1907 | 316 |
| Huelva BOP | 22 | 256 | 43 |
| Ciudad Real BOP | 22 | 396 | 26 |
| Guadalajara BOP | 22 | 295 | 12 |
| Toledo BOP | 21 | 541 | 33 |
| DOCM Castilla-La Mancha | 22 | 760 | 31 |
| **Total** | **137** | **4155** | **461** |

**Pruebas y artefacto privado:** https://github.com/MJTBApps/OpoAlert/actions/runs/40843611083

**Límites:** No se incorporan ediciones futuras de estas seis fuentes
hasta crear un nuevo paquete o una sincronización verificada, y la
cifra de candidatas no equivale a plazas confirmadas.

## Bloqueos pendientes en el portal de origen

- Albacete: `https://bop.dipualba.es/` causa timeout desde
  GitHub Actions en Windows, Ubuntu y macOS; no se dispone de 30 días.
- Cuenca: `https://www.dipucuenca.es/boletin-oficial-de-la-provincia`
  devuelve HTTP 403 de su filtro de acceso (F5) en las tres redes.
- Jaén: `https://bop.dipujaen.es/` devuelve HTTP 500 y la hemeroteca
  accesible presenta huecos de números de BOP de octubre.
- Málaga: el sumario oficial se lee desde macOS enviando cabeceras de
  navegación normales, pero el portal bloquea varias solicitudes y
  `verificacion.php` exige Cloudflare Turnstile para los PDF oficiales.
  No se elude el CAPTCHA ni se fingen documentos verificados.

Ninguno de estos cuatro BOP aparece como **completo** en la APK.
Esta limitación procede de sus servidores y no se resuelve cambiando
un contador o creando archivos JSON con datos inventados.

## Reproducibilidad

El workflow `.github/workflows/apk-privada-116.yml` descarga las
seis auditorías completas de los artefactos anteriores de GitHub
Actions, las comprueba con `backend/validar_apk_privada.py`,
ejecuta pruebas Kotlin y genera un instalador privado.
La generación fallará cuando expiren los artefactos originales;
en ese caso se deberán realizar nuevas auditorías y actualizar los
identificadores de run, no utilizar datos caducados.

**Versión pública del repositorio principal:** no modificada.
