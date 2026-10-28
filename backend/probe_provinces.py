#!/usr/bin/env python3
"""Small non-writing audit of Alicante/Castellon official BOP markup and links.

This probes the *public* bulletin indexes, no mass scraping. Output is a compact
summary to design stable extractors and verify announcement identity/coverage.
"""
import json
from pathlib import Path
import re
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

TARGETS = {
  'alicante': 'https://sede.diputacionalicante.es/consultas.bop/',
  'castellon': 'https://bop.dipcas.es/PortalBOP/',
}

def analyze(page, name):
    meta = page.evaluate('''() => ({
        title: document.title, url: location.href,
        forms: [...document.forms].slice(0,5).map(f=>({id:f.id, action:f.action, method:f.method})),
        inputs: [...document.querySelectorAll('input, select')].slice(0,38).map(i=>({tag:i.tagName, id:i.id, name:i.name, placeholder:i.getAttribute('placeholder'),type:i.type, value:i.value?.slice(0,32)})),
        tables: [...document.querySelectorAll('table')].slice(0,9).map(t=>({id:t.id, className:t.className, rows:t.rows.length, text:t.innerText?.slice(0,250)})),
        headings: [...document.querySelectorAll('h1,h2,h3,h4')].slice(0,18).map(t=>t.innerText?.slice(0,90)),
        notices: [...document.querySelectorAll('a')].filter(a=>/(edicto|anuncio|pdf|descargar|resoluci[oó]n|bases|plaza|convocatoria|oposici[oó]n|lista provisional|n[ºú]m\.?\s*1[123])/i.test(a.innerText||a.title||a.href)).slice(0,28).map(a=>({text:a.innerText?.slice(0,85),href:a.href?.slice(0,240),className:(typeof a.className==='string'?a.className:'').slice(0,80),parent:(a.parentElement?.innerText||'').slice(0,160)})),
        buttons: [...document.querySelectorAll('button')].slice(0,25).map(b=>({text:b.innerText?.slice(0,80),title:b.title,id:b.id})),
        frames: [...document.querySelectorAll('iframe')].slice(0,8).map(f=>f.src),
        text: (document.body?.innerText||'').slice(0,2800)
    })''')
    print('PORTAL_DIAGNOSTIC=' + json.dumps({'province':name, **meta}, ensure_ascii=False),flush=True)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    try:
        for name,url in TARGETS.items():
            try:
                page=browser.new_page(locale='es-ES',viewport={'width':1366,'height':850})
                seen=[]
                def on_response(response):
                    if len(seen)>=45: return
                    u=response.url
                    if urlparse(u).hostname not in ('sede.diputacionalicante.es','bop.dipcas.es'): return
                    if re.search(r'api|ajax|bop|edicto|anunci|boletin',u,re.I):
                        seen.append({'status':response.status,'contentType':response.headers.get('content-type','')[:60],'url':u[:220]})
                page.on('response',on_response)
                page.goto(url,wait_until='domcontentloaded',timeout=55000)
                page.wait_for_timeout(3200)
                analyze(page,name)
                target = Path('backend/diag_sources')
                target.mkdir(parents=True, exist_ok=True)
                (target / f'{name}.html').write_text(page.content(), encoding='utf-8')
                print('REQUESTS=' + json.dumps({'province':name,'urls':seen[:30]},ensure_ascii=False),flush=True)
                page.close()
            except Exception as exc:
                print('PROBE_ERROR='+json.dumps({'province':name,'error':str(exc)[:700]},ensure_ascii=False),flush=True)
    finally:
        browser.close()
