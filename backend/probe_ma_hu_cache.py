#!/usr/bin/env python3
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests,re,hashlib,json
TESTS=[
("MA-basic","https://www.bopmalaga.es/sumario.php?fecha=20-10-2026",{}),
("MA-bust","https://www.bopmalaga.es/sumario.php?fecha=20-10-2026&nocache=827483",{}),
("MA-ref","https://www.bopmalaga.es/sumario.php?fecha=20-10-2026",{"Cache-Control":"no-cache","Pragma":"no-cache","Referer":"https://www.bopmalaga.es/sumario.php"}),
("MA-apex","https://bopmalaga.es/sumario.php?fecha=20-10-2026",{}),
("MA-sep","https://www.bopmalaga.es/sumario.php?fecha=03-09-2026",{}),
("MA-encode","https://www.bopmalaga.es/sumario.php?fecha=2026-10-20",{}),
("MA-query","https://www.bopmalaga.es/?fecha=20-10-2026",{}),
("HU-archive","https://s2.diphuelva.es/servicios/boparchivo",{}),
("HU-ultimo","https://s2.diphuelva.es/servicios/bope_web/UltimoBop",{}),
("HU-calendar","https://s2.diphuelva.es/servicios/bope_web/busquedaCalendario",{}),
]
for key,url,headers in TESTS:
 try:
  r=requests.get(url,headers={"User-Agent":"Mozilla/5.0",**headers},timeout=(10,18))
  h=BeautifulSoup(r.content,"html.parser")
  print("\n====",key,r.status_code,len(r.content),"HASH",hashlib.sha256(r.content).hexdigest()[:14],"END",r.url,"CACHE",[(k,v) for k,v in r.headers.items() if k.lower() in ("age","cache-control","vary","x-cache","etag","last-modified")],flush=True)
  if key.startswith("MA"):
   th=h.select_one("h2 time")
   date=th.get("datetime") if th else "-"
   cal=h.select_one('#table_calendario a[title*="20 de Octubre"],#table_calendario a[title*="Octubre"]')
   print("DATE",date,"FIRST",str(cal)[:220] if cal else "-","LIST",[(x.get_text(" ",strip=True)[:80],x.get("href","")) for x in h.select("section article a[href]")[:4]],flush=True)
  else:
   print("FIRST_TEXT",repr(h.get_text(" ",strip=True)[:370]),flush=True)
   print("FORMS",[(f.get("action"),f.get("method"),f.get("name"),[(i.get("name"),i.get("value"),i.name) for i in f.select("input,select")[:17]]) for f in h.select("form")[:5]],flush=True)
   print("SELECTS",[(x.get("id"),x.get("name"),[a.get("value") for a in x.select("option")[:8]],[a.get("value") for a in x.select("option")[-6:]]) for x in h.select("select")[:9]],flush=True)
   print("IFRAMES",[(x.name,x.get("src"),x.get("data")) for x in h.select("frame,iframe,embed,object")[:12]],flush=True)
   print("JS-LINES",[line.strip()[:400] for line in r.text.splitlines() if re.search(r"2026|2025|UltimoBop|cargarAnuncios|boparchivo|Calendario|bope_web",line,re.I)][:18],flush=True)
 except Exception as e:print("ERROR",key,type(e).__name__,str(e)[:340],flush=True)
