import requests,re
from bs4 import BeautifulSoup
cases=[
("TO-28","https://bop.diputoledo.es/webEbop/ebopResumen.jsp?publication_date=28/10/2026&publication_date_to=28/10/2026",True),
("TO-19","https://bop.diputoledo.es/webEbop/ebopResumen.jsp?publication_date=19/10/2026&publication_date_to=19/10/2026",True),
("TO-CAL","https://bop.diputoledo.es/webEbop/ebopCalendar.jsp",True),
("GU-26","https://boletin.dguadalajara.es/boletin/index.php/9-general/66386-Boletin-Oficial-de-la-Provincia-de-Guadalajara-num-204-de-lunes-26-de-Octubre-de-2026",True),
("GU-30","https://boletin.dguadalajara.es/boletin/index.php/buscar-k2-menu/date/2026/09/30?catid=9",True),
("DOCM-29","https://docm.jccm.es/docm/cambiarBoletin.do?fecha=20261029",True),
("DOCM-28","https://docm.jccm.es/docm/cambiarBoletin.do?fecha=20261028",True),
("CR-29","https://bop.dipucr.es/bop/2026/10/29",False),
]
for name,url,verify in cases:
 try:
  r=requests.get(url,timeout=(9,22),verify=verify,headers={"User-Agent":"Mozilla/5.0"})
  s=BeautifulSoup(r.content,"html.parser")
  print("\n====",name,r.status_code,"LEN",len(r.content),"TITLE",(s.title.get_text(" ",strip=True) if s.title else "")[:140],flush=True)
  print("BODY",repr(s.get_text(" ",strip=True)[-1800:]),flush=True)
  if name.startswith("TO"):
   for elm in s.select("tr,li,div[class*=anuncio],div[class*=Anuncio],a[href]")[:50]:
    if (elm.name=="a" or "resumen" in elm.get_text(" ",strip=True).lower() or "29/10" in elm.get_text(" ",strip=True)):
     print("NODE",str(elm)[:1500],flush=True)
   print("LINKS",[(a.get_text(" ",strip=True)[:70],a.get("href","")) for a in s.select("a[href]") if "pdf" in a.get("href","").lower() or "anun" in a.get("href","").lower()][:25],flush=True)
  if name.startswith("GU"):
   for elm in s.select(".itemSumario")[:2]:print("ITEM",str(elm)[:4400],flush=True)
   print("ISSUE-LINKS",[(a.get_text(" ",strip=True)[:120],a.get("href","")) for a in s.select(".genericItemTitle a,.itemList a,.itemFullText a")[-28:]],flush=True)
  if name.startswith("DOCM"):
   for elm in s.select("tr[class*=disposicion],.filaDisposicion,.filaSumario,div[class*=item],li[class*=item]")[:4]:print("ITEM",str(elm)[:4000],flush=True)
   for a in s.select('a[href*="descargarArchivo.do"]')[:3]:print("LINK_PARENT",str(a.parent.parent)[:2400],flush=True)
   print("META",[(t.name,t.get("class"),t.get_text(" ",strip=True)[:150]) for t in s.select("h2,h3,h4")[:14]],flush=True)
  if name.startswith("CR"):
   for elm in s.select("h3.admons")[:1]:print("ISSUE",str(elm.parent)[:7500],flush=True)
   print("ANNOUNCEMENT_LINKS",[(a.get_text(" ",strip=True)[:80],a.get("href",""),a.parent.name,a.parent.get("class")) for a in s.select('a[href*="getDocument"]')[:16]],flush=True)
 except Exception as ex:print("ERROR",name,type(ex).__name__,str(ex)[:270],flush=True)
