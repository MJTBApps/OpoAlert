#!/usr/bin/env python3
"""Read-only diagnostics: nine provincial official BOP portals and Junta BOCYL."""
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
import requests,re,json
CHECKS=[
("AV-list","https://www.diputacionavila.es/boletin-oficial/2026/"),
("AV-day","https://www.diputacionavila.es/boletin-oficial/2026/28-10-2026.html"),
("BU-root","https://bopbur.diputaciondeburgos.es/"),
("BU-day","https://bopbur.diputaciondeburgos.es/bopbur-2026-205"),
("LE-calendar","https://bop.dipuleon.es/publica/consulta-de-bops/index.html"),
("LE-day","https://bop.dipuleon.es/publica/consulta-de-bops/buscador/BOP-28-10-2026/"),
("PA-search","https://www.diputaciondepalencia.es/servicios/boletin-oficial-provincia"),
("SA-sede","https://sede.diputaciondesalamanca.gob.es/BOP/"),
("SA-historic","https://www.dipsanet.es/Aplicaciones/GestorInter.jsp?funcion=MenuIzquierda&prestacion=Boletines"),
("SG-web","https://www.dipsegovia.es/bop"),
("SG-bop","https://bop.dipsegovia.es/"),
("SO-index","https://bop.dipsoria.es/index.php/mod.boloficial/relmenu.149"),
("SO-root","https://bop.dipsoria.es/"),
("VA-calendar","https://bop.sede.diputaciondevalladolid.es/calendario"),
("VA-root","https://bop.sede.diputaciondevalladolid.es/"),
("ZA-list","https://www.diputaciondezamora.es/opencms/servicios/BOP/busqueda-en-el-bop/"),
("ZA-all","https://www.diputaciondezamora.es/opencms/servicios/BOP/bop-total/"),
("CY-portal","https://bocyl.jcyl.es/"),
("CY-api","https://analisis.datosabiertos.jcyl.es/api/explore/v2.1/catalog/datasets/bocyl/records?limit=2"),
]
def get(item):
 name,url=item
 try:
  resp=requests.get(url,timeout=(7,15),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"},allow_redirects=True)
  print("\n#####",name,"STATUS",resp.status_code,"MIME",resp.headers.get("content-type"),"LEN",len(resp.content),"URL",resp.url,flush=True)
  if "json" in resp.headers.get("content-type",""):
   try:
    v=resp.json()
    print("JSON KEYS",list(v),"FIRST",repr(v.get("results",[])[:2])[:3500],flush=True)
   except Exception as e:print("JSON_ERROR",str(e)[:180],flush=True)
   return
  h=BeautifulSoup(resp.content[:1100000],"html.parser")
  print("TITLE",h.title.get_text(" ",strip=True)[:140] if h.title else "-",flush=True)
  print("TEXT",repr(h.get_text(" ",strip=True)[:1100]),flush=True)
  print("HEADINGS",[(x.name,x.get_text(" ",strip=True)[:95]) for x in h.select("h1,h2,h3")[:10]],flush=True)
  print("FORMS",[(x.get("action"),x.get("method"),[i.get("name") for i in x.select("input[name]")[:7]]) for x in h.select("form")[:4]],flush=True)
  links=[(a.get_text(" ",strip=True)[:70],urljoin(resp.url,a.get("href",""))) for a in h.select("a[href]")]
  interesting=[a for a in links if re.search(r"2026|bolet|bop|pdf|28/10|octubre|28-10|sumario|descarg|avisos|p=|dia",a[0]+a[1],re.I)]
  print("LINKS",json.dumps(interesting[:28],ensure_ascii=False),flush=True)
  print("PDFS",json.dumps([x for x in interesting if ".pdf" in x[1].lower()][:9],ensure_ascii=False),flush=True)
  print("IFRAMES",[(x.get("src")) for x in h.select("iframe")[:5]],flush=True)
 except Exception as e:print("ERROR",name,type(e).__name__,str(e)[:360],flush=True)
with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(get,CHECKS))
