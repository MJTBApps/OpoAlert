#!/usr/bin/env python3
"""Investigate a third-party BON index only for original official links.

This diagnostic NEVER equates third-party articles with official full BON coverage.
"""
from collections import Counter
from urllib.parse import urljoin,urlsplit
import re,requests
from bs4 import BeautifulSoup
urls=[
 "https://boletinbien.com/navarra",
 "https://boletinbien.com/navarra/2026/10/29",
 "https://boletinbien.com/navarra/navarra",
 "https://boletinbien.com/navarra?fecha=2026-10-28",
]
for url in urls:
 print("\nSTART",url,flush=True)
 try:
  r=requests.get(url,timeout=15,headers={"User-Agent":"Mozilla/5.0"})
  print("RESPONSE",r.status_code,r.url,len(r.content),flush=True)
  if r.status_code!=200:continue
  h=BeautifulSoup(r.content,"html.parser")
  links=[]
  for a in h.select("a[href]"):
   link=urljoin(r.url,a.get("href",""))
   label=a.get_text(" ",strip=True)
   if any(k in (label+" "+link).lower() for k in ("navarra","2026","bon","anuncio","oposicion","empleo","pdf")):
    links.append((label[:85],link[:220]))
  print("RELEVANT_LINKS",repr(links[:145]),flush=True)
  print("OFFICIAL_HOST_LINKS",repr([(t,u) for t,u in links if any(x in urlsplit(u).hostname or "" for x in ("navarra.es","cfnavarra.es"))][:60]),flush=True)
  print("LINK_HOST_COUNT",dict(Counter(urlsplit(u).hostname for _,u in links)),flush=True)
  print("TEXT",h.get_text(" ",strip=True)[-3500:],flush=True)
 except Exception as ex:print("ERROR",repr(ex),flush=True)
