"""Technical probe of modern Huesca BOP: cards, exported JSON, issue dates and PDF."""
from urllib.request import Request,urlopen
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import re,json
urls=[
 "https://bop.dphuesca.es/publica/consulta-de-bops/",
 "https://bop.dphuesca.es/publica/consulta-de-bops/buscador/BOP-28-10-2026/",
 "https://bop.dphuesca.es/publica/consulta-de-bops/buscador/BOP-28-10-2026/?page=2",
 "https://bop.dphuesca.es/publica/consulta-de-bops/buscador/BOP-25-10-2026/",
 "https://bop.dphuesca.es/system/modules/com.saga.inpro.theme.bop/elements/exportar-sumario.jsp?bop=7958cc5f-d213-11f1-ae02-00163e2193df&formato=json",
 "https://bop.dphuesca.es/publica/buscador-anuncios/anuncio/Bases-Bolsa-de-Empleo-Limpieza-Personal-Laboral-Temporal/",
]
for url in urls:
 print("\nPROBE",url,flush=True)
 try:
  with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"}),timeout=16) as r:
   raw=r.read(800_000);final=r.url
   print("HTTP",r.status,"TYPE",r.headers.get("content-type"),"BYTES",len(raw),"FINAL",final,flush=True)
  try:
   value=json.loads(raw)
   print("JSON VALID",list(value.keys())[:20],flush=True)
   print("JSON SAMPLE",str(value)[:900],flush=True)
   continue
  except Exception as e:print("NOT JSON",str(e)[:130],flush=True)
  soup=BeautifulSoup(raw,"html.parser")
  print("TITLE",soup.title.get_text(" ",strip=True) if soup.title else None,flush=True)
  print("H1...H4",[(x.name,x.get_text(" ",strip=True)[:85],x.get("class")) for x in soup.select("h1,h2,h3,h4")[:14]],flush=True)
  print("SELECTION",[ (css,len(soup.select(css))) for css in [".listado","li","div.resultado","div.listado","div.card","article","a[href*='anuncio']","a[href*='exportar']"]],flush=True)
  print("LINKS",[(a.get("href"),a.get_text(" ",strip=True)[:45]) for a in soup.select("a[href]") if any(k in a.get("href","") for k in ("pagina","page","?n","sumario","bop-","BOP-","pdf","publica/consulta","anuncio"))][:60],flush=True)
  for t in soup.find_all(string=re.compile(r"BOPH-2026-20700[1-9]"))[:2]:
   print("NOTICE_PARENT",str(t.parent.parent.parent)[:4400],flush=True)
  for t in soup.select("h3,h2"):
   if "Bolsa de Empleo Limpieza" in t.get_text(" ",strip=True):
    print("DETAIL_PARENT",str(t.parent)[:3200],flush=True)
  print("TAGS",[(s.name,s.get("class"),s.get("id")) for s in soup.select("form")[:6]],flush=True)
 except Exception as e:print("ERROR",type(e).__name__,str(e)[:250],flush=True)
