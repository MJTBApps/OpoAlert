#!/usr/bin/env python3
"""Analyze BOIB section indices and official document export consistency."""
import requests,json,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
URLS=[
("138-II","https://www.caib.es/eboibfront/es/2026/12352/seccion-ii-autoridades-y-personal/473"),
("138-III","https://www.caib.es/eboibfront/es/2026/12352/seccion-iii-otras-disposiciones-y-actos-administra/472"),
("138-V","https://www.caib.es/eboibfront/es/2026/12352/seccion-v-anuncios/475"),
("122-II","https://www.caib.es/eboibfront/es/2026/12335/seccion-ii-autoridades-y-personal/473"),
("138-PDF","https://www.caib.es/eboibfront/pdf/es/2026/138/sumari/12352"),
("123-PDF","https://www.caib.es/eboibfront/pdf/es/2026/123/1229328"),
("122-PDF","https://www.caib.es/eboibfront/pdf/es/2026/122/1229146"),
("138-ELI-PDF","https://www.caib.es/eboibfront/eli/es-ib/o/2026/10/23/39/dof/spa/pdf"),
]
for name,url in URLS:
 try:
  r=requests.get(url,timeout=(10,34),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"})
  h=BeautifulSoup(r.content,"html.parser")
  l=h.select("ul.resolucions > li")
  boxes=h.select("div.caja")
  pdfs=h.select('a[aria-label="Exportar a PDF"]')
  data={"name":name,"http":r.status_code,"len":len(r.content),"ct":r.headers.get("Content-Type"),"start":repr(r.content[:15]),
     "title":h.title.get_text(" ",strip=True)[:110] if h.title else None,
     "n_resolutions":len(l),"n_boxes":len(boxes),"n_pdfs":len(pdfs),
     "headings":[(z.name,z.get_text(" ",strip=True)[:160]) for z in h.select("h1,h2,h3")[:20]],
     "cases":[{"text":x.get_text(" ",strip=True)[:550],"inner":str(x)[:3800],
               "parent":x.parent.get("class"),"agency":x.find_parent("div",class_="caja").select_one("h3.organisme").get_text(" ",strip=True)[:170] if x.find_parent("div",class_="caja") and x.find_parent("div",class_="caja").select_one("h3.organisme") else "?"} for x in l[:3]],
     "pathSamples":[urljoin(r.url,z.get("href","")) for z in pdfs[:7]],
     "pagination":[(z.get_text(" ",strip=True)[:90],z.get("href")) for z in h.select("a[href]") if re.search(r"page|pagi|siguiente|seg[üu]ent",z.get_text(" ",strip=True)+" "+z.get("href",""),re.I)][:15],
     "sections":[(z.get_text(" ",strip=True)[:70],z.get("href")) for z in h.select('a[href*="/seccion-"]')][:10]}
  print("BOIB_DEEP",json.dumps(data,ensure_ascii=False)[:14500],flush=True)
 except Exception as e:print("BOIB_DEEP_ERROR",name,repr(e)[:350],flush=True)
