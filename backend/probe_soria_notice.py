#!/usr/bin/env python3
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests,re
url="https://bop.dipsoria.es/index.php/mod.boloficial/mem.detalle/id.55780/relcategoria.210"
r=requests.get(url,timeout=18)
h=BeautifulSoup(r.content,"html.parser")
links=[a for a in h.select("a[href]") if "mem.descargar" in a.get("href","")]
print("COUNT",len(links),flush=True)
for a in links[:4]:
 for n,p in enumerate(list(a.parents)[:5]):
  print("PARENT",n,p.name,p.get("class"),"TEXT",repr(p.get_text(" ",strip=True)[:500]),"HTML",str(p)[:1350],flush=True)
 print("--------",flush=True)
for a in links[:2]:
 u=urljoin(url,a["href"]).replace("http://","https://")
 try:
  z=requests.get(u,timeout=(7,17),headers={"Range":"bytes=0-90"},stream=True)
  print("DOC",z.status_code,z.url,z.headers.get("Content-Type"),repr(next(z.iter_content(100),b"")[:55]),flush=True)
  z.close()
 except Exception as ex:print("ERR",str(ex)[:250],flush=True)
