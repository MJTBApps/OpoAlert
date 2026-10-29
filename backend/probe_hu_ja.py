#!/usr/bin/env python3
"""Targeted legacy Huelva and Jaén official search HTML diagnostics."""
import requests,re,sys
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from collections import Counter
URLS=[
("HU-ARCHIVE","https://s2.diphuelva.es/servicios/boparchivo"),
("HU-ULTIMO","https://s2.diphuelva.es/servicios/bope_web/UltimoBop"),
("HU-CALENDAR","https://s2.diphuelva.es/servicios/bope_web/busquedaCalendario"),
("HU-SEARCH","https://s2.diphuelva.es/servicios/bope_web/busquedaAvanzada?desde=01%2F10%2F2026&hasta=29%2F10%2F2026&btnBuscar=Buscar"),
("HU-SEARCH-DAY","https://s2.diphuelva.es/servicios/bope_web/busquedaAvanzada?desde=28%2F10%2F2026&hasta=28%2F10%2F2026&btnBuscar=Buscar"),
("JA-RESULTS","https://bophistorico.dipujaen.es/results.vm?view=boletin"),
("JA-QUERY","https://bophistorico.dipujaen.es/results.vm?q=2026&view=boletin"),
]
for name,url in URLS:
 try:
  r=requests.get(url,timeout=(10,22),headers={"User-Agent":"Mozilla/5.0"})
  s=BeautifulSoup(r.content,"html.parser",from_encoding="iso-8859-1" if name.startswith("HU") else None)
  print("\n==========",name,"STATUS",r.status_code,"LEN",len(r.content),"URL",r.url,"MIME",r.headers.get("Content-Type"),flush=True)
  print("TITLE",s.title.get_text(" ",strip=True) if s.title else "-",flush=True)
  print("BODY",repr(s.get_text(" ",strip=True)[-2100:]),flush=True)
  print("FORMS",[(f.get("action"),f.get("method"),f.get("name"),f.get("id")) for f in s.select("form")],flush=True)
  print("LINKS",[(a.get_text(" ",strip=True)[:65],urljoin(r.url,a.get("href",""))[:240],a.get("onclick")) for a in s.select('a[href]')[:40]],flush=True)
  print("SCRIPT_NAMES",[(x.get("src"),x.get("type")) for x in s.select("script[src]")[:20]],flush=True)
  print("ONCLICK",[(x.name,x.get("onclick")) for x in s.select("[onclick]")[:20]],flush=True)
  print("TABLE_ROWS",[(x.get_text(" ",strip=True)[:300],str(x)[:650]) for x in s.select("tr")[:6]],flush=True)
  print("BODY_HTML",str(s.body)[-5200:] if s.body else "-",flush=True)
 except Exception as e:print("ERR",name,type(e).__name__,str(e)[:350],flush=True)
