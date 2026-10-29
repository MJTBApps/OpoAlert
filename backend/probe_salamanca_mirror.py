#!/usr/bin/env python3
"""Read-only official Salamanca mirror and old calendar investigation."""
import requests,re,json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
urls={
"calendar":"https://www.lasalina.es/Aplicaciones/GestorInter.jsp?funcion=MenuIzquierda&prestacion=Boletines",
"new-bop-info":"https://www.lasalina.es/lasalina/organizacionyrrhh/serviciosgenerales/boletin/bop.html",
"moad-bop-info":"https://moad.lasalina.es/lasalina/organizacionyrrhh/serviciosgenerales/boletin/bop.html",
"pdf-known-2026":"https://www.lasalina.es/documentacion/bop/2026/20260505/BOP-SA-20260505-013.pdf",
"pdf-oct16-003":"https://www.lasalina.es/documentacion/bop/2026/20261016/BOP-SA-20261016-003.pdf",
"pdf-oct28-001":"https://www.lasalina.es/documentacion/bop/2026/20261028/BOP-SA-20261028-001.pdf",
"pdf-oct28-002":"https://www.lasalina.es/documentacion/bop/2026/20261028/BOP-SA-20261028-002.pdf",
"pdf-oct28-003":"https://www.lasalina.es/documentacion/bop/2026/20261028/BOP-SA-20261028-003.pdf",
"pdf-oct28-004":"https://www.lasalina.es/documentacion/bop/2026/20261028/BOP-SA-20261028-004.pdf",
"moad-pdf-oct16-003":"https://moad.lasalina.es/documentacion/bop/2026/20261016/BOP-SA-20261016-003.pdf",
"directory-oct16":"https://www.lasalina.es/documentacion/bop/2026/20261016/",
"directory-oct28":"https://www.lasalina.es/documentacion/bop/2026/20261028/",
"summary1":"https://www.lasalina.es/documentacion/bop/2026/20261028/SUMARIO.pdf",
"summary2":"https://www.lasalina.es/documentacion/bop/2026/20261028/BOP-20261028.pdf",
"search":"https://www.lasalina.es/presidencia/buscador.html?action=search&query=BOP-SA-20261028&searchPage=1"
}
for name,url in urls.items():
 try:
  r=requests.get(url,timeout=(6,14),stream=True,headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
  c=b""
  for b in r.iter_content(8192):
   c+=b
   if len(c)>180000:break
  r.close()
  result={"name":name,"http":r.status_code,"end":r.url,"ct":r.headers.get("Content-Type",""),"partial":len(c),"pdf":c.startswith(b"%PDF-")}
  if not result["pdf"]:
   h=BeautifulSoup(c,"html.parser")
   result["title"]=h.title.get_text(" ",strip=True)[:120] if h.title else ""
   result["text"]=h.get_text(" ",strip=True)[:750]
   if name=="calendar":
    html=c.decode("latin-1","replace")
    matches=[m for m in re.finditer("octubre|2026|javascript:|onClick|fecha|bop",html,re.I)]
    result["patterns"]=[html[max(0,m.start()-170):m.end()+300] for m in matches[20:55]]
    result["hrefs"]=[(a.get_text(" ",strip=True)[:50],urljoin(r.url,a.get("href"))) for a in h.select("a[href]") if re.search("bop|bolet|2026|octubre|septiembre|pdf|fecha",a.get("href","")+" "+a.get_text(" ",strip=True),re.I)][:60]
    result["controls"]= [str(x)[:450] for x in h.select("[onclick],[onchange]") if re.search("BOP|bolet|2026|fecha|pdf|public",str(x),re.I)][:30]
   elif name=="search":
    result["searchresults"]=[(x.get_text(" ",strip=True)[:85],urljoin(r.url,x.get("href"))) for x in h.select("a[href]") if "20261028" in str(x)][:55]
   elif "info" in name:
    result["links"]=[(a.get_text(" ",strip=True)[:50],urljoin(r.url,a.get("href"))) for a in h.select("a[href]") if re.search("bop|bolet|pdf|sede",str(a),re.I)][:35]
   else:result["head"]=repr(c[:160])
  print("SALAMANCA_MIRROR",json.dumps(result,ensure_ascii=False)[:14000],flush=True)
 except Exception as e:print("SALAMANCA_MIRROR",json.dumps({"name":name,"error":type(e).__name__+": "+str(e)[:200]}),flush=True)
