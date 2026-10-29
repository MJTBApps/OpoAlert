import requests,re,json
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
Q=[
("DOGSEC","https://www.xunta.gal/diario-oficial-galicia/mostrarContenido.do?paginaCompleta=false&idEstado=5&rutaRelativa=true&ruta=/2026/20261029/Secciones2_es.html"),
("DOGDIRECT","https://www.xunta.gal/dog/Publicados/2026/20261029/Secciones2_es.html"),
("DOGPREV","https://www.xunta.gal/diario-oficial-galicia/portalPublicoHome.do?fecha=20261028&lang=es"),
("PO","https://boppo.depo.gal/es/consulta-do-boppo"),
("OU","https://dou.gnoss.com/gl/comunidade/dou/busqueda-bop"),
("LU","https://deputacionlugo.gal/gl/node/85194")
]
def get(pair):
 name,url=pair
 try:
  r=requests.get(url,timeout=(10,28),headers={"User-Agent":"Mozilla/5.0"})
  soup=BeautifulSoup(r.content,"html.parser")
  o={"n":name,"status":r.status_code,"url":r.url,"length":len(r.content),"text":soup.get_text(" ",strip=True)[:700]}
  if name.startswith("DOG"):
   o["content"]=[(x.get_text(" ",strip=True)[:180],urljoin(r.url,x.get("href",""))) for x in soup.select("a[href]") if "pdf" in x.get("href","").lower() or "Anuncio" in x.get("href","")][:24]
   o["excerpt"]=str(soup.select_one("#contenido") or soup.select_one("body") or soup)[:1700]
  if name=="PO":
   li=[a for a in soup.select("a[href]") if re.search(r"pdf|documento|boletin|anuncio",a.get("href",""),re.I)]
   o["pdf"]= [(a.get_text(" ",strip=True)[:90],a.get("href")) for a in li[-24:]]
   o["dom"]=[str(a.parent.parent)[:1550] for a in li[-15:-12]]
   o["dates"]=[(a.get_text(" ",strip=True),a.get("href"),a.get("onclick")) for a in soup.select("a[href*='calendar']")[:14]]
   o["scriptSignals"]=[x[:280] for x in re.findall(r".{0,120}(?:20261029|idBoletin|idAnuncio|fechaBoletin|loadPage|calendar.date|_calendar.date).{0,120}",r.text,re.I)[:12]]
  if name=="OU":
   o["h2"]=[x.get_text(" ",strip=True)[:160] for x in soup.select("h2")[:15]]
   o["item"]=str(soup.select('a[href*="portalapi"]')[0].parent.parent)[:2300] if soup.select('a[href*="portalapi"]') else None
   o["numLinks"]=[(a.get_text(" ",strip=True)[:90],a.get("href")) for a in soup.select("a[href]") if re.search(r"boletin|boletín|N.º|Número|descarga.bolet|csv",a.get_text(" ",strip=True)+" "+a.get("href",""),re.I)][:25]
   o["forms"]=[(f.get("action"),f.get("method"),[(x.get("name"),x.get("value")) for x in f.select("input")[:12]]) for f in soup.select("form")[:4]]
  if name=="LU":
   o["num"]=[x.get_text(" ",strip=True)[:120] for x in soup.select("h2")]
   o["node"]=[str(a.parent.parent)[:1500] for a in soup.select('a[href*="inline-files"]')[:4]]
   o["pdf"]= [(a.get("href"),a.get_text(" ",strip=True)[:100]) for a in soup.select('a[href*=".pdf"]')[:9]]
  return o
 except Exception as e:return {"n":name,"error":str(e)}
with ThreadPoolExecutor(max_workers=6) as p:
 for o in p.map(get,Q):print("GAL_SHORT",json.dumps(o,ensure_ascii=False)[:11000],flush=True)
