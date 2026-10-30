#!/usr/bin/env python3
"""Compare 2026 end pages on two official Jaen Pandora archive hosts."""
import requests,json,re,concurrent.futures
from bs4 import BeautifulSoup
P=["https://www.dipujaen.es/hemerotecadigital/","https://bophistorico.dipujaen.es/"]
COUNT=41781
START=((COUNT-1)//15)*15
TASKS=[(base,offset) for base in P for offset in [START-45,START-30,START-15,START]]
def work(task):
 base,offset=task
 u=base+"results.vm?q=parent:0000395018&view=boletin&s="+str(offset)
 try:
  r=requests.get(u,timeout=(6,26))
  h=BeautifulSoup(r.content,"html.parser")
  cards=[]
  for c in h.select("div.list-frame"):
   pdf=c.find("a",href=re.compile("high\.raw"))
   cards.append({"id":c.get("id"),"text":c.get_text(" ",strip=True)[:125],
     "pdf":pdf.get("href","")[:120] if pdf else ""})
  return {"host":base,"s":offset,"status":r.status_code,"count":re.search(r"Resultados:\s*[\d.]+",h.get_text(" ",strip=True)).group(0) if re.search(r"Resultados:\s*[\d.]+",h.get_text(" ",strip=True)) else "", "cards":cards}
 except Exception as ex:return {"host":base,"s":offset,"error":str(ex)[:150]}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
 for x in pool.map(work,TASKS):print("JAEN_PUBLISHER_LAST",json.dumps(x,ensure_ascii=True)[:7500],flush=True)
