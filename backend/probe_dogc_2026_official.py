#!/usr/bin/env python3
"""DOGC first-party original issue discovery; never mark coverage by a single PDF."""
import requests,concurrent.futures,platform,json,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlsplit
TARGETS={
 "dogc_home":"https://dogc.gencat.cat/ca/inici/",
 "dogc_es":"https://dogc.gencat.cat/es/inici/",
 "dogc_issue_web":"https://dogc.gencat.cat/ca/dogc-por-data/",
 "dogc_document_2026":"https://dogc.gencat.cat/es/document-del-dogc/?documentId=1057895",
 "dogc_full_9782":"https://portaldogc.gencat.cat/utilsEADOP/AppJava/PdfProviderServlet?dogcId=9782&language=ca_ES&anexos=1",
 "dogc_full_9781":"https://portaldogc.gencat.cat/utilsEADOP/AppJava/PdfProviderServlet?dogcId=9781&language=ca_ES&anexos=1",
 "dogc_pdf_original":"https://portaldogc.gencat.cat/utilsEADOP/AppJava/PdfProviderServlet?documentId=1036015&type=01&language=ca_ES",
 "dogc_static_9782":"https://portaldogc.gencat.cat/utilsEADOP/PDF/9782/9782.pdf",
 "dogc_index_portal":"https://portaldogc.gencat.cat/utilsEADOP/AppJava/Index",
 "dogc_legacy":"https://www.gencat.cat/dogc/index.htm",
}
def inspect(pair):
 k,url=pair
 try:
  r=requests.get(url,stream=True,timeout=(6,13),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"ca,es;q=0.9"},allow_redirects=True)
  raw=b""
  for ch in r.iter_content(8192):
   raw+=ch
   if len(raw)>130000:break
  r.close()
  o={"name":k,"http":r.status_code,"final":r.url,"mime":r.headers.get("Content-Type",""),"partial_size":len(raw),"pdf":raw.startswith(b"%PDF-"),"official":(urlsplit(r.url).hostname or "").endswith("gencat.cat")}
  if not o["pdf"]:
   h=BeautifulSoup(raw,"html.parser")
   o["title"]=h.title.get_text(" ",strip=True)[:160] if h.title else ""
   o["text"]=h.get_text(" ",strip=True)[:370]
   o["links"]=[(a.get_text(" ",strip=True)[:70],urljoin(r.url,a.get("href",""))[:165]) for a in h.select("a[href]") if re.search("DOGC|2026|9782|sumari|sumario|número|numero|diari|data|data|consulta",a.get_text(" ",strip=True)+" "+a.get("href",""),re.I)][:22]
  return o
 except Exception as e:return {"name":k,"error":type(e).__name__+":"+str(e)[:160]}
print("HOST",platform.platform(),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
 for x in pool.map(inspect,TARGETS.items()):print("DOGC_OFFICIAL_PROBE",json.dumps(x,ensure_ascii=True),flush=True)
print("TRANSPORT_ONLY: run full date, issue, sumario, originality and article audit before claiming DOGC",flush=True)
