#!/usr/bin/env python3
"""Probe only authentic BOP Huelva and Malaga official endpoints; no data publication."""
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
CHECKS=[
 ("HUELVA-ULTIMO","https://s2.diphuelva.es/servicios/bope_web/UltimoBop"),
 ("HUELVA-CALENDAR","https://s2.diphuelva.es/servicios/bope_web/busquedaCalendario"),
 ("HUELVA-AVANZADA","https://s2.diphuelva.es/servicios/bope_web/busquedaAvanzada"),
 ("HUELVA-SEDE-JSP","https://sede.diphuelva.es/opencms/system/modules/gsede/elements/contenido/BOP.jsp"),
 ("MALAGA-SUMARIO-28","https://www.bopmalaga.es/sumario.php?fecha=28-10-2026"),
 ("MALAGA-SUMARIO-01","https://www.bopmalaga.es/sumario.php?fecha=01-10-2026"),
]
def run(x):
 key,url=x
 try:
  s=requests.Session()
  s.headers["User-Agent"]="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125 Safari/537.36"
  z=s.get(url,timeout=(12,35),allow_redirects=True)
  content=z.content
  txt=z.text
  h=BeautifulSoup(txt[:500000],"html.parser")
  print("\n====",key,z.status_code,"END",z.url,"TYPE",z.headers.get("Content-Type"),"LEN",len(content),"ENC",z.encoding,flush=True)
  print("BODY",repr(h.get_text(" ",strip=True)[:1500]),flush=True)
  print("FORMS",[(f.get("action"),f.get("method"),f.get("id")) for f in h.select("form")[:10]],flush=True)
  print("LINKS",[(a.get_text(" ",strip=True)[:95],urljoin(z.url,a.get("href",""))[:240]) for a in h.select("a[href]")[:60]],flush=True)
  if key.startswith("MALAGA"):
   print("SAMPLE_HTML",str(h.body)[-9000:] if h.body else "-",flush=True)
  if key.startswith("HUELVA-"):
   print("HTML",txt[:4000],flush=True)
 except Exception as exc:print("ERROR",key,type(exc).__name__,str(exc)[:280],flush=True)
with ThreadPoolExecutor(max_workers=2) as pool:list(pool.map(run,CHECKS))
