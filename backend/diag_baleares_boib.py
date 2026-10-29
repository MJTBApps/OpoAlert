#!/usr/bin/env python3
"""Read-only reconnaissance of the BOIB Government portal for 30-day archives."""
import requests,re,json,concurrent.futures
from bs4 import BeautifulSoup
from urllib.parse import urljoin
LINKS=[
("CAIB_CATALAN","https://www.caib.es/eboibfront/"),
("CAIB_SPANISH","https://www.caib.es/eboibfront/es"),
("CAIB_MONTH_OCT","https://www.caib.es/eboibfront/es/2026/mes/9"),
("CAIB_MONTH_SEP","https://www.caib.es/eboibfront/es/2026/mes/8"),
("CAIB_SEP_ALT","https://www.caib.es/eboibfront/es/2026/mes/10"),
("CAIB_CURRENT","https://www.caib.es/eboibfront/es/2026/138"),
("CAIB_API","https://www.caib.es/eboibfront/es/2026/138/seccion/"),
("CAIB_WWWBOIB","https://www.caib.es/boib/index.do"),
("CAIB_ALT","https://caib.es/eboibfront/es"),
]
def probe(item):
 name,url=item
 try:
  r=requests.get(url,timeout=(10,33),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"},allow_redirects=True)
  soup=BeautifulSoup(r.content,"html.parser")
  anchors=[(a.get_text(" ",strip=True)[:90],urljoin(r.url,a.get("href",""))) for a in soup.select("a[href]")]
  dates=[x for x in anchors if re.search(r"bolet|sumari|2026|29|28|30|octubr|septi|BOP|BOIB|pdf",x[0]+" "+x[1],re.I)]
  forms=[(f.get("action"),f.get("method"),[(i.name,i.get("name"),i.get("value")) for i in f.select("input")[:7]]) for f in soup.select("form")[:5]]
  return {"name":name,"status":r.status_code,"url":r.url,"bytes":len(r.content),
  "title":soup.title.get_text(" ",strip=True)[:120] if soup.title else "",
  "heads":[(h.name,h.get_text(" ",strip=True)[:120]) for h in soup.select("h1,h2,h3,h4")[:18]],
  "forms":forms,"links":dates[:30],"allLinks":anchors[:30],
  "sample":soup.get_text(" ",strip=True)[:1400],
  "scripts":[v.get("src") for v in soup.select("script[src]")[-10:]]}
 except Exception as e:return {"name":name,"error":repr(e)[:330]}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for item in pool.map(probe,LINKS):
  print("BOIB_DIAG",json.dumps(item,ensure_ascii=False)[:17500],flush=True)
