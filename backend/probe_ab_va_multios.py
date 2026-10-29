#!/usr/bin/env python3
"""Read-only cross-platform probe of two provincial BOP publisher hosts.

Every apparent success must provide official 2026 issues and originals. The
probe does not mark a region as covered and never eludes human verification.
"""
import requests,concurrent.futures,platform,json,re
from bs4 import BeautifulSoup
URLS={
 "AB_home":"https://bop.dipualba.es/",
 "AB_view":"https://bop.dipualba.es/consulta",
 "AB_view2":"https://bop.dipualba.es/consulta-bop",
 "AB_legacy":"https://www.dipualba.es/webbop/",
 "AB_rss":"https://www.dipualba.es/webbop/rss.aspx",
 "AB_rss2":"https://web.dipualba.es/webbop/rss.aspx",
 "AB_pdf_host":"https://www.dipualba.es/bop/ficheros/2026/120/BOP%20120-26-P.PDF",
 "AB_pdf_host2":"https://web.dipualba.es/bop/ficheros/2026/120/BOP%20120-26-P.PDF",
 "AB_institution":"https://web.dipualba.es/",
 "AB_sede":"https://sede.dipualba.es/",
 "VA_home":"https://bop.sede.diputaciondevalladolid.es/",
 "VA_cal":"https://bop.sede.diputaciondevalladolid.es/calendario",
 "VA_today":"https://bop.sede.diputaciondevalladolid.es/ultimobop",
 "VA_pdf":"https://bop.sede.diputaciondevalladolid.es/boletines/2026/octubre/08/BOPVA-A-2026-02920.pdf",
 "VA_sede":"https://www.sede.diputaciondevalladolid.es/",
 "VA_bopinfo":"https://www.sede.diputaciondevalladolid.es/web/guest/ov/bop",
 "VA_bopinfo2":"https://www.sede.diputaciondevalladolid.es/web/guest/bop",
 "VA_pdf_sede":"https://www.sede.diputaciondevalladolid.es/boletines/2026/octubre/08/BOPVA-A-2026-02920.pdf",
 "VA_pdf_registro":"https://sede.diputaciondevalladolid.es/boletines/2026/octubre/08/BOPVA-A-2026-02920.pdf",
 "VA_pdf_dipu":"https://www.diputaciondevalladolid.es/boletines/2026/octubre/08/BOPVA-A-2026-02920.pdf",
}
def probe(item):
 k,u=item
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert source-health-check/1.0)","Accept-Language":"es-ES,es;q=0.9"})
   r=s.get(u,timeout=(6,12),stream=True,allow_redirects=True)
   b=b""
   for chunk in r.iter_content(8192):
    b+=chunk
    if len(b)>110000:break
   r.close()
   d={"key":k,"status":r.status_code,"url":r.url,"contentType":r.headers.get("content-type",""),
      "size":len(b),"pdf":b.startswith(b"%PDF-")}
   if not d["pdf"]:
    h=BeautifulSoup(b,"html.parser")
    d["title"]=h.title.get_text(" ",strip=True)[:130] if h.title else ""
    d["sample"]=h.get_text(" ",strip=True)[:260]
    d["links"]=[(a.get_text(" ",strip=True)[:45],a.get("href","")[:200]) for a in h.select("a[href]") if re.search(r"bolet|bop|2026|sumario|pdf",str(a),re.I)][:16]
   return d
 except Exception as e:return {"key":k,"error":type(e).__name__+": "+str(e)[:185]}
print("RUNNER",platform.platform(),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=16) as pool:
 for x in pool.map(probe,URLS.items()):
  print("AB_VA_ALT",json.dumps(x,ensure_ascii=False)[:5500],flush=True)
