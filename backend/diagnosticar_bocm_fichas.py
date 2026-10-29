#!/usr/bin/env python3
"""Probe official BOCM item JSON and HTML notice elements for emergency XML fallback."""
import requests,concurrent.futures,json,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
items=[
 ("json-extra","https://www.bocm.es/boletin/CM_Orden_BOCM/2026/10/28/BOCM-20261028-37.json"),
 ("json-normal","https://www.bocm.es/boletin/CM_Orden_BOCM/2026/10/28/BOCM-20261028-2.json"),
 ("html-extra","https://www.bocm.es/boletin-completo/BOCM-20261028/259"),
 ("html-normal","https://www.bocm.es/boletin-completo/BOCM-20261028/258"),
]
def one(item):
 key,url=item
 try:
  r=requests.get(url,timeout=(8,18),headers={"User-Agent":"Mozilla/5.0"})
  print("\n",key,r.status_code,"LEN",len(r.content),"MIME",r.headers.get("content-type"),flush=True)
  if key.startswith("json"):
   print("HEAD",r.text[:6000],flush=True)
   return
  h=BeautifulSoup(r.content,"html.parser")
  a=next((x for x in h.select('a[href]') if re.search(r"/CM_Orden_BOCM/.+\.PDF",x.get("href",""),re.I)),None)
  if a:
   node=a
   for level in range(1,6):
    node=node.parent
    print("PARENT",level,node.name,node.get("class"),str(node)[:3600],flush=True)
  print("ALL_HEADINGS",[(x.name,x.get_text(" ",strip=True)[:200]) for x in h.select("h1,h2,h3,h4")[:15]],flush=True)
 except Exception as ex:print("ERROR",key,type(ex).__name__,str(ex)[:180],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as p:list(p.map(one,items))
