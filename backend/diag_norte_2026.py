#!/usr/bin/env python3
"""Inspect 6 official bulletin archives: BOPV BOTHA BOB BOG BOC BOPA."""
import requests,re,json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
SOURCES=[
 ("PV-API","https://opendata.euskadi.eus/api-bopv/?api=bopv"),
 ("PV-LATEST","https://www.euskadi.eus/y22-bopv/es/bopv2/datos/Ultimo.shtml"),
 ("PV-2026","https://www.euskadi.eus/y22-bopv/es/bopv2/datos/2026.shtml"),
 ("AV-INDEX","https://e-s.araba.eus/BOTHA/Inicio/SGBO5001.aspx"),
 ("AV-RECENT","https://araba.eus/botha/busquedas/sgbo5014.aspx"),
 ("BI-INDEX","https://www.bizkaia.eus/es/bob"),
 ("BI-LATEST","https://www.bizkaia.eus/es/bob/resultados?p_p_id=IYBIWBCC"),
 ("GI-INDEX","https://egoitza.gipuzkoa.eus/es/bog"),
 ("GI-ACCESS","https://egoitza.gipuzkoa.eus/es/bog/acceso-boletin"),
 ("CB-INDEX","https://boc.cantabria.es/boces/"),
 ("CB-LATEST","https://boc.cantabria.es/boces/verBoletin.do?fechaBoletin=2026-10-29"),
 ("CB-PDF","https://boc.cantabria.es/boces/verAnuncioAction.do?idAnuBlob=8420"),
 ("AS-INDEX","https://miprincipado.asturias.es/bopa/"),
 ("AS-LATEST","https://miprincipado.asturias.es/bopa/ultimos-boletines?p_r_p_summaryLastBopa=true"),
 ("AS-OPEN","https://descargas.asturias.es/asturias/opendata/LegislacionyJusticia/BOPA2019-28/dataset-sum-bopa-2026.csv")
]
def probe(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=(11,32),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"},stream=True)
  raw=b""
  for chunk in r.iter_content(150000):
   raw+=chunk
   if len(raw)>=250000:break
  r.close()
  info={"name":name,"status":r.status_code,"url":r.url[:230],"mime":r.headers.get("Content-Type"),"length":len(raw),"prefix":repr(raw[:85])}
  if raw.startswith(b"%PDF-"):info["pdf"]=True;return info
  soup=BeautifulSoup(raw,"html.parser")
  info["title"]=soup.title.get_text(" ",strip=True)[:150] if soup.title else ""
  info["forms"]=[{"action":x.get("action"),"method":x.get("method"),"controls":[(q.name,q.get("name"),q.get("value")) for q in x.select("input[name],select[name]")[:12]]} for x in soup.select("form")[:8]]
  info["headings"]=[(x.name,x.get_text(" ",strip=True)[:110]) for x in soup.select("h1,h2,h3,h4")[-15:]]
  links=[(a.get_text(" ",strip=True)[:90],urljoin(r.url,a.get("href",""))[:220]) for a in soup.select("a[href]")]
  filtered=[x for x in links if re.search(r"bop|boc|pdf|bolet|2026|202610|index|ultim|resumen|sumario|anuncio|bog|botha|download",x[0]+" "+x[1],re.I)]
  info["links_count"]=len(links)
  info["links"]=filtered[:28]
  info["last_links"]=filtered[-10:]
  info["scripts"]=[x.get("src") for x in soup.select("script[src]")][-15:]
  info["text"]=soup.get_text(" ",strip=True)[-1200:]
  if "csv" in url:
   info["csv_head"]=raw[:650].decode("utf-8","replace")
  return info
 except Exception as e:return {"name":name,"ERROR":str(e)[:250]}
with ThreadPoolExecutor(max_workers=7) as pool:
 for info in pool.map(probe,SOURCES):print("DIAG",json.dumps(info,ensure_ascii=False)[:16000],flush=True)
