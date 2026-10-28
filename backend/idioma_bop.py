"""Selecciona la version castellana ORIGINAL de los titulos del portal BOP.

El BOP tiene dos opciones oficiales de idioma, CAS/VAL, independientes del
idioma preferido del navegador. Elegimos CAS antes de leer cualquier anuncio.
El selector se verifico con Chromium sobre el portal real el 28/10/2026.

NO traduce titulos: conserva la redaccion castellana proporcionada por el BOP.
"""
from __future__ import annotations

from typing import Any


class IdiomaBOPError(RuntimeError):
    """El portal no ha confirmado que se este mostrando la version castellana."""


def seleccionar_castellano(page: Any) -> bool:
    """Asegura la interfaz CAS, con confirmacion visible en DOM.

    Devuelve True si hubo que cambiar el idioma, False si ya era CAS.
    Nunca continua en VAL por un fallo de la operacion.
    """
    activo = page.locator('span.ui-state-disabled:has-text("CAS")')
    cambiado = False
    if activo.count() == 0:
        enlace = page.locator('a[title="Castellà"], a[aria-label="Castellà"]')
        if enlace.count() == 0 or not enlace.first.is_visible():
            raise IdiomaBOPError('No se encuentra el selector oficial CAS del BOP')
        enlace.first.click(timeout=15000)
        cambiado = True

    # La peticion PrimeFaces cambia los anuncios por AJAX, no basta con hacer
    # click: esperamos a que se actualice la cabecera y el primer titulo.
    try:
        page.wait_for_function(
            '''() => {
                const cas = [...document.querySelectorAll('span.ui-state-disabled')]
                    .some(n => n.textContent.trim() === 'CAS');
                const titulo = document.querySelector('#list_content .ui-datagrid-column .sumario');
                return cas && titulo && /^Anuncio\\b/i.test(titulo.textContent.trim());
            }''',
            timeout=20000,
        )
    except Exception as exc:
        raise IdiomaBOPError(
            'El BOP no ha confirmado anuncios en castellano despues de seleccionar CAS'
        ) from exc

    return cambiado
