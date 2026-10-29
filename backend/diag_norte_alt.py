#!/usr/bin/env python3
"""Read-only alternate official entry-point checks for Cantabria BOC and Asturias BOPA."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests,json,re
URLS=[
("CB-LEGACY","https://boc.gobcantabria.es/boces/"),
("CB-LEGACY2","https://boc.gobcantabria.es/"),
("CB-WWW","https://www.boc.cantabria.es/boces/"),
("CB-WEB","https://www.cantabria.es/web/boc"),
("CB-PORTAL","https://www.cantabria.es/web/boc/boletin-oficial-de-cantabria"),
("CB-SEDE","https://sede.cantabria.es/boc"),
("CB-XML","https://boc.cantabria.es/boces/2026/10/29/"),
("AS-LEGACY","https://www.asturias.es/bopa/"),
("AS-SEDE","https://sede.asturias.es/bopa/"),
("AS-PORTAL","https://sede.asturias.es/bopa"),
("AS-WEB","https://www.asturias.es/bopa/ultimos-boletines"),
("AS-OPENDATA","https://datos.asturias.es/"),
("AS-BOPA-SUM","https://sede.asturias.es/bopa-sumario"),
("AS-DOWNLOAD","https://descargas.asturias.es/"),
("AS-ALT-WWW","https://www.miprincipado.asturias.es/bopa/"),
]
def probe(it):
 name,u=it
 try:
  r=requests.get(u,timeout=(6,12),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"},allow_redirects=True,stream=True)
  data=b""
  for block in r.iter_content(40000):
   data+=block
   if len(data)>=120000:break
  r.close()
  h=BeautifulSoup(data,"html.parser")
  return {"name":name,"http":r.status_code,"url":r.url,"mime":r.headers.get("Content-Type"),"bytes":len(data),
  "title":h.title.get_text(" ",strip=True)[:100] if h.title else "",
  "links":[(a.get_text(" ",strip=True)[:80],urljoin(r.url,a.get("href",""))) for a in h.select('a[href]') if re.search(r"boc|bopa|bolet|pdf|sumario|2026",a.get("href","")+" "+a.get_text(" ",strip=True),re.I)][:14],
  "head":h.get_text(" ",strip=True)[:280]}
 except Exception as e:return {"name":name,"ERROR":str(e)[:180]}
with ThreadPoolExecutor(max_workers=12) as p:
 for row in p.map(probe,URLS):print("ALT",json.dumps(row,ensure_ascii=False)[:7000],flush=True)
