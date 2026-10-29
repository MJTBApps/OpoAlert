#!/usr/bin/env python3
"""Research fallback sources for official Ceuta document access; do not publish secondary data as verified."""
import requests,json,re,concurrent.futures
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlsplit
URLS=[
("CEUTA_AGGREGATOR","https://www.elperiodicodeceuta.es/ayudas-oposiciones-ceuta/"),
("CEUTA_GOV_PROXY","https://r.jina.ai/https://www.ceuta.es/ceuta/bocce"),
("CEUTA_GOV_PROXY_OCT","https://r.jina.ai/http://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1981-octubre?Itemid=534"),
("CEUTA_OTHER","https://bocce.ceuta.es/"),
("CEUTA_GOOGLE_TRANSLATE","https://www-ceuta-es.translate.goog/ceuta/component/jdownloads/viewcategory/1965-2026?Itemid=534&_x_tr_sl=es&_x_tr_tl=en&_x_tr_hl=es"),
("DATEAS_CEUTA","https://www.dateas.com/es/docs/boletin-oficial-ciudad-de-ceuta-extraordinario/2026/10/09"),
]
def work(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=(5,17),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"},allow_redirects=False)
  h=BeautifulSoup(r.content,"html.parser")
  links=[(a.get_text(" ",strip=True)[:100],urljoin(r.url,a.get("href",""))) for a in h.select("a[href]")]
  rel=[x for x in links if re.search("bocce|bolet|PDF|document|Ceuta|2026/10|2026",x[0]+" "+x[1],re.I)]
  return {"name":name,"status":r.status_code,"url":r.url,"len":len(r.content),
       "ct":r.headers.get("Content-Type"),"links":rel[:30],
       "sample":h.get_text(" ",strip=True)[:1800],"raw":r.text[:300] if "PROXY" in name else None}
 except Exception as e:return {"name":name,"error":repr(e)[:240]}
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 for x in ex.map(work,URLS):print("CEUTA_ALT",json.dumps(x,ensure_ascii=False)[:12000],flush=True)
