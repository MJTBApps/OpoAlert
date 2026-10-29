#!/usr/bin/env python3
"""Read the official Diputacion de Malaga open-data dataset metadata.

Public CKAN catalogue: https://opendata.malaga.es/dataset/edictos
National registry: https://datos.gob.es/es/catalogo/l02000029-edictos-del-boletin-oficial-de-la-provincia-de-malaga-bopma
No BOPMA CAPTCHA requests. Discovery only: CSV summaries are NOT a BOP original.
"""
from __future__ import annotations
import json,re,requests
from urllib.parse import urlsplit
from datetime import datetime

HOST="opendata.malaga.es"
DATASET_ID="f9fde2a3-ced6-43e0-9b94-821dfd604c5c"
API=f"https://{HOST}/api/3/action/package_show"
OUT="MALAGA_CKAN_EVIDENCE"

def get(url,**kw):
 p=urlsplit(url)
 if p.scheme!="https" or p.hostname!=HOST or p.username or p.password:
  raise ValueError("Not a publisher-owned endpoint")
 r=requests.get(url,timeout=(9,25),headers={"User-Agent":"OpoAlert/1.29 (non-invasive official data catalogue audit)"},**kw)
 print(OUT,"GET",r.status_code,r.url,"bytes",len(r.content),flush=True)
 if r.status_code!=200 or urlsplit(r.url).hostname!=HOST:raise ValueError("Official CKAN response unavailable")
 return r

for key in (DATASET_ID,"edictos"):
 try:
  r=get(API,params={"id":key})
  item=r.json()
  if item.get("success") is not True or not isinstance(item.get("result"),dict):
   raise ValueError("Not valid CKAN JSON")
  x=item["result"]
  rows=x.get("resources",[])
  print(OUT,"package_id",x.get("id"),"title",x.get("title"),"resource_count",len(rows),flush=True)
  for v in rows:
   name=v.get("name","")
   u=v.get("url","")
   p=urlsplit(u)
   print(OUT,"resource",json.dumps({"name":name,"format":v.get("format"),"url":u,"size":v.get("size"),"modified":v.get("last_modified"),"official_host":p.hostname==HOST},ensure_ascii=False),flush=True)
  fresh=[v for v in rows if re.search(r"\b2026\b",v.get("name","")) or re.search(r"edictos_2026",v.get("url",""))]
  if not fresh:print(OUT,"RESULT: no 2026 edicts resource available; coverage UNVERIFIED",flush=True)
  else:
   print(OUT,"RESULT: 2026 RESOURCES FOUND",len(fresh),"; must compare all original edicts / BOP editions before coverage",flush=True)
   for v in fresh:
    u=v.get("url","")
    if urlsplit(u).hostname==HOST and v.get("format","").upper() in ("JSON","CSV","XML"):
     try:
      sample=get(u,headers={"Range":"bytes=0-4095"})
      print(OUT,"2026 sample",repr(sample.content[:700]),flush=True)
     except (requests.RequestException,ValueError) as e:print(OUT,"2026 sample error",str(e)[:260],flush=True)
  break
 except (requests.RequestException,ValueError,KeyError) as exc:
  print(OUT,"catalogue error for",key,repr(exc)[:290],flush=True)
else:
 print(OUT,"RESULT: official CKAN endpoint unreachable; coverage UNVERIFIED",flush=True)
