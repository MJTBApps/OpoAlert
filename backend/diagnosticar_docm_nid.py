#!/usr/bin/env python3
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests,re
from concurrent.futures import ThreadPoolExecutor
ROOT="https://docm.jccm.es/docm/"
DAYS=["20261001","20261002","20261005","20261006","20261007","20261028-ext-2&numDogv=2"]
def one(day):
 url=ROOT+"cambiarBoletin.do?fecha="+day
 try:
  z=requests.get(url,timeout=(15,24),headers={"User-Agent":"Mozilla/5.0"})
  h=BeautifulSoup(z.content,"html.parser")
  cal=[a.get("href") for a in h.select('a[href*="cambiarBoletin.do?fecha="]') if "-ext-" in a.get("href","")]
  print("\nISSUE",day,z.status_code,"SIZE",len(z.content),"TITLE",h.get_text(" ",strip=True)[300:740],"EXTRA-CALENDAR",cal[:8],flush=True)
  rows=h.select("p.sumario")
  print("ROWS",len(rows),flush=True)
  for p in rows:
   t=p.get_text(" ",strip=True)
   a=p.select_one('a[href*="descargarArchivo.do"]')
   u=urljoin(ROOT,a["href"]) if a else ""
   nid=re.search(r"\[NID\s+(\d{4})/(\d+)\]",t)
   pdf=re.search(r"ruta=(\d{4})/(\d{2})/(\d{2})/pdf/(\d{4})_(\d+)\.pdf",u)
   if not nid or not pdf or pdf.group(1)+pdf.group(2)+pdf.group(3)!=day[:8] or (pdf.group(4),int(pdf.group(5)))!=(nid.group(1),int(nid.group(2))):
    print("MISMATCH",day,"NID",nid.groups() if nid else None,"PDF",pdf.groups() if pdf else None,"URL",u,"TITLE",t[:230],flush=True)
 except Exception as e:print("ERROR",day,type(e).__name__,str(e)[:370],flush=True)
with ThreadPoolExecutor(max_workers=3) as p:list(p.map(one,DAYS))
