#!/usr/bin/env python3
"""Probe official DOGV backend formats, dates, summary and document export endpoints."""
import requests,json
from concurrent.futures import ThreadPoolExecutor
BASE="https://dogv.gva.es/dogv-portal"
TESTS=[
("latest","/dogv/latest",{"lang":"es_es"}),
("latest-es","/dogv/latest",{"lang":"es"}),
("latest-va","/dogv/latest",{"lang":"va"}),
("calendar","/dogv/calendar",{"startDate":"2026-09-30","endDate":"2026-10-29"}),
("29-iso","/dogv",{"date":"2026-10-29","lang":"es_es"}),
("29-esp","/dogv",{"date":"29-10-2026","lang":"es_es"}),
("29-slash","/dogv",{"date":"29/10/2026","lang":"es_es"}),
("28-iso","/dogv",{"date":"2026-10-28","lang":"es_es"}),
("30-iso","/dogv",{"date":"2026-09-30","lang":"es_es"}),
]
def minimize(obj):
 if isinstance(obj,dict):
  out={"keys":list(obj)}
  for k,v in obj.items():
   if isinstance(v,list):out[k]={"len":len(v),"first":v[:2]}
   elif isinstance(v,dict):out[k]={"keys":list(v),"fields":{a:b for a,b in v.items() if isinstance(b,(str,int,float,bool))}}
   else:out[k]=v
  return out
 if isinstance(obj,list):return {"type":"array","count":len(obj),"first":obj[:3]}
 return {"type":type(obj).__name__,"value":str(obj)[:4000]}
def probe(x):
 name,path,params=x
 try:
  r=requests.get(BASE+path,params=params,timeout=(12,40),headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
  out={"name":name,"status":r.status_code,"url":r.url,"mime":r.headers.get("Content-Type"),"length":len(r.content)}
  try:out["body"]=minimize(r.json())
  except ValueError:out["text"]=r.text[:1000]
  return out
 except Exception as e:return {"name":name,"error":str(e)[:250]}
with ThreadPoolExecutor(max_workers=6) as ex:
 for out in ex.map(probe,TESTS):print("DOGV_API",json.dumps(out,ensure_ascii=False)[:13000],flush=True)
