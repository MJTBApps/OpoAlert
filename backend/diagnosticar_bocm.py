#!/usr/bin/env python3
"""Exploratory diagnostics only for the official Madrid BOCM. Never publish partial data."""
import requests,concurrent.futures,re
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
TARGETS=[
 ("HOME","https://www.bocm.es/"),
 ("HOME-NO-WWW","https://bocm.es/"),
 ("RSS-BOLETINES","https://www.bocm.es/boletines.rss"),
 ("RSS-SUMARIOS","https://www.bocm.es/sumarios.rss"),
 ("ISSUE-DAY-28","https://www.bocm.es/boletin/CM_Boletin_BOCM/2026/10/28/BOCM-20261028.PDF"),
 ("INDEX-DAY-28","https://www.bocm.es/boletin/CM_Sumario_BOCM/2026/10/28/BOCM-20261028.XML"),
 ("XML-DAY-28","https://www.bocm.es/boletin/CM_Sumario_BOCM/2026/10/28/BOCM-20261028.xml"),
 ("ISSUE-DAY-29","https://www.bocm.es/boletin/CM_Boletin_BOCM/2026/10/29/BOCM-20261029.PDF"),
 ("INDEX-DAY-01","https://www.bocm.es/boletin/CM_Sumario_BOCM/2026/10/01/BOCM-20261001.XML"),
 ("NOTICE-PDF","https://www.bocm.es/boletin/CM_Orden_BOCM/2026/10/16/BOCM-20261016-72.PDF"),
 ("BOLETIN-PATH","https://www.bocm.es/boletin/CM_Boletin_BOCM/2026/10/28"),
 ("CALENDAR","https://www.bocm.es/boletines"),
]
def one(x):
 label,url=x
 try:
  resp=requests.get(url,timeout=(8,24),allow_redirects=True,headers={"User-Agent":"Mozilla/5.0 (compatible; OpoAlert verified index)","Accept-Language":"es"})
  head=resp.content[:600000]
  print("\n====",label,resp.status_code,"URL",resp.url,"MIME",resp.headers.get("Content-Type"),"SIZE",len(resp.content),"HEAD",repr(head[:210]),flush=True)
  if head[:4]==b"%PDF":return
  if "<" not in resp.text[:300]:return
  h=BeautifulSoup(head,"html.parser")
  print("TITLE",h.title.get_text(" ",strip=True) if h.title else "-",flush=True)
  print("HEADINGS",[(a.name,a.get_text(" ",strip=True)[:140]) for a in h.select("h1,h2,h3")[:14]],flush=True)
  print("FORMS",[(f.get("action"),f.get("method"),f.get("id")) for f in h.select("form")[:12]],flush=True)
  links=[(a.get_text(" ",strip=True)[:95],urljoin(resp.url,a.get("href",""))) for a in h.select("a[href]") if any(word in (a.get("href","")+" "+a.get_text(" ",strip=True)).lower() for word in ("sumario","boletin","boletín","xml","pdf","boletines.rss","fecha","octubre","2026"))]
  print("OFFICIAL-LINKS",links[:90],flush=True)
  print("SAMPLE-BODY",repr(h.get_text(" ",strip=True)[-2500:]),flush=True)
 except Exception as ex: print("ERROR",label,type(ex).__name__,str(ex)[:250],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:list(pool.map(one,TARGETS))
