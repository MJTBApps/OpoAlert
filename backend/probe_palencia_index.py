#!/usr/bin/env python3
import requests,fitz,re
from bs4 import BeautifulSoup
U="https://www.diputaciondepalencia.es/servicios/boletin-oficial-provincia"
for idx in (0,1,2):
 try:
  z=requests.get(U+(f"?page={idx}" if idx else ""),timeout=17)
  s=BeautifulSoup(z.content,"html.parser")
  a=[x for x in s.select('a[href*="/system/files/bop/2026/"]') if ".pdf" in x.get("href","")]
  print("INDEX",idx,z.status_code,len(a),[(x.get("href"),x.get_text(" ",strip=True)[:75]) for x in a[:18]],flush=True)
 except Exception as e:print("INDEX_ERR",idx,str(e)[:210],flush=True)
url="https://www.diputaciondepalencia.es/system/files/bop/2026/20261028-bop-129-Ordinario.pdf"
r=requests.get(url,timeout=(12,30));pdf=fitz.open(stream=r.content,filetype="pdf")
for k in (0,1,2,3,4,64,65):
 print("PAGE",k+1,"HEAD",repr(pdf[k].get_text()[:3400]),flush=True)
