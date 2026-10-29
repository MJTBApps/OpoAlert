#!/usr/bin/env python3
"""Inspect current Pontevedra calendar links and Ourense portal JS/API contracts."""
import requests,re,json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
Q=[
("PO","https://boppo.depo.gal/es/consulta-do-boppo"),
("PO-FORM","https://boppo.depo.gal/es/buscas-no-boppo"),
("OU-SHELL","https://bop.depourense.es/portal/"),
("OU-JS","https://bop.depourense.es/portal/main.js"),
("OU-CONSULTA","https://bop.depourense.es/portal/consulta?fecha=20261028"),
("OU-API","https://bop.depourense.es/portalapi/api/boletin/descargar/91576/idioma/gl"),
]
def probe(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=(10,25),stream=True,headers={"User-Agent":"Mozilla/5.0"},allow_redirects=True)
  blob=b""
  for chunk in r.iter_content(50000):
   blob+=chunk
   if len(blob)>100000:break
  r.close()
  if blob.startswith(b"%PDF-"):return {"name":name,"http":r.status_code,"pdf":True,"mime":r.headers.get("Content-Type"),"length":r.headers.get("Content-Length")}
  h=BeautifulSoup(blob,"html.parser");out={"name":name,"http":r.status_code,"size":len(blob),"url":r.url,"prefix":blob[:100].decode("utf-8","replace")}
  if name.startswith("PO"):
   out["calendar_links"]=[(x.get("href"),x.get("onclick"),x.get("title"),x.get_text(" ",strip=True)[:40]) for x in h.select('a') if "calendar" in str(x.get("href","")) or re.search(r"day|fecha|boppo|pdf|documento",str(x.get("class",""))+" "+str(x.get("onclick","")),re.I)][:55]
   out["calendar_html"]=[str(x)[:2800] for x in h.select('[id*="calendar"],[id*="calendari"],[class*="calendari"]')[:4]]
   out["pdf_links"]=[(x.get("href"),x.get_text(" ",strip=True)[:90],str(x.parent.parent)[:1550]) for x in h.select('a[href]') if ".pdf" in x.get("href","").lower()][:6]
   out["scriptMatches"]=re.findall(r".{0,100}(?:fecha|calendar|bopv2portlet|idAnuncio|downloadFile|idBoletin).{0,110}",h.get_text(" ",strip=True)+str(h.find_all("script",src=False)[-2:]),re.I)[:20]
  if name.startswith("OU"):
   out["html"]=str(h)[:2200]
   out["scripts"]=[x.get("src") for x in h.select("script[src]")[:15]]
  return out
 except Exception as e:return {"name":name,"error":str(e)[:230]}
with ThreadPoolExecutor(max_workers=6) as p:
 for o in p.map(probe,Q):print("GAL_PORTAL",json.dumps(o,ensure_ascii=False)[:9000],flush=True)
