#!/usr/bin/env python3
"""Explore alternate first-party Ceuta hosts for official October 2026 BOCCE PDFs.

Uses a known official BOCCE PDF path (n. 6657, 02/10/2026) and publisher
document indexes, not a secondary scraped summary. A valid PDF must begin
with %PDF- and later be checked for date, number and contents.
"""
from concurrent.futures import ThreadPoolExecutor
import requests,json
PDF="/ceuta/component/jdownloads/finish/1982-octubre/23280-bocce-6657-02-10-2026?Itemid=534"
hosts=[
 "www.ceuta.es","ceuta.es","www2.ceuta.es","www3.ceuta.es",
 "sede.ceuta.es","webs.ceuta.es","www.sede.ceuta.es",
 "www.ceuta.com","transparencia.ceuta.es","datosabiertos.ceuta.es",
]
targets=[(f"{x}-pdf",f"https://{x}{PDF}") for x in hosts]
targets+=[
 ("ceuta-docs","https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1982-octubre?Itemid=534"),
 ("ceuta-index","https://www.ceuta.es/ceuta/bocce"),
 ("sede-boletines","https://sede.ceuta.es/controlador/controlador?cmd=publicacion&modulo=principal"),
 ("bocce-other","https://bocce.ceuta.es/"),
 ("sede-no-www","https://sede.ceuta.es/"),
 ("http-pdf","http://www.ceuta.es"+PDF),
 ("www-http-index","http://www.ceuta.es/ceuta/bocce")
]
def check(pair):
 name,url=pair
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0 (OpoAlert; audit of public BOCCE sources)","Accept-Language":"es-ES,es;q=0.9"})
   r=s.get(url,timeout=(6,13),stream=True,allow_redirects=True)
   b=b""
   for part in r.iter_content(8192):
    b+=part
    if len(b)>2700:break
   r.close()
   return {"name":name,"status":r.status_code,"url":r.url,"type":r.headers.get("content-type",""),
           "size":r.headers.get("content-length"),"pdf":b.startswith(b"%PDF-"),
           "head":repr(b[:110]) if not b.startswith(b"%PDF-") else ""}
 except Exception as e:return {"name":name,"error":type(e).__name__+": "+str(e)[:170]}
with ThreadPoolExecutor(max_workers=14) as ex:
 for r in ex.map(check,targets):print("CEUTA_OFFICIAL_HOST",json.dumps(r,ensure_ascii=True),flush=True)
