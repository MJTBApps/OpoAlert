#!/usr/bin/env python3
"""Probe official Aragón BOP sources; no feed is published."""
from urllib.request import Request,urlopen
from urllib.parse import urljoin
import re
from bs4 import BeautifulSoup
import json

URLS=[
 "https://bop.dphuesca.es/publica/consulta-de-bops/buscador/BOP-28-10-2026/",
 "https://bop.dphuesca.es/publica/consulta-de-bops/buscador/BOP-27-10-2026/",
 "https://bop.dphuesca.es/publica/consulta-de-bops/buscador/BOP-12-10-2026/",
 "https://bop.dphuesca.es/publica/buscador-anuncios/anuncio/Bases-Bolsa-de-Empleo-Limpieza-Personal-Laboral-Temporal/",
 "https://bender.dpteruel.es/dpt/bopt.nsf/inicio.xsp",
 "https://boletin.dpz.es/BOPZ/",
]
for url in URLS:
 print("\nURL",url,flush=True)
 try:
  with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; OpoAlert source audit/1.7)","Accept-Language":"es"}),timeout=18) as r:
   raw=r.read(550_000); ct=r.headers.get("content-type");target=r.url
  print("HTTP 200",target,ct,"BYTES",len(raw),flush=True)
  soup=BeautifulSoup(raw,"html.parser")
  print("TITLE",soup.title.get_text(" ",strip=True)[:120] if soup.title else "(none)",flush=True)
  print("TEXT",soup.get_text(" ",strip=True)[:1500],flush=True)
  print("SELECTORS",[(css,len(soup.select(css))) for css in [".listado", ".listado-anuncios", ".elemento-listado", ".ficha","article", ".item", "a[href*='sumario']", "a[href*='exportar-sumario']", "a[href*='pdf']", "a[href*='anuncio']"]],flush=True)
  print("LINKS",[(a.get("href"),a.get_text(" ",strip=True)[:65]) for a in soup.select("a[href]") if any(t in a.get("href","").lower() for t in ("pdf","json","anuncio","sumario","buscar","exportar","bop"))][:42],flush=True)
  for m in re.findall(r".{0,120}BOPH-\d{4}-\d{3}\d{3}.{0,130}",str(soup))[:3]:
   print("CODE CONTEXT",m,flush=True)
 except Exception as e:print("ERROR",type(e).__name__,str(e)[:350],flush=True)
