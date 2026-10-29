#!/usr/bin/env python3
"""Compare legitimate official BOP access from hosted runner networks."""
import requests,concurrent.futures,time,platform
S=[
("AB","https://bop.dipualba.es/"),
("CU","https://www.dipucuenca.es/boletin-oficial-de-la-provincia"),
("JA","https://bop.dipujaen.es/bop/20-10-2026"),
("JA-ARCHIVE","https://bophistorico.dipujaen.es/"),
("HU","https://s2.diphuelva.es/servicios/boparchivo"),
("MA","https://www.bopmalaga.es/sumario.php?fecha=20-10-2026"),
("MD","https://www.bocm.es/boletin/CM_Boletin_BOCM/2026/10/20/BOCM-20261020252.xml")
]
print("MACHINE",platform.platform(),flush=True)
def run(x):
 name,url=x;start=time.monotonic()
 try:
  r=requests.get(url,timeout=(8,14),headers={"User-Agent":"Mozilla/5.0"},stream=True)
  raw=next(r.iter_content(128),b"")
  print("RESULT",name,r.status_code,"elapsed",round(time.monotonic()-start,1),"END",r.url,"TYPE",r.headers.get("Content-Type"),"HEAD",repr(raw[:105]),flush=True)
  r.close()
 except Exception as e:print("ERROR",name,round(time.monotonic()-start,1),type(e).__name__,str(e)[:260],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as p:list(p.map(run,S))
