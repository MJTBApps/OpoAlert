#!/usr/bin/env python3
import requests,json
from concurrent.futures import ThreadPoolExecutor
BASE="https://dogv.gva.es/dogv-portal"
targets=[
("cal","/dogv/calendar",{"startDate":"2026-09-30","endDate":"2026-10-29"}),
("oct01","/dogv",{"date":"2026-10-01","lang":"es_es"}),
("oct01-versions","/dogv/10463/versionesSumario",{}),
("oct01-version1","/dogv/10463",{"ordenSumario":1,"lang":"es_es"}),
("oct01-version2","/dogv/10463",{"ordenSumario":2,"lang":"es_es"}),
("oct29-versions","/dogv/10482/versionesSumario",{}),
("oct29-1","/dogv/10482",{"ordenSumario":1,"lang":"es_es"}),
("pdf","/export/disposicion/492729/pdf",{"lang":"es_es"}),
]
def summarize(d):
 if isinstance(d,list):return {"kind":"list","count":len(d),"first":d[:3],"last":d[-3:]}
 if isinstance(d,dict):
  return {"keys":list(d),"scalars":{k:v for k,v in d.items() if isinstance(v,(str,bool,int))},
      "collections":{k:{"n":len(v),"first":v[:1]} for k,v in d.items() if isinstance(v,list)},
      "objects":{k:v for k,v in d.items() if isinstance(v,dict)}}
 return d
def run(row):
 name,path,params=row
 try:
  r=requests.get(BASE+path,params=params,timeout=(12,36),headers={"Accept":"application/json","User-Agent":"Mozilla/5.0"},allow_redirects=False)
  try:body=summarize(r.json())
  except ValueError:body=r.text[:750]
  return {"name":name,"status":r.status_code,"url":r.url,"mime":r.headers.get("Content-Type"),"body":body}
 except Exception as e:return {"name":name,"error":repr(e)[:300]}
with ThreadPoolExecutor(max_workers=6) as p:
 for row in p.map(run,targets):print("DOGV_EXTRA",json.dumps(row,ensure_ascii=False)[:12000],flush=True)
for url in ("https://dogv.gva.es/datos/2026/10/28/pdf/2026_31402_es.pdf",
            "https://dogv.gva.es/datos/2026/10/29/pdf/sumario_2026_10482_es.pdf"):
 try:
  r=requests.get(url,timeout=(12,32),stream=True,headers={"Range":"bytes=0-140"},allow_redirects=False)
  b=b""
  for chunk in r.iter_content(140):
   b+=chunk
   if len(b)>=6:break
  print("DOGV_PDF",r.status_code,r.url,r.headers.get("Content-Type"),repr(b[:12]),flush=True)
  r.close()
 except Exception as e:print("DOGV_PDF_ERROR",str(e)[:300],flush=True)
