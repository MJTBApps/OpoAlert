#!/usr/bin/env python3
"""Inspect official daily archive list structure for Barcelona and Girona, Lleida availability. No publishing."""
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re
import time

URLS=[
 "https://bop.diba.cat/anteriors/2026-10-28",
 "https://bop.diba.cat/anteriors/2026-10-27",
 "https://bop.diba.cat/anteriors/2026-10-27/2",
 "https://bop.diba.cat/anteriors/2026-10-24",
 "https://www.ddgi.cat/bop/mostra-bop/2026-10-27/2026/207",
 "https://www.ddgi.cat/bop/mostra-bop/2026-10-26/2026/206",
 "https://www.ddgi.cat/bop/mostra-bop/2026-10-25/2026/205",
 "https://www.ddgi.cat/bop/mostra-bop/2026-10-28/2026/208",
 "https://ebop.diputaciolleida.cat/bop/",
]
for url in URLS:
 print("\nARCHIVE",url,flush=True)
 try:
  with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (OpoAlert validation)","Accept-Language":"ca,es;q=0.8"}),timeout=11) as r:
   raw=r.read(1_100_000);print("HTTP",r.status,"FINAL",r.url,"SIZE",len(raw),"CONTENT TYPE",r.headers.get("content-type"),flush=True)
  soup=BeautifulSoup(raw,"html.parser")
  print("TITLE",soup.title.get_text(" ",strip=True) if soup.title else "",flush=True)
  print("HEADINGS",[(x.name,x.get_text(" ",strip=True)[:110],x.get("class")) for x in soup.select("h1,h2,h3,h4")[:20]],flush=True)
  print("TEXT TOP",soup.get_text(" ",strip=True)[:1700],flush=True)
  print("BOP CARD SELECTORS",[(selector,len(soup.select(selector))) for selector in ("div.card.bg-white","div.card","a[href*='anuncio']","a[href*='anunci']","a[href*='pdf']",".row")],flush=True)
  candidates=[a for a in soup.select("a[href]") if any(t in a.get("href","") for t in ("anuncio","anunci","pdf","mostra-bop","anteriors"))]
  for a in candidates[:5]:
   print("LINK",a.get("href"),a.get_text(" ",strip=True)[:220],"PARENT",str(a.parent.parent)[:2000],flush=True)
  print("ARCHIVE LINKS",[(a.get("href"),a.get_text(" ",strip=True)[:90]) for a in soup.select("a[href]") if any(t in a.get("href","") for t in ("anteriors","mostra-bop"))][:30],flush=True)
 except HTTPError as e:print("HTTP ERR",e.code,e.read(350)[:200],flush=True)
 except Exception as e:print("ERR",type(e).__name__,str(e)[:300],flush=True)
 time.sleep(.1)
