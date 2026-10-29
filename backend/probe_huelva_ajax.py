#!/usr/bin/env python3
"""Official Huelva AJAX protocol: test date and response shape, never edit server data."""
import requests,json,re
from bs4 import BeautifulSoup
URL="https://s2.diphuelva.es/lib/bope/anuncios_bop/ajaxAnuncios.php"
S=[
("LATEST",{"tipo":"1","fecha":"0"}),
("2026-10-28",{"tipo":"2","fecha":"2026-10-28"}),
("2026-10-20",{"tipo":"2","fecha":"2026-10-20"}),
("2026-09-30",{"tipo":"2","fecha":"2026-09-30"}),
("NO-ISSUE",{"tipo":"2","fecha":"2026-10-25"}),
]
for label,form in S:
 try:
  r=requests.post(URL,data=form,timeout=(10,24),
    headers={"User-Agent":"Mozilla/5.0","Referer":"https://s2.diphuelva.es/servicios/bope_web/busquedaCalendario",
    "X-Requested-With":"XMLHttpRequest","Accept":"application/json,text/javascript,*/*"})
  print("\n===",label,r.status_code,len(r.content),"CT",r.headers.get("content-type"),"BODY",repr(r.text[:400]),flush=True)
  d=r.json()
  print("KEYS",list(d),"VALUES",[(k,type(v).__name__,str(v)[:250]) for k,v in d.items() if k not in ("CodigoCompletoSeccion","CodigoCompletoSecciones","Anuncios","anuncios")][:30],flush=True)
  for k,v in d.items():
   if isinstance(v,list):
    print("ARRAY",k,"LEN",len(v),"FIRST",str(v[:2])[:1800],flush=True)
   elif isinstance(v,dict):
    print("OBJECT",k,"KEYS",list(v)[:45],"SAMPLE",str(v)[:2700],flush=True)
   elif isinstance(v,str) and len(v)>350:
    soup=BeautifulSoup(v,"html.parser")
    print("LONG",k,"BYTES",len(v),"TEXT",repr(soup.get_text(" ",strip=True)[:800]),"LINKS",[(a.get_text(" ",strip=True)[:55],a.get("href","")) for a in soup.select("a[href]")[:10]],flush=True)
 except Exception as ex:print("ERROR",label,type(ex).__name__,str(ex)[:450],flush=True)
