#!/usr/bin/env python3
"""Check accessibility of Ceuta's official document server from independent runners."""
import requests,json,socket,time
S=[
"https://www.ceuta.es/ceuta/bocce",
"https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1965-2026?Itemid=534",
"https://www.ceuta.es/ceuta/component/jdownloads/finish/1980-septiembre/23254-bocce-6650-08-09-2026?Itemid=0",
"https://ceuta.es/ceuta/bocce",
"https://sede.ceuta.es/"
]
for u in S:
 t=time.monotonic()
 try:
  r=requests.get(u,timeout=(6,10),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES"},stream=True,allow_redirects=False)
  data=next(r.iter_content(140),b"")
  r.close()
  print("CEUTA_NET",json.dumps({"url":u,"status":r.status_code,"type":r.headers.get("Content-Type"),"bytes":len(data),"first":repr(data[:25]),"seconds":round(time.monotonic()-t,2)},ensure_ascii=False),flush=True)
 except Exception as e:
  print("CEUTA_NET",json.dumps({"url":u,"error":repr(e)[:250],"seconds":round(time.monotonic()-t,2)},ensure_ascii=False),flush=True)
