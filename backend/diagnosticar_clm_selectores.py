import requests,re,urllib3
from bs4 import BeautifulSoup
urllib3.disable_warnings()
targets=[
("TO","https://bop.diputoledo.es/webEbop/ebopResumen.jsp?publication_date=28/10/2026&publication_date_to=28/10/2026",True),
("DOCM","https://docm.jccm.es/docm/cambiarBoletin.do?fecha=20261029",True),
("GU-ITEM","https://boletin.dguadalajara.es/boletin/index.php/2-anuncios/66374-PROCEDIMIENTO-SELECTIVO-PARA-LA-FORMACIÓN-POR-EL-PROCEDIMIENTO-DE-CONCURSO-DE-UNA-BOLSA-DE-TÉCNICO/A-AUXILIAR-DE-BIBLIOTECA",True),
("CR","https://bop.dipucr.es/bop/2026/10/29",False)
]
for k,u,v in targets:
 try:
  r=requests.get(u,timeout=(12,22),verify=v,headers={"User-Agent":"Mozilla/5.0"})
  h=BeautifulSoup(r.content,"html.parser")
  print("\n===",k,r.status_code,len(r.content),flush=True)
  if k=="TO":
   for a in h.select('a[href^="DocGet?"]')[:3]:
    node=a
    for i in range(1,5):
     node=node.parent
     print("PARENT",i,str(node)[:4500],flush=True)
  if k=="DOCM":
   for a in h.select('a[href*="descargarArchivo.do?ruta=2026/10/29/pdf/2026_"]')[:2]:
    node=a
    for i in range(1,5):
     node=node.parent
     print("PARENT",i,str(node)[:3600],flush=True)
  if k=="GU-ITEM":
   print("ARTICLE",str(h.select_one('.itemView') or h.select_one('.itemFullText'))[-9000:],flush=True)
   print("PDFLINK",[(a.get_text(" ",strip=True),a.get("href")) for a in h.select("a[href]") if "pdf" in str(a).lower()][-10:],flush=True)
  if k=="CR":
   for a in h.select('a[href*="getDocument.do"]')[:3]:
    node=a
    for i in range(1,5):
     node=node.parent
     print("PARENT",i,str(node)[:3500],flush=True)
   print("SIGEM HEAD")
   try:
    doc=requests.get("https://se1.dipucr.es:4443/SIGEM_BuscadorDocsWeb/getDocument.do?entidad=005&doc=7852888",timeout=(8,15),stream=True)
    print("SIGEM",doc.status_code,doc.headers.get("Content-Type"),flush=True)
   except Exception as e:print("SIGEM_ERR",str(e)[:250],flush=True)
 except Exception as e:print("ERROR",k,type(e).__name__,str(e)[:210],flush=True)
