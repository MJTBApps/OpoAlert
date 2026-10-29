#!/usr/bin/env python3
"""Reconnaissance: the three official Canary Islands journals (read-only)."""
from __future__ import annotations
import requests,re,json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
HOSTS=[
("BOC archive","https://www.gobiernodecanarias.org/boc/archivo/2026/"),
("BOC latest","https://www.gobiernodecanarias.org/boc/2026/217/"),
("BOC latest index","https://www.gobiernodecanarias.org/boc/2026/217/index.html"),
("BOC article","https://www.gobiernodecanarias.org/boc/2026/217/3724.html"),
("BOP Tenerife home","https://www.bopsantacruzdetenerife.es/"),
("BOP Tenerife index","https://www.bopsantacruzdetenerife.es/bopsc2/"),
("BOP Tenerife 28","https://www.bopsantacruzdetenerife.es/bopsc2/sumario.php?codigopub=1&fecha_mas_reciente=2026-10-28"),
("BOP Tenerife 30sept","https://www.bopsantacruzdetenerife.es/bopsc2/sumario.php?codigopub=1&fecha_mas_reciente=2026-09-30"),
("BOP LP official https","https://www.boplaspalmas.net/nbop2/"),
("BOP LP official http","http://www.boplaspalmas.net/nbop2/"),
("BOP LP .com","https://www.boplaspalmas.com/nbop2/"),
("BOP LP root","https://www.boplaspalmas.net/"),
("BOP LP alt","https://boplaspalmas.net/nbop2/"),
]
def probe(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=(10,35),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
  h=BeautifulSoup(r.content,"html.parser")
  links=[(a.get_text(" ",strip=True)[:90],urljoin(r.url,a.get("href",""))) for a in h.select("a[href]")]
  relevant=[x for x in links if re.search(r"2026|PDF|bolet|sumari|2026|descarg|indice|buscar|calend|mes",x[0]+" "+x[1],re.I)]
  return {"name":name,"status":r.status_code,"len":len(r.content),
  "url":r.url,"type":r.headers.get("Content-Type"),"title":h.title.get_text(" ",strip=True)[:200] if h.title else "",
  "headings":[(x.name,x.get_text(" ",strip=True)[:140]) for x in h.select("h1,h2,h3,h4")[:14]],
  "linksN":len(links),"links":relevant[:32],"allLinks":links[:20],
  "forms":[(f.get("action"),f.get("method"),[(i.get("name"),i.get("value")) for i in f.select("input")[:14]]) for f in h.select("form")[:4]],
  "text":h.get_text(" ",strip=True)[:1400],"scripts":[x.get("src") for x in h.select("script[src]")[-8:]]}
 except Exception as e:return {"name":name,"url":url,"error":repr(e)[:330]}
with ThreadPoolExecutor(max_workers=9) as p:
 for x in p.map(probe,HOSTS):print("CANARIAS_DIAG",json.dumps(x,ensure_ascii=False)[:17500],flush=True)
