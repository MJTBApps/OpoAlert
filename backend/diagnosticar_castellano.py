#!/usr/bin/env python3
"""Prueba real del selector CAS del BOP; no escribe datos de OpoAlert."""
import json
from playwright.sync_api import sync_playwright

PORTAL = "https://bop.dival.es/bop/xhtml/portal.xhtml"

def titles(page):
    return [s.strip() for s in page.locator(
        "#list_content .ui-datagrid-column .sumario"
    ).all_text_contents() if s.strip()][:4]

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    try:
        page = b.new_page(locale="ca-ES", viewport={"width": 1280, "height": 900})
        page.goto(PORTAL, wait_until="domcontentloaded", timeout=60000)
        page.locator("body").wait_for(timeout=15000)
        page.wait_for_timeout(1200)
        before = titles(page)
        links = page.locator("a[title='Castellà'],a[aria-label='Castellà'],a:has-text('CAS')")
        if links.count() == 0:
            raise RuntimeError("No se detecta enlace CAS")
        from idioma_bop import seleccionar_castellano
        seleccionar_castellano(page)
        after = titles(page)
        report = {
            "before": before,
            "after": after,
            "changed": before != after,
            "spanish_title": any(t.casefold().startswith("anuncio") for t in after),
            "spanish_locale_selected": page.locator("span.ui-state-disabled:has-text('CAS')").count() > 0,
        }
        print("CASTELLANO_DIAGNOSTICO=" + json.dumps(report, ensure_ascii=False), flush=True)
        ficha = page.locator("#list_content .ui-datagrid-column").first.inner_text()
        from scan import META, extract_index
        lectura = "OK"
        try:
            datos, _ = extract_index(page.content())
            lectura = {"fichas": len(datos), "primer_id": datos[0]["id"] if datos else None}
        except Exception as err:
            lectura = {"error": str(err)}
        print("CASTELLANO_FICHA=" + json.dumps({
            "text": ficha[:750],
            "meta_match": bool(META.search(ficha)),
            "extraccion": lectura
        }, ensure_ascii=False), flush=True)
        if not before or not after:
            raise RuntimeError("Los titulos del BOP no se cargaron")
        if not report["changed"] or not report["spanish_title"]:
            raise RuntimeError("El selector CAS no cambia los titulos a castellano")
    finally:
        b.close()
