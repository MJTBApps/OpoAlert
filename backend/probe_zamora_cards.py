#!/usr/bin/env python3
import requests,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
u="https://www.diputaciondezamora.es/opencms/servicios/BOP/"
z=requests.get(u+"busqueda-en-el-bop/",timeout=18)
h=BeautifulSoup(z.content,"html.parser")
for a in h.select('a[href*="/indice-bop/"]')[:3]:
 p=a
 for j in range(4):
  if not p.parent:break
  p=p.parent
 print("LIST_CARD",a.get_text(" ",strip=True),str(p)[:2600],flush=True)
page=requests.get(u+"indice-bop/232446e5-d207-11f1-a057-1576f9d14bbb/",timeout=18)
h=BeautifulSoup(page.content,"html.parser")
print("DATE_META",[(x.name,x.get("class"),x.get_text(" ",strip=True)[:160]) for x in h.select("h1,h2,h3,time,.date,.dateDetail")[:13]],flush=True)
for card in h.select("#anuncio")[:2]:
 print("NOTICE",str(card)[:5100],flush=True)
