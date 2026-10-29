#!/usr/bin/env python3
"""DOGC strict first-party index discovery. Diagnostic only, no coverage declaration."""
import requests,concurrent.futures,json,re
from bs4 import BeautifulSoup
from urllib.parse import urlsplit,urljoin
ROOT="https://dogc.gencat.cat/"
P={
 "new_9782":"https://dogc.gencat.cat/ca/sumari-del-dogc/?anexos=1&selectedYear=2026&selectedMonth=10&numDOGC=9782&language=ca_ES",
 "new_9770":"https://dogc.gencat.cat/ca/sumari-del-dogc/?anexos=1&selectedYear=2026&selectedMonth=10&numDOGC=9770&language=ca_ES",
 "old_9693":"https://dogc.gencat.cat/ca/sumari-del-dogc/?anexos=1&selectedYear=2026&selectedMonth=6&numDOGC=9693&language=ca_ES",
 "short_9782":"https://dogc.gencat.cat/ca/sumari-del-dogc/?numDOGC=9782",
 "index_9782":"https://dogc.gencat.cat/ca/sumari-del-dogc/index.html?numDOGC=9782",
 "es_9782":"https://dogc.gencat.cat/es/sumari-del-dogc/?anexos=1&selectedYear=2026&selectedMonth=10&numDOGC=9782&language=es_ES",
 "es_9770":"https://dogc.gencat.cat/es/sumari-del-dogc/?numDOGC=9770",
 "2026_document":"https://dogc.gencat.cat/es/document-del-dogc/?documentId=1057895"
}
def task(t):
 name,url=t
 try:
  r=requests.get(url,timeout=(7,20),headers={"User-Agent":"Mozilla/5.0 (compatible; OpoAlert official DOGC read-only issue discovery)","Accept-Language":"ca,es;q=0.9"})
  h=BeautifulSoup(r.content[:550000],"html.parser"); raw=h.get_text(" ",strip=True)
  links=[{"title":a.get_text(" ",strip=True)[:110],"url":urljoin(r.url,a["href"])} for a in h.select("a[href]") if re.search("documentId|document-del-dogc|portal|sumari|DOGC|anunci|resoluci|pdf|documento",a.get("href","")+" "+a.get_text(" ",strip=True),re.I)]
  return {"name":name,"http":r.status_code,"final":r.url,"bytes":len(r.content),"title":h.title.get_text(" ",strip=True)[:140] if h.title else "",
    "mentions9782":"9782" in raw,"mentions2026":"2026" in raw,"mentionsDOGC":"diari oficial" in raw.lower(),
    "notices":len(links),"body_head":raw[:900],"body_tail":raw[-350:],"links":links[-35:]}
 except Exception as ex:return {"name":name,"error":type(ex).__name__+":"+str(ex)[:180]}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for row in pool.map(task,P.items()):
  print("DOGC_SUMARIO_DIAG",json.dumps(row,ensure_ascii=True),flush=True)
print("STRICT_REQUIRES_CALENDAR_AND_ALL_SUMARIOS_AND_ORIGINAL_HTML_XML_VALIDATION",flush=True)
