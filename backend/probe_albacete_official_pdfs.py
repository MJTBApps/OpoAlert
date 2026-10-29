#!/usr/bin/env python3
"""Probe publisher-owned BOP Albacete archival PDFs and legacy RSS.

This is only source discovery. Historical PDF filenames are tentative and
must be independently checked against publisher calendar, date and issue number.
"""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import quote
import requests,time,json
CANDIDATES={
 "control_2025":"https://www.dipualba.es/bop/ficheros/2025/116/BOP%20116-25-P.PDF",
 "control2025_newhost":"https://web.dipualba.es/bop/ficheros/2025/116/BOP%20116-25-P.PDF",
 "rss_www":"https://www.dipualba.es/webbop/rss.aspx",
 "rss_web":"https://web.dipualba.es/webbop/rss.aspx",
 "portal_www":"https://www.dipualba.es/bop/",
 "portal_web":"https://web.dipualba.es/bop/",
 "host_old":"https://www.dipualba.es/webbop/",
 "host_new":"https://web.dipualba.es/webbop/",
 "new_root":"https://bop.dipualba.es/",
 "old_path":"https://www.dipualba.es/bop/2026",
 "new_rss":"https://bop.dipualba.es/rss",
 "sede_bop":"https://sede.dipualba.es/portafirmas",
 "pdf_299623":"https://bop.dipualba.es/servicesajax/descargararchivopaginaBOP/299623"
}
for num in (116,118,120,122,124,125,126,127,128,130):
 for domain in ("www.dipualba.es", "web.dipualba.es"):
  code="pdf2026_"+str(num)+"_"+domain.split(".")[0]
  CANDIDATES[code]=f"https://{domain}/bop/ficheros/2026/{num}/BOP%20{num}-26-P.PDF"
def run(pair):
 name,url=pair
 try:
  s=requests.Session()
  s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
  r=s.get(url,timeout=(5,13),stream=True,allow_redirects=True)
  b=b""
  for chunk in r.iter_content(8192):
   b+=chunk
   if len(b)>=700:break
  r.close()
  return {"name":name,"status":r.status_code,"url":r.url,"contentType":r.headers.get("content-type"),
          "contentLength":r.headers.get("content-length"),"pdf":b.startswith(b"%PDF-"),
          "sample":repr(b[:100])}
 except Exception as ex:return {"name":name,"error":type(ex).__name__+": "+str(ex)[:180]}
with ThreadPoolExecutor(max_workers=10) as pool:
 for result in pool.map(run,CANDIDATES.items()):
  print("ALBACETE_PDF_PROBE",json.dumps(result,ensure_ascii=False),flush=True)
