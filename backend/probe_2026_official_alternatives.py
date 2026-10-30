#!/usr/bin/env python3
"""Read-only first-party alternative source probe for OpoAlert.
Investigate only public official domains. No feed, archive, coverage or APK
is enabled by this transport diagnostic. Check 30 days separately.
"""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
import json, platform, requests, time

TARGETS = {
  "AB_official_archive_root": "https://www.dipualba.es/bop/",
  "AB_official_legacy_rss": "https://www.dipualba.es/webbop/rss.aspx",
  "AB_official_pdf_control_2025": "https://www.dipualba.es/bop/ficheros/2025/116/BOP%20116-25-P.PDF",
  "AB_official_pdf_guess_118_2026": "https://www.dipualba.es/bop/ficheros/2026/118/BOP%20118-26-P.PDF",
  "AB_official_pdf_guess_120_2026": "https://www.dipualba.es/bop/ficheros/2026/120/BOP%20120-26-P.PDF",
  "AB_official_pdf_guess_125_2026": "https://www.dipualba.es/bop/ficheros/2026/125/BOP%20125-26-P.PDF",
  "AS_official_2026_csv": "https://descargas.asturias.es/asturias/opendata/LegislacionyJusticia/BOPA2019-28/dataset-sum-bopa-2026.csv",
  "AS_official_2026_xml": "https://descargas.asturias.es/asturias/opendata/LegislacionyJusticia/BOPA2019-28/dataset-sum-bopa-2026.xml",
  "AS_official_2026_json": "https://descargas.asturias.es/asturias/opendata/LegislacionyJusticia/BOPA2019-28/dataset-sum-bopa-2026.json",
  "LD_official_bop": "https://ebop.diputaciolleida.cat/",
  "LD_official_catalogue": "https://www.diputaciolleida.cat/ca/arees/area-darxius-estudis-i-informacio/recursos-i-subvencions/consultas-en-linia/butlleti-oficial-de-la-provincia-bop",
  "CB_official_original_control": "https://boc.cantabria.es/boces/verAnuncioAction.do?idAnuBlob=427404",
  "NA_official_legacy": "https://www.cfnavarra.es/BON/BONIDX.HTM",
  "CE_official_october": "https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1982-octubre?Itemid=534",
  "JA_official_archive": "https://www.dipujaen.es/hemerotecadigital/",
}
def inspect(arg):
 name,url=arg
 stamp=time.monotonic()
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert official archive diagnostic)",
                    "Accept-Language":"es-ES,es;q=0.9"})
   r=s.get(url,allow_redirects=True,timeout=(5,13),stream=True)
   raw=b""
   for part in r.iter_content(chunk_size=8192):
    raw+=part
    if len(raw)>=160000:break
   r.close()
   mime=r.headers.get("Content-Type","")
   text=raw[:6000].decode("utf-8","replace")
   return {"test":name, "status":r.status_code,"url":r.url,
    "official_host":urlsplit(url).hostname==urlsplit(r.url).hostname,
    "mime":mime,"sample_size":len(raw),"pdf":raw.startswith(b"%PDF-"),
    "html":b"<html" in raw[:1000].lower() or b"<!doctype" in raw[:1000].lower(),
    "security":any(x in text.lower() for x in ("captcha","turnstile","verification required","verificacion de seguridad","verificación de seguridad")),
    "head":text[:220] if not raw.startswith(b"%PDF-") else "",
    "seconds":round(time.monotonic()-stamp,1)}
 except Exception as ex:
  return {"test":name,"error":type(ex).__name__ + ": " + str(ex)[:180],"seconds":round(time.monotonic()-stamp,1)}
print("RUNNER",platform.platform(),flush=True)
with ThreadPoolExecutor(max_workers=8) as pool:
 results=list(pool.map(inspect,TARGETS.items()))
for x in results:print("ALTERNATIVE",json.dumps(x,ensure_ascii=False),flush=True)
print("OFFICIAL_2026_PDF_ALBACETE",any(x["test"].startswith("AB_official_pdf_guess_") and x.get("status")==200 and x.get("pdf") and x.get("official_host") for x in results),flush=True)
print("OFFICIAL_2026_DATA_BOPA",any(x["test"].startswith("AS_official_2026") and x.get("status")==200 and x.get("official_host") and x.get("sample_size",0)>1000 for x in results),flush=True)
print("DIAGNOSTIC_ONLY: every source still requires a strict independent 30-day audit and original document validation before integration",flush=True)
