# OpoAlert — cierre técnico de ocho fuentes provinciales (29/10/2026)

Esta rama continúa `feature/cierre-10-recolector-navarra-20261029` sin tocar la APK privada 1.29.
La auditoría de las fuentes de esta nota **NO está completa**: las pruebas de
conectividad no son una auditoría de 30 días y nunca activan fuentes.

## Pruebas ejecutadas

- Linux y Windows: https://github.com/MJTBApps/OpoAlert/actions/runs/40941368959
- Exploración de enlaces internos de la sede de Albacete:
  https://github.com/MJTBApps/OpoAlert/actions/runs/40941569893
- Espejo PDF directo de Albacete:
  https://github.com/MJTBApps/OpoAlert/actions/runs/40941715465

Las pruebas de código y ejecución terminaron con éxito. Ese «success» solo
significa que los diagnósticos se completaron; no que los BOP estén completos.

| Zona | Comprobación estricta de acceso | Cobertura |
|---|---|---|
| Jaén | Portal directo y calendario HTTP 500. Hemeroteca oficial HTTP 200; persisten huecos BOP #198, #199 y #201. | No auditada |
| Albacete | BOP directo ConnectTimeout; sede HTTPS 200, pero enlaza a BOP inaccesible. | No auditada |
| Cuenca | Portada y ruta del BOP HTTP 403. | No auditada |
| Burgos | Archivo BOP y portal de Diputación no responden. | No auditada |
| Valladolid | Calendario y último BOP no responden. | No auditada |
| Asturias | Portada BOPA y las rutas candidatas del archivo de datos abiertos 2026 no responden. No se acredita que exista el dataset 2026. | No auditada |
| Cantabria | Portada y prueba de documento oficial no responden. | No auditada |
| Ceuta | Portal BOCCE, archivo 2026 y sección documental no responden. | No auditada |

## Hallazgo sobre los PDF originales de Albacete

La sede HTTPS de la Diputación sí es accesible pero solo ofrece como enlace BOP
`https://bop.dipualba.es/`, que sigue sin responder. Se ha identificado
un archivo estático histórico del propio editor
(`https://www.dipualba.es/bop/ficheros/`).
El PDF oficial del número 106 de 2025 devuelve **HTTP 200 y cabecera %PDF-**,
lo que valida la accesibilidad al archivo antiguo.

Con los boletines de 2026 que se pueden fechar por referencias del BOE
(#114 del 30 de septiembre, #116 del 5 de octubre y #117 del 7 de octubre)
se han probado las rutas equivalentes del archivo antiguo:
**HTTP 404 en las tres**, también en la página 4 del n.º 117.
Por tanto, no es defendible afirmar que el archivo de 2025 conserva
necesariamente el histórico de 2026.

## Requisitos antes de declarar la fuente activa

1. Obtener de su propio editor la serie oficial de fechas, incluidos
   extraordinarios, y la totalidad de los sumarios de los 30 días.
2. Contrastar títulos, organismos e identificadores con originales y
   comprobar que no hay días o números omitidos.
3. Pasar el validador independiente y las pruebas Android.
4. Incorporar únicamente la fuente que supere el proceso, sin mezclar
   datos parciales, índices privados ni capturas del buscador.

**Resultado actual:** cero fuentes nuevas certificadas en estas ocho zonas.
No se ha generado una APK ni se han cambiado los feeds de producción.
