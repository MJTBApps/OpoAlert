#!/usr/bin/env python3
"""Inspección inicial oficial de nueve BOP de Castilla y León y BOCYL; sin publicar feeds."""
import requests,concurrent.futures,re,json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
URLS={
"Avila":"https://www.diputacionavila.es/",
"Burgos":"https://www.burgos.es/",
"Leon":"https://bop.dipuleon.es/publica/consulta-de-bops/",
"Palencia":"https://www.diputaciondepalencia.es/servicios/boletin-oficial-provincia",
"Salamanca":"https://www.lasalina.es/",
"Segovia":"https://www.dipsegovia.es/",
"Soria":"https://bop.dipsoria.es/index.php/mod.boloficial/relmenu.149",
"Valladolid":"https://bop.sede.diputaciondevalladolid.es/",
"Zamora":"https://www.diputaciondezamora.es/servicios/BOP/bop/",
"BOCYL":"https://bocyl.jcyl.es/",
}
def inspect(item):
 name,url=item
 try:
  s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
  r=s.get(url,timeout=(9,22),allow_redirects=True)
  h=BeautifulSoup(r.content[:1800000],"html.parser")
  title=h.title.get_text(" ",strip=True)[:130] if h.title else "-"
  anchors=[(a.get_text(" ",strip=True)[:80],urljoin(r.url,a.get("href",""))[:250]) for a in h.select("a[href]") if re.search("bop|bolet|2026|pdf|sumario|edicto|anuncio",a.get_text(" ",strip=True)+" "+a.get("href",""),re.I)]
  print("RESULT",name,"STATUS",r.status_code,"END",r.url,"SIZE",len(r.content),"TITLE",title,flush=True)
  print("TEXT",name,repr(h.get_text(" ",strip=True)[:750]),flush=True)
  print("LINKS",name,json.dumps(anchors[:32],ensure_ascii=False),flush=True)
  print("FORMS",name,[(f.get("method"),f.get("action"),[i.get("name") for i in f.select("input[name]")[:12]]) for f in h.select("form")[:5]],flush=True)
 except Exception as e:print("ERROR",name,type(e).__name__,str(e)[:230],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:list(pool.map(inspect,URLS.items()))
