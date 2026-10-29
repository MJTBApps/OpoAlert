#!/usr/bin/env python3
"""Targeted discovery of archive, article and PDF links in accessible basque bulletins."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests,re,json
CASES=[
("GI-DAY","https://egoitza.gipuzkoa.eus/gao-bog/castell/bog/2026/10/29/bc261029.htm"),
("GI-SEP","https://egoitza.gipuzkoa.eus/gao-bog/castell/bog/2026/09/30/bc260930.htm"),
("PV-DAY","https://www.euskadi.eus/bopv2/datos/2026/10/Indice-2026-10-29.shtml"),
("PV-ARCH","https://www.euskadi.eus/bopv2/datos/2026/10/indes_c.shtml"),
("PV-XML","https://www.euskadi.eus/bopv2/datos/Ultimo.xml"),
("PV-APIJS","https://opendata.euskadi.eus/scripts/webopd00-apirest-docs.js"),
("PV-APIB","https://opendata.euskadi.eus/scripts/webopd00-apibulletin-script.js"),
("PV-APISC","https://opendata.euskadi.eus/scripts/webopd00-script.js"),
("AV-INDEX","https://e-s.araba.eus/BOTHA/Inicio/SGBO5001.aspx"),
("BI-DAY","https://www.bizkaia.eus/es/bob/resultados?p_p_id=IYBIWBCC&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_IYBIWBCC_mvcRenderCommandName=%2Fdetail&_IYBIWBCC_bdate=20261029&_IYBIWBCC_bnum=208")
]
def sample(z):
 n,u=z
 try:
  r=requests.get(u,timeout=(9,28),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"},allow_redirects=True)
  s=BeautifulSoup(r.content,"html.parser")
  out={"name":n,"status":r.status_code,"mime":r.headers.get("Content-Type"),"url":r.url,"len":len(r.content)}
  if "JS" in n or n.endswith("APIB") or n.endswith("APISC"):
   out["jsFirst"]=r.text[:5000];out["apiHints"]=[r.text[max(0,m.start()-180):m.start()+400] for m in list(re.finditer("api|swagger|openapi|endpoints|https://",r.text,re.I))[:12]]
   return out
  if n=="PV-XML":out["xmlHead"]=r.text[:4000];return out
  main=s.select_one("main") or s.select_one("#main") or s.select_one("#contenido") or s.body
  out["header"]=[(x.name,x.get_text(" ",strip=True)[:150]) for x in main.select("h1,h2,h3,h4")[:28]]
  out["mainStarts"]=str(main)[:8500]
  out["mainEnds"]=str(main)[-3000:]
  out["matched_links"]=[(a.get_text(" ",strip=True)[:90],urljoin(r.url,a.get("href",""))) for a in main.select("a[href]") if re.search(r"pdf|htm|shtml|descarga|indice",a.get("href",""),re.I)][:35]
  out["html_tags"]=[(x.name,x.get("class"),x.get("id")) for x in main.select("article,li,table,tr,div")[:30]]
  return out
 except Exception as e:return {"name":n,"ERROR":str(e)[:350]}
with ThreadPoolExecutor(max_workers=5) as p:
 for v in p.map(sample,CASES):print("DEEP",json.dumps(v,ensure_ascii=False)[:22000],flush=True)
