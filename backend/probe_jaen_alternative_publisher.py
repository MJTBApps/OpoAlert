#!/usr/bin/env python3
"""Cross-check official Jaén BOP records on Diputación's alternate hemeroteca host.

No private/secondary sources. Tests public read-only search, original PDFs and
archive pagination. Do not infer missing issues unless the originals verify.
"""
import requests,json,concurrent.futures,re,math
from bs4 import BeautifulSoup
from urllib.parse import urlsplit
ROOTS={
"dip_www":"https://www.dipujaen.es/hemerotecadigital/",
"dip_naked":"https://dipujaen.es/hemerotecadigital/",
"dip_hemeroteca":"https://www.dipujaen.es/hemeroteca/",
"dip_bop":"https://www.dipujaen.es/bop/",
"dip_bopdigital":"https://www.dipujaen.es/bopdigital/",
"existing":"https://bophistorico.dipujaen.es/",
"new_bop":"https://bop.dipujaen.es/"
}
ITEMS=[]
for key,root in ROOTS.items():
 ITEMS.append((key+"_root",root))
 if key in ("dip_www","dip_naked","existing"):
  ITEMS.append((key+"_archive",root+"results.vm?q=parent:0000395018&view=boletin"))
  ITEMS.append((key+"_known_pdf",root+"high.raw?id=0001730629&name=00000001.original.pdf&attachment=0001730629.pdf"))
def go(item):
 name,u=item
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
   r=s.get(u,timeout=(7,15),allow_redirects=True,stream=True)
   data=b""
   for part in r.iter_content(8192):
    data+=part
    if len(data)>200000:break
   r.close()
   o={"name":name,"http":r.status_code,"url":r.url,"ct":r.headers.get("Content-Type",""),
      "bytes":len(data),"pdf":data.startswith(b"%PDF-")}
   if not o["pdf"]:
    soup=BeautifulSoup(data,"html.parser")
    o["title"]=soup.title.get_text(" ",strip=True)[:110] if soup.title else ""
    o["count"]=re.findall(r"Resultados:\s*[\d.]+",soup.get_text(" ",strip=True))[:1]
    o["cards"]=[{"id":c.get("id"),"text":c.get_text(" ",strip=True)[:160]} for c in soup.select("div.list-frame")[:3]]
    o["head"]=soup.get_text(" ",strip=True)[:280]
   return o
 except Exception as ex:return {"name":name,"error":type(ex).__name__+":"+str(ex)[:180]}
with concurrent.futures.ThreadPoolExecutor(max_workers=9) as pool:
 for o in pool.map(go,ITEMS):print("JAEN_ALT_PUBLISHER",json.dumps(o,ensure_ascii=True),flush=True)
