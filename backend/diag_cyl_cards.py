#!/usr/bin/env python3
import requests,re
from bs4 import BeautifulSoup
checks=[
("CY","https://bocyl.jcyl.es/boletin.do?fechaBoletin=29/10/2026"),
("AV","https://www.diputacionavila.es/boletin-oficial/2026/28-10-2026.html"),
("LE","https://bop.dipuleon.es/publica/consulta-de-bops/buscador/BOP-28-10-2026/"),
("ZA","https://www.diputaciondezamora.es/opencms/servicios/BOP/indice-bop/232446e5-d207-11f1-a057-1576f9d14bbb/"),
("SO","https://bop.dipsoria.es/index.php/mod.boloficial/mem.listadodia/fecha.28-10-2026"),
]
for name,url in checks:
 try:
  z=requests.get(url,timeout=14);h=BeautifulSoup(z.content,"html.parser")
  print("\n###",name,z.status_code,len(z.content),flush=True)
  if name=="CY":
   anchors=[a for a in h.select('a[href*="/pdf/BOCYL-D-"]') if ".pdf" in a.get("href","")]
   print("NUM_CANDIDATES",len(anchors),flush=True)
   for a in anchors[:3]:print("PDF_ROW",str(a.parent.parent.parent)[:3600],flush=True)
  elif name=="AV":
   print("NUM",[(v,h.get_text(" ",strip=True)[v.start()-100:v.start()+160]) for v in list(re.finditer(r"B\.O\.P\.\s*\d{1,3}/\d{2}",h.get_text(" ",strip=True)))[:3]],flush=True)
   print("CAND",str(h.select_one("div.listado"))[:2400],flush=True)
   print("BOOK_PDF",[(a.get_text(" ",strip=True)[:40],a.get("href")) for a in h.select("a[href]") if "bops/2026/28-10-2026" in a.get("href","")][:8],flush=True)
  elif name=="LE":
   first=h.select_one("li.elementoListado")
   print("FIRST",str(first)[:6200],flush=True)
   print("RESULTS",re.findall(r"Resultados\s+del\s+\d+\s+al\s+\d+\s+de\s+\d+",h.get_text(" ",strip=True))[:2],flush=True)
  elif name=="ZA":
   first=h.select_one('a[href$=".pdf"]')
   print("FIRSTPDF",str(first.parent.parent.parent)[:3100] if first else "-",flush=True)
   print("NODE",[(el.get("class"),str(el)[:2500]) for el in h.select("article,.anuncio,.anuncios,.listado_anuncios,.item,.panel")[:4]],flush=True)
  elif name=="SO":
   div=h.find("h3")
   print("H3",str(div.parent.parent)[:6000] if div else "-",flush=True)
   print("LINKS",[(a.get_text(" ",strip=True)[:65],a.get("href")) for a in h.select("a[href]")[-15:]],flush=True)
 except Exception as ex:print("ERROR",name,type(ex).__name__,str(ex)[:190],flush=True)
