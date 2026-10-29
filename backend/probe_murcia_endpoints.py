#!/usr/bin/env python3
"""Probe exact official BORM REST contracts for dates, summaries and supplements."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
import requests,json,re
BASE="https://www.borm.es/"
ENDPOINTS=[
("ultimo","services/boletin/ultimo"),
("fechas","services/boletin/fechas"),
("by-fecha-es","services/boletin/fecha/29-10-2026"),
("by-fecha-iso","services/boletin/fecha/2026-10-29"),
("by-fecha-28es","services/boletin/fecha/28-10-2026"),
("by-fecha-28iso","services/boletin/fecha/2026-10-28"),
("by-fecha-slashed","services/boletin/fecha/29%2F10%2F2026"),
("sumario-es","services/boletin/fecha/29-10-2026/sumario"),
("sumario-iso","services/boletin/fecha/2026-10-29/sumario"),
("apartados-es","services/boletin/fecha/29-10-2026/sumario/apartados"),
("suplementos-es","services/suplemento/fecha/29-10-2026"),
("suplementos-iso","services/suplemento/fecha/2026-10-29"),
("boletin-by-number","services/boletin?"+urlencode({"ano":2026,"numero":245})),
("controller-boletin","scripts/boletines/controllers/boletinController.js"),
("controller-sumario","scripts/sumario/controllers/sumarioController.js"),
("controller-home","scripts/homeBorm/controllers/homeController.js"),
]
def summarize(obj):
 if isinstance(obj,list):
  return {"type":"list","count":len(obj),"first":obj[:2],"last":obj[-2:] if len(obj)>2 else None}
 if isinstance(obj,dict):
  return {"type":"dict","keys":list(obj),"fields":{k:v for k,v in obj.items() if isinstance(v,(str,int,float,bool))},
      "collections":{k:{"type":type(v).__name__,"count":len(v),"first":v[:1] if isinstance(v,list) else list(v.items())[:5]} for k,v in obj.items() if isinstance(v,(list,dict))}}
 return {"type":type(obj).__name__,"repr":str(obj)[:2000]}
def probe(pair):
 name,path=pair
 try:
  r=requests.get(BASE+path,timeout=(10,28),headers={"User-Agent":"Mozilla/5.0","Accept":"application/json, text/plain, */*","X-Requested-With":"XMLHttpRequest"})
  ct=r.headers.get("Content-Type","")
  if path.endswith(".js"):result={"script":r.text[:5200]}
  else:
   try:result=summarize(r.json())
   except ValueError:result={"text":r.text[:650],"mime":ct}
  return {"name":name,"http":r.status_code,"type":ct,"url":r.url,"bytes":len(r.content),"result":result}
 except Exception as e:return {"name":name,"error":repr(e)}
with ThreadPoolExecutor(max_workers=7) as p:
 for v in p.map(probe,ENDPOINTS):
  print("BORM_API",json.dumps(v,ensure_ascii=False)[:18000],flush=True)
