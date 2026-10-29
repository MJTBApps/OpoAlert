#!/usr/bin/env python3
"""Diagnose Almeria ZK AU browser bootstrap, Pandora library, Jaen alternate hosts."""
import requests,re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

urls=[
 ("ZK publico","https://app.dipalme.org/bop/publico.zul"),
 ("ZK validar","https://app.dipalme.org/bop/publicoValidar.zul?protocolo=https&urlInicial=https%3A%2F%2Fapp.dipalme.org%2Fbop%2Fpublico.zul"),
 ("Almeria anuncio PDF","https://app.dipalme.org/bop/services/manager/edicto/2026/2715/anuncio.pdf"),
 ("PANDORA main","https://app.dipalme.org/pandora/?view=boletines"),
 ("PANDORA index","https://app.dipalme.org/pandora/index.vm?s=1371&view=boletines"),
 ("PANDORA root","https://app.dipalme.org/pandora/"),
 ("Jaen root www","https://www.bop.dipujaen.es/"),
 ("Jaen homepage","https://bop.dipujaen.es/"),
 ("Jaen old","https://bop.dipujaen.es/pagina_bop.dip"),
 ("Jaen pdf old","https://bop.dipujaen.es/descargarws.dip?anioExpedienteEdicto=2026&boletinSuplemento=0&ejercicioBop=2026&fechaBoletin=2026-09-25&numeroEdicto=4451&tipo=bop"),
 ("Jaen historico","https://bophistorico.dipujaen.es/"),
 ("Jaen news","https://www.dipujaen.es/"),
]
def worker(pair):
 name,url=pair
 print("\n===== CHECK",name,flush=True)
 try:
  s=requests.Session()
  s.headers["User-Agent"]="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
  r=s.get(url,timeout=(10,22),allow_redirects=True)
  print("HTTP",r.status_code,"LEN",len(r.content),"TYPE",r.headers.get("Content-Type"),"URL",r.url[:220],flush=True)
  if "pdf" in r.headers.get("Content-Type","").lower():
   print("PDFHEAD",repr(r.content[:30]),flush=True);return
  h=BeautifulSoup(r.content[:600000],"html.parser")
  print("TITLE",h.title.get_text(" ",strip=True) if h.title else "-","BODY",repr(h.get_text(" ",strip=True)[:1100]),flush=True)
  if name.startswith("ZK"):
   print("WHOLE_HTML",repr(r.text[:12000]),flush=True)
  else:
   print("FORMS",[(f.get("action"),f.get("id"),f.get("method")) for f in h.select("form")[:12]],flush=True)
   print("INPUTS",[(x.get("name"),x.get("id"),x.get("value")) for x in h.select("input[name]")[:25]],flush=True)
   print("LINKS",[(a.get("href"),a.get_text(" ",strip=True)[:75]) for a in h.select("a[href]")[:80]],flush=True)
   print("SCRIPTS",[x.get("src") for x in h.select("script[src]")[:30]],flush=True)
 except Exception as ex: print("ERROR",type(ex).__name__,str(ex)[:230],flush=True)
with ThreadPoolExecutor(max_workers=3) as p:list(p.map(worker,urls))
