#!/usr/bin/env python3
"""Inspect all 2026 Zaragoza provincial subsections and official document PDFs."""
from urllib.parse import urlsplit,parse_qs
from collections import Counter
import requests,re
ROOT="https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI"
BASE={"CMD":"VERLST","OUTPUTMODE":"JSON","BASE":"BZHT","DOCS":"1-10000",
"SEC":"OPENDATABOAJSON","SORT":"-PUBL","SEPARADOR":"",
"@PUBL-GE":"20261028","@PUBL-LE":"20261028",
"NUMB":"","RANG":"","TITU-C":"","FDIS-C":"","TITU":"",
"ORGA-C":"","TEXT-C":"","SECC-C":"zaragoza","SECC":"","SUBS-C":""}
ses=requests.Session();ses.headers["User-Agent"]="Mozilla/5.0 OpoAlert audit"
for mode,param in [("all BOPZ",{}),("sexta",{"SUBS-C":"sexta"}),("primera",{"SUBS-C":"primera"}),("other date",{"@PUBL-GE":"20261023","@PUBL-LE":"20261023"}),("month",{"@PUBL-GE":"20261001","@PUBL-LE":"20261028"})]:
 try:
  r=ses.get(ROOT,params={**BASE,**param},timeout=45)
  print("\nMODE",mode,"status",r.status_code,"bytecount",len(r.content),"ctype",r.headers.get("Content-Type"),flush=True)
  print("RAWHEAD",repr(r.content[:150]),flush=True)
  j=r.json()
  if not isinstance(j,list):print("INVALID SHAPE",repr(j)[:250],flush=True);continue
  secs=Counter((str(x.get("Seccion"))[:60],str(x.get("Subseccion"))[:45]) for x in j)
  nums=Counter(str(x.get("Numeroboletin")) for x in j)
  dates=Counter(str(x.get("FechaPublicacion")) for x in j)
  orders=[str(x.get("NOrden")) for x in j]
  print("COUNT",len(j),"ORDERFIRST",orders[:4],"ORDERLAST",orders[-4:],
     "DATES",dates.most_common(40),"NUMBERS",nums.most_common(15),"SECTIONS",secs.most_common(30),flush=True)
  print("FIRST_RECORD_MINI",[{k:j[0].get(k) for k in ["DOCN","NOrden","FechaPublicacion","Numeroboletin","Seccion","Subseccion","Emisor","Titulo","UrlPdf","UrlBCOM"]}] if j else [],flush=True)
  if mode=="all BOPZ" and j:
   for i,record in enumerate([j[0],j[-1]]):
    raw=record.get("UrlPdf","")
    match=re.search(r"https://www\.boa\.aragon\.es/cgi-bin/EBOA/BRSCGI\?CMD=VEROBJ&MLKOB=\d+",raw)
    if not match:print("PDF_MALFORMED",repr(raw));continue
    url=match.group()
    try:
     p=ses.get(url,timeout=25,headers={"Range":"bytes=0-4096"},stream=True)
     head=next(p.iter_content(chunk_size=512),b"")
     print("DOC",i,url,"status",p.status_code,"type",p.headers.get("Content-Type"),"head",repr(head[:180]),"final",p.url[:170],flush=True)
     p.close()
    except Exception as ex: print("PDF_ERROR",type(ex).__name__,str(ex)[:300],flush=True)
 except Exception as ex:print("ERROR",mode,type(ex).__name__,str(ex)[:300],flush=True)
