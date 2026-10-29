#!/usr/bin/env python3
"""Inspect official Huelva classic application and Malaga date URL variants."""
import requests,re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
URLS=[
 ("MA-DOT28","https://www.bopmalaga.es/sumario.php.?fecha=28-10-2026"),
 ("MA-DOT01","https://www.bopmalaga.es/sumario.php.?fecha=01-10-2026"),
 ("MA-PHP28","https://www.bopmalaga.es/sumario.php?fecha=28-10-2026"),
 ("MA-BOPHTML28","https://www.bopmalaga.es/sumario.php?date=28-10-2026"),
 ("HU-LAST","https://s2.diphuelva.es/servicios/bope_web/UltimoBop"),
 ("HU-CAL","https://s2.diphuelva.es/servicios/bope_web/busquedaCalendario"),
 ("HU-ADV","https://s2.diphuelva.es/servicios/bope_web/busquedaAvanzada"),
]
def one(item):
 name,url=item
 try:
  z=requests.get(url,timeout=(12,26),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"})
  h=BeautifulSoup(z.content,"html.parser",from_encoding="iso-8859-1" if name.startswith("HU") else "utf-8")
  print("\n======",name,z.status_code,z.url,"BYTES",len(z.content),flush=True)
  print("H",[(x.name,x.get_text(" ",strip=True)[:160]) for x in h.select("h1,h2,h3,h4")[:15]],flush=True)
  print("T",repr(h.get_text(" ",strip=True)[-2200:]),flush=True)
  print("IFRAMES",[(x.get("src"),x.get("id"),x.get("name")) for x in h.select("iframe")[:6]],flush=True)
  print("FORM",[(f.get("action"),f.get("method"),f.get("id"),[(v.get("name"),v.get("value")) for v in f.select("input")[:15]]) for f in h.select("form")[:8]],flush=True)
  print("LINKS",[(a.get_text(" ",strip=True)[:35],urljoin(z.url,a.get("href",""))) for a in h.select("a[href]")[-25:]],flush=True)
  if name.startswith("HU"):
   print("HTML_END",repr(z.text[-8500:]),flush=True)
  else:
   print("MAIN",str(h.select_one("#sumario") or h.select_one(".sumario") or h.select_one("#lista_pdf"))[:4500],flush=True)
 except Exception as ex:print("ERROR",name,type(ex).__name__,str(ex)[:200],flush=True)
with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(one,URLS))
