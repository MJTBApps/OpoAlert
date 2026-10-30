#!/usr/bin/env python3
"""Locate a complete BOP Burgos publication on publisher-owned alternate web hosts.

The real publisher BOPBUR uses /sites/default/files/private/publicado/.
This checks whether original bytes are also served by another official
Diputacion de Burgos subdomain. An HTTP 200 alone is not a passed audit.
"""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
import requests, json, re
HOSTS=[
"bopbur.diputaciondeburgos.es",
"burgos.es",
"www.burgos.es",
"prewww.burgos.es",
"telecentros.burgos.es",
"www.telecentros.burgos.es",
"idj.burgos.es",
"cultura.burgos.es",
"www.cultura.burgos.es",
"registro.diputaciondeburgos.es",
]
ED=(51,186,195,200,205)
PATH="/sites/default/files/private/publicado/bopbur-2026-{n:03}/bopbur-2026-{n:03}.pdf"
CONTROL=[("control",host,51) for host in HOSTS]
PROBES=[("oct",host,n) for host in HOSTS if host in
("bopbur.diputaciondeburgos.es","burgos.es","prewww.burgos.es","telecentros.burgos.es") for n in ED[1:]]
TASKS=CONTROL+PROBES

def test(t):
 typ,host,n=t
 u="https://"+host+PATH.format(n=n)
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert official BOP research)","Accept":"application/pdf"})
   r=s.get(u,timeout=(5,12),stream=True,allow_redirects=True)
   b=b""
   for chunk in r.iter_content(1024):
    b+=chunk
    if len(b)>=2048:break
   r.close()
   return {"type":typ,"host":host,"issue":n,"http":r.status_code,"final":r.url,
     "mime":r.headers.get("Content-Type",""),"size":r.headers.get("Content-Length"),
     "pdf":b.startswith(b"%PDF-"),"body":repr(b[:120]) if not b.startswith(b"%PDF-") else ""}
 except Exception as e:return {"type":typ,"host":host,"issue":n,"error":type(e).__name__+": "+str(e)[:150]}
with ThreadPoolExecutor(max_workers=16) as ex:
 for item in ex.map(test,TASKS):print("BURGOS_MIRROR",json.dumps(item,ensure_ascii=True),flush=True)
