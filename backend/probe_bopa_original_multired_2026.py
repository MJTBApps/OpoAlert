#!/usr/bin/env python3
"""Check original BOPA 2026 PDF + HTML transports from official publisher.
A successful control is NOT 30-day coverage: fetch candidates and audit dates
separately. No login, CAPTCHA bypass or unsafe SSL validation.
"""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
import json, requests, platform, time
TARGETS={
 "pdf_sep30":"https://miprincipado.asturias.es/bopa/2026/09/30/2026-07732.pdf",
 "pdf_oct1":"https://miprincipado.asturias.es/bopa/2026/10/01/2026-07765.pdf",
 "pdf_oct15":"https://miprincipado.asturias.es/bopa/2026/10/15/2026-08390.pdf",
 "pdf_oct29":"https://miprincipado.asturias.es/bopa/2026/10/29/2026-08847.pdf",
 "html_oct29":"https://miprincipado.asturias.es/ast/bopa/disposiciones?p_p_id=pa_sede_bopa_web_portlet_SedeBopaDispositionWeb&p_p_lifecycle=0&_pa_sede_bopa_web_portlet_SedeBopaDispositionWeb_mvcRenderCommandName=%2Fdisposition%2Fdetail&p_r_p_dispositionText=2026-08847&p_r_p_dispositionReference=2026-08847&p_r_p_dispositionDate=29%2F10%2F2026",
 "legacy_pdf":"https://www.asturias.es/bopa/2026/10/29/2026-08847.pdf",
 "sede_pdf":"https://sede.asturias.es/bopa/2026/10/29/2026-08847.pdf",
 "sede2_pdf":"https://sede2.asturias.es/bopa/2026/10/29/2026-08847.pdf",
}
def run(pair):
 name,url=pair;start=time.monotonic()
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert source-integrity test)",
                     "Accept-Language":"es-ES,es;q=0.9"})
   with s.get(url,stream=True,timeout=(6,16),allow_redirects=True) as r:
    body=b""
    for chunk in r.iter_content(8192):
     body+=chunk
     if len(body)>230000:break
    final=urlsplit(r.url)
    off=final.hostname and final.hostname.endswith(".asturias.es")
    soup=BeautifulSoup(body,"html.parser") if not body.startswith(b"%PDF-") else None
    return {"test":name,"http":r.status_code,"url":r.url,"official":bool(off),
      "contentType":r.headers.get("Content-Type",""),"bytesSampled":len(body),
      "pdfHeader":body.startswith(b"%PDF-"),"htmlTitle":soup.title.get_text(" ",strip=True)[:120] if soup and soup.title else "",
      "htmlContainsNotice":("2026-08847" in soup.get_text(" ",strip=True)) if soup else None,
      "elapsedSeconds":round(time.monotonic()-start,2)}
 except Exception as e:
  return {"test":name,"error":type(e).__name__+":"+str(e)[:195],"elapsedSeconds":round(time.monotonic()-start,2)}
print("ENVIRONMENT",platform.platform(),flush=True)
with ThreadPoolExecutor(max_workers=4) as pool:
 for x in pool.map(run,TARGETS.items()):
  print("BOPA_ORIGINAL_TRANSPORT",json.dumps(x,ensure_ascii=True),flush=True)
print("PROBE_ONLY: cannot declare coverage without all summaries + original documents",flush=True)
