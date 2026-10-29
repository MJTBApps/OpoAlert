#!/usr/bin/env python3
"""Measure availability of BOCM official www and apex host with HTTP sessions and Range."""
import concurrent.futures,requests
URLS=[
"/boletin/CM_Boletin_BOCM/2026/10/03/BOCM-20261003236.xml",
"/boletin/CM_Boletin_BOCM/2026/09/30/BOCM-20260930233.xml",
"/boletin/CM_Orden_BOCM/2026/09/30/BOCM-20260930-1.PDF",
"/boletin/CM_Orden_BOCM/2026/10/28/BOCM-20261028-37.PDF",
]
def run(t):
 host,path=t
 with requests.Session() as s:
  s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es"})
  url=f"https://{host}{path}"
  try:
   r=s.get(url,timeout=(8,15),stream=True,headers={"Range":"bytes=0-63"})
   first=next(r.iter_content(chunk_size=64),b"")
   print("RESULT",host,path,r.status_code,"END",r.url,"TYPE",r.headers.get("content-type"),"RANGE",r.headers.get("content-range"),"BYTES",len(first),"HEAD",repr(first[:60]),flush=True)
   r.close()
  except Exception as e:print("ERROR",host,path,type(e).__name__,str(e)[:190],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as p:list(p.map(run,[(h,u) for h in ["www.bocm.es","bocm.es"] for u in URLS]))
