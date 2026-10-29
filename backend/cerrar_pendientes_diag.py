#!/usr/bin/env python3
"""Read-only check of outstanding BOP, regional journals and official fallbacks."""
import json,requests,re,platform
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
from bs4 import BeautifulSoup
TARGETS=[
("Burgos","https://bopbur.diputaciondeburgos.es/"),
("Burgos2","https://bopbur.diputaciondeburgos.es/bopbur-2026-207"),
("BurgosDip","https://www.burgos.es/boletin-oficial-de-la-provincia"),
("Salamanca","https://www.lasalina.es/Aplicaciones/GestorInter.jsp?funcion=MenuIzquierda&prestacion=Boletines"),
("SalamancaSede","https://sede.diputaciondesalamanca.gob.es/BOP/"),
("SalamancaAlt","https://www.lasalina.es/bop"),
("Segovia","https://www.dipsegovia.es/bop"),
("SegoviaBOP","https://bop.dipsegovia.es/"),
("Valladolid","https://bop.sede.diputaciondevalladolid.es/calendario"),
("ValladolidRoot","https://bop.sede.diputaciondevalladolid.es/"),
("ValladolidDip","https://www.diputaciondevalladolid.es/"),
("Albacete","https://bop.dipualba.es/"),
("AlbaceteAlt","https://www.dipualba.es/servicios/boletin-oficial-de-la-provincia"),
("Cuenca","https://www.dipucuenca.es/boletin-oficial-de-la-provincia"),
("CuencaBOP","https://bop.dipucuenca.es/"),
("Jaen","https://bop.dipujaen.es/bopdigital/"),
("JaenHist","https://bophistorico.dipujaen.es/"),
("Malaga","https://www.bopmalaga.es/sumario.php?fecha=29-10-2026"),
("Lleida","https://ebop.diputaciolleida.cat/bop/"),
("LleidaRoot","https://ebop.diputaciolleida.cat/"),
("LleidaHist","https://ebop.diputaciolleida.cat/aplicacions/bop/bopV1/"),
("Cantabria","https://boc.cantabria.es/boces/"),
("CantabriaAlt","https://boc.gobcantabria.es/boces/"),
("CantabriaOpen","https://datos.cantabria.es/"),
("Asturias","https://miprincipado.asturias.es/bopa/"),
("AsturiasAlt","https://sede.asturias.es/bopa/"),
("AsturiasOpen","https://datos.asturias.es/"),
("DOGV","https://dogv.gva.es/"),
("DOGC","https://dogc.gencat.cat/"),
("BOA","https://www.boa.aragon.es/"),
("BOJA","https://www.juntadeandalucia.es/eboja.html"),
]
def check(pair):
 name,u=pair
 try:
  req=requests.get(u,timeout=(7,13),headers={"User-Agent":"Mozilla/5.0 (compatible; OpoAlert source audit/2.0)","Accept-Language":"es-ES,es;q=0.9"},stream=True)
  raw=b""
  for chunk in req.iter_content(50000):
   raw+=chunk
   if len(raw)>135000:break
  req.close()
  h=BeautifulSoup(raw,"html.parser")
  links=[(a.get_text(" ",strip=True)[:46],urljoin(req.url,a.get("href",""))[:190]) for a in h.select("a[href]") if re.search(r"2026|octubre|setembre|bolet|bop|pdf|sumario|listado|archiv|histor",a.get_text(" ",strip=True)+" "+a.get("href",""),re.I)][:12]
  out={"name":name,"http":req.status_code,"length":len(raw),"type":req.headers.get("Content-Type"),"url":req.url[:200],"title":(h.title.get_text(" ",strip=True)[:100] if h.title else ""),"text":h.get_text(" ",strip=True)[:240],"links":links}
  if raw.startswith(b"%PDF"):out["pdf"]=True
  return out
 except Exception as e:return {"name":name,"error":type(e).__name__+": "+str(e)[:160]}
print("PLATFORM",platform.platform(),flush=True)
with ThreadPoolExecutor(max_workers=12) as ex:
 for data in ex.map(check,TARGETS):print("CLOSE_DIAG",json.dumps(data,ensure_ascii=False)[:4800],flush=True)
