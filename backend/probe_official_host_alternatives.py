#!/usr/bin/env python3
"""Investigate publisher-owned alternate hosts for outstanding provincial BOPs.

Read-only diagnostic. A responding institutional home is NOT 30-day BOP
coverage, and publisher-only PDF links must be checked independently.
"""
import requests,concurrent.futures,json,re
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
URLS = {
"SA-CALENDAR":"https://www.lasalina.es/Aplicaciones/GestorInter.jsp?funcion=MenuIzquierda&prestacion=Boletines",
"SA-HOST":"https://www.lasalina.es/",
"SA-MOAD":"https://moad.lasalina.es/lasalina/",
"SA-MOADBOP":"https://moad.lasalina.es/lasalina/organizacionyrrhh/serviciosgenerales/archivo/servicios/hemeroteca/",
"SA-ALT":"https://www.lasalina.es/bop",
"SA-BOP":"https://sede.diputaciondesalamanca.gob.es/BOP/",
"SA-DIRECT":"https://sede.diputaciondesalamanca.gob.es/documentacion/bop/2026/20261028/BOP-SA-20261028-001.pdf",
"SA-DIRECT2":"https://sede.diputaciondesalamanca.gob.es/documentacion/bop/2026/20261028/BOP-SA-20261028.pdf",
"VA-SEDE":"https://www.sede.diputaciondevalladolid.es/",
"VA-SEDE2":"https://sede.diputaciondevalladolid.es/",
"VA-VERIFY":"https://www.sede.diputaciondevalladolid.es/verifica",
"VA-BOP":"https://bop.sede.diputaciondevalladolid.es/calendario",
"VA-PORTAL":"https://www.diputaciondevalladolid.es/boletin-oficial",
"VA-ALT":"https://www.sede.diputaciondevalladolid.es/bop",
"VA-WWW":"https://www.valladolid.gob.es/es/boletines-oficiales",
"BU-NOWWW":"https://burgos.es/",
"BU-WWW":"https://www.burgos.es/",
"BU-PORTAL":"https://bopbur.diputaciondeburgos.es/",
"BU-ALT":"https://sede.diputaciondeburgos.es/",
"BU-DIP":"https://www.diputaciondeburgos.es/",
"BU-2026PDF":"https://burgos.es/sites/default/files/file/subvencion/renat2026_15_extracto_bases_bop_16-03-2026.pdf",
"CE-NOWWW":"https://ceuta.es/ceuta/bocce",
"CE-WWW":"https://www.ceuta.es/ceuta/bocce",
"CE-DOCS":"https://ceuta.es/ceuta/documentos",
"CE-PORTAL":"https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1965-2026?Itemid=534",
"CE-PDF":"https://www.ceuta.es/ceuta/component/jdownloads/finish/1973-abril/23103-bocce-6607-10-04-2026?Itemid=0",
"CE-BOCCE":"https://bocce.ceuta.es/",
"CE-DATOS":"https://datosabiertos.ceuta.es/",
"CE-ALT":"https://www.ceuta.es/",
"CU-NOWWW":"https://dipucuenca.es/boletin-oficial-de-la-provincia",
"CU-BOP":"https://bop.dipucuenca.es/",
"CU-OTHER":"https://sede.dipucuenca.es/",
"CU-WWW":"https://www.dipucuenca.es/boletin-oficial-de-la-provincia",
"CB-NOWWW":"https://cantabria.es/web/boc",
"CB-BOC":"https://boc.cantabria.es/boces/",
"CB-ALT":"https://boc.gobcantabria.es/boces/",
"CB-DOWN":"https://www.cantabria.es/",
"AS-WWW":"https://www.asturias.es/",
"AS-SUM":"https://www.asturias.es/bopa/bopa2",
"AS-OPEN":"https://www.asturias.es/portal/site/asturias",
"AS-SERVICE":"https://www.asturias.es/servicios-del-bopa",
"AS-URL":"https://sede2.asturias.es/bopa/",
"NA-ALT":"https://bon.navarra.es/es/inicio"
}
def go(pair):
 name,url=pair
 try:
  s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0", "Accept-Language":"es-ES,es;q=0.9"})
  r=s.get(url,timeout=(5,13),allow_redirects=True,stream=True)
  body=b""
  for part in r.iter_content(8192):
   body+=part
   if len(body)>115000:break
  r.close()
  obj={"name":name,"status":r.status_code,"end":r.url,"ct":r.headers.get("Content-Type",""),
       "partialBytes":len(body),"pdf":body.startswith(b"%PDF-")}
  if not obj["pdf"]:
   h=BeautifulSoup(body,"html.parser")
   obj["title"]=h.title.get_text(" ",strip=True)[:140] if h.title else ""
   obj["text"]=h.get_text(" ",strip=True)[:330]
   refs=[]
   for a in h.select("a[href]"):
    label=a.get_text(" ",strip=True)
    link=urljoin(r.url,a.get("href",""))
    if re.search(r"(bop|bolet|pdf|2026|octubre|septiembre|hemeroteca|calendario)",label+" "+link,re.I):
     refs.append((label[:85],link[:250]))
   obj["links"]=refs[:22]
   if name=="SA-CALENDAR":
    obj["forms"]=[{"method":f.get("method"),"action":urljoin(r.url,f.get("action","")), "names":[t.get("name") for t in f.select("input[name]")][:30]} for f in h.select("form")[:8]]
    obj["htmlHints"]= [m.group(0) for m in re.finditer(r".{0,140}(?:202610|2026/10|boletin|descarga|onclick=).{0,220}",body.decode("iso-8859-1","replace"),re.I)][:12]
  return obj
 except Exception as ex:
  return {"name":name,"error":type(ex).__name__+": "+str(ex)[:210]}
with concurrent.futures.ThreadPoolExecutor(max_workers=18) as ex:
 for result in ex.map(go,URLS.items()):
  print("CLOSURE_ALTERNATIVE",json.dumps(result,ensure_ascii=False)[:12500],flush=True)
