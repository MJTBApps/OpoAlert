#!/usr/bin/env python3
import requests,re,json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
TARGETS=[
("SG-LIST","https://www.dipsegovia.es/bop"),
("SG-DETAIL","https://www.dipsegovia.es/bop?p_p_id=as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm&p_p_lifecycle=0&_as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm_mvcPath=%2Fpublisher%2Fdetail.jsp&_as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm_articleId=20195381"),
("BOJA","https://www.juntadeandalucia.es/eboja/2026/210/"),
("BOJA2","https://www.juntadeandalucia.es/eboja/2026/210/s53.html"),
("SA","https://www.lasalina.es/Aplicaciones/GestorInter.jsp?funcion=MenuIzquierda&prestacion=Boletines")
]
for name,url in TARGETS:
 try:
  r=requests.get(url,timeout=(12,40),headers={"User-Agent":"Mozilla/5.0"});h=BeautifulSoup(r.content,"html.parser")
  print("DET",name,"HTTP",r.status_code,"URL",r.url,"LEN",len(r.content),"HEADERS",[(z.name,z.get_text(" ",strip=True)[:120]) for z in h.select("h1,h2,h3,h4") if re.search("BOP|BOJA|Bolet|octubre|BOLET",z.get_text(" ",strip=True),re.I)][:12],flush=True)
  if name=="SG-LIST":
   cards=h.select("div.card.card-box")
   print("SG_CARDS",len(cards),[c.get_text(" ",strip=True)[:70] for c in cards[:20]],flush=True)
   print("SG_LIST_PAGINATION",[str(a)[:1200] for a in h.select("a[href]") if re.search("cur=|delta=|page=|start=",a.get("href","")) and "bulletin" in a.get("href","")][:15],flush=True)
   print("SG_LIST_FORMS",[str(x)[:3200] for x in h.select("form") if "bulletins" in str(x.get("action","")).lower()][:2],flush=True)
  if name=="SG-DETAIL":
   print("SG_DETAIL_H",[(x.name,x.get_text(" ",strip=True)[:125]) for x in h.select("h1,h2,h3,h4,h5")[-28:]],flush=True)
   links=[a for a in h.select("a[href]") if re.search(r"\\.pdf|/documents/|descarga|anuncios|pdf",a.get("href","")+" "+a.get_text(" ",strip=True),re.I)]
   print("SG_DETAIL_PDFS",len(links),[(a.get_text(" ",strip=True)[:90],a.get("href","")[:240]) for a in links[-28:]],flush=True)
   print("SG_DETAIL_LAST",str(h.select_one(".portlet-content-container") or h.select_one("main") or h.body)[-11500:],flush=True)
  if name.startswith("BOJA"):
   pdfs=h.select("a.item_pdf_grupo")
   print("BOJA_PDFS",len(pdfs),"ROOT_TAGS",[(x.name,x.get("class"),x.get("id"),len(x.select('a.item_pdf_grupo'))) for x in h.select("div,section,ul") if len(x.select('a.item_pdf_grupo'))>0][:22],flush=True)
   for a in pdfs[:3]:
    parent=a
    for depth in range(5):
     parent=parent.parent
     print("BOJA_ANCESTOR",name,depth,parent.name,parent.get("id"),parent.get("class"),parent.get_text(" ",strip=True)[:330],"HTML",str(parent)[:1800],flush=True)
   print("BOJA_H",[(x.name,x.get_text(" ",strip=True)[:180]) for x in h.select("h2,h3,h4") if re.search(r"(?i)(oposiciones|autoridades|consejeria|convocatorias|personal)",x.get_text(" ",strip=True))][:18],flush=True)
  if name=="SA":
   print("SA_DYNAMIC",(h.get_text(" ",strip=True)[-3200:]),flush=True)
   print("SA_CAL_LINKS",[(str(a)[:300]) for a in h.select("table[summary*='Octubre'] a,table[summary*='Septiembre'] a")][:14],flush=True)
 except Exception as e:print("ERROR",name,str(e)[:300],flush=True)
