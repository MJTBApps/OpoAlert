#!/usr/bin/env python3
"""Inspect anomalous candidate issuers Almeria and missing BOP dates Jaen."""
from pandora_bop import *
from bs4 import BeautifulSoup
import requests,re

sa=session()
issues,total,pages=fetch_index(ALMERIA,date(2026,9,30),date(2026,10,29),sa)
for day,code in [(date(2026,10,2),2661),(date(2026,10,27),2921)]:
 issue=next(x for x in issues if x["date"]==day)
 txt=get(sa,text_url(ALMERIA,issue["id"])).content.decode("utf-8")
 ms=list(AL_BODY.finditer(txt))
 for i,m in enumerate(ms):
  if int(m.group(1))!=code:continue
  nxt=ms[i+1].start() if i+1<len(ms) else len(txt)
  print("ALMERIA",day,code,"PRE",repr(txt[max(0,m.start()-650):m.start()]),"BODY",repr(txt[m.start():min(nxt,m.start()+1400)]),flush=True)
print("JAEN SEARCH MISSING EDITIONS",flush=True)
params=["2026/10/10","10/10/2026","12/10/2026","14/10/2026","198","199","201","2026"]
from urllib.parse import quote
for q in params:
 try:
  url="https://bophistorico.dipujaen.es/results.vm"
  r=sa.get(url,params={"q":q,"view":"boletin"},timeout=18)
  soup=BeautifulSoup(r.text,"html.parser")
  cards=soup.select("div.list-frame")
  print("SEARCH",q,"HTTP",r.status_code,"CARDS",len(cards),"RESULTS",re.search(r"Resultados:\s*[\d,.]+",soup.get_text(" ",strip=True)).group() if re.search(r"Resultados:\s*[\d,.]+",soup.get_text(" ",strip=True)) else "-",
   "DATES",[x.get_text(" ",strip=True)[:140] for x in cards[:9]],flush=True)
 except Exception as e:print("ERROR",q,type(e).__name__,str(e)[:220],flush=True)
