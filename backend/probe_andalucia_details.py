#!/usr/bin/env python3
"""Validate province web structures, edge cases and first announcement PDF destinations."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests,re
TASKS=[]
for province,base in [("GRANADA","https://bop.dipgra.es"),("SEVILLA","https://bopsevilla.dipusevilla.es")]:
 for days in range(30):
  d=date(2026,10,29)-timedelta(days=days)
  TASKS.append((province,d,f"{base}/publica/consulta-de-bops/buscador/BOP-{d:%d-%m-%Y}/"))
for d in [date(2026,10,29),date(2026,10,28),date(2026,10,27),date(2026,10,15),date(2026,10,1),date(2026,10,4)]:
 TASKS.append(("CORDOBA",d,f"https://bop.dipucordoba.es/dia/{d:%d-%m-%Y}"))
for u in [
 "https://sede.diphuelva.es",
 "https://sede.diphuelva.es/portal/boletin",
 "https://www.diphuelva.es/servicios/bop/",
 "https://www.bopmalaga.es",
 "http://www.bopmalaga.es",
 "https://bopmalaga.es/sumario.php?fecha=28-10-2026",
 "https://www.bopmalaga.es/sumario.php?fecha=28-10-2026",
 "https://bopmalaga.es",
]:
 TASKS.append(("OTHER",None,u))
def run(t):
 province,day,url=t
 try:
  r=requests.get(url,timeout=(5,12),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"},allow_redirects=True)
  h=BeautifulSoup(r.content[:700000],"html.parser")
  header=h.select_one("h2")
  title=h.title.get_text(" ",strip=True) if h.title else ""
  count=re.search(r"Resultados del\s+\d+\s+al\s+\d+\s+de\s+(\d+)",h.get_text(" ",strip=True))
  cards=h.select("li.elementoListado")
  pdf=[urljoin(r.url,a.get("href","")) for a in h.select("a[href]") if ".pdf" in a.get("href","").lower()]
  if province in ("GRANADA","SEVILLA"):
   if r.status_code!=200 or (not header or "BOP núm" not in header.get_text(" ",strip=True)) or not cards:
    print("DAY",province,day,r.status_code,len(r.content),"T",title[:70],"H",(header.get_text(" ",strip=True)[:70] if header else "-"),"COUNT",(count.group(1) if count else "-"),"CARDS",len(cards),"URL",r.url,flush=True)
   else:
    print("DAY",province,day,"OK","NUM",header.get_text(" ",strip=True)[:55],"TOTAL",count.group(1) if count else "-","LOADED",len(cards),"PDFS",len(pdf),flush=True)
   if (day.day in (29,28,15,1) and cards):
    candidate=next((c for c in cards if "Bases de la convocatoria" in c.get_text(" ",strip=True) or "proceso selectivo" in c.get_text(" ",strip=True)),cards[0])
    a=candidate.select_one("a.enlace_elemento")
    detail=urljoin(r.url,a["href"])
    d=requests.get(detail,timeout=(5,15))
    dh=BeautifulSoup(d.content[:700000],"html.parser")
    dp=[urljoin(detail,a.get("href","")) for a in dh.select("a[href]") if ".pdf" in a.get("href","").lower()]
    print("DETAIL",province,day,"HTTP",d.status_code,"URL",detail,"TITLE",str(dh.select_one("h1.titulo_detalle"))[:380],
      "PDFS",dp[:8],"TEXT",repr(dh.get_text(" ",strip=True)[:900]),flush=True)
  elif province=="CORDOBA":
   btext=h.get_text(" ",strip=True)
   htext=header.get_text(" ",strip=True) if header else "-"
   print("CORDOBA",day,r.status_code,"TITLE",title[:65],"HEADER",htext,"PDFS",len(pdf),flush=True)
   if len(pdf)>1:
    link=h.select_one('a[href*="/visor-pdf/"]')
    print("CORDOBA_SAMPLE",day,str(link.parent.parent)[:1800],flush=True)
  else:
   print("OTHER",r.status_code,url,"END",r.url,"BYTES",len(r.content),"TITLE",title[:130],"TEXT",repr(h.get_text(" ",strip=True)[:200]),flush=True)
 except Exception as ex:print("ERROR",province,str(day),url,type(ex).__name__,str(ex)[:145],flush=True)
with ThreadPoolExecutor(max_workers=8) as pool:list(pool.map(run,TASKS))
