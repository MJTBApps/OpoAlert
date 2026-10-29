#!/usr/bin/env python3
"""Inspect Pandora official repositories for recent issues and stable PDF URLs."""
import requests,re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
pairs=[
 ("AL ROOT","https://app.dipalme.org/pandora/results.vm?q=root&t=%2Balpha&lang=es&view=boletines"),
 ("AL 2026","https://app.dipalme.org/pandora/results.vm?w=2026&view=boletines"),
 ("AL SEARCH","https://app.dipalme.org/pandora/advanced.vm?view=boletines"),
 ("AL RESULTS","https://app.dipalme.org/pandora/results.vm?view=boletines"),
 ("AL PARAM 2026","https://app.dipalme.org/pandora/results.vm?q=2026&view=boletines"),
 ("JA ROOT","https://bophistorico.dipujaen.es/results.vm?q=root&t=%2Balpha&lang=es&view=boletin"),
 ("JA 2026","https://bophistorico.dipujaen.es/results.vm?w=2026&view=boletin"),
 ("JA ADV","https://bophistorico.dipujaen.es/advanced.vm?view=boletin"),
 ("JA RES","https://bophistorico.dipujaen.es/results.vm?view=boletin"),
]
def worker(item):
 label,url=item
 print("\n###",label,flush=True)
 try:
  r=requests.get(url,timeout=(12,25),headers={"User-Agent":"Mozilla/5.0"})
  print("STATUS",r.status_code,"END",r.url,"SIZE",len(r.content),flush=True)
  s=BeautifulSoup(r.text,"html.parser")
  print("TEXT",repr(s.get_text(" ",strip=True)[:2400]),flush=True)
  print("FORMS",[(f.get("action"),f.get("method"),f.get("id")) for f in s.select("form")[:10]],flush=True)
  print("FIELDS",[(x.name,x.get("name"),x.get("id"),x.get("value"),x.get("type")) for x in s.select("input,select")[:90]],flush=True)
  print("LINKS",[(x.get("href"),x.get_text(" ",strip=True)[:80]) for x in s.select("a[href]")[-100:]],flush=True)
  print("HEAD",repr(r.text[:1100]),flush=True)
 except Exception as ex:print("ERROR",type(ex).__name__,str(ex)[:200],flush=True)
with ThreadPoolExecutor(max_workers=3) as p:list(p.map(worker,pairs))
