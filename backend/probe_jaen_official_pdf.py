#!/usr/bin/env python3
"""Check official BOP Jaen full-PDF download endpoint for missing editions.

A positive match requires PDF header AND matching issue/date inside the
original; this script only discovers possible files, never publishes notices.
"""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode
from io import BytesIO
from pypdf import PdfReader
import requests,json
API="https://bop.dipujaen.es/descargarws.dip"
rows=[
 ("control197","2026-10-09",197),("control200","2026-10-13",200),
 ("control202","2026-10-15",202),
 ("missing198-10oct","2026-10-10",198),
 ("missing198-12oct","2026-10-12",198),
 ("missing199-10oct","2026-10-10",199),
 ("missing199-12oct","2026-10-12",199),
 ("missing199-13oct","2026-10-13",199),
 ("missing201-14oct","2026-10-14",201),
 ("missing201-13oct","2026-10-13",201),
]
def read(row):
 label,date,number=row
 url=API+"?"+urlencode({"boletinSuplemento":0,"ejercicioBop":2026,
                         "fechaBoletin":date,"numeroBoletin":number,"tipo":"bopCompleto"})
 try:
  s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0"})
  r=s.get(url,timeout=(7,15),stream=True)
  b=b""
  for chunk in r.iter_content(8192):
   b+=chunk
   if len(b)>1600000:break
  r.close()
  obj={"label":label,"date":date,"number":number,"status":r.status_code,
       "mime":r.headers.get("Content-Type"),"size":len(b),"pdfHeader":b.startswith(b"%PDF-")}
  if b.startswith(b"%PDF-"):
   try:
    p=PdfReader(BytesIO(b),strict=False)
    obj["pages"]=len(p.pages)
    obj["firstText"]=(p.pages[0].extract_text() or "")[:800]
   except Exception as ex:obj["partialPdfError"]=str(ex)[:120]
  else:obj["head"]=b[:130].decode("utf-8","replace")
  return obj
 except Exception as ex:return {"label":label,"error":type(ex).__name__+": "+str(ex)[:160]}
with ThreadPoolExecutor(max_workers=5) as pool:
 for obj in pool.map(read,rows):print("JAEN_OFFICIAL_PDF",json.dumps(obj,ensure_ascii=False),flush=True)
