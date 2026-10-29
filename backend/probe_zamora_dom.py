#!/usr/bin/env python3
import requests,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
HOST="https://www.diputaciondezamora.es/opencms/servicios/BOP/busqueda-en-el-bop/"
for page in [0,1,2,3]:
 url=HOST+(f"?page={page}" if page else "")
 try:
  r=requests.get(url,timeout=(10,20));s=BeautifulSoup(r.content,"html.parser")
  links=s.select('a[href*="/indice-bop/"]')
  allb=[]
  for a in links:
   if re.search(r"BOP\s+\d+",a.get_text(" ",strip=True)):
    p=a
    for i in range(3):
     if p.parent is None:break
     p=p.parent
    allb.append((a.get_text(" ",strip=True),p.get_text(" ",strip=True)[:120]))
  print("PAGE",page,"STATUS",r.status_code,"COUNT",len(allb),"ISSUES",allb[:18],flush=True)
  print("PAGINATION",[(z.get("class"),z.get_text(" ",strip=True)[:150]) for z in s.select("nav,ul.pagination,.pagination,[class*=pagination]")[-4:]],flush=True)
 except Exception as ex:print("ERR",page,str(ex)[:240],flush=True)
issue="https://www.diputaciondezamora.es/opencms/servicios/BOP/indice-bop/232446e5-d207-11f1-a057-1576f9d14bbb/"
z=requests.get(issue,timeout=20);s=BeautifulSoup(z.content,"html.parser")
a=next(x for x in s.select("a[href]") if re.search(r"/anuncios/2026/127/\d+\.pdf",x["href"]))
for i,p in enumerate(list(a.parents)[:8]):
 print("PARENT",i,p.name,p.get("class"),"TEXT",repr(p.get_text(" ",strip=True)[:650]),"HTML",str(p)[:1100],flush=True)
