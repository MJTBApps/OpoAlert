#!/usr/bin/env python3
"""Diagnose XPages POST search by publication date, without publishing."""
import requests,re
from bs4 import BeautifulSoup
ROOT="https://bender.dpteruel.es/dpt/bopt.nsf"
s=requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es"})
for page in ["busquedas.xsp","busquedasn.xsp","inicio.xsp"]:
 print("\nPAGE",page,flush=True)
 r=s.get(f"{ROOT}/{page}",timeout=20);print("GET",r.status_code,len(r.content),r.url,flush=True)
 soup=BeautifulSoup(r.content,"html.parser")
 for x in soup.find_all(["input","button","select","textarea"]):
  print("FIELD",str(x)[:420].replace("\n"," "),flush=True)
 for x in soup.find_all(["a","script"]):
  if "buscar" in x.get_text(" ",strip=True).lower() or (x.get("onclick") and "buscar" in x.get("onclick").lower()):
   print("SEARCH_ELEMENT",str(x)[:550].replace("\n"," "),flush=True)
 print("DATE_SNIPPETS",flush=True)
 for regex in [r".{0,180}inputfechadesde.{0,280}",r".{0,160}inputText2.{0,250}",r".{0,160}SearchContenido1.{0,350}",r".{0,160}xspsubmitid.{0,160}",r".{0,160}Buscar.{0,320}"]:
  for m in list(re.finditer(regex,r.text,re.I|re.S))[:4]:print(repr(m.group(0)[:420]),flush=True)

# Reproduce native XPages button submit with view-id and date fields.
url=f"{ROOT}/busquedas.xsp"
for day in ["28/10/2026","27/10/2026","25/10/2026","01/10/2026"]:
 s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es"})
 home=s.get(url,timeout=20);h=BeautifulSoup(home.content,"html.parser")
 form=h.find("form")
 payload={i["name"]:i.get("value","") for i in form.select("input[name]") if i.get("type")=="hidden"}
 payload.update({
  "$$xspsubmitid":"Busquedas:_id1:_id53:_id139",
  "Busquedas:_id1:_id53:Seccion1":"",
  "Busquedas:_id1:_id53:Emisor1":"",
  "Busquedas:_id1:_id53:SearchContenido1":"",
  "Busquedas:_id1:_id53:inputfechadesde":day,
  "Busquedas:_id1:_id53:inputText2":day,
 })
 try:
  r=s.post(url,data=payload,timeout=28,headers={"Referer":url})
  h=BeautifulSoup(r.content,"html.parser")
  a=[(x.get("href"),x.get_text(" ",strip=True)[:80]) for x in h.select("a[href]") if re.search(r"/0/[A-Fa-f0-9]{32}",x.get("href",""))]
  print("POST_DATE",day,r.status_code,len(r.content),r.url,"MATCHES",len(a),"RECORDS",a[:15],flush=True)
  print("TEXT_LAST",h.get_text(" ",strip=True)[-2100:],flush=True)
  for m in list(re.finditer(r".{0,150}(?:anuncios encontrados|resultados|2026-3129|No hay anuncios).{0,300}",r.text,re.I|re.S))[:4]:print("HTML_MATCH",repr(m.group(0)[:500]),flush=True)
 except Exception as e:print("POST_ERROR",day,type(e).__name__,str(e)[:220],flush=True)
for day in ["28octubre","27octubre","24octubre","01octubre"]:
 u="https://bender.dpteruel.es/estatico/boletines/2026/"+day+".pdf"
 try:
  r=requests.get(u,headers={"Range":"bytes=0-128","User-Agent":"Mozilla/5.0"},timeout=22,stream=True)
  raw=next(r.iter_content(160),b"")
  print("PDF_LINK",day,r.status_code,r.url,r.headers.get("content-type"),r.headers.get("content-length"),repr(raw[:30]),flush=True)
  r.close()
 except Exception as e:print("PDF_LINK_ERROR",day,type(e).__name__,str(e)[:200],flush=True)
