#!/usr/bin/env python3
"""Inspect results table, pagination and official HTML notice URLs."""
import requests,re
from bs4 import BeautifulSoup
url="https://bender.dpteruel.es/dpt/bopt.nsf/busquedas.xsp"
s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es"})
r=s.get(url,timeout=22);p=BeautifulSoup(r.content,"html.parser")
payload={i["name"]:i.get("value","") for i in p.select("form input[name]") if i.get("type")=="hidden"}
payload.update({"$$xspsubmitid":"Busquedas:_id1:_id53:_id139","Busquedas:_id1:_id53:Seccion1":"",
"Busquedas:_id1:_id53:Emisor1":"","Busquedas:_id1:_id53:SearchContenido1":"",
"Busquedas:_id1:_id53:inputfechadesde":"28/10/2026","Busquedas:_id1:_id53:inputText2":"28/10/2026"})
r=s.post(url,data=payload,timeout=27,headers={"Referer":url})
soup=BeautifulSoup(r.content,"html.parser")
print("POST",r.status_code,len(r.content),"COOKIE",list(s.cookies.keys()),flush=True)
for tag in soup.find_all(id=re.compile("viewPanel1|pager",re.I)):
 if tag.name in ("table","div","span","a") and ("OUTER_TABLE" in tag.get("id","") or tag.name=="a"):
  print("RESULT_TAG",tag.name,tag.get("id"),str(tag)[:6200],flush=True)
print("ALL_RESULT_LINKS",[(a.get("href"),a.get("onclick"),a.get("id"),a.get_text(" ",strip=True)[:75]) for a in soup.select("a[href]")][-60:],flush=True)
for m in list(re.finditer(r'.{0,450}(?:Anterior|Siguiente|Se han encontrado 16 anuncios|2026-3142).{0,850}',r.text,re.I|re.S))[:8]:
 print("MATCH",repr(m.group(0)[:1100]),flush=True)
