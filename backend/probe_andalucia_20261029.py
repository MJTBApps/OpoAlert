#!/usr/bin/env python3
"""Explorar portales de Almeria y Jaen para lectores auditados de OpoAlert."""
import requests, concurrent.futures, re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
urls=[
 ("JAEN hoy","https://bop.dipujaen.es/bop/29-10-2026"),
 ("JAEN ayer","https://bop.dipujaen.es/bop/28-10-2026"),
 ("JAEN 01","https://bop.dipujaen.es/bop/01-10-2026"),
 ("JAEN 15","https://bop.dipujaen.es/bop/15-10-2026"),
 ("JAEN calendario","https://bop.dipujaen.es/anioCompleto"),
 ("JAEN busqueda","https://bop.dipujaen.es/busquedas"),
 ("ALMERIA dominio","https://bop.almeria.es/"),
 ("ALMERIA origen","https://www.dipalme.org/Servicios/Boletin/BOP.nsf/"),
 ("ALMERIA buscar","https://www.dipalme.org/Servicios/Boletin/BOP.nsf/buscar-www?OpenForm"),
 ("ALMERIA consultas","https://app.dipalme.org/bop/publico.zul"),
 ("ALMERIA diario viejo","https://www.dipalme.org/Servicios/Boletin/BOP.nsf/UltimoBoletin?OpenView"),
 ("ALMERIA vista edicto","https://www.dipalme.org/Servicios/Boletin/BOP.nsf/procedenciaasunto?OpenView&RestrictToCategory=Ayuntamiento+de+Almeria"),
]
def run(item):
 label,url=item
 print("\n========",label,flush=True)
 try:
  r=requests.get(url,timeout=(12,23),headers={"User-Agent":"Mozilla/5.0 (compatible; OpoAlert/1.12; boletines oficiales)","Accept-Language":"es"},allow_redirects=True)
  print("STATUS",r.status_code,"END",r.url[:230],"SIZE",len(r.content),"TYPE",r.headers.get("Content-Type"),flush=True)
  h=BeautifulSoup(r.content[:700000],"html.parser")
  print("TITLE",h.title.get_text(" ",strip=True)[:180] if h.title else "-",flush=True)
  print("TEXT",repr(h.get_text(" ",strip=True)[:1850]),flush=True)
  print("FORMS",[(f.get("action"),f.get("method"),f.get("id")) for f in h.find_all("form")[:7]],flush=True)
  print("INPUTS",[(x.get("name"),x.get("id"),x.get("value"),x.get("type")) for x in h.select("input")[:35]],flush=True)
  print("LINKS",[(a.get("href"),a.get_text(" ",strip=True)[:85]) for a in h.select("a[href]")[:90]],flush=True)
  print("SCRIPTS",[(s.get("src")) for s in h.select("script[src]")[:15]],flush=True)
  if label.startswith("JAEN"):
   print("BOP_MARKUP",repr(r.text[r.text.find("Boletín Nº"):r.text.find("Boletín Nº")+3000]),flush=True)
 except Exception as ex:
  print("ERROR",type(ex).__name__,str(ex)[:260],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run,urls))
