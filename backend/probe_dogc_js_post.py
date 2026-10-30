#!/usr/bin/env python3
"""DOGC public Javascript method/payload discovery for the official POST API."""
import requests,json,re
from bs4 import BeautifulSoup
ROOT="https://dogc.gencat.cat"
FILES={
 "summary":"/web/system/modules/cat.gencat.wcmResponsive.formatters.httpFetch/resources/fpca_sumari_DOGC/js/fpca_sumari_DOGC.js",
 "summary_calendar":"/web/system/modules/cat.gencat.wcmResponsive.formatters.httpFetch/resources/fpca_sumari_DOGC/js/fpca_sumari_DOGC_calendari_dogc.js",
 "document":"/web/system/modules/cat.gencat.wcmResponsive.formatters.httpFetch/resources/fpca_fitxa_dogc/js/fpca_fitxa_dogc.js",
 "constants":"/web/system/modules/cat.gencat.wcmResponsive.formatters.httpFetch/resources/common/js/constants.js"
}
for name,path in FILES.items():
 try:
  r=requests.get(ROOT+path,timeout=(6,18),headers={"User-Agent":"Mozilla/5.0"})
  body=r.text
  keys=["ajax","POST","post","summaryDOGC","getMonth","fecha","http","numDOGC","contentType","JSON.stringify","data:","uriSumari","hostSumari"]
  spans=[]
  for m in re.finditer("|".join(re.escape(k) for k in keys),body,re.I):
   span=(max(0,m.start()-270),min(len(body),m.end()+480))
   if spans and span[0]<=spans[-1][1]+120:spans[-1]=(spans[-1][0],max(spans[-1][1],span[1]))
   else:spans.append(span)
  excerpts=[body[i:j] for i,j in spans][:60]
  print("DOGC_JS",json.dumps({"name":name,"status":r.status_code,"bytes":len(body),"sample":body[:900],"excerpts":excerpts[:45]},ensure_ascii=True),flush=True)
 except Exception as e:print("DOGC_JS_ERROR",name,type(e).__name__,str(e)[:180],flush=True)
