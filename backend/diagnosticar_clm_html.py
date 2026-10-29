#!/usr/bin/env python3
"""Inspect official issue pages, item containers, and alternative host status. Diagnostics only."""
from bs4 import BeautifulSoup
import requests,concurrent.futures,re,json,urllib3
from urllib.parse import urljoin
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
TESTS=[
 ("TO-DAY","https://bop.diputoledo.es/webEbop/ebopResumen.jsp?publication_date=29/10/2026&publication_date_to=29/10/2026",True),
 ("TO-OLD","https://bop.diputoledo.es/webEbop/ebopResumen.jsp?publication_date=19/10/2026&publication_date_to=19/10/2026",True),
 ("TO-CALENDAR","https://bop.diputoledo.es/webEbop/ebopCalendar.jsp",True),
 ("TO-SEARCH","https://bop.diputoledo.es/webEbop/ebop.jsp",True),
 ("GU-CURRENT","https://boletin.dguadalajara.es/boletin/",True),
 ("GU-DAY","https://boletin.dguadalajara.es/boletin/index.php/buscar-k2-menu/date/2026/10/26?catid=9",True),
 ("GU-ISSUE","https://boletin.dguadalajara.es/boletin/index.php/9-general/66386-Boletin-Oficial-de-la-Provincia-de-Guadalajara-num-204-de-lunes-26-de-Octubre-de-2026",True),
 ("DOCM-OLD","https://docm.jccm.es/docm/cambiarBoletin.do?fecha=20261027",True),
 ("DOCM-EXT","https://docm.jccm.es/docm/cambiarBoletin.do?fecha=20261028-ext-2&numDogv=2",True),
 ("CR-NOVERIFY","https://bop.dipucr.es/",False),
 ("CR-SEARCH","https://bop.dipucr.es/buscador",False),
 ("CR-WWW","https://www.dipucr.es/",True),
 ("CU-WWW","https://dipucuenca.es/boletin-oficial-de-la-provincia",True),
 ("CU-HTTP","http://www.dipucuenca.es/boletin-oficial-de-la-provincia",True),
 ("CU-SEDE","https://sede.dipucuenca.es/",True),
 ("AB-WWW","https://www.dipualba.es/",True),
 ("AB-HTTP","http://bop.dipualba.es/",True),
]
def task(x):
 label,url,verify=x
 try:
  r=requests.get(url,timeout=(8,16),verify=verify,headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36","Accept-Language":"es"},allow_redirects=True)
  print("\n=== ",label,r.status_code,r.url,"BYTES",len(r.content),"CT",r.headers.get("Content-Type"),flush=True)
  if "html" not in r.headers.get("Content-Type","").lower():print("START",repr(r.content[:200]),flush=True);return
  h=BeautifulSoup(r.content,"html.parser")
  print("TEXT",repr(h.get_text(" ",strip=True)[:1800]),flush=True)
  print("TITLE",h.title.get_text(" ",strip=True) if h.title else "-",flush=True)
  print("HEADERS",[(p.name,p.get("class"),p.get_text(" ",strip=True)[:160]) for p in h.select("h1,h2,h3,h4")[:25]],flush=True)
  links=[(a.get_text(" ",strip=True)[:80],urljoin(r.url,a["href"]),a.parent.name,a.parent.get("class")) for a in h.select("a[href]") if re.search(r"bolet|bop|pdf|anunc|2026|ver|descarg|202[0-9]/|cambiar",str(a),re.I)]
  print("LINKS",json.dumps(links[:85],ensure_ascii=False),flush=True)
  print("HTML_DIVS",[(e.name,e.get("class"),e.get("id"),e.get_text(" ",strip=True)[:150]) for e in h.select("article,section,div[class*='item'],div[class*='dispos'],table,tr")[:32]],flush=True)
 except Exception as e:print("ERROR",label,type(e).__name__,str(e)[:330],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:list(ex.map(task,TESTS))
