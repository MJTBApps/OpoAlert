#!/usr/bin/env python3
"""Probe official Euskadi BOPV API JSON schema and pagination."""
import requests,json
from concurrent.futures import ThreadPoolExecutor
ENDPOINTS=[
("oct-page","https://api.euskadi.eus/bopv/administrative-acts/2026/10?itemsOfPage=3&currentPage=1&lang=SPANISH"),
("sept-page","https://api.euskadi.eus/bopv/administrative-acts/2026/9?itemsOfPage=3&currentPage=1&lang=SPANISH"),
("oct-large","https://api.euskadi.eus/bopv/administrative-acts/2026/10?itemsOfPage=500&currentPage=1&lang=SPANISH"),
("day-id","https://api.euskadi.eus/bopv/administrative-acts/2026/10/4558"),
]
def inspect(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=40,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
  out={"name":name,"status":r.status_code,"url":r.url,"type":r.headers.get("Content-Type"),"len":len(r.content)}
  try:
   j=r.json()
   if isinstance(j,dict):
    out["keys"]=list(j);out["flat"]={k:v for k,v in j.items() if isinstance(v,(str,int,float,bool))}
    out["arrays"]={k:{"count":len(v),"first":v[:2],"last":v[-1:]} for k,v in j.items() if isinstance(v,list)}
    out["dicts"]={k:str(v)[:1300] for k,v in j.items() if isinstance(v,dict)}
   else:out["data"]=j[:2] if isinstance(j,list) else j
  except ValueError:out["html"]=r.text[:700]
  return out
 except Exception as e:return {"name":name,"error":repr(e)[:400]}
with ThreadPoolExecutor(max_workers=4) as p:
 for row in p.map(inspect,ENDPOINTS):print("PVREST",json.dumps(row,ensure_ascii=False)[:13500],flush=True)
