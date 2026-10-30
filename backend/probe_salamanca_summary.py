#!/usr/bin/env python3
"""Check original BOPSA PDF index zero (sumario) and special editions."""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pypdf import PdfReader
import requests,json,re
dates=["20260930","20261001","20261012","20261016","20261028","20261029"]
items=[(d,0) for d in dates]+[("20261028",16),("20261029",1),("20261016",17),("20261016",18)]
def run(pair):
 d,n=pair
 url=f"https://www.lasalina.es/documentacion/bop/2026/{d}/BOP-SA-{d}-{n:03}.pdf"
 try:
  r=requests.get(url,timeout=(8,28),allow_redirects=False)
  obj={"date":d,"n":n,"status":r.status_code,"bytes":len(r.content),"ct":r.headers.get("Content-Type",""),"url":r.url,"pdf":r.content[:5]==b"%PDF-"}
  if obj["pdf"] and len(r.content)<=25000000:
   doc=PdfReader(BytesIO(r.content),strict=False)
   texts=[(p.extract_text() or "") for p in doc.pages[:4]]
   obj["pages"]=len(doc.pages)
   obj["cves"]=re.findall(r"BOP-SA-\d{8}-\d{3}"," ".join(texts))[:25]
   obj["head"]=repr(texts[0][:1300])
  else:obj["head"]=repr(r.content[:150])
  return obj
 except Exception as e:return {"date":d,"n":n,"error":type(e).__name__+":"+str(e)[:200]}
with ThreadPoolExecutor(max_workers=6) as pool:
 for o in pool.map(run,items):print("BOPSA_INDEX_TEST",json.dumps(o,ensure_ascii=False)[:2400],flush=True)
