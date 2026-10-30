#!/usr/bin/env python3
"""Explore missing 198,199,201 BOP Jaen through original Pandora publisher search.

This diagnostic does not synthesize missing issues, trust secondary mirrors,
or declare Jaen complete. Limited read-only lookups to the official archive.
"""
from __future__ import annotations
import requests, json, math, re, concurrent.futures
from bs4 import BeautifulSoup
from datetime import date
HOST="https://bophistorico.dipujaen.es/"
COLLECTION="0000395018"
def read(name,url):
 try:
  r=requests.get(url,timeout=(7,17),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
  h=BeautifulSoup(r.content,"html.parser")
  cards=[]
  for div in h.select("div.list-frame"):
   text=div.get_text(" ",strip=True)
   pdf=div.find("a",href=re.compile(r"high\.raw"))
   cards.append({"head":text[:320],"id":div.get("id"),"pdf":pdf.get("href","")[:160] if pdf else ""})
  res={"q":name,"status":r.status_code,"url":r.url,"title":h.title.get_text(" ",strip=True)[:150] if h.title else "",
       "bytes":len(r.content),"cards":cards,"text":h.get_text(" ",strip=True)[:180]}
  if name=="main":
   res["forms"]=[str(x)[:2500] for x in h.select("form")[:3]]
   res["js"]=[(x.get("src")," ".join((x.get_text() or "").split())[:260]) for x in h.select("script")[:14]]
  return res
 except Exception as e:return {"q":name,"error":type(e).__name__+": "+str(e)[:170]}
base=HOST+"results.vm?q=parent:"+COLLECTION+"&view=boletin"
tests=[
 ("main",HOST),
 ("parent",base),
 ("page_5800",base+"&s=5800"),
 ("october_a",HOST+"results.vm?q=2026-10-13&view=boletin"),
 ("october_b",HOST+"results.vm?q=13%2F10%2F2026&view=boletin"),
 ("year_num",HOST+"results.vm?q=%22Boletin%20198%22&view=boletin"),
 ("bop_198",HOST+"results.vm?q=%22BOP-2026-198%22&view=boletin"),
 ("bop_199",HOST+"results.vm?q=%22BOP-2026-199%22&view=boletin"),
 ("bop_201",HOST+"results.vm?q=%22BOP-2026-201%22&view=boletin"),
 ("collection_search",HOST+"results.vm?q=parent:"+COLLECTION+"%20AND%202026&view=boletin"),
]
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for result in pool.map(lambda pair:read(*pair),tests):
  print("JAEN_PANDORA_SEARCH",json.dumps(result,ensure_ascii=False)[:9200],flush=True)
