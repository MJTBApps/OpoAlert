#!/usr/bin/env python3
"""Visit the official Almeria public BOP in headless Chrome and inspect DOM/events."""
from playwright.sync_api import sync_playwright
import re
URL="https://app.dipalme.org/bop/publicoValidar.zul?protocolo=https&urlInicial=https%3A%2F%2Fapp.dipalme.org%2Fbop%2Fpublico.zul"
with sync_playwright() as p:
 print("CHROMIUM EXEC",p.chromium.executable_path,flush=True)
 browser=p.chromium.launch(channel="chrome",headless=True,args=["--no-sandbox"])
 context=browser.new_context(locale="es-ES",viewport={"width":1440,"height":900})
 page=context.new_page()
 traffic=[]
 def track(r):
  if "zkau" in r.url:
   data=r.post_data or ""
   traffic.append((r.method,r.url[:180],data[:700]))
 page.on("request",track)
 try:
  page.goto(URL,wait_until="domcontentloaded",timeout=35000)
  page.wait_for_timeout(8500)
  print("FIRST_URL",page.url,"TITLE",page.title(),flush=True)
  print("BODY",repr(page.locator("body").inner_text()[:7500]),flush=True)
  print("INPUTS",[(i.get_attribute("id"),i.get_attribute("placeholder"),i.get_attribute("type")) for i in page.locator("input").all()[:70]],flush=True)
  print("BUTTONS",[(x.get_attribute("id"),x.inner_text()[:60]) for x in page.locator("button").all()[:55]],flush=True)
  print("TABS",[(x.get_attribute("id"),x.inner_text()[:55]) for x in page.locator("[role=tab],.z-tab").all()[:30]],flush=True)
  print("ROWS",page.locator("tr").count(),flush=True)
  print("TRAFFIC",traffic[-25:],flush=True)
  locator=page.get_by_text("Histórico",exact=True)
  if locator.count():
   locator.first.click(timeout=6500)
   page.wait_for_timeout(5000)
   print("AFTER_HISTORICO",repr(page.locator("body").inner_text()[:7000]),flush=True)
   print("TRAFFIC2",traffic[-25:],flush=True)
  else:
   print("NO_HISTORICO_TAB",flush=True)
 except Exception as e:print("PAGE_ERROR",type(e).__name__,str(e)[:750],flush=True)
 browser.close()
