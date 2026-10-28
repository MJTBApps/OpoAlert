#!/usr/bin/env python3
"""Read-only live probes of date selection (Alicante) and edition carousel (Castellon)."""
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

def show(name,page):
    details=page.evaluate('''() => ({
      forms: [...document.forms].slice(0,5).map(f=>({id:f.id,method:f.method})),
      date: document.querySelector('#fechaboletin')?.value,
      alicante: [...document.querySelectorAll('table.tabla-edictos-inner tbody tr')].slice(0,3).map(r=>[...r.querySelectorAll('td')].map(x=>x.innerText?.slice(0,75))),
      alicanteCount: document.querySelectorAll('table.tabla-edictos-inner tbody tr').length,
      alicanteError: document.querySelector('#avisos')?.innerText?.slice(0,180),
      csIssue: document.querySelector('[id="busquedaBoletinesForm:j_idt88"]')?.innerText,
      csDate: document.querySelector('[id="busquedaBoletinesForm:j_idt90"]')?.innerText,
      csCount: document.querySelectorAll('a[href*="api/descargarAnuncio"]').length,
      csCarousel: [...document.querySelectorAll('a[aria-label^="Nº "]')].map(a=>({aria:a.getAttribute('aria-label')?.replace(/\\s+/g,' '),visible:a.offsetParent!==null})).slice(0,22)
    })''')
    print('NAV_DIAGNOSTIC='+json.dumps({'name':name,**details},ensure_ascii=False),flush=True)
    path=Path('backend/diag_sources');path.mkdir(parents=True,exist_ok=True)
    (path/(name+'.html')).write_text(page.content(),encoding='utf-8')

with sync_playwright() as p:
    b=p.chromium.launch(headless=True)
    try:
        pg=b.new_page(locale='es-ES',viewport={'width':1366,'height':850})
        pg.goto('https://sede.diputacionalicante.es/consultas.bop/',wait_until='domcontentloaded',timeout=60000)
        pg.wait_for_selector('table.tabla-edictos-inner tbody tr',timeout=25000)
        for day in ['2026-10-27','2026-10-25','2026-09-29']:
            try:
                pg.locator('#fechaboletin').fill(day,timeout=12000)
                pg.locator('#fechaboletin').dispatch_event('change')
                pg.wait_for_timeout(1700)
                show('alicante-'+day,pg)
            except Exception as e:print('NAV_ERROR='+json.dumps({'date':day,'message':str(e)[:350]}),flush=True)
        pg.close()
        pg=b.new_page(locale='es-ES',viewport={'width':1366,'height':850})
        pg.goto('https://bop.dipcas.es/PortalBOP/',wait_until='domcontentloaded',timeout=60000)
        pg.locator('span.titulo4').first.wait_for(timeout=18000)
        show('castellon-first',pg)
        try:
            pg.locator('a[aria-label^="Nº 129"]').first.click(timeout=15000)
            pg.wait_for_timeout(1700)
            show('castellon-129',pg)
            for i in range(6):
                if pg.locator('a[aria-label^="Nº 117"]').count():
                    pg.locator('a[aria-label^="Nº 117"]').first.click(timeout=10000)
                    pg.wait_for_timeout(1700)
                    show('castellon-117',pg)
                    break
                nextp=pg.locator('a.ui-carousel-next')
                if not nextp.count() or nextp.first.get_attribute('aria-disabled')=='true':break
                nextp.first.click(timeout=12000)
                pg.wait_for_timeout(450)
                show('castellon-next-'+str(i),pg)
        except Exception as e:print('NAV_ERROR='+json.dumps({'site':'castellon','message':str(e)[:400]}),flush=True)
        pg.close()
    finally:
        b.close()
