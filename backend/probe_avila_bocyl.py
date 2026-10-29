#!/usr/bin/env python3
from bs4 import BeautifulSoup
import requests,re
for d in ["02-10-2026","06-10-2026","28-10-2026"]:
 u=f"https://www.diputacionavila.es/boletin-oficial/2026/{d}.html"
 try:
  z=requests.get(u,timeout=16);h=BeautifulSoup(z.content,"html.parser")
  matches=[a for a in h.select("a[href]") if a.get("href","").endswith(f"/{d}.pdf")]
  print("AV",d,"STATUS",z.status_code,"NUMBERS",re.findall(r"B\.\s*O\.\s*P\.\s*\d+/\d\d",h.get_text(" ",strip=True))[:5],flush=True)
  print("TOP",str(h.select_one("div.inf"))[:4400],flush=True)
  print("EDITIONS",[(a.get("href"),a.get_text(" ",strip=True),str(a.parent)[:450]) for a in matches[:5]],flush=True)
  print("BLOCKS",len(h.select("div.listado")),"ITEMS",sum(len(b.select("li")) for b in h.select("div.listado")),flush=True)
 except Exception as e:print("ERR",d,str(e)[:160],flush=True)
url="https://bocyl.jcyl.es/boletin.do?fechaBoletin=29/10/2026"
z=requests.get(url,timeout=17);h=BeautifulSoup(z.text,"html.parser")
print("CY_ISSUE",len(h.select("ul.descargaBoletin")),flush=True)
for ul in h.select("ul.descargaBoletin")[:3]:
 print("CY_UL",str(ul)[:2300],flush=True)
 print("CY_PREV",str(ul.find_previous_sibling("p"))[:1300],flush=True)
 print("CY_PREV_H5",str(ul.find_previous("h5"))[:350],flush=True)
 print("CY_PARENT",ul.parent.name,ul.parent.get("class"),flush=True)
