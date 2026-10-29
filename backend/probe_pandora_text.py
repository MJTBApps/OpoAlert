#!/usr/bin/env python3
"""Investigate accessible OCR text vs viewer in both official digital hemerotecas."""
import requests,re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
PAGES=[
 ("AL-viewer","https://app.dipalme.org/pandora/viewer.vm?id=392773&view=boletines&lang=es"),
 ("JA-viewer","https://bophistorico.dipujaen.es/viewer.vm?id=0001747120&page=1&search=&lang=es&view=boletin"),
 ("AL-text","https://app.dipalme.org/pandora/text.raw?id=0000392773"),
 ("JA-text","https://bophistorico.dipujaen.es/text.raw?id=0001747120"),
 ("AL-ocr","https://app.dipalme.org/pandora/ocr.raw?id=0000392773"),
 ("JA-ocr","https://bophistorico.dipujaen.es/ocr.raw?id=0001747120"),
 ("AL-textlayer","https://app.dipalme.org/pandora/text.vm?id=0000392773&view=boletines"),
 ("JA-textlayer","https://bophistorico.dipujaen.es/text.vm?id=0001747120&view=boletin"),
]
def worker(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=(10,20),headers={"User-Agent":"Mozilla/5.0"})
  print("\n",name,"STATUS",r.status_code,"SIZE",len(r.content),"TYPE",r.headers.get("Content-Type"),"END",r.url[:200],flush=True)
  if r.status_code!=200:print("HEAD",repr(r.content[:200]),flush=True);return
  soup=BeautifulSoup(r.content[:120000],"html.parser")
  print("TEXT",repr(soup.get_text(" ",strip=True)[:2800]),flush=True)
  print("VIEWER LINKS",[(x.get("href"),x.get_text(" ",strip=True)[:65]) for x in soup.select("a[href]") if re.search("ocr|text|txt|download|raw|alto|xml|transcri|busca",x.get("href",""),re.I)][:40],flush=True)
  print("SCRIPT",[(x.get("src")) for x in soup.select("script[src]")][:12],flush=True)
 except Exception as ex:print(name,"ERROR",type(ex).__name__,str(ex)[:160],flush=True)
with ThreadPoolExecutor(max_workers=3) as p:list(p.map(worker,PAGES))
