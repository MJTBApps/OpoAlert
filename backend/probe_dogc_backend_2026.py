#!/usr/bin/env python3
"""Official DOGC HTML integration investigation: inspect embed and scripts, not credentials.
No external/private aggregators, CAPTCHA or feed activation."""
import requests,re,json
from bs4 import BeautifulSoup
urls={
 "summary9782":"https://dogc.gencat.cat/ca/sumari-del-dogc/?numDOGC=9782",
 "document1057895":"https://dogc.gencat.cat/es/document-del-dogc/?documentId=1057895",
 "home":"https://dogc.gencat.cat/ca/inici/"
}
for name,url in urls.items():
 try:
  r=requests.get(url,timeout=(7,22),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"ca,es;q=0.8"})
  html=r.text
  h=BeautifulSoup(html,"html.parser")
  embeds=[{"tag":x.name,"src":x.get("src"),"data":{k:v for k,v in x.attrs.items() if k not in ("src","class","style")}} for x in h.select("iframe,object,embed")]
  scripts=[{"src":x.get("src"),"inline":x.get_text()[:650] if x.get("src") is None else ""} for x in h.select("script")]
  selectors=[{"tag":x.name,"id":x.get("id"),"class":x.get("class"),"inner":x.get_text(" ",strip=True)[:230]} for x in h.find_all(["div","section","form"]) if re.search("dogc|sumari|numero|núm|consulta|frame|document|iframe",str(x.get("id",""))+" "+str(x.get("class","")),re.I)]
  positions=[]
  for m in re.finditer("portaldogc|utilsEADOP|documentId|numDOGC|eadop-rest|iframe|sumari-del-dogc",html,re.I):
   positions.append(html[max(0,m.start()-120):m.end()+170].replace("\n"," ")[:320])
  obj={"name":name,"http":r.status_code,"len":len(html),"embeds":embeds[:28],
   "scripts":scripts[-35:],"selectors":selectors[:33],"related_fragments":positions[-65:]}
  print("DOGC_BACKEND_DIAG",json.dumps(obj,ensure_ascii=True),flush=True)
 except Exception as exc:print("DOGC_BACKEND_ERROR",name,type(exc).__name__,str(exc)[:200])
