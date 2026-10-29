#!/usr/bin/env python3
"""Precise DOM and API schema for verified Castilla y León source readers."""
import requests,re,json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
S=[
("AV-day","https://www.diputacionavila.es/boletin-oficial/2026/28-10-2026.html"),
("AV-index","https://www.diputacionavila.es/boletin-oficial/2026/"),
("LE-day","https://bop.dipuleon.es/publica/consulta-de-bops/buscador/BOP-28-10-2026/"),
("PA-day","https://www.diputaciondepalencia.es/servicios/boletin-oficial-provincia/bop-no-129-miercoles-28-octubre-2026"),
("SG-day","https://www.dipsegovia.es/bop?p_p_id=as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm&p_p_lifecycle=0&_as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm_mvcPath=%2Fpublisher%2Fdetail.jsp&_as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm_articleId=20195381"),
("SO-day","https://bop.dipsoria.es/index.php/mod.boloficial/mem.listadodia/fecha.28-10-2026"),
("ZA-day","https://www.diputaciondezamora.es/opencms/servicios/BOP/indice-bop/232446e5-d207-11f1-a057-1576f9d14bbb/"),
("CY-day","https://bocyl.jcyl.es/boletin.do?fechaBoletin=28/10/2026"),
]
for n,u in S:
 try:
  z=requests.get(u,timeout=(9,18),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"})
  h=BeautifulSoup(z.content,"html.parser")
  print("\n##",n,z.status_code,len(z.content),z.url,flush=True)
  print("H",[(x.name,x.get("id"),x.get("class"),x.get_text(" ",strip=True)[:90]) for x in h.select("h2,h3,h4")[:9]],flush=True)
  if n=="AV-day":
   a=h.find(string=re.compile("Listado de los anuncios publicados"))
   print("TITLE_SCOPE",str(a.parent.parent)[:4400] if a else "-",flush=True)
   print("TARGET",[(a.get_text(" ",strip=True)[:65],urljoin(z.url,a["href"])) for a in h.select("a[href]") if re.search(r"pdf|/anuncios/|no |nº |número",a.get_text(" ",strip=True)+a["href"],re.I)][-20:],flush=True)
  elif n=="AV-index":
   print("LINKS",[(a.get_text(" ",strip=True)[:55],urljoin(z.url,a["href"])) for a in h.select("a[href]") if re.search(r"(/boletin-oficial/2026/\d{1,2}-10-2026|/boletin-oficial/2026/\d{1,2}-09-2026)",a["href"])][:34],flush=True)
  elif n=="LE-day":
   rows=h.select("li.elementoListado")
   print("LI_COUNTS",len(rows),"HTML_FIRST",str(rows[0])[:5100] if rows else "-",flush=True)
   print("LINKS_PDF",[(a.get_text(" ",strip=True)[:55],urljoin(z.url,a["href"])) for a in h.select("a[href]") if ".pdf" in a["href"].lower()][:7],flush=True)
  elif n=="PA-day":
   print("ROWS",[(x.name,x.get("class"),str(x)[:3600]) for x in h.select("article,.field--name-body,.field,section")[-7:]],flush=True)
   print("PDF",[(a.get_text(" ",strip=True)[:65],urljoin(z.url,a["href"])) for a in h.select("a[href]") if ".pdf" in a["href"].lower()][:12],flush=True)
  elif n=="SG-day":
   print("TEXT",repr(h.get_text(" ",strip=True)[-1600:]),flush=True)
   print("PDF",[(a.get_text(" ",strip=True)[:65],urljoin(z.url,a["href"])) for a in h.select("a[href]") if ".pdf" in a["href"].lower()][:30],flush=True)
  elif n=="SO-day":
   print("TEXT",repr(h.get_text(" ",strip=True)[-2200:]),flush=True)
   print("CONTENT",str(h.select_one("#content") or h.select_one("#contenido") or h.body)[-5700:],flush=True)
   print("PDF",[(a.get_text(" ",strip=True)[:80],urljoin(z.url,a["href"])) for a in h.select("a[href]") if ".pdf" in a["href"].lower()][:14],flush=True)
  elif n=="ZA-day":
   print("H",[(x.name,x.get_text(" ",strip=True)[:140]) for x in h.select("h1,h2,h3,h4")[:22]],flush=True)
   print("TEXT",repr(h.get_text(" ",strip=True)[-1600:]),flush=True)
   print("LINKS",[(a.get_text(" ",strip=True)[:80],urljoin(z.url,a["href"])) for a in h.select("a[href]") if re.search("pdf|anuncio|detalle|bop",a["href"],re.I)][-20:],flush=True)
  elif n=="CY-day":
   print("H",[(x.name,x.get_text(" ",strip=True)[:110]) for x in h.select("h1,h2,h3,h4")[:13]],flush=True)
   print("LINKS",[(a.get_text(" ",strip=True)[:90],urljoin(z.url,a["href"])) for a in h.select("a[href]") if re.search(r"2026|\.pdf|\.xml",a["href"],re.I)][:35],flush=True)
 except Exception as e:print("ERROR",n,type(e).__name__,str(e)[:220],flush=True)
BASE="https://analisis.datosabiertos.jcyl.es/api/explore/v2.1/catalog/datasets/bocyl/records"
for label,params in [
 ("RECENT",{"order_by":"fecha_publicacion desc","limit":1}),
 ("FILTER",{"where":"fecha_publicacion >= date'2026-09-30' and fecha_publicacion <= date'2026-10-29'","limit":1}),
 ("FILTER2",{"where":"fecha_publicacion between '2026-09-30' and '2026-10-29'","limit":1}),
]:
 try:
  z=requests.get(BASE,params=params,timeout=(8,20))
  print("API",label,z.status_code,z.url,"DATA",repr(z.text[:1400]),flush=True)
 except Exception as e:print("APIERROR",label,type(e).__name__,str(e)[:220],flush=True)
