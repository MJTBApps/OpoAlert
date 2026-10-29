#!/usr/bin/env python3
"""Explore BOP frame archives (main1.php) and table rows in issue abstracts."""
import requests,json,re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
HOSTS=[("LP_MAIN","https://www.boplaspalmas.net/nbop2/main1.php"),
("LP_CAB","https://www.boplaspalmas.net/nbop2/cab.php"),
("LP_28","https://www.boplaspalmas.net/nbop2/sumario.php?fecha_mas_reciente=2026-10-28"),
("LP_30SEP","https://www.boplaspalmas.net/nbop2/sumario.php?fecha_mas_reciente=2026-09-30"),
("LP_29","https://www.boplaspalmas.net/nbop2/sumario.php?fecha_mas_reciente=2026-10-29"),
("TF_MAIN","https://www.bopsantacruzdetenerife.es/bopsc2/main1.php"),
("TF_CAB","https://www.bopsantacruzdetenerife.es/bopsc2/cab.php"),
("TF_28","https://www.bopsantacruzdetenerife.es/bopsc2/sumario.php?codigopub=1&fecha_mas_reciente=2026-10-28"),
("TF_30SEP","https://www.bopsantacruzdetenerife.es/bopsc2/sumario.php?codigopub=1&fecha_mas_reciente=2026-09-30"),
("LP_PDF","https://www.boplaspalmas.net/boletines/2026/28-10-26/28-10-26.pdf"),
("TF_PDF","https://www.bopsantacruzdetenerife.es/boletines/2026/28-10-26/28-10-26.pdf")]
def probe(x):
 n,u=x
 try:
  r=requests.get(u,timeout=(10,32),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES"},stream=True)
  b=b""
  for c in r.iter_content(140000):
   b+=c
   if len(b)>230000:break
  r.close()
  h=BeautifulSoup(b,"html.parser")
  tbl=h.select("table");rows=h.select("tr");td=h.select("td")
  links=[(a.get_text(" ",strip=True)[:100],a.get("href")) for a in h.select("a[href]")]
  raw=b.decode(r.apparent_encoding or "utf-8",errors="replace")
  return {"name":n,"http":r.status_code,"len":len(b),"ct":r.headers.get("Content-Type"),
  "bytes":repr(b[:35]),"text":h.get_text(" ",strip=True)[:1800],"links":links[:60],
  "forms":[str(v)[:1600] for v in h.select("form")[:5]],
  "tables":len(tbl),"trs":len(rows),"tds":len(td),
  "rows":[str(v)[:2100] for v in rows[:9]],
  "titleRows":[str(v)[:2200] for v in rows if re.search(r"EXCMO\. CABILDO|AYUNTAMIENTO DE|convocatoria|pruebas selectiv",v.get_text(" ",strip=True),re.I)][:5],
  "scripts":[x.get("src") for x in h.select("script[src]")[:10]],
  "extra":raw[:2400] if "MAIN" in n else "",
  }
 except Exception as e:return {"name":n,"error":repr(e)[:280]}
with ThreadPoolExecutor(max_workers=9) as ex:
 for v in ex.map(probe,HOSTS):print("CANARIAS_STRUCT",json.dumps(v,ensure_ascii=False)[:19000],flush=True)
