#!/usr/bin/env python3
"""DOGC official portal API mapping discovery, diagnostic only.
Production remains failed-closed without real issues/originals."""
import json,re,requests,concurrent.futures
from bs4 import BeautifulSoup
urls={
 "summary":"https://dogc.gencat.cat/ca/sumari-del-dogc/?numDOGC=9782",
 "document":"https://dogc.gencat.cat/ca/document-del-dogc/?documentId=1057895",
}
def get(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=(7,19));h=BeautifulSoup(r.content,"html.parser")
  fields={x["id"]:x.get("value","") for x in h.select("input[type=hidden][id]") if re.search("host|protocol|port|uri|root",x["id"],re.I)}
  scripts=[x.get("src") for x in h.select("script[src]") if re.search("dogc|sumari|fitxa|eadop|jquery",x.get("src",""),re.I)]
  return {"name":name,"http":r.status_code,"fields":fields,"scripts":scripts}
 except Exception as e:return {"name":name,"error":repr(e)[:170]}
for k,u in urls.items():print("DOGC_FIELDS",json.dumps(get((k,u)),ensure_ascii=True),flush=True)
test={
 "summary_official_rehost":"https://dogc.gencat.cat/eadop-rest/api/dogc/summaryDOGC?numDOGC=9782",
 "summary_www":"https://www.gencat.cat/eadop-rest/api/dogc/summaryDOGC?numDOGC=9782",
 "summary_main":"https://portaldogc.gencat.cat/eadop-rest/api/dogc/summaryDOGC?numDOGC=9782",
 "summary_preprod_probe_only":"https://preproduccio.portaldogc.gencat.cat/eadop-rest/api/dogc/summaryDOGC?numDOGC=9782",
 "summary_http":"http://portaldogc.gencat.cat/eadop-rest/api/dogc/summaryDOGC?numDOGC=9782",
 "summary_portaljuridic":"https://portaljuridic.gencat.cat/eadop-rest/api/dogc/summaryDOGC?numDOGC=9782"
}
def check(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=(5,13),headers={"User-Agent":"Mozilla/5.0"},stream=True)
  data=b""
  for x in r.iter_content(8192):
   data+=x
   if len(data)>90000:break
  r.close()
  return {"key":name,"status":r.status_code,"end":r.url,"type":r.headers.get("Content-Type",""),"bytes":len(data),"head":data[:200].decode("utf-8","replace")}
 except Exception as e:return {"key":name,"error":type(e).__name__+":"+str(e)[:160]}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for r in pool.map(check,test.items()):print("DOGC_ENDPOINT",json.dumps(r,ensure_ascii=True),flush=True)
print("ALL_ENDPOINT_PROBES_ONLY: preproduction is never a source of verified official original publications")
