#!/usr/bin/env python3
"""Read-only BOA open data export, using established Zaragoza official API client."""
import requests,json,re
from urllib.parse import urlencode
from zaragoza_bop import BASE,SOURCE
from datetime import date
for day in (date(2026,10,29),date(2026,9,30)):
 q=dict(BASE)
 q.update({"BASE":"BOLE","SECC-C":"","@PUBL-GE":day.strftime("%Y%m%d"),"@PUBL-LE":day.strftime("%Y%m%d")})
 for mode in ["JSON","XML"]:
  q["OUTPUTMODE"]=mode
  q["SEC"]="OPENDATABOA"+mode
  try:
   r=requests.get(SOURCE,params=q,timeout=(12,50))
   print("BOA_HTTP",day,mode,r.status_code,"size",len(r.content),"type",r.headers.get("Content-Type"),"url",r.url[:290],flush=True)
   if mode=="JSON":
    try:
     d=r.json()
     print("BOA_COUNT",day,len(d) if isinstance(d,list) else str(d)[:300],flush=True)
     if isinstance(d,list) and d:
      print("BOA_SAMPLE",json.dumps(d[0],ensure_ascii=False)[:6500],flush=True)
      print("BOA_LAST",json.dumps(d[-1],ensure_ascii=False)[:1700],flush=True)
      print("BOA_SECTIONS",list(set(str(x.get("Seccion",""))[:150] for x in d))[:13],flush=True)
    except ValueError as e:print("BOA_JSON_ERR",repr(e),"start",repr(r.text[:450]),flush=True)
   else:print("BOA_XML_START",repr(r.content[:800]),flush=True)
  except Exception as e:print("BOA_ERROR",day,mode,repr(e)[:400],flush=True)
