#!/usr/bin/env python3
"""Inspect publication ranges of the official BORM open-data index."""
from datetime import datetime
from collections import Counter
import requests,json,re,sys
urls=[
("json","https://transparencia.carm.es/rest-services/services/restFile/BORMIndice.json"),
]
for kind,u in urls:
 try:
  s=requests.Session()
  r=s.get(u,timeout=(12,90),headers={"User-Agent":"Mozilla/5.0","Accept":"application/json"})
  print("BORM_OPEN_DATA","HTTP",r.status_code,"LAST_MODIFIED",r.headers.get("Last-Modified"),
        "CONTENT_TYPE",r.headers.get("Content-Type"),"BYTES",len(r.content),flush=True)
  if r.status_code!=200:continue
  v=r.json()
  print("BORM_ROWS",len(v),"ROW_SAMPLE",json.dumps(v[:1],ensure_ascii=False)[:3000],flush=True)
  if not isinstance(v,list) or not v or not isinstance(v[0],list):
   raise ValueError("Missing array rows")
  print("COLUMN_COUNTS",Counter(map(len,v)),flush=True)
  if len(v[0])<=16:raise ValueError("Too few cols")
  d=[x[4][:10] for x in v if len(x)>4 and isinstance(x[4],str)]
  count=Counter(x[:7] for x in d)
  print("BORM_RANGE","DATE_MIN",min(d),"DATE_MAX",max(d),"MONTHS",sorted(count.items()),
        "LATEST_ROWS",sum(x>="2026-09-30" for x in d),flush=True)
  recent=[x for x in v if len(x)>4 and isinstance(x[4],str) and x[4][:10]>="2026-09-30"]
  print("BORM_RECENT_FIRST",json.dumps(recent[:2],ensure_ascii=False)[:3600],flush=True)
  print("BORM_RECENT_LAST",json.dumps(recent[-2:],ensure_ascii=False)[:3600],flush=True)
 except Exception as e:print("BORM_OPEN_ERROR",type(e).__name__,str(e),flush=True)
