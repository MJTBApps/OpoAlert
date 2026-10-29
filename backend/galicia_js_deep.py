import requests,re,json
from bs4 import BeautifulSoup
p=requests.get("https://boppo.depo.gal/es/consulta-do-boppo",timeout=35).text
s=BeautifulSoup(p,"html.parser")
print("PONTEVEDRA_CALENDAR_SELECT",len(s.select('[id*="calendario"]')),flush=True)
for x in s.select('[id*="calendario"], [class*="calendar"],[class*="calendari"]')[:8]:
 v=str(x)
 print("PO_CALENDAR",json.dumps({"tag":x.name,"id":x.get("id"),"classes":x.get("class"),"html":v[:3200]},ensure_ascii=False),flush=True)
links=[x for x in s.select("a[href]") if re.search("pdf|download|document|sumario",x.get("href",""),re.I)]
for a in links[-20:]:
 print("PO_LINK",json.dumps({"title":a.get_text(" ",strip=True)[:65],"href":a.get("href"),"parent":str(a.parent.parent)[:1200]},ensure_ascii=False),flush=True)
for m in list(re.finditer("calendar.date|calendarDate|_calendar|fecha|datePicker|idAnuncio|anuncio|boletin",p,re.I))[:40]:
 print("PO_SCRIPT",json.dumps(p[max(0,m.start()-125):m.end()+180].replace("\n"," "),ensure_ascii=False)[:400],flush=True)
o=requests.get("https://bop.depourense.es/portal/main.js",timeout=60).text
print("OUR_JS_LEN",len(o),flush=True)
print("OUR_FILES",json.dumps(re.findall(r"src/app/[^*]{3,110}",o)[:70],ensure_ascii=False)[:5000],flush=True)
for pat in ["boletin","edicto","obtener","descargar","environment","servicio","consulta","api","baseUrl","http"]:
 ms=list(re.finditer(pat,o,re.I))
 print("OUR_TOK",pat,len(ms),flush=True)
 for m in ms[-5:]:
  print("OUR_CTX",json.dumps(o[max(0,m.start()-130):m.end()+180].replace("\n"," "),ensure_ascii=False)[:390],flush=True)
