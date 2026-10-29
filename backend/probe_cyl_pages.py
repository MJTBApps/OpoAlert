#!/usr/bin/env python3
import requests,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
URLs=[
 ("ZA-P0","https://www.diputaciondezamora.es/opencms/servicios/BOP/busqueda-en-el-bop/"),
 ("ZA-P1","https://www.diputaciondezamora.es/opencms/servicios/BOP/busqueda-en-el-bop/?page=1"),
 ("ZA-P2","https://www.diputaciondezamora.es/opencms/servicios/BOP/busqueda-en-el-bop/?page=2"),
 ("ZA-D","https://www.diputaciondezamora.es/opencms/servicios/BOP/indice-bop/232446e5-d207-11f1-a057-1576f9d14bbb/"),
 ("SO-D","https://bop.dipsoria.es/index.php/mod.boloficial/mem.detalle/id.55780/relcategoria.210"),
 ("SG-LIST","https://www.dipsegovia.es/bop"),
]
for n,u in URLs:
 try:
  z=requests.get(u,timeout=(9,20));h=BeautifulSoup(z.content,"html.parser")
  print("\n###",n,z.status_code,len(z.content),"URL",z.url,flush=True)
  print("TITLE",h.title.get_text(" ",strip=True)[:95] if h.title else "-",flush=True)
  if n.startswith("ZA-P"):
   print("HEADINGS",[x.get_text(" ",strip=True)[:90] for x in h.select("h3")[:16]],flush=True)
   print("PAGE_LINKS",[(a.get_text(" ",strip=True),urljoin(u,a["href"])) for a in h.select('a[href*="page"],a[href*="offset"],a[href*="p="]')][-15:],flush=True)
   print("FORMS",[(f.get("action"),f.get("method"),str(f)[:1700]) for f in h.select("form")[-2:]],flush=True)
  elif n=="ZA-D":
   a=next((a for a in h.select('a[href$=".pdf"]') if "anuncios/" in a["href"]),None)
   print("ANC",str(a),flush=True)
   if a:
    print("PARENT",str(a.parent.parent.parent)[:4400],flush=True)
   print("COUNT",len([a for a in h.select('a[href$=".pdf"]') if "anuncios/" in a["href"]]),flush=True)
  elif n=="SO-D":
   print("ARTICLE",str(h.select_one("div.noticia") or h.select_one(".contenido") or h.body)[-5500:],flush=True)
   print("PDFS",[(a.get_text(" ",strip=True)[:100],urljoin(u,a["href"])) for a in h.select("a[href]") if ".pdf" in a["href"].lower()],flush=True)
  elif n=="SG-LIST":
   print("DATES",[(a.get_text(" ",strip=True),urljoin(u,a["href"])) for a in h.select("a[href]") if re.search(r"\d{2} de octubre 2026|\d{2} de septiembre 2026",a.get_text(" ",strip=True),re.I)][:35],flush=True)
   print("PDFS",[(a.get_text(" ",strip=True)[:50],urljoin(u,a["href"])) for a in h.select("a[href]") if re.search(r"\d{8}.*\.pdf",a["href"],re.I)][:6],flush=True)
 except Exception as e:print("ERROR",n,type(e).__name__,str(e)[:320],flush=True)
