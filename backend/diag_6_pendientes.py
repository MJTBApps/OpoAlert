#!/usr/bin/env python3
"""Diagnóstico solo de lectura: seis fuentes oficiales pendientes, sin publicar datos."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests,re,json,sys
P=[
("AB-HOME","https://bop.dipualba.es/"),
("AB-WWW","https://www.dipualba.es/"),
("AB-BOPALT","https://www.dipualba.es/servicios/boletin-oficial-de-la-provincia"),
("AB-BOPHTTP","http://bop.dipualba.es/"),
("CU-PORTAL","https://www.dipucuenca.es/boletin-oficial-de-la-provincia"),
("CU-ROOT","https://www.dipucuenca.es/"),
("CU-HOST","https://bop.dipucuenca.es/"),
("CU-PDF","https://www.dipucuenca.es/documents/"),
("JA-DIGITAL","https://bop.dipujaen.es/bopdigital/"),
("JA-NEW","https://bop.dipujaen.es/"),
("JA-OLD","https://bophistorico.dipujaen.es/"),
("HU-DIP","https://diphuelva.es/servicios/bop"),
("HU-ULTIMO","https://s2.diphuelva.es/servicios/bope_web/UltimoBop"),
("HU-CAL","https://s2.diphuelva.es/servicios/bope_web/busquedaCalendario"),
("HU-SEDE","https://sede.diphuelva.es/servicios/bop"),
("MA-TODAY","https://www.bopmalaga.es/sumario.php?fecha=29-10-2026"),
("MA-OLD","https://www.bopmalaga.es/sumario.php?fecha=20-10-2026"),
("MA-DOT","https://www.bopmalaga.es/sumario.php.?fecha=20-10-2026"),
("MA-NOW","https://www.bopmalaga.es/"),
("MD-SUM","https://www.bocm.es/boletin/CM_Boletin_BOCM/2026/10/28/BOCM-20261028258.xml"),
("MD-ALT","https://w3.bocm.es/boletin/CM_Boletin_BOCM/2026/10/28/BOCM-20261028258.xml"),
("MD-ORIGIN","https://origin-www.bocm.es/boletin/CM_Boletin_BOCM/2026/10/28/BOCM-20261028258.xml"),
]
def run(item):
 name,url=item
 try:
  resp=requests.get(url,timeout=(7,13),headers={"User-Agent":"Mozilla/5.0","Accept":"text/html,application/xml,application/pdf,*/*"},allow_redirects=True)
  print("\n###",name,"CODE",resp.status_code,"LEN",len(resp.content),"END",resp.url,"MIME",resp.headers.get("Content-Type"),flush=True)
  data=resp.content
  if b"<" not in data[:200]:
   print("HEAD",repr(data[:230]),flush=True);return
  if (b"<sumario>" in data[:200] or data.lstrip().startswith(b"<?xml")):
   print("XML_HEAD",repr(data[:1600]),flush=True);return
  h=BeautifulSoup(data,"html.parser")
  print("TITLE",h.title.get_text(" ",strip=True)[:200] if h.title else "-",flush=True)
  print("TEXT",repr(h.get_text(" ",strip=True)[:1000]),flush=True)
  links=[(a.get_text(" ",strip=True)[:65],urljoin(resp.url,a.get("href",""))[:230]) for a in h.select("a[href]")]
  selected=[x for x in links if re.search(r"(bop|bolet|2026|archiv|PDF|calend|sumari|descarg|anunci|octubre|fecha)",x[0]+" "+x[1],re.I)]
  print("LINKS",json.dumps(selected[:35],ensure_ascii=False),flush=True)
  print("FORMS",[(f.get("action"),f.get("method"),[a.get("name") for a in f.select("input[name]")[:12]]) for f in h.select("form")[:5]],flush=True)
  print("IFRAMES",[(x.get("src"),x.get("id")) for x in h.select("iframe")[:10]],flush=True)
  print("SCRIPT",[(x.get("src"),x.get("type")) for x in h.select("script[src]")[:12]],flush=True)
 except Exception as ex:print("ERR",name,type(ex).__name__,str(ex)[:350],flush=True)
with ThreadPoolExecutor(max_workers=7) as p:list(p.map(run,P))
