#!/usr/bin/env python3
"""Diagnose September 30 BOP Malaga: session, date, Referer and archival link."""
from bs4 import BeautifulSoup
import requests
BASE="https://www.bopmalaga.es/"
REFS=["https://www.bopmalaga.es/sumario.php","https://www.bopmalaga.es/sumario.php?fecha=01-10-2026","https://www.bopmalaga.es/sumario.php?fecha=29-09-2026","https://www.bopmalaga.es/"]
URLS=["sumario.php?fecha=30-09-2026","sumario.php?fecha=29-09-2026","sumario.php?fecha=01-10-2026"]
for ref in REFS:
 with requests.Session() as s:
  s.headers.update({"User-Agent":"Mozilla/5.0","Cache-Control":"no-cache","Referer":ref})
  try:
   init=s.get("https://www.bopmalaga.es/sumario.php?fecha=01-10-2026",timeout=(12,25))
   print("INITIAL",ref,init.status_code,len(init.content),"cookies",s.cookies.get_dict(),flush=True)
  except Exception as ex:print("INIT_ERR",str(ex)[:210],flush=True)
  for u in URLS:
   try:
    r=s.get(BASE+u,timeout=(12,25))
    h=BeautifulSoup(r.content,"html.parser")
    t=h.select_one("h2 time")
    print("FETCH",ref,u,r.status_code,len(r.content),"DATE",t.get("datetime") if t else "-", "TITLE",h.title.get_text(" ",strip=True)[:120] if h.title else "-","TEXT",h.get_text(" ",strip=True)[-180:],flush=True)
   except Exception as ex:print("ERR",ref,u,str(ex)[:190],flush=True)
