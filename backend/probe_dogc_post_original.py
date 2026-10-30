#!/usr/bin/env python3
"""Official DOGC POST reader proof of concept with CA-validated legacy TLS.
No coverage enabled; outputs only structural metadata and examples.
"""
import requests,ssl,json,sys
from requests.adapters import HTTPAdapter
from urllib.parse import urlsplit
class TLSAdapter(HTTPAdapter):
 def init_poolmanager(self,*args,**kwargs):
  ctx=ssl.create_default_context()
  ctx.maximum_version=ssl.TLSVersion.TLSv1_2
  ctx.set_ciphers("DEFAULT:@SECLEVEL=1")
  kwargs["ssl_context"]=ctx
  return super().init_poolmanager(*args,**kwargs)
session=requests.Session()
session.mount("https://portaldogc.gencat.cat",TLSAdapter())
session.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert official DOGC authenticated-originals audit)","Accept":"application/json,text/javascript,*/*;q=0.01","Accept-Language":"ca,es;q=0.9","Referer":"https://dogc.gencat.cat/ca/"})
HOST="https://portaldogc.gencat.cat"
CALLS=[
 ("summary9782","/eadop-rest/api/dogc/summaryDOGC",{"numDOGC":"9782","language":"ca"}),
 ("summary9770","/eadop-rest/api/dogc/summaryDOGC",{"numDOGC":"9770","language":"ca"}),
 ("calendar_oct","/eadop-rest/api/dogc/calendarDOGC",{"month":"10","year":"2026","language":"ca"}),
 ("calendar_sep","/eadop-rest/api/dogc/calendarDOGC",{"month":"9","year":"2026","language":"ca"}),
 ("original1057895","/eadop-rest/api/dogc/documentDOGC",{"documentId":"1057895","language":"es"})
]
def trim(x,depth=0):
 if depth>4:return type(x).__name__
 if isinstance(x,dict):return {k:trim(v,depth+1) for k,v in list(x.items())[:18]}
 if isinstance(x,list):
  return {"total":len(x),"samples":[trim(v,depth+1) for v in x[:2]]}
 if isinstance(x,str):return x[:190]
 return x
print("OFFICIAL_CA_TLS12",ssl.OPENSSL_VERSION,flush=True)
for name,path,data in CALLS:
 try:
  r=session.post(HOST+path,data=data,timeout=(8,32),allow_redirects=False)
  print("DOGC_POST_META",json.dumps({"name":name,"http":r.status_code,"mime":r.headers.get("Content-Type",""),"bytes":len(r.content),"url":r.url},ensure_ascii=True),flush=True)
  if r.status_code!=200:
   print("DOGC_POST_ERROR",name,repr(r.text[:650]),flush=True);continue
  obj=r.json()
  print("DOGC_POST_RESULT",json.dumps({"name":name,"structure":trim(obj)},ensure_ascii=True),flush=True)
 except Exception as ex:
  print("DOGC_POST_ERROR",name,type(ex).__name__,str(ex)[:250],flush=True)
print("NOTE: Original authentic editions must undergo exhaustive 30-day independent audit before Android integration",flush=True)
