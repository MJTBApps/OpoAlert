#!/usr/bin/env python3
"""Structural samples only, to develop rigorous BOP Cordoba and Malaga readers."""
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests,re,concurrent.futures
URLS=[
("CORDOBA-01","https://bop.dipucordoba.es/dia/01-10-2026"),
("CORDOBA-28","https://bop.dipucordoba.es/dia/28-10-2026"),
("CORDOBA-29","https://bop.dipucordoba.es/dia/29-10-2026"),
("CORDOBA-SAT","https://bop.dipucordoba.es/dia/24-10-2026"),
("MALAGA-28","https://www.bopmalaga.es/sumario.php?fecha=28-10-2026"),
("MALAGA-29","https://www.bopmalaga.es/sumario.php?fecha=29-10-2026"),
("MALAGA-01","https://www.bopmalaga.es/sumario.php?fecha=01-10-2026"),
("HUELVA-SEDE","https://sede.diphuelva.es"),
("HUELVA-OFFICIAL","https://www.diphuelva.es/servicios/bop/"),
]
def run(item):
 label,url=item
 try:
  r=requests.get(url,timeout=(10,28),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"})
  h=BeautifulSoup(r.text,"html.parser")
  print("\n======",label,"HTTP",r.status_code,"LEN",len(r.content),flush=True)
  if label.startswith("CORDOBA"):
   a=next((a for a in h.select('a[href]') if re.search(r"/visor-pdf/\d\d-\d\d-\d{4}/BOP-A-\d{4}-\d+\.pdf",a.get("href",""))),None)
   print("TITLE",h.title.get_text(" ",strip=True) if h.title else "-")
   print("H2",[(n.get_text(" ",strip=True)) for n in h.select("h2")[:14]])
   if a:
    for n in range(1,7):
     a=a.parent
     print("PARENT",n,a.name,a.get("class"),str(a)[:2700])
   print("RAW_LINKS",[(a.get_text(" ",strip=True)[:75],a.get("href")) for a in h.select("a[href]")[:25]],flush=True)
  elif label.startswith("MALAGA"):
   print("TITLE",h.title.get_text(" ",strip=True)[:140] if h.title else "-")
   print("HEADINGS",[(x.name,x.get_text(" ",strip=True)[:175]) for x in h.select("h1,h2,h3,h4")[:18]])
   print("BODY",repr(h.get_text(" ",strip=True)[-3200:]))
   print("PDFS",[(a.get_text(" ",strip=True)[:90],a.get("href")) for a in h.select('a[href]') if ".pdf" in a.get("href","").lower()][:20])
   x=h.find(string=re.compile("Edicto \\d+/2026"))
   print("EDICT_PARENT",str(x.parent.parent)[:4500] if x else "-",flush=True)
   print("HTML_HEAD",str(h.body)[:3000] if h.body else "-",flush=True)
  else:
   links=[(a.get_text(" ",strip=True)[:70],urljoin(r.url,a.get("href",""))[:230]) for a in h.select('a[href]') if "BOP" in a.get_text(" ",strip=True).upper() or "bolet" in a.get("href","").lower() or "bop" in a.get("href","").lower()]
   print("BOP_LINKS",links[:28],flush=True)
   if label=="HUELVA-SEDE":print("SCRIPT_URLS",[x.get("src") for x in h.select("script[src]")[:15]],flush=True)
 except Exception as e:print("ERROR",label,type(e).__name__,str(e)[:250],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(run,URLS))
