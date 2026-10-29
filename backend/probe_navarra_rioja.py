#!/usr/bin/env python3
"""Temporary official-site probe: prints response structure, never user data."""
import requests,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin,quote
URLS=[
 "https://bon.navarra.es/es/inicio",
 "https://bon.navarra.es/es/inicio/-/sumario/2026/195",
 "https://bon.navarra.es/es/inicio/-/sumario/2026/214",
 "https://bon.navarra.es/es/inicio/-/sumario/2026/215",
 "https://web.larioja.org/bor-portada/bor?filtros=%7B%22type%22%3A%5B%22bor%22%5D%7D&page=1&sort=fecha_publicacion+desc",
 "https://web.larioja.org/bor-portada/bor",
 "https://web.larioja.org/bor-portada"
]
s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
for url in URLS:
 print("\n====",url,flush=True)
 try:
  r=s.get(url,timeout=(8,22),allow_redirects=True)
  print("status",r.status_code,"final",r.url,"type",r.headers.get("Content-Type"),"bytes",len(r.content),flush=True)
  h=BeautifulSoup(r.content[:1250000],"html.parser")
  print("title",h.title.get_text(" ",strip=True) if h.title else "<none>",flush=True)
  if r.status_code!=200:continue
  for a in h.select("a[href]")[:75]:
   t=" ".join(a.get_text(" ",strip=True).split())[:105]
   u=urljoin(r.url,a.get("href"))
   if t or any(k in u for k in ("sumario","2026","normativa","pdf","item")):
    print("LINK",repr(t),u[:240],flush=True)
  for f in h.select("form")[:4]:
   print("FORM",f.get("action"),f.get("method"),[(x.get("name"),x.get("type")) for x in f.select("input")][:25],flush=True)
  for script in h.select("script[src]")[:20]:
   print("SCRIPT",script.get("src"),flush=True)
  print("TEXT"," ".join(h.get_text(" ",strip=True).split())[:1800],flush=True)
 except Exception as ex:print("ERROR",repr(ex),flush=True)
