#!/usr/bin/env python3
"""Probe true PHP entries of province Las Palmas / Santa Cruz BOP portals."""
import requests,re,json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
PS=[
("LP index PHP","https://www.boplaspalmas.net/nbop2/index.php"),
("LP .com index","https://www.boplaspalmas.com/nbop2/index.php"),
("LP old index","http://www.boplaspalmas.net/nbop2/index.php"),
("LP sumario","https://www.boplaspalmas.net/nbop2/sumario.php?codigopub=1&fecha_mas_reciente=2026-10-28"),
("LP sumario alt","https://www.boplaspalmas.net/nbop2/sumario.php?fecha_mas_reciente=2026-10-28"),
("Tenerife index PHP","https://www.bopsantacruzdetenerife.es/bopsc2/index.php"),
("Tenerife menu","https://www.bopsantacruzdetenerife.es/bopsc2/index.php?lang=es"),
("Tenerife dated","https://www.bopsantacruzdetenerife.es/bopsc2/sumario.php?codigopub=1&fecha_mas_reciente=2026-10-29"),
]
def test(pair):
 n,url=pair
 try:
  r=requests.get(url,timeout=(9,32),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"},allow_redirects=True)
  soup=BeautifulSoup(r.content,"html.parser")
  l=[(a.get_text(" ",strip=True)[:100],urljoin(r.url,a.get("href",""))) for a in soup.select("a[href]")]
  return {"name":n,"status":r.status_code,"len":len(r.content),"url":r.url,
   "head":soup.get_text(" ",strip=True)[:800],"scripts":[x.get("src") for x in soup.select("script[src]")[:15]],
   "frames":[(x.get("src"),x.get("name")) for x in soup.select("frame,iframe")],
   "links":l[:35],"forms":[str(f)[:800] for f in soup.select("form")[:5]],
   "raw":r.text[:1600]}
 except Exception as e:return {"name":n,"error":repr(e)[:280]}
with ThreadPoolExecutor(max_workers=8) as p:
 for row in p.map(test,PS):print("CANARIAS_PHP",json.dumps(row,ensure_ascii=False)[:10000],flush=True)
