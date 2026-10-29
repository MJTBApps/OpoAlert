#!/usr/bin/env python3
"""Read official PDF bulletin headers; do not OCR or synthesize notices."""
import requests,fitz,re
from bs4 import BeautifulSoup
tasks=[
 ("PA","https://www.diputaciondepalencia.es/system/files/bop/2026/20261028-bop-129-Ordinario.pdf"),
 ("SO","https://bop.dipsoria.es/index.php/mod.boloficial/mem.detalle/id.55780/relcategoria.210"),
 ("SG","https://www.dipsegovia.es/bop"),
]
for name,url in tasks:
 try:
  r=requests.get(url,timeout=(12,26),headers={"User-Agent":"Mozilla/5.0"})
  print("RESPONSE",name,r.status_code,len(r.content),r.headers.get("Content-Type"),flush=True)
  if r.content.startswith(b"%PDF-"):
   pdf=fitz.open(stream=r.content,filetype="pdf")
   print("PDF",name,"PAGES",len(pdf),"FIRST",repr(pdf[0].get_text()[:4700]),flush=True)
   print("PAGE2",repr(pdf[1].get_text()[:2300]) if len(pdf)>1 else "-",flush=True)
  elif name=="SO":
   soup=BeautifulSoup(r.content,"html.parser")
   for a in soup.select("a[href]"):
    if "descargar" in a.get("href","").lower() or "pdf" in a.get_text(" ",strip=True).lower():
     print("SO_LINK",a.get_text(" ",strip=True)[:110],a.get("href"),flush=True)
   print("SO_TEXT",repr(soup.get_text(" ",strip=True)[-2200:]),flush=True)
  elif name=="SG":
   soup=BeautifulSoup(r.content,"html.parser")
   print("SG_TITLE",soup.title.get_text(" ",strip=True) if soup.title else "-",flush=True)
   print("SG_ARTICLES",[(a.get_text(" ",strip=True)[:55],a.get("href","")) for a in soup.select("a[href]") if "articleId=" in a.get("href","")][:6],flush=True)
 except Exception as e:print("ERR",name,type(e).__name__,str(e)[:310],flush=True)
