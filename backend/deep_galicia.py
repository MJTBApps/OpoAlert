#!/usr/bin/env python3
"""Deep structural inspection of five Galician publisher archives."""
import requests,json,re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
T=[
("AC-DAY","https://bop.dacoruna.gal/bopportal/cambioBoletin?fechaInput=28%2f10%2f2026"),
("AC-INDEX","https://bop.dacoruna.gal/bopportal/ultimoBoletin?lang=es"),
("LU-NODE","https://deputacionlugo.gal/gl/node/85194"),
("LU-NODE-OLD","https://deputacionlugo.gal/gl/node/85060"),
("PO-INDEX","https://boppo.depo.gal/es/consulta-do-boppo"),
("OU-GNOSS","https://dou.gnoss.com/gl/comunidade/dou/busqueda-bop"),
("OU-PDF","https://bop.depourense.es/portalapi/api/edicto/descargar/pdf/353097/idioma/gl"),
("DOG-SEC","https://www.xunta.gal/diario-oficial-galicia/mostrarContenido.do?paginaCompleta=false&idEstado=5&rutaRelativa=true&ruta=/2026/20261029/Secciones2_es.html"),
("DOG-SEC-DIRECT","https://www.xunta.gal/dog/Publicados/2026/20261029/Secciones2_es.html"),
("DOG-OLD","https://www.xunta.gal/dog/Publicados/2026/20261028/Indice206_es.html")
]
def diag(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=(11,35),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"},stream=True)
  raw=b""
  for chunk in r.iter_content(150000):
   raw+=chunk
   if len(raw)>350000:break
  r.close()
  if raw.startswith(b"%PDF-"):return {"name":name,"http":r.status_code,"type":"pdf","url":r.url,"bytes":len(raw)}
  h=BeautifulSoup(raw,"html.parser")
  out={"name":name,"http":r.status_code,"url":r.url,"bytes":len(raw),
       "title":h.title.get_text(" ",strip=True)[:100] if h.title else ""}
  if name=="AC-DAY" or name=="AC-INDEX":
   header=h.find(string=re.compile(r"Sumario\s+d[oe]l?\s+Bolet",re.I))
   out["header"]=str(header)[:250]
   links=[a for a in h.select('a[href$=".pdf"]') if re.search(r"2026_\d{10}\.pdf",a.get("href",""))]
   out["pdf_count"]=len(links)
   out["samples"]=[str(a.parent.parent)[:1800] for a in links[::3][:4]]
   out["title_candidates"]=[(a.get("href"),a.get_text(" ",strip=True)[:100]) for a in links[:12]]
   out["prev"]=[(a.get_text(" ",strip=True),a.get("href")) for a in h.select('a[href*="cambioBoletin"]')]
  if name.startswith("LU"):
   out["headers"]=[(x.name,x.get_text(" ",strip=True)[:250]) for x in h.select("h1,h2,h3,h4")[:18]]
   out["links"]=[(a.get_text(" ",strip=True)[:80],urljoin(r.url,a.get("href",""))) for a in h.select('a[href]') if "pdf" in a.get("href","").lower() or "bop" in a.get("href","").lower() or "anuncio" in a.get("href","").lower()][:22]
   out["main_excerpt"]=(h.select_one("main") or h.select_one("article") or h.body).get_text(" ",strip=True)[-2600:]
   out["pdf_parent"]=[str(a.parent.parent)[:1500] for a in h.select('a[href*=".pdf"]')[:3]]
  if name=="PO-INDEX":
   out["h2"]=[x.get_text(" ",strip=True) for x in h.select("h2")]
   out["detail"]=[(a.get_text(" ",strip=True)[:80],a.get("href"),str(a.parent.parent)[:800]) for a in h.select('a[href]') if re.search(r"pdf|anuncio|sumario|descarga",a.get("href",""),re.I)][:26]
   out["date_calendar"]=[(a.get_text(" ",strip=True),a.get("href"),a.get("class"),a.get("onclick")) for a in h.select('a[href]') if re.search(r"calendar|fecha|date|day|sumario",a.get("href",""),re.I)][:28]
   out["form_attrs"]=[(f.get("action"), [(x.name,x.get("name"),x.get("value")) for x in f.select("input,select")[:18]]) for f in h.select("form")[:2]]
   out["portlet"]=[str(x)[:5500] for x in h.select("[id*='calendario']")[:2]]
  if name=="OU-GNOSS":
   cards=[x for x in h.select('h2') if "N.º" in x.get_text(" ",strip=True) or "Nº" in x.get_text(" ",strip=True)]
   out["issues"]=[str(x.parent.parent)[:3000] for x in cards[:3]]
   out["first_cards"]=[str(x.parent.parent)[:1500] for x in h.select("h2")[:4]]
   out["pagination"]=[(a.get_text(" ",strip=True)[:30],a.get("href")) for a in h.select('a[href]') if re.search("pagina|pagin|next",a.get("href","")+" "+a.get_text(" ",strip=True),re.I)][:20]
   out["doclinks"]=[(a.get_text(" ",strip=True)[:90],a.get("href")) for a in h.select('a[href*="portalapi"]')[:12]]
  if name.startswith("DOG"):
   out["headers"]=[(x.name,x.get_text(" ",strip=True)[:240]) for x in h.select("h2,h3,h4,h5,strong")[:14]]
   out["links"]=[(a.get_text(" ",strip=True)[:160],urljoin(r.url,a.get("href",""))) for a in h.select("a[href]") if re.search(r"Anuncio|DOG|pdf|Secciones",a.get("href",""),re.I)][:30]
   out["first_content"]=str(h.body)[:6500] if h.body else str(h)[:6500]
  return out
 except Exception as e:return {"name":name,"error":repr(e)[:350]}
with ThreadPoolExecutor(max_workers=7) as pool:
 for o in pool.map(diag,T):print("GAL_DEEP",json.dumps(o,ensure_ascii=False)[:19000],flush=True)
