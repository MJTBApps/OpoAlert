# Análisis de captura local v3 — cuatro boletines (30/10/2026)

## Procedencia

ZIP entregado por el usuario: `OpoAlert_pendientes_oficiales_v3_20261030_101035.zip`.

SHA-256: `7c49716257bb1dec55b62f3c9a22f4a8c502fc95ab8f36d8439090d2bcdfa6ec`.

Archivo interior `evidencias_pendientes_v3.json`, generado mediante `scripts/recolector_pendientes_oficiales_v3.py`. Periodo solicitado por ese programa: `2026-09-30` a `2026-10-29`. 75 consultas a los editores oficiales, 4 fuentes. Ningún resultado constituye por sí solo auditoría íntegra de 30 días.

| Código | Páginas consultadas | Índices/HTML publicados | PDFs completos leídos y SHA-256 registrado | Cobertura 30 días |
|---|---:|---:|---:|---|
| CB — Cantabria | 8 | 7 | 0 | **NO** |
| CE — Ceuta | 21 | 20 | 1 | **NO** |
| VD — Valladolid | 22 | 3 | 18 | **NO** |
| CL — Lleida BOP | 24 | 3 | 20 | **NO** |

## Evidencias concretas y limitaciones

**Lleida**: el verdadero editor `https://ebop.diputaciolleida.cat/bop/` funciona desde la conexión española del usuario. El índice devuelto contiene `Bop número: 208/0 - 30/10/2026` y enlaces a PDFs oficiales `/aplicacions/bop/bopV1/fitxers/pdf/2026/208/2026208....pdf`; 20 ficheros se descargaron íntegros y registraron hash. Son del **30 de octubre (fuera del periodo 30/09–29/10)**. La búsqueda histórica oficial se encuentra en `/bop/cerca`. Pendiente consultar 30 días, índices íntegros y originales, posibles suplementos.

**Valladolid**: la web del editor `https://bop.sede.diputaciondevalladolid.es/ultimobop` proporciona el último BOP `2026/209, 30/10/2026` y enlaces a boletín íntegro, sumario, certificado y PDFs originales. Se capturaron **18 PDF íntegros**, todos **30/10**, también fuera del periodo anterior. Portada `/calendario` describe el archivo histórico pero el HTML del recolector v3 no tiene el listado de fechas. Buscar acceso desde `/historico-bop` o formulario/calen­ dario oficial; nunca deducir retrospectivamente fechas/números sin cotejar PDF.

**Ceuta**: acceso a `https://www.ceuta.es/ceuta/bocce`, archivo `/component/jdownloads/viewcategory/1982-octubre?Itemid=534` y septiembre REAL `/viewcategory/1980-septiembre?Itemid=534`. El ID `1981-septiembre` del seed v3 era incorrecto y redirige al inicio. En las páginas aparece el último grupo de **cinco** BOCCE: ordinario #6665 30/10, extraordinario #51 28/10, ordinario #6664 27/10, ordinario #6663 23/10 y extraordinario #50 22/10. Desde `/component/jdownloads/viewdownload/1982/{id}` se accede a fichas con enlaces públicos `/component/jdownloads/finish/1982-octubre/{id}-{slug}` a originales, todos del mismo editor. Solo se capturó íntegramente PDF BOCCE **#6665 del 30/10**, 730.571 bytes, SHA `1a689333667a8eb84a2e890df6c4f7fbdb03744ad450367d2e23f16f3e579e2e`; también fuera de ventana 30/09–29/10. No afirmar íntegra la secuencia de septiembre/octubre por solo cinco entradas del sidebar. Se preparó `scripts/ceuta_bocce_originales_local_v4.py` para la lectura controlada de los documentos públicos numerados, originales y extraordinarios, con check de fecha y PDF, guardado de progreso y exclusión de acceso privado.

**Cantabria**: `https://boc.cantabria.es/boces/` y `/descargaBoletines.do` responden HTML 200 desde España; la búsqueda requiere formulario público `POST /boces/boletines.do` con `boletinBean.fecBolString`, `boletinBean.numBolString` y `boletinBean.tipoBol`. Para índices existe formulario `POST /boces/descargaBoletines.do` con `anyo`, `mes`, `formato`. Las llamadas GET inventadas de fechas devuelven formulario con aviso de parámetros y NO el boletín solicitado. 0 PDF original. Se requiere reproducir **el formulario público**, sin sesiones ni controles humanos.

## Estado de distribución

Última APK pública NO PUBLICADA: privada OpoAlert 1.32.0, build https://github.com/MJTBApps/OpoAlert/actions/runs/41028871921, validada y acumulativa.

**No crear fuente nueva, no generar APK 1.33, ni marcar ninguna de estas cuatro como cerrada con este ZIP.**

El siguiente paso es obtener originales por 30 días en cada editor y ejecutar un validador independiente. Para Ceuta existe el scanner local v4; comprobar su run de GitHub antes de facilitar ejecutable.


## Auditor local Ceuta v4 verificado

- **Workflow GitHub Actions confirmado `success`**: https://github.com/MJTBApps/OpoAlert/actions/runs/41032538936, tests Python Linux y executable Python incluido en Windows con `--self-test` superados.
- ZIP artefacto: https://github.com/MJTBApps/OpoAlert/actions/runs/41032538936/artifacts/12966127101, contiene `OpoAlert-Ceuta-BOCCE-v4.exe`, tamaño ~10 MB.
- Funcionamiento: detectar IDs oficiales de publicación vistos en el ZIP v3, consultar un máximo limitado de IDs de fichas públicas `viewdownload`, incluir octubre y septiembre, recuperar sus enlaces reales `finish` a PDF, calcular SHA256, verificar cabecera fecha/número, extraer páginas y fragmentos de posibles anuncios de empleo y guardar checkpoints ZIP locales.
- Ejecutar solamente en ordenador personal autorizado y con conexión en la que funcione el editor `www.ceuta.es`. Reutiliza automáticamente el ZIP anterior `OpoAlert_pendientes_oficiales_v3_*.zip` desde `Documentos/OpoAlert`; guarda `OpoAlert_Ceuta_BOCCE_originales_v4_*.zip` en la misma carpeta. No se requiere repetir las cuatro fuentes ni instalar Python.
- **El éxito de GitHub certifica las pruebas del programa y su empaquetado, NO que las ediciones de Ceuta estén recuperadas.** Falta que el programa descargue los originales desde la conexión española y validar el histórico y los extraordinarios independientemente antes de crear APK 1.33.
