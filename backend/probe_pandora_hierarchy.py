#!/usr/bin/env python3
"""Summarize Pandora folder hierarchy for 2026 BOP Almeria and Jaen."""
import requests,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin,unquote
ROOTS=[
 ("AL1","https://app.dipalme.org/pandora/results.vm?q=parent:0000010918&t=%2Balpha&lang=es&view=boletines"),
 ("AL1sort","https://app.dipalme.org/pandora/results.vm?q=parent:0000010918&t=-alpha&lang=es&view=boletines"),
 ("AL2026q","https://app.dipalme.org/pandora/results.vm?q=2026&t=-date&view=boletines"),
 ("AL2026field","https://app.dipalme.org/pandora/results.vm?q=year:2026&view=boletines"),
 ("JA1","https://bophistorico.dipujaen.es/results.vm?q=parent:0000395018&t=%2Balpha&lang=es&view=boletin"),
 ("JA2026","https://bophistorico.dipujaen.es/results.vm?q=2026&view=boletin"),
]
for name,url in ROOTS:
 print("\n##",name,flush=True)
 try:
  r=requests.get(url,timeout=25,headers={"User-Agent":"Mozilla/5.0"})
  h=BeautifulSoup(r.text,"html.parser")
  t=h.get_text(" ",strip=True)
  print("HTTP",r.status_code,"LEN",len(r.content),"SUMMARY",t[150:1500],flush=True)
  q=re.search(r"P[aá]gina\s+\d+\s+de\s+[\d,.]+.{0,120}Resultados:\s*[\d,.]+",t)
  print("COUNT",q.group() if q else "-",flush=True)
  for a in h.select("a[href]"):
   url=a["href"]
   if "results.vm?q=parent" in url or "results.vm?q=" in url and "s=" in url:
    p=a.parent
    print("ITEM",a.get_text(" ",strip=True)[:55],"href",url[:180],"parent",p.get_text(" ",strip=True)[:160],flush=True)
  print("DETAILS",[(a.get("href"),a.get_text(" ",strip=True)[:60]) for a in h.select("a[href]") if "viewer.vm" in a.get("href","")][:10],flush=True)
 except Exception as ex:print("ERROR",type(ex).__name__,str(ex)[:160],flush=True)
