#!/usr/bin/env python3
import requests,re,html
from bs4 import BeautifulSoup
from urllib.parse import urljoin
tasks=[
 ("HU-CAL","https://s2.diphuelva.es/servicios/bope_web/busquedaCalendario",{}),
 ("HU-ULT","https://s2.diphuelva.es/servicios/bope_web/UltimoBop",{}),
 ("MA-DATE","https://www.bopmalaga.es/sumario.php?fecha=20-10-2026",{"Referer":"https://www.bopmalaga.es/sumario.php","Cache-Control":"no-cache"}),
 ("MA-EDICT","https://www.bopmalaga.es/edicto.php?edicto=20261020-03688-2026-00",{"Referer":"https://www.bopmalaga.es/sumario.php?fecha=20-10-2026"}),
 ("MA-BOLETIN","https://www.bopmalaga.es/verificacion.php?archivo=201026202.pdf",{"Referer":"https://www.bopmalaga.es/sumario.php?fecha=20-10-2026"}),
]
for name,url,hd in tasks:
 try:
  z=requests.get(url,timeout=(8,20),headers={"User-Agent":"Mozilla/5.0",**hd},stream=False)
  raw=z.content
  h=BeautifulSoup(raw,"html.parser")
  print("\n===",name,z.status_code,"MIME",z.headers.get("Content-Type"),"LEN",len(raw),"URL",z.url,"HEAD",repr(raw[:130]),flush=True)
  if name.startswith("HU"):
   scripts=[x.string or x.get_text() for x in h.select("script:not([src])") if x.string or x.get_text()]
   merged="\n".join(scripts)
   for p in ["function cargarAnuncios", "new Ajax.Request", "Ajax.Updater","fetch(", "new XMLHttpRequest","servicio", "bope_web/", "consultaAnuncios", "ultBop", "cargarBoletines","obtenerAnuncios"]:
    mm=list(re.finditer(re.escape(p),merged,re.I))
    for match in mm[:4]:print("SCRIPT",p,repr(merged[max(0,match.start()-360):match.end()+1000]),flush=True)
   print("SELECT_IDS",[(x.name,x.get("id"),x.get("class")) for x in h.select("select,input[id],div[id]")[-35:]],flush=True)
   print("CAL_MONTH",[(x.get("id"),x.get("class")) for x in h.select("table")[:5]],flush=True)
  else:
   print("TITLE",h.title.get_text(" ",strip=True) if h.title else "-",flush=True)
   print("HEADERS",[(x.name,x.get_text(" ",strip=True)[:90]) for x in h.select("h2,h3")[:9]],flush=True)
   print("TEXT",repr(h.get_text(" ",strip=True)[-1300:]),flush=True)
   print("LINKS",[(a.get_text(" ",strip=True)[:100],urljoin(z.url,a.get("href",""))) for a in h.select("a[href]") if re.search(r"pdf|verific|edicto|descarg",str(a),re.I)][:22],flush=True)
   print("PDF-TAGS",[(x.name,x.get("src"),x.get("data")) for x in h.select("embed,iframe,object")[:8]],flush=True)
 except Exception as e:print("ERROR",name,type(e).__name__,str(e)[:300],flush=True)
