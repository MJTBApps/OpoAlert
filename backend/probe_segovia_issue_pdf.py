#!/usr/bin/env python3
"""Inspect Segovia BOP public detail and original PDF for Sep 30 and Oct 28."""
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlsplit
from pypdf import PdfReader
from io import BytesIO
import requests,re,json
base="https://www.dipsegovia.es/bop"
q="?p_r_p_startDate=30%2F09%2F2026&p_r_p_endDate=30%2F09%2F2026"
urls=[("sep30",base+q),("oct",base)]
s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0"})
for key,url in urls:
 print("\nISSUE_PAGE",key,url,flush=True)
 r=s.get(url,timeout=(8,22));h=BeautifulSoup(r.content,"html.parser")
 print("ISSUE_HTTP",r.status_code,len(r.content),flush=True)
 cards=h.select("div.card.card-box")
 card=next((x for x in cards if ("30 de septiembre" if key=="sep30" else "28 de octubre") in x.get_text(" ",strip=True).lower()),None)
 if not card:
  print("ISSUE_MISSING",len(cards),flush=True);continue
 print("ISSUE_CARD",str(card)[:9000],flush=True)
 a=card.select_one('a[href*="articleId"]')
 if not a:print("ARTICLE_MISSING",flush=True);continue
 detail=urljoin(r.url,a.get("href"))
 dr=s.get(detail,timeout=(8,27));d=BeautifulSoup(dr.content,"html.parser")
 print("DETAIL",dr.status_code,len(dr.content),detail,flush=True)
 main=d.select_one("main") or d.select_one(".portlet-content") or d.body
 print("DETAIL_TITLE",d.title.get_text(" ",strip=True) if d.title else "",flush=True)
 print("DETAIL_HEADINGS",[(x.name,x.get_text(" ",strip=True)[:170]) for x in main.select("h1,h2,h3,h4")[:35]],flush=True)
 print("DETAIL_TEXT",main.get_text(" ",strip=True)[-5500:],flush=True)
 anchors=[]
 for a in d.select("a[href]"):
  href=urljoin(detail,a.get("href"))
  if ("document" in href.lower() or "pdf" in href.lower() or "bop" in a.get_text(" ",strip=True).lower()):
   anchors.append((a.get_text(" ",strip=True)[:125],href[:320]))
 print("DETAIL_DOCUMENT_LINKS",json.dumps(anchors[-45:],ensure_ascii=False),flush=True)
 pdfs=[]
 for title,pdf in anchors:
  if "documents/" in pdf and any(x in (title+" "+pdf).lower() for x in ("bop","bolet","pdf","anunci")):pdfs.append((title,pdf))
 for title,pdf in pdfs[:3]:
  try:
   resp=s.get(pdf,timeout=(10,35))
   print("CANDIDATE_PDF",title,resp.status_code,resp.headers.get("content-type"),len(resp.content),repr(resp.content[:18]),flush=True)
   if resp.content.startswith(b"%PDF-"):
    reader=PdfReader(BytesIO(resp.content))
    print("PDF_PAGE_COUNT",len(reader.pages),flush=True)
    for i in range(min(5,len(reader.pages))):
     txt=reader.pages[i].extract_text() or ""
     print("PDF_TEXT_SAMPLE",i,repr(txt[:6700]),flush=True)
  except Exception as ex:print("PDF_ERROR",type(ex).__name__,str(ex)[:240],flush=True)
