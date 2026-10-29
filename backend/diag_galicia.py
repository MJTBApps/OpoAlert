#!/usr/bin/env python3
"""Probe official Galicia DOG and four provincial BOP, read-only."""
import requests,json,re
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from urllib.parse import urljoin
TARGETS=[
("AC-INDEX","https://bop.dacoruna.gal/bopportal/ultimoBoletin?lang=es"),
("AC-DATE","https://bop.dacoruna.gal/bopportal/ultimoBoletin?fecha=28/10/2026"),
("AC-DAY","https://bop.dacoruna.gal/bopportal/publicado/2026/10/29/2026_0000006954.pdf"),
("LU-INDEX","https://deputacionlugo.gal/gl/boletin-oficial-da-provincia-de-lugo/bop"),
("LU-PAGE2","https://deputacionlugo.gal/gl/boletin-oficial-da-provincia-de-lugo/bop?page=2"),
("OU-PORTAL","https://bop.depourense.es/portal/"),
("OU-PORTAL2","https://bop.depourense.es/portal/PORTAL/"),
("OU-ALT","https://dou.gnoss.com/gl/comunidade/dou/busqueda-bop"),
("PO-PORTAL","https://boppo.depo.gal/es/consulta-do-boppo"),
("PO-SEARCH","https://boppo.depo.gal/es/buscas-no-boppo"),
("DOG-HOME","https://www.xunta.gal/diario-oficial-galicia/Welcome.do?lang=es"),
("DOG-DAY","https://www.xunta.gal/diario-oficial-galicia/portalPublicoHome.do?fecha=20261029&lang=es"),
("DOG-INDEX","https://www.xunta.gal/dog/Publicados/2026/20261029/Indice207_es.html"),
("DOG-INDEXPDF","https://www.xunta.gal/dog/Publicados/2026/20261029/Indice207_es.pdf")
]
def inspect(row):
 n,u=row
 try:
  r=requests.get(u,timeout=(10,30),stream=True,headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"},allow_redirects=True)
  content=b""
  for chunk in r.iter_content(100000):
   content+=chunk
   if len(content)>240000:break
  r.close()
  out={"name":n,"status":r.status_code,"url":r.url,"mime":r.headers.get("Content-Type"),"read_bytes":len(content),"size":r.headers.get("Content-Length"),"first":repr(content[:70])}
  if content.startswith(b"%PDF-"):return out
  soup=BeautifulSoup(content,"html.parser")
  out["title"]=soup.title.get_text(" ",strip=True)[:110] if soup.title else ""
  out["headings"]=[(x.name,x.get_text(" ",strip=True)[:155]) for x in soup.select("h1,h2,h3,h4,h5")[:24]]
  out["forms"]=[(x.get("action"),x.get("method"),[(z.name,z.get("name"),z.get("value")) for z in x.select("input[name],select[name]")[:8]]) for x in soup.select("form")[:5]]
  out["links"]=[(a.get_text(" ",strip=True)[:85],urljoin(r.url,a.get("href",""))[:210]) for a in soup.select("a[href]") if re.search(r"2026|10/|pdf|bop|dog|sumario|anuncio|bolet|descarga|publicad",a.get("href","")+" "+a.get_text(" ",strip=True),re.I)][:34]
  out["links_total"]=len(soup.select("a[href]"))
  out["scripts"]=[x.get("src") for x in soup.select('script[src]')][-7:]
  out["text"]=soup.get_text(" ",strip=True)[:500]
  return out
 except Exception as e:return {"name":n,"error":str(e)[:260]}
with ThreadPoolExecutor(max_workers=8) as pool:
 for data in pool.map(inspect,TARGETS):print("GALICIA_DIAG",json.dumps(data,ensure_ascii=False)[:14000],flush=True)
