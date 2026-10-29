#!/usr/bin/env python3
"""Inspect latest BOP editions in Pandora before authoring independent readers."""
import requests,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
PAGES=[
 ("AL 48150","https://app.dipalme.org/pandora/results.vm?q=parent:0000010919&view=boletines&s=48150"),
 ("AL 48165","https://app.dipalme.org/pandora/results.vm?q=parent:0000010919&view=boletines&s=48165"),
 ("AL 48180","https://app.dipalme.org/pandora/results.vm?q=parent:0000010919&view=boletines&s=48180"),
 ("JA 41745","https://bophistorico.dipujaen.es/results.vm?q=parent:0000395018&view=boletin&s=41745"),
 ("JA 41760","https://bophistorico.dipujaen.es/results.vm?q=parent:0000395018&view=boletin&s=41760"),
 ("JA 41775","https://bophistorico.dipujaen.es/results.vm?q=parent:0000395018&view=boletin&s=41775"),
]
for name,url in PAGES:
 print("\n#",name,flush=True)
 try:
  r=requests.get(url,timeout=(12,25),headers={"User-Agent":"Mozilla/5.0"})
  soup=BeautifulSoup(r.text,"html.parser")
  text=soup.get_text(" ",strip=True)
  print("STATUS",r.status_code,"LEN",len(r.content),"TEXT",repr(text[150:2300]),flush=True)
  # Pair each viewer/download with short surrounding title to preserve dates.
  links=[(a.get("href"),a.get_text(" ",strip=True)[:55]) for a in soup.select('a[href]') if any(t in a.get("href","") for t in ("viewer.vm","high.raw","results.vm?q=parent"))]
  print("LINKS",links[:60],flush=True)
 except Exception as ex:print("ERROR",type(ex).__name__,str(ex)[:220],flush=True)
