# Play Console: respuestas para OpoAlert

Para rellenar en **Panel → Configura tu aplicación** (sección «Contenido de la aplicación»).
Comprueba siempre que lo que marcas sigue siendo cierto si la app cambia.

## 1. Política de privacidad

`https://mjtbapps.github.io/OpoAlert/privacidad.html`

## 2. Acceso a la aplicación

**Toda la funcionalidad está disponible sin restricciones de acceso especiales.**
(No hay inicio de sesión. Premium se compra con Google Play.)

## 3. Anuncios

**Sí, mi aplicación contiene anuncios.**

## 4. Clasificación de contenido (cuestionario IARC)

- Correo: mjtbapps@gmail.com
- Categoría: **«Todas las demás categorías de aplicaciones»** (no es un juego ni red social).
- Violencia, sexo, lenguaje malsonante, drogas, alcohol, tabaco, apuestas: **No** a todo.
- ¿Los usuarios pueden interactuar o intercambiar contenido entre ellos? **No.**
- ¿Comparte la ubicación del usuario con otros usuarios? **No.**
- ¿Permite comprar productos digitales? **Sí** (suscripción Premium).
- ¿Es un navegador web o buscador general? **No.**

Resultado esperado: apto para todos los públicos (PEGI 3 o similar).

## 5. Público objetivo

- Edades: **18 años o más** (solo esa casilla).
  Así la app no entra en el programa de familias, que tiene normas muy estrictas para la publicidad.
- ¿Podría atraer a niños sin querer? **No.**

## 6. Apps de noticias / gubernamentales / financieras / salud

- ¿Es una app de noticias? **No.**
- ¿Es una app gubernamental o representa a un organismo público? **No.**
  (En la descripción ya dice que no es oficial y cita las fuentes.)
- Funciones financieras: **ninguna.** Salud: **ninguna.**

## 7. Seguridad de los datos

OpoAlert en sí no recoge datos personales, pero el **SDK de anuncios de Google (AdMob)** sí.
Lo que se declara es lo que recoge AdMob. **Antes de enviar, compáralo con la guía oficial de
Google**, por si ha cambiado: busca «Google Mobile Ads SDK data disclosure» en la ayuda de AdMob.

- ¿Recoge o comparte la app alguno de los tipos de datos de usuario obligatorios? **Sí.**
- ¿Todos los datos se cifran en tránsito? **Sí.**
- ¿Ofreces una forma de solicitar la eliminación de datos? **Sí**: correo mjtbapps@gmail.com
  (y desinstalar la app borra todo lo guardado en el móvil).

Tipos de datos a marcar (recogidos por AdMob):

| Tipo | Recogido | Compartido | ¿Obligatorio? | Finalidad |
|---|---|---|---|---|
| Ubicación aproximada (por la IP) | Sí | Sí | Obligatorio | Publicidad, prevención de fraude |
| ID de dispositivo u otros identificadores (ID de publicidad) | Sí | Sí | Obligatorio | Publicidad, analíticas, prevención de fraude |
| Actividad en la app: interacciones con la app (con los anuncios) | Sí | Sí | Obligatorio | Publicidad, analíticas |
| Información y rendimiento de la app: registros de fallos y diagnóstico | Sí | Sí | Obligatorio | Analíticas, prevención de fraude |

**No** se marcan: nombre, correo, contactos, ubicación precisa, fotos, mensajes, búsquedas,
información financiera ni de pago (los pagos los gestiona Google Play, no la app).

## 8. Categoría y datos de contacto (Presencia en Google Play → Ajustes de la ficha)

- Tipo: Aplicación · Categoría: **Empresa**
- Correo: mjtbapps@gmail.com · Web: https://mjtbapps.github.io/OpoAlert/

## 9. Países

Para empezar, **solo España** (los boletines y los textos son de España).

---

# Suscripción OpoAlert Premium (Monetizar → Productos → Suscripciones)

Necesita el **perfil de pagos** creado (Configuración → Perfil de pagos) y la app subida
al menos una vez a una pista de prueba. Los identificadores deben ser **exactamente** estos,
porque la app los busca así:

1. **Crear suscripción**
   - ID del producto: **`opoalert_premium`**
   - Nombre: **OpoAlert Premium**
2. **Plan base** → Añadir plan base
   - ID: **`anual`** · Tipo: **Renovación automática** · Período: **1 año**
   - Precio: **5,99 €** en España (Google calcula el resto de países si los activas)
   - Período de gracia y suspensión: deja los valores por defecto.
   - **Activar** el plan base.
3. **Oferta de prueba** → Añadir oferta (dentro del plan `anual`)
   - ID: **`prueba-7-dias`**
   - Requisito: **Adquisición de nuevos clientes** (nunca ha tenido esta suscripción)
   - Fase: **Prueba gratuita de 7 días**
   - **Activar** la oferta.
4. Ventajas (texto que ve el usuario): «Sin publicidad» y «Alertas de convocatorias nuevas».

## Probar el pago sin cobrar

Configuración → **Pruebas de licencia**: añade tu correo y el de los testers. Sus compras en la
prueba cerrada son de prueba (no se cobra) y las renovaciones van aceleradas (un año = 30 minutos).
