#!/usr/bin/env python3
"""Deep inspection of BOC and both Canary BOP sites to recover official links."""
import requests,json,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
TARGETS=[
("LP HOME","https://www.boplaspalmas.net/nbop2/"),
("LP ROOT","https://www.boplaspalmas.net/"),
("TENERIFE INDEX","https://www.bopsantacruzdetenerife.es/bopsc2/"),
("TENERIFE 28","https://www.bopsantacruzdetenerife.es/bopsc2/sumario.php?codigopub=1&fecha_mas_reciente=2026-10-28"),
("TENERIFE 30","https://www.bopsantacruzdetenerife.es/bopsc2/sumario.php?codigopub=1&fecha_mas_reciente=2026-09-30"),
("BOC 217","https://www.gobiernodecanarias.org/boc/2026/217/index.html"),
("BOC 212","https://www.gobiernodecanarias.org/boc/2026/212/index.html"),
]
def go(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=(12,28),headers={"User-Agent":"Mozilla/5.0"})
  raw=r.content
  soup=BeautifulSoup(raw,"html.parser")
  return {"name":name,"status":r.status_code,"url":r.url,
   "source":raw[:6500].decode(r.apparent_encoding or "utf-8","replace")[:6500],
   "frames":[(v.name,v.get("src"),v.get("name"),v.get("id")) for v in soup.select("frame,iframe")],
   "styles":[x.get("href") for x in soup.select("link[href]")[:10]],
   "scripts":[x.get("src") for x in soup.select("script[src]")[:10]],
   "forms":[str(f)[:1000] for f in soup.select("form")[:4]],
   "docSections":[str(x)[:2500] for x in soup.select("h4,h3,article,dl,li") if re.search("Secretaría General Técnica|Oposiciones y concursos|Ayuntamiento de|Anuncio",x.get_text(" ",strip=True),re.I)][:2],
   "titles":[str(x.parent)[:900] for x in soup.select('a[href*="boc-a-2026"]')[:3]],
   "head":soup.get_text(" ",strip=True)[:1300],
  }
 except Exception as e:return {"name":name,"error":repr(e)[:220]}
with ThreadPoolExecutor(max_workers=7) as ex:
 for x in ex.map(go,TARGETS):print("CANARIAS_DEEP",json.dumps(x,ensure_ascii=False)[:14500],flush=True)
