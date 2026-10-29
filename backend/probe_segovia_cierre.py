#!/usr/bin/env python3
"""Segovia BOP: official archive pagination and PDF table-of-contents diagnostics."""
import requests,re,io,json
from bs4 import BeautifulSoup
from pypdf import PdfReader
from urllib.parse import urljoin
BASE="https://www.dipsegovia.es/bop"
PREF="_as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm_"
QUERY=[
 ("default",BASE),
 ("sep-month",BASE+"?mes=9&ano=2026"),
 ("month",BASE+"?month=9&year=2026"),
 ("page2",BASE+"?page=2"),
 ("liferay-cur",BASE+"?"+PREF+"cur=2"),
 ("liferay-ym",BASE+"?"+PREF+"month=9&"+PREF+"year=2026"),
 ("liferay-date",BASE+"?"+PREF+"date=2026-09-30"),
]
for name,url in QUERY:
 try:
  r=requests.get(url,timeout=(10,28),headers={"User-Agent":"Mozilla/5.0"})
  h=BeautifulSoup(r.content,"html.parser")
  cards=h.select("div.card.card-box")
  print("SG_PAGE",name,r.status_code,"cards",len(cards),
        "samples",[c.get_text(" ",strip=True)[:100] for c in cards[:3]],
        "end",[c.get_text(" ",strip=True)[:100] for c in cards[-3:]],flush=True)
  if name=="default":
   print("SG_AROUND",repr(r.text[r.text.find("02 de octubre")-300:r.text.find("02 de octubre")+280]),flush=True)
   print("SG_PAGINATOR",json.dumps([str(z)[:2200] for z in h.select(".portlet-content,.pager,.lfr-pagination") if "117" in str(z) or "siguiente" in str(z).lower()][:3],ensure_ascii=False)[:6800],flush=True)
   print("SG_LINKS",[(a.get_text(" ",strip=True)[:35],a.get("href","")[:250]) for a in h.select("a[href]") if re.search(r"mes|month|calendario|siguiente|anteriores|2026|117",a.get("href","")+" "+a.get_text(" ",strip=True),re.I)][-30:],flush=True)
 except Exception as e:print("SG_ERR",name,type(e).__name__,str(e)[:250],flush=True)
detail="https://www.dipsegovia.es/bop?p_p_id=as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm&p_p_lifecycle=0&_as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm_mvcPath=%2Fpublisher%2Fdetail.jsp&_as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm_articleId=20195381"
r=requests.get(detail,timeout=(10,30))
h=BeautifulSoup(r.content,"html.parser")
pdfs=[urljoin(detail,a.get("href")) for a in h.select('a[href*="/documents/39512/"]') if "Nº 118" in a.get_text(" ",strip=True)]
print("SG_PDF_URLS",pdfs,flush=True)
if pdfs:
 p=requests.get(pdfs[0],timeout=(12,45))
 print("SG_PDF_RESP",p.status_code,p.headers.get("Content-Type"),len(p.content),p.content[:8],flush=True)
 if p.content.startswith(b"%PDF-"):
  reader=PdfReader(io.BytesIO(p.content))
  print("SG_PDF_PAGES",len(reader.pages),flush=True)
  for idx in range(min(4,len(reader.pages))):
   print("SG_PDF_TEXT",idx,repr(reader.pages[idx].extract_text()[:2900]),flush=True)
