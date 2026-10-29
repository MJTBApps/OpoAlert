#!/usr/bin/env python3
"""Compare official BOP connectivity from independent runner networks."""
from concurrent.futures import ThreadPoolExecutor
import requests,time,platform
items=[
 ("BU","https://bopbur.diputaciondeburgos.es/bopbur-2026-105"),
 ("SA","https://sede.diputaciondesalamanca.gob.es/BOP/"),
 ("VA","https://bop.sede.diputaciondevalladolid.es/calendario"),
 ("BU-http","http://bopbur.diputaciondeburgos.es/bopbur-2026-105"),
 ("SA-web","https://www.lasalina.es/bop"),
 ("VA-www","https://www.diputaciondevalladolid.es/"),
]
print("PLATFORM",platform.platform(),flush=True)
def go(item):
 name,url=item;t=time.monotonic()
 try:
  z=requests.get(url,timeout=(8,12),headers={"User-Agent":"Mozilla/5.0"},stream=True)
  head=next(z.iter_content(chunk_size=180),b"")
  print("RESULT",name,z.status_code,"sec",round(time.monotonic()-t,1),"final",z.url,"type",z.headers.get("Content-Type"),"head",repr(head[:120]),flush=True)
  z.close()
 except Exception as ex:print("ERROR",name,round(time.monotonic()-t,1),type(ex).__name__,str(ex)[:210],flush=True)
with ThreadPoolExecutor(max_workers=6) as e:list(e.map(go,items))
