#!/usr/bin/env python3
"""Evaluate public publisher mirror for BOP Salamanca: date/CVE/PDF consistency."""
import requests,concurrent.futures,json,io,re
from bs4 import BeautifulSoup
from pypdf import PdfReader
from urllib.parse import urlsplit
DATES=["20260930","20261001","20261002","20261005","20261009","20261012","20261016","20261022","20261028","20261029"]
TASKS=[(day,1) for day in DATES]
TASKS +=[("20261028",i) for i in range(2,27)]
TASKS +=[("20261016",i) for i in (2,3,4,5,8,12,16,20)]
BASE="https://www.lasalina.es/documentacion/bop/2026/{day}/BOP-SA-{day}-{number:03}.pdf"
def one(item):
 day,num=item
 url=BASE.format(day=day,number=num)
 try:
  r=requests.get(url,timeout=(6,18),headers={"User-Agent":"Mozilla/5.0","Accept":"application/pdf"},stream=True,allow_redirects=False)
  body=b""
  for chunk in r.iter_content(4096):
   body+=chunk
   if len(body)>1000000:break
  r.close()
  o={"day":day,"number":num,"status":r.status_code,"size":len(body),"total":r.headers.get("Content-Length"),"pdf":body.startswith(b"%PDF-")}
  if o["pdf"] and (num<=4 or num in (10,20)):
   try:
    pdf=PdfReader(io.BytesIO(body),strict=False)
    t=pdf.pages[0].extract_text() or ""
    o["pages"]=len(pdf.pages)
    o["CVE"]=re.findall(r"(?i)(?:CVE|C.V.E.).{0,15}(BOP-SA-\d{8}-\d{3})",t)[:3]
    o["head"]=repr(t[:820])
   except Exception as ex:o["parse_error"]=type(ex).__name__+":"+str(ex)[:130]
  return o
 except Exception as e:return {"day":day,"number":num,"error":type(e).__name__+":"+str(e)[:180]}
with concurrent.futures.ThreadPoolExecutor(max_workers=7) as ex:
 for result in ex.map(one,TASKS):
  print("SA_DOCUMENT",json.dumps(result,ensure_ascii=False)[:2350],flush=True)
try:
 r=requests.get("https://www.lasalina.es/Aplicaciones/GestorInter.jsp?funcion=MenuIzquierda&prestacion=Boletines",timeout=20)
 soup=BeautifulSoup(r.content,"html.parser")
 for tab in soup.find_all("table"):
  if re.search("octubre 2026|septiembre 2026",tab.get("summary",""),re.I):
   print("SA_LEGACY_CALENDAR",str(tab)[:8500],flush=True)
except Exception as e:print("SA_LEGACY_ERR",type(e).__name__,str(e)[:170],flush=True)
