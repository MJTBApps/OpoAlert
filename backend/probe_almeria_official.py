#!/usr/bin/env python3
"""Probe Diputacion de Almeria BOP public archives and document endpoints."""
import requests
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
URLS=[
"https://app.dipalme.org/bop/publico.zul",
"https://app.dipalme.org/bop/publicoValidar.zul?protocolo=https&urlInicial=https%3A%2F%2Fapp.dipalme.org%2Fbop%2Fpublico.zul",
"https://app.dipalme.org/bop/",
"https://www.dipalme.org/Servicios/Boletin/BOP.nsf/buscar-www?OpenForm",
"https://www.dipalme.org/Servicios/Boletin/BOP.nsf/procedenciaasunto?OpenView",
"https://www.dipalme.org/Servicios/Boletin/BOP.nsf/fechaedicto/2026_002792",
"https://app.dipalme.org/bop/services/manager/edicto/2026/2792/anuncio.pdf",
"https://app.dipalme.org/bop/services/manager/boletin/2026/200/boletin.pdf",
"https://app.dipalme.org/bop/services/manager/boletin/2026/200/indice.pdf",
"https://app.dipalme.org/bop/services/manager/boletin/2026/208/boletin.pdf",
"https://app.dipalme.org/bop/services/manager/boletin/2026/208",
"https://app.dipalme.org/bop/services/manager/boletin/2026/208/index.pdf",
"https://app.dipalme.org/bop/services/manager/boletin/2026/208/bop.pdf",
"https://app.dipalme.org/bop/services/manager/boletin/2026/208/sumario.pdf",
"https://app.dipalme.org/bop/services/manager/boletin/2026/208/indice",
"https://app.dipalme.org/bop/services/manager/",
"https://bop.almeria.es/",
"https://www.dipalme.org/Servicios/Boletin/BOP.nsf/ultimo?OpenView"
]
def inspect(url):
 try:
  s=requests.get(url,timeout=(9,16),headers={"User-Agent":"Mozilla/5.0 (OpoAlert source verification)","Accept-Language":"es"},stream=True)
  raw=b""
  for chunk in s.iter_content(chunk_size=8192):
   raw+=chunk
   if len(raw)>280000:break
  print("\nURL",url,"STATUS",s.status_code,"FINAL",s.url[:250],"CT",s.headers.get("Content-Type"),"LENGTH",s.headers.get("Content-Length"),"HEAD",repr(raw[:120]),flush=True)
  if b"%PDF" in raw[:12]:return
  if b"<html" in raw[:1000].lower():
   soup=BeautifulSoup(raw,"html.parser")
   print("TITLE",soup.title.get_text(" ",strip=True) if soup.title else "-","TEXT",soup.get_text(" ",strip=True)[:900],flush=True)
   print("LINKS",[(a.get("href"),a.get_text(" ",strip=True)[:55]) for a in soup.select("a[href]")[:45]],flush=True)
   print("FORMS",[(f.get("action"),f.get("method"),f.get("id")) for f in soup.select("form")[:12]],flush=True)
   print("SCRIPTS",[a.get("src") for a in soup.select("script[src]")[:16]],flush=True)
 except Exception as e:
  print("ERROR",url,type(e).__name__,str(e)[:220],flush=True)
with ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(inspect,URLS))
