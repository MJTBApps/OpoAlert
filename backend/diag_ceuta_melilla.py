#!/usr/bin/env python3
"""Read-only official BOCCE and BOME website diagnostics for 30-day archive."""
import requests,re,json
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from urllib.parse import urljoin
URLS=[
 ("CEUTA_BOC","https://www.ceuta.es/ceuta/bocce"),
 ("CEUTA_YEAR","https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1965-2026?Itemid=534"),
 ("CEUTA_YEAR_MONTH","https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1975-octubre?Itemid=534"),
 ("CEUTA_HOME","https://www.ceuta.es/ceuta/"),
 ("CEUTA_JDOWN","https://www.ceuta.es/ceuta/component/jdownloads"),
 ("MELILLA_HOME","https://bomemelilla.es/"),
 ("MELILLA_2026","https://bomemelilla.es/bomes/2026"),
 ("MELILLA_6412","https://bomemelilla.es/bome/BOME-B-2026-6412"),
 ("MELILLA_6426","https://bomemelilla.es/bome/BOME-B-2026-6426"),
 ("MELILLA_2026_EXTRA","https://bomemelilla.es/bome/BOME-A-2026-0048"),
 ("MELILLA_OFFICIAL","https://www.melilla.es/melillaPortal/contenedor.jsp?codMenu=144&codMenuPN=601&codMenuSN=4&codResi=1&contenido=3589&language=es&nivel=1400&seccion=s_fdes_d4_v1.jsp&tipo=6"),
]
def probe(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=(11,38),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"},allow_redirects=True)
  h=BeautifulSoup(r.content,"html.parser")
  links=[(a.get_text(" ",strip=True)[:110],urljoin(r.url,a.get("href",""))) for a in h.select("a[href]")]
  rel=[a for a in links if re.search(r"2026|BOME|BOCCE|octubr|septie|2026|bome/|jdownloads|PDF|descarg|edici|bolet[ií]n",a[0]+" "+a[1],re.I)]
  forms=[{"method":f.get("method"),"action":f.get("action"),"elements":[(x.get("name"),x.get("value")) for x in f.select("input")[:7]]} for f in h.select("form")[:3]]
  return {"name":name,"status":r.status_code,"url":r.url,"len":len(r.content),"contentType":r.headers.get("Content-Type"),
   "title":h.title.get_text(" ",strip=True)[:130] if h.title else None,
   "headings":[(x.name,x.get_text(" ",strip=True)[:100]) for x in h.select("h1,h2,h3,h4")[:12]],
   "linksN":len(links),"links":rel[:32],"allLinks":links[:12],
   "forms":forms,"sample":h.get_text(" ",strip=True)[:1200],
   "pdfs":[x for x in links if ".pdf" in x[1]][:8],
   "scripts":[x.get("src") for x in h.select("script[src]")[-8:]],"error":None}
 except Exception as e:return {"name":name,"error":repr(e)[:280]}
with ThreadPoolExecutor(max_workers=7) as ex:
 for x in ex.map(probe,URLS):print("CM_DIAG",json.dumps(x,ensure_ascii=False)[:17500],flush=True)
