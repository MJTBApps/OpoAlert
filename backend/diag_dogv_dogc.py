#!/usr/bin/env python3
"""Read-only discovery of official DOGV and DOGC daily issue metadata and PDF links."""
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
import requests,re,json
S=[
("DOGV-FRONT","https://dogv.gva.es/dogv-portal-frontend/es"),
("DOGV-FRONT-VA","https://dogv.gva.es/dogv-portal-frontend/va"),
("DOGV-OLD","https://dogv.gva.es/datos/2026/10/29/pdf/"),
("DOGV-2026","https://dogv.gva.es/datos/2026/10/29/"),
("DOGV-DATE","https://dogv.gva.es/dogv-portal-frontend/es/2026/10/29"),
("DOGC-HOME","https://dogc.gencat.cat/es/inici/"),
("DOGC-INDEX","https://dogc.gencat.cat/es/serveis/Consulta-del-DOGC/"),
("DOGC-FECHA","https://dogc.gencat.cat/es/dogc-por-data/"),
("DOGC-CERCA","https://dogc.gencat.cat/es/serveis/Consulta-del-DOGC/"),
]
def probe(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=(10,32),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"},stream=True,allow_redirects=True)
  raw=b""
  for chunk in r.iter_content(100000):
   raw+=chunk
   if len(raw)>180000:break
  r.close()
  h=BeautifulSoup(raw,"html.parser")
  out={"name":name,"http":r.status_code,"url":r.url,"size":len(raw),"mime":r.headers.get("Content-Type"),
       "title":h.title.get_text(" ",strip=True)[:150] if h.title else "",
       "headings":[z.get_text(" ",strip=True)[:130] for z in h.select("h1,h2,h3")[:12]],
       "iframes":[x.get("src") for x in h.select("iframe")[:5]],
       "scripts":[x.get("src") for x in h.select("script[src]")[-16:]],
       "links":[(x.get_text(" ",strip=True)[:100],urljoin(r.url,x.get("href",""))) for x in h.select("a[href]") if re.search(r"2026|pdf|oct|DOGV|DOGC|buscar|consul|data|calendar",x.get("href","")+" "+x.get_text(" ",strip=True),re.I)][:30],
       "text":h.get_text(" ",strip=True)[:560]}
  return out
 except Exception as e:return {"name":name,"error":repr(e)[:280]}
with ThreadPoolExecutor(max_workers=8) as p:
 for out in p.map(probe,S):print("DIARIO_DIAG",json.dumps(out,ensure_ascii=False)[:12500],flush=True)
