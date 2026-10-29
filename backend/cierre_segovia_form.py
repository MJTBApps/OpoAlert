#!/usr/bin/env python3
"""Find Segovia Sep 30 official BOP 117 via Liferay catalog form.

Only read-only queries on the publisher's public form.
"""
import json,re,requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
url="https://www.dipsegovia.es/bop"
with requests.Session() as s:
 r=s.get(url,timeout=(8,24),headers={"User-Agent":"Mozilla/5.0"})
 print("HOME",r.status_code,r.url,len(r.content),flush=True)
 h=BeautifulSoup(r.content,"html.parser")
 for i,f in enumerate(h.select("form")):
  txt=f.get_text(" ",strip=True)
  html=str(f)
  if any(w in (txt+html).lower() for w in ("bolet","ano","year","mes","month","2026")):
   print("FORM",i,"method",f.get("method"),"action",urljoin(url,f.get("action","")),"id",f.get("id"),"HTML",html[:12500],flush=True)
 for j,sel in enumerate(h.select("select")):
  attrs={k:v for k,v in sel.attrs.items() if k in ("id","name","onchange")}
  if any(w in str(sel).lower() for w in ("año","ano","mes","2026","septiembre")):
   print("SELECT",j,attrs,str(sel)[:4500],flush=True)
 for i,script in enumerate(h.select("script")):
  txt=script.string or script.get_text(" ",strip=True)
  if any(w in txt.lower() for w in ("bulletinsweb","searchbulletins","searchbulletin","mesbusqueda","searchform","searchbop")):
   print("SCRIPT_MATCH",i,txt[:5500],flush=True)
 for term in ("Septiembre","2026","calendar","form-bop","search-year","searchYear","articleId","Portlets","20260930","page="):
  matches=list(re.finditer(re.escape(term),r.text,re.I))
  print("OCC",term,len(matches),[(m.start(),r.text[max(0,m.start()-160):m.end()+300].replace("\n"," ")[:500]) for m in matches[:3]],flush=True)
