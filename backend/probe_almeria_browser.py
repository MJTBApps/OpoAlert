#!/usr/bin/env python3
"""Inspect ZK official Almeria BOP portal using an actual browser.

Diagnostic only. No feed is published until archive coverage is validated.
"""
import asyncio,json,re
from playwright.async_api import async_playwright

URL="https://app.dipalme.org/bop/publico.zul"
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,args=["--no-sandbox"])
  page=await browser.new_page(viewport={"width":1440,"height":900},locale="es-ES")
  stats={"responses":0,"zkau":[],"pdf":[]}
  async def response(resp):
   stats["responses"]+=1
   u=resp.url
   if "zkau" in u and len(stats["zkau"])<24:stats["zkau"].append((resp.status,u[:200],resp.request.method,resp.headers.get("content-type")))
   if "/services/" in u and len(stats["pdf"])<16:stats["pdf"].append((resp.status,u[:220]))
  page.on("response",response)
  page.on("console",lambda msg:print("BROWSER_CONSOLE",msg.type,msg.text[:160],flush=True) if msg.type=="error" else None)
  try:
   await page.goto(URL,wait_until="domcontentloaded",timeout=65000)
   await page.wait_for_timeout(8000)
   print("URL",page.url,"TITLE",await page.title(),flush=True)
   print("TEXT",repr((await page.locator("body").inner_text())[:11000]),flush=True)
   print("BUTTONS",await page.locator("button").all_text_contents(),flush=True)
   print("ANCHORS",await page.locator("a").evaluate_all("(els)=>els.slice(0,80).map(e=>({text:e.textContent.trim().slice(0,90),href:e.href,title:e.title,onclick:e.getAttribute('onclick')}))"),flush=True)
   print("INPUTS",await page.locator("input").evaluate_all("(els)=>els.slice(0,90).map(e=>({id:e.id,type:e.type,placeholder:e.placeholder,value:e.value}))"),flush=True)
   print("ZOOMS",await page.locator("[role=tab]").all_text_contents(),flush=True)
   print("TABLES",await page.locator("table").count(),flush=True)
   print("BODY_HTML_SLICE",(await page.locator("body").inner_html())[:8500],flush=True)
   print("NETWORK",json.dumps(stats,ensure_ascii=False),flush=True)
   print("ROW_CLASSES",await page.locator("tr").evaluate_all("(els)=>[...new Set(els.map(e=>e.className))].slice(0,25)"),flush=True)
   for sel in [".z-listitem",".z-listcell",".z-grid",".z-row",".z-rows",".z-listbox","tr.z-listitem","[role=row]","a[title]"]:
    print("SELECTOR",sel,"COUNT",await page.locator(sel).count(),flush=True)
   for sel in ["tr.z-listitem",".z-listitem","tr.z-row",".z-row"]:
    if await page.locator(sel).count():
     print("SAMPLE_ROWS",sel,await page.locator(sel).evaluate_all("(els)=>els.slice(0,4).map(e=>({text:e.innerText,html:e.outerHTML.slice(0,2200)}))"),flush=True)
   for day in ["27/10/2026","01/10/2026","25/10/2026"]:
    print("SEARCH_DAY",day,flush=True)
    try:
     fields=page.locator('input[placeholder="dd/mm/aaaa"]')
     print("DATE_FIELDS",await fields.count(),flush=True)
     await fields.first.fill(day)
     await page.locator('a[title="Buscar registros con los parámetros indicados"]').click(timeout=12000)
     await page.wait_for_timeout(2200)
     txt=await page.locator("body").inner_text()
     idx=txt.find("Anuncios\n")
     print("RESULT_DAY",day,repr(txt[idx:idx+4000]),flush=True)
     for sel in ["tr.z-listitem",".z-listitem","tr.z-row"]:
      if await page.locator(sel).count():
       print("RESULT_ROWS",sel,await page.locator(sel).count(),(await page.locator(sel).all_inner_texts())[:4],flush=True)
    except Exception as ex:print("SEARCH_ERROR",day,type(ex).__name__,str(ex)[:520],flush=True)
   for title in ("Boletines","Histórico","Último boletín"):
    candidate=page.get_by_text(title,exact=True)
    count=await candidate.count()
    print("TAB",title,"count",count,flush=True)
    if count:
     try:
      await candidate.first.click(timeout=10000)
      await page.wait_for_timeout(2400)
      print("TAB_TEXT",title,repr((await page.locator("body").inner_text())[:9500]),flush=True)
      print("TAB_INPUTS",title,await page.locator("input").evaluate_all("(els)=>els.slice(0,50).map(e=>({id:e.id,type:e.type,value:e.value}))"),flush=True)
     except Exception as ex:print("TAB_ERROR",title,type(ex).__name__,str(ex)[:260],flush=True)
  except Exception as e:print("ERROR",type(e).__name__,str(e)[:950],flush=True)
  finally:
   await browser.close()

asyncio.run(main())
