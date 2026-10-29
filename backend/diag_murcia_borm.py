#!/usr/bin/env python3
"""Probe source-of-truth BORM access (Murcia), without publishing unverified notices."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin,urlsplit
import requests,re,json
from bs4 import BeautifulSoup

TARGETS=[
("BORM-home","https://www.borm.es/"),
("BORM-home-path","https://www.borm.es/#/home/boletin/29-10-2026"),
("BORM-services","https://www.borm.es/services/"),
("BORM-boletin","https://www.borm.es/services/boletin/"),
("BORM-day1","https://www.borm.es/services/boletin/fecha/20261029"),
("BORM-day2","https://www.borm.es/services/boletin/fecha/2026-10-29"),
("BORM-day3","https://www.borm.es/services/boletin/29-10-2026"),
("BORM-day4","https://www.borm.es/services/boletin/20261029"),
("BORM-sumario","https://www.borm.es/services/boletin/sumario/20261029"),
("BORM-pdf","https://www.borm.es/services/anuncio/844460/pdf"),
("BORM-pdf2","https://www.borm.es/services/anuncio/844460/html"),
("BORM-data-json","https://transparencia.carm.es/rest-services/services/restFile/BORMIndice.json"),
("BORM-data-txt","https://transparencia.carm.es/rest-services/services/restFile/BORMIndice.txt"),
]
def inspect(target):
 label,url=target
 try:
  r=requests.get(url,timeout=(12,37),stream=True,headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36","Accept-Language":"es-ES,es;q=0.9"})
  size=r.headers.get("Content-Length")
  media=r.headers.get("Content-Type")
  initial=b""
  for chunk in r.iter_content(65536):
   if chunk:initial+=chunk
   if len(initial)>=min(600000,500000 if label=="BORM-home" else 150000):break
  r.close()
  info={"name":label,"http":r.status_code,"size":size,"type":media,"bytes":len(initial),"url":r.url,
      "prefix":initial[:270].decode("utf-8","replace")}
  if initial.startswith(b"%PDF-"):info["pdf"]=True
  elif "json" in (media or "").lower() or (initial[:1]==b"["):
   try:
    decoded=json.loads(initial)
    info["json_info"]={"type":type(decoded).__name__,"length":len(decoded),
      "first":decoded[0][:20] if isinstance(decoded,list) and decoded and isinstance(decoded[0],list) else
       str(decoded[0] if isinstance(decoded,list) and decoded else decoded)[:1200]}
   except Exception as e:info["parse_error"]=type(e).__name__
  elif "<html" in initial[:1000].decode("utf-8","replace").lower():
   soup=BeautifulSoup(initial,"html.parser")
   info["title"]=soup.title.get_text(" ",strip=True) if soup.title else ""
   info["scripts"]=[(x.get("src"),x.get("type")) for x in soup.select("script")][:40]
   info["links"]=[(x.get_text(" ",strip=True)[:80],urljoin(r.url,x.get("href",""))) for x in soup.select("a[href]")][:24]
   info["text"]=soup.get_text(" ",strip=True)[:1300]
  return info
 except Exception as e:return {"name":label,"error":str(e)[:400]}
with ThreadPoolExecutor(max_workers=7) as ex:
 for info in ex.map(inspect,TARGETS):
  print("BORM_DIAG",json.dumps(info,ensure_ascii=False),flush=True)
