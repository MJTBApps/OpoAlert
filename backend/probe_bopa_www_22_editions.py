#!/usr/bin/env python3
"""Official BOPA alternate publisher host - issue PDF availability and summary paths.

Only verified public HTTPS under asturias.es. If URL resolves to unrelated
HTML or other date, it is explicitly rejected. No private aggregator.
"""
import concurrent.futures, requests, json, re, time
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
SAMPLES={
 "189/2026-09-30":"2026-07732", "190/2026-10-01":"2026-07765",
 "191/2026-10-02":"2026-07781", "192/2026-10-05":"2026-07831",
 "193/2026-10-06":"2026-07857", "194/2026-10-07":"2026-07919",
 "195/2026-10-08":"2026-07937", "196/2026-10-09":"2026-07971",
 "197/2026-10-12":"2026-08339", "198/2026-10-13":"2026-08032",
 "199/2026-10-14":"2026-08071", "200/2026-10-15":"2026-07852",
 "201/2026-10-16":"2026-08165", "202/2026-10-19":"2026-08202",
 "203/2026-10-20":"2026-08241", "204/2026-10-21":"2026-08288",
 "205/2026-10-22":"2026-08335", "206/2026-10-23":"2026-08382",
 "207/2026-10-26":"2026-08421", "208/2026-10-27":"2026-08465",
 "209/2026-10-28":"2026-08442", "210/2026-10-29":"2026-08563"
}
TARGETS={}
for key,code in SAMPLES.items():
 number,day=key.split("/")
 TARGETS["PDF_"+number]="https://www.asturias.es/bopa/"+day.replace("-","/")+"/"+code+".pdf"
TARGETS.update({
 "WWW_BOPA_SUMARIO":"https://www.asturias.es/ast/bopa-sumario?p_p_id=pa_sede_bopa_web_portlet_SedeBopaSummaryWeb&p_p_lifecycle=0&p_r_p_summaryDate=29%2F10%2F2026&p_r_p_summaryIsSearch=false",
 "WWW_BOPA_ES":"https://www.asturias.es/es/bopa-sumario?p_p_id=pa_sede_bopa_web_portlet_SedeBopaSummaryWeb&p_p_lifecycle=0&p_r_p_summaryDate=29%2F10%2F2026&p_r_p_summaryIsSearch=false",
 "WWW_OLD_BOPA":"https://www.asturias.es/bopa",
 "WWW_BOPA2":"https://www.asturias.es/bopa/bopa2",
 "WWW_BOPA_DATA":"https://www.asturias.es/asturias/opendata/LegislacionyJusticia/BOPA2019-28/dataset-sum-bopa-2026.json",
 "WWW_BOPA_ISSUE_PDF":"https://www.asturias.es/bopa/2026/10/29/2026-08847.pdf",
})
def run(item):
 k,url=item;tick=time.monotonic()
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert publisher original audit)",
    "Accept-Language":"es-ES,es;q=0.9"})
   with s.get(url,timeout=(6,17),stream=True,allow_redirects=True) as r:
    b=b""
    for ch in r.iter_content(16384):
     b+=ch
     if len(b)>240000:break
    p=urlsplit(r.url); official=p.scheme=="https" and (p.hostname=="www.asturias.es")
    html=BeautifulSoup(b,"html.parser") if not b.startswith(b"%PDF-") else None
    return {"test":k,"http":r.status_code,"final":r.url,"official":official,"pdfHeader":b.startswith(b"%PDF-"),
      "mime":r.headers.get("Content-Type",""),"sizeSample":len(b),
      "title":html.title.get_text(" ",strip=True)[:100] if html and html.title else "",
      "head":html.get_text(" ",strip=True)[:170] if html else "",
      "elapsed":round(time.monotonic()-tick,1)}
 except Exception as e:return {"test":k,"error":type(e).__name__+":"+str(e)[:180],"elapsed":round(time.monotonic()-tick,1)}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 res=list(pool.map(run,TARGETS.items()))
for x in res:print("BOPA_WWW",json.dumps(x,ensure_ascii=True),flush=True)
pdfs=[x for x in res if x["test"].startswith("PDF_")]
print("OFFICIAL_PDF_ISSUES",sum(x.get("pdfHeader") and x.get("http")==200 and x.get("official") for x in pdfs),"/",len(pdfs),flush=True)
print("PROBE_ONLY: 22 PDF samples do not certify the 917 original links",flush=True)
