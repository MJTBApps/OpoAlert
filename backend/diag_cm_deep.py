#!/usr/bin/env python3
"""Investigate Melilla issue structured notices, headings, CVE PDF and Ceuta alternative official access."""
import requests,re,json,concurrent.futures
from urllib.parse import urljoin
from bs4 import BeautifulSoup
TARGETS=[
("BOME_6426","https://bomemelilla.es/bome/BOME-B-2026-6426"),
("BOME_EXTRA_48","https://bomemelilla.es/bome/BOME-BX-2026-48"),
("BOME_EXTRA_43","https://bomemelilla.es/bome/BOME-BX-2026-43"),
("BOME_6423","https://bomemelilla.es/bome/BOME-B-2026-6423"),
("BOME_6426_PDF","https://bomemelilla.es/bome/descargar/BOME-B-2026-6426.pdf"),
("BOME_1203_PDF","https://bomemelilla.es/bome/descargar/BOME-A-2026-1203.pdf"),
("CEUTA_NO_WWW","https://ceuta.es/ceuta/bocce"),
("CEUTA_HTTP","http://www.ceuta.es/ceuta/bocce"),
("CEUTA_HTTPS_IP","https://www.ceuta.es/ceuta/component/jdownloads/finish/1980-septiembre/23254-bocce-6650-08-09-2026?Itemid=0"),
("CEUTA_SEDE","https://sede.ceuta.es"),
("CEUTA_DNS","https://www.ceuta.es"),
]
def run(target):
 name,url=target
 try:
  r=requests.get(url,timeout=(5,16),allow_redirects=True,stream=True,
       headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"})
  chunks=b""
  for c in r.iter_content(200000):
   chunks+=c
   if len(chunks)>=180000:break
  r.close()
  if "pdf" in r.headers.get("Content-Type","").lower():
   return {"name":name,"status":r.status_code,"url":r.url,"contentType":r.headers.get("Content-Type"),"starts":repr(chunks[:35]),"len":len(chunks)}
  h=BeautifulSoup(chunks,"html.parser")
  data={"name":name,"status":r.status_code,"url":r.url,"len":len(chunks),"title":h.title.get_text(" ",strip=True)[:130] if h.title else "",
   "articleLabels":[(x.name,x.get_text(" ",strip=True)[:210]) for x in h.find_all(["h1","h2","h3","h4","h5","blockquote"])[:34]],
   "selectors":[(sel,len(h.select(sel))) for sel in ["article","blockquote","ul > li","li","h5","h6","a[href$='.pdf']","a[href*='articulo']",".entry-content","[class*=articulo]"]],
   "pdfs":[(a.get_text(" ",strip=True)[:55],urljoin(r.url,a["href"])) for a in h.select("a[href$='.pdf']")[:15]],
   "sample":h.get_text(" ",strip=True)[:1200]}
  if name.startswith("BOME"):
   snippets=[{"h":str(x)[:450],"parent":str(x.parent)[:1400]} for x in h.select("h5")[:2]]
   data["snippets"]=snippets
  return data
 except Exception as e:return {"name":name,"error":repr(e)[:260]}
with concurrent.futures.ThreadPoolExecutor(max_workers=9) as ex:
 for row in ex.map(run,TARGETS):print("CM_DEEP",json.dumps(row,ensure_ascii=False)[:13000],flush=True)
