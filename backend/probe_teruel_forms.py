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
