#!/usr/bin/env python3
"""DOGC official summary structure and publication-calendar full metadata (read-only)."""
import requests,ssl,json,collections
from requests.adapters import HTTPAdapter
class TLSAdapter(HTTPAdapter):
 def init_poolmanager(self,*args,**kwargs):
  c=ssl.create_default_context();c.maximum_version=ssl.TLSVersion.TLSv1_2;c.set_ciphers("DEFAULT:@SECLEVEL=1")
  kwargs["ssl_context"]=c;return super().init_poolmanager(*args,**kwargs)
s=requests.Session();s.mount("https://portaldogc.gencat.cat",TLSAdapter())
base="https://portaldogc.gencat.cat/eadop-rest/api/dogc/"
def post(path,params):
 r=s.post(base+path,data=params,timeout=(12,40));r.raise_for_status();return r.json()
for mon in (9,10):
 data=post("calendarDOGC",{"month":mon,"year":2026,"language":"ca"})
 r=data.get("calendar",[])
 print("CALENDAR",json.dumps({"month":mon,"count":len(r),"published":[x for x in r if x.get("hasDOGC")],"unpublished_count":sum(not x.get("hasDOGC") for x in r)},ensure_ascii=False),flush=True)
def walk(v,out,parents=()):
 if isinstance(v,dict):
  if "documentId" in v or ("title" in v and "linkDownloadDocumentPDF" in v):
   out.append((parents,v));return
  for k,x in v.items():walk(x,out,parents+(k,))
 elif isinstance(v,list):
  for x in v:walk(x,out,parents)
for n in (9761,9770,9782,9783):
 try:
  data=post("summaryDOGC",{"numDOGC":str(n),"language":"ca"})
  issues=data.get("sumaris",[])
  for issue in issues:
   found=[];walk(issue.get("section",[]),found)
   shapes=collections.Counter(tuple(sorted(doc)) for _,doc in found)
   print("DOGC_ISSUE_SHAPE",json.dumps({"requested":n,"number":issue.get("numDOGC"),"date":issue.get("dateDOGC"),
     "issue_keys":list(issue.keys()),"section_count":len(issue.get("section",[])),
     "sections":[{"title":x.get("title"),"nHeaders":len(x.get("header",[]))} for x in issue.get("section",[])],
     "documents_found":len(found),"keys_frequency":{str(k):v for k,v in shapes.most_common(4)},
     "samples":[{"parents":p,"document":d} for p,d in found[:3]]},ensure_ascii=False)[:13000],flush=True)
 except Exception as e:print("DOGC_SHAPE_ERROR",n,type(e).__name__,str(e)[:190],flush=True)
