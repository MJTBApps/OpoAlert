#!/usr/bin/env python3
"""Inspect DOGC supplementary issue API official JS, no activation."""
import requests,re,json
from bs4 import BeautifulSoup
root="https://dogc.gencat.cat"
u=root+"/ca/sumari-del-suplement/?numDOGC=9782SN"
r=requests.get(u,timeout=(6,20))
h=BeautifulSoup(r.content,"html.parser")
print("SUPPLEMENT_HTML",json.dumps({"http":r.status_code,"size":len(r.content),"title":h.title.get_text(" ",strip=True) if h.title else "","inputs":{x.get("id"):x.get("value") for x in h.select('input[type=hidden][id]') if re.search("supp|supl|uri|protocol|host|num|language|locale",x.get("id",""),re.I)},"scripts":[x.get("src") for x in h.select("script[src]") if re.search("supl|sumari",x.get("src",""),re.I)]},ensure_ascii=False),flush=True)
js_files=[x.get("src") for x in h.select("script[src]") if re.search("supl|sumari",x.get("src",""),re.I)]
for item in js_files:
 try:
  res=requests.get(requests.compat.urljoin(root,item),timeout=(5,18))
  body=res.text
  spans=[]
  for m in re.finditer("summarySuplement|uriSumari|type: 'post'|type: 'POST'|numDOGC|numSuplement|data: inputParameters",body,re.I):
   spans.append(body[max(0,m.start()-350):min(len(body),m.end()+550)])
  print("SUPPLEMENT_JS",json.dumps({"src":item,"http":res.status_code,"len":len(body),"fragments":spans[:15]},ensure_ascii=False),flush=True)
 except Exception as e:print("SUPPLEMENT_ERROR",type(e).__name__,str(e)[:180],flush=True)

print("SUPPLEMENT_PARAMS_EXACT_BEGIN",flush=True)
try:
 r=requests.get(root+"/web/system/modules/cat.gencat.wcmResponsive.formatters.httpFetch/resources/fpca_sumari_suplement/js/fpca_sumari_suplement.js",timeout=(5,15))
 m=re.search(r"function\\s+searchSuplementsAjaxCall\\s*\\(",r.text)
 print(repr(r.text[m.start():m.start()+2400] if m else "NO MATCH")[:4000],flush=True)
except Exception as e:print(repr(e),flush=True)

try:
 x=requests.get(root+'/web/system/modules/cat.gencat.wcmResponsive.formatters.httpFetch/resources/fpca_sumari_suplement/js/fpca_sumari_suplement.js',timeout=18).text
 i=x.find('function searchSuplementsAjaxCall')
 print('SUPPLEMENT_CALL_EXACT',repr(x[i:i+3200]),flush=True)
except Exception as e:print('SUPPLEMENT_CALL_ERROR',repr(e),flush=True)
