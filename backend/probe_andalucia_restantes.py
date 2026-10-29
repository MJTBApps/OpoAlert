#!/usr/bin/env python3
"""Inspect official Andalusian province portals on GitHub Actions network.

Diagnostic only: does not publish announcements or guess missing issues.
"""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit, urljoin
from bs4 import BeautifulSoup
import re, requests
TASKS = [
 ("GRANADA-29","https://bop.dipgra.es/publica/consulta-de-bops/buscador/BOP-29-10-2026/"),
 ("GRANADA-28","https://bop.dipgra.es/publica/consulta-de-bops/buscador/BOP-28-10-2026/"),
 ("SEVILLA-29","https://bopsevilla.dipusevilla.es/publica/consulta-de-bops/buscador/BOP-29-10-2026/"),
 ("SEVILLA-28","https://bopsevilla.dipusevilla.es/publica/consulta-de-bops/buscador/BOP-28-10-2026/"),
 ("MALAGA-29","https://www.bopmalaga.es/sumario.php?fecha=29-10-2026"),
 ("MALAGA-28","https://www.bopmalaga.es/sumario.php?fecha=28-10-2026"),
 ("MALAGA-dot","https://www.bopmalaga.es/sumario.php.?fecha=28-10-2026"),
 ("CORDOBA-home","https://bop.dipucordoba.es/"),
 ("CORDOBA-29","https://bop.dipucordoba.es/?action=index&calendar=20261029&controller=index"),
 ("CORDOBA-21","https://bop.dipucordoba.es/?action=index&calendar=20261021&controller=index"),
 ("HUELVA-se","https://sede.diphuelva.es/servicios/bop"),
 ("HUELVA-bop","https://bop.diphuelva.es/"),
]
def worker(item):
 label,url=item
 try:
  r=requests.get(url,timeout=(10,32),headers={"User-Agent":"Mozilla/5.0 (compatible; OpoAlert public provincial diagnostics)","Accept-Language":"es"},allow_redirects=True)
  h=BeautifulSoup(r.content[:900000],"html.parser")
  print("\n===== "+label,flush=True)
  print("HTTP",r.status_code,"FINAL",r.url,"LEN",len(r.content),"TYPE",r.headers.get("Content-Type"),flush=True)
  print("TITLE",h.title.get_text(" ",strip=True)[:160] if h.title else "-",flush=True)
  print("HEADING",[(x.name,x.get_text(" ",strip=True)[:140]) for x in h.select("h1,h2,h3")[:8]],flush=True)
  print("TEXT",repr(h.get_text(" ",strip=True)[:1100]),flush=True)
  print("CARDS",len(h.select("li.elementoListado")),"COUNTERS",re.findall(r"Resultados\s+del\s+\d+\s+al\s+\d+\s+de\s+\d+",h.get_text(" ",strip=True))[:3],flush=True)
  c=h.select_one("li.elementoListado")
  if c:
   print("FIRST_CARD_HTML",str(c)[:3400],flush=True)
  print("PDFS",[(a.get_text(" ",strip=True)[:75],urljoin(r.url,a.get("href",""))[:230]) for a in h.select("a[href]") if ".pdf" in a.get("href","").lower()][:9],flush=True)
  print("LINKS",[(a.get_text(" ",strip=True)[:55],a.get("href","")[:160]) for a in h.select("a[href]")[:22]],flush=True)
  if label.startswith("CORDOBA"):
   print("HTML_SNIPPET",str(h.select_one("body"))[:3000],flush=True)
  if label.startswith("MALAGA"):
   print("SUMARIO_HTML",str(h.select_one("main") or h.select_one("body"))[:3500],flush=True)
 except Exception as exc: print("ERROR",label,type(exc).__name__,str(exc)[:220],flush=True)
with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(worker,TASKS))
