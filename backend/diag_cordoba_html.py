#!/usr/bin/env python3
"""Inspect previously unmodelled official Cordoba BOP HTML nodes."""
from bs4 import BeautifulSoup
import requests,re
for day in ["05-10-2026","09-10-2026","15-10-2026","29-10-2026"]:
 url="https://bop.dipucordoba.es/dia/"+day
 try:
  resp=requests.get(url,timeout=(10,30),headers={"User-Agent":"Mozilla/5.0"})
  soup=BeautifulSoup(resp.text,"html.parser")
  print("\nDAY",day,"HTTP",resp.status_code,"LI",len(soup.select("li.announcement")),flush=True)
  for i,li in enumerate(soup.select("li.announcement")):
   a=li.select_one('a.pdf[href*="/visor-pdf/"]')
   first=li.find("p")
   parent=li.find_parent("li",class_="emisor")
   emitter=parent.find("h2",recursive=False) if parent else None
   if a is None or first is None or emitter is None:
    print("MISSING",i,"LINK",a.get("href") if a else "-","EMITTER",emitter.get_text(" ",strip=True) if emitter else "-",
    "PARENT",li.parent.name,li.parent.get("class"),
    "HTML",str(li)[:4000],"ABOVE",str(li.parent.parent)[:2800],flush=True)
 except Exception as ex:print("ERROR",day,type(ex).__name__,str(ex)[:260],flush=True)
