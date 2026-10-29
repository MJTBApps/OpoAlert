#!/usr/bin/env python3
"""Inspect official BOIB issue and announcement DOM, including extraordinary editions."""
import requests,re,json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
ISSUES=[("29-oct","https://www.caib.es/eboibfront/es/2026/12352/"),
("29-sep","https://www.caib.es/eboibfront/es/2026/12335/"),
("1-oct","https://www.caib.es/eboibfront/es/2026/12336/"),
("1-oct-extra","https://www.caib.es/eboibfront/es/2026/12339/"),
("21-oct-extra","https://www.caib.es/eboibfront/es/2026/12348/")]
def probe(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=(12,42),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
  soup=BeautifulSoup(r.content,"html.parser")
  anchors=[(x.get_text(" ",strip=True)[:145],urljoin(r.url,x.get("href",""))) for x in soup.select("a[href]")]
  hits=[x for x in anchors if re.search(r"pdf|doc|anun|secc|visual|2026|2026|opos|plaza|bolsa|convoc",x[0]+" "+x[1],re.I)]
  sections=[(h.name,h.get("class"),h.get("id"),h.get_text(" ",strip=True)[:210]) for h in soup.select("h1,h2,h3,h4,h5,h6")[:38]]
  output={"name":name,"http":r.status_code,"url":r.url,"len":len(r.content),
  "title":soup.title.get_text(" ",strip=True)[:180] if soup.title else "",
  "sections":sections,"linksCount":len(anchors),"links":hits[:55],"lastLinks":hits[-20:],
  "intro":soup.get_text(" ",strip=True)[:3000],
  "pdflinks":[x for x in anchors if ".pdf" in x[1]][:24],
  "struct":[{"class":x.get("class"),"id":x.get("id"),"text":x.get_text(" ",strip=True)[:160],
   "html":str(x)[:1200]} for x in soup.select("article,li,section") if re.search(r"plaza|opos|convoc|bolsa",x.get_text(" ",strip=True),re.I)][:3]}
  return output
 except Exception as e:return {"name":name,"error":repr(e)[:300]}
with ThreadPoolExecutor(max_workers=5) as p:
 for r in p.map(probe,ISSUES):print("BOIB_ISSUE",json.dumps(r,ensure_ascii=False)[:29000],flush=True)
