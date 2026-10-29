#!/usr/bin/env python3
"""Identify DOGV official JSON services from deployed Angular app; read-only."""
import requests,re,json
from urllib.parse import urljoin
from bs4 import BeautifulSoup
ROOT="https://dogv.gva.es/dogv-portal-frontend/es"
r=requests.get(ROOT,timeout=(12,35))
h=BeautifulSoup(r.content,"html.parser")
print("DOGV_BOOT",r.status_code,len(r.content),"BASE",[(b.get("href")) for b in h.select("base")],"SCRIPTS",[(b.get("src")) for b in h.select("script[src]")],flush=True)
scripts=[urljoin(r.url,s.get("src")) for s in h.select("script[src]") if s.get("src","").startswith("main.")]
for url in scripts:
 try:
  z=requests.get(url,timeout=(12,80))
  body=z.text
  print("DOGV_JS",z.status_code,url,"len",len(body),"type",z.headers.get("Content-Type"),flush=True)
  if len(body)<100000:continue
  terms=[
    "api/","/api","urlBase","baseUrl","environment","dogvService",
    "buscador","sumario","boletines","getBoletin","consultaBoletin",
    "verDocumento","calendario","resoluciones","publicaciones",
    "es/datos","datos/2026","basePath","endpoint",
  ]
  for key in terms:
   ms=list(re.finditer(re.escape(key),body,re.I))
   print("DOGV_SIGNAL",key,len(ms),flush=True)
   for m in ms[:5]:
    print("DOGV_JS_HINT",key,json.dumps(body[max(0,m.start()-200):m.end()+290],ensure_ascii=False)[:650],flush=True)
  matches=re.findall(r"""["']((?:https?:)?//[^"' ]{8,200}|/[a-zA-Z][\w\-/.{}?=&]{5,180})["']""",body)
  selected=sorted(set(x for x in matches if re.search(r"bolet|dogv|api|busca|indice|sumario|diari|fecha",x,re.I)))
  print("DOGV_JS_URLS",json.dumps(selected[:130],ensure_ascii=False)[:14000],flush=True)
 except Exception as e:print("DOGV_JS_ERROR",repr(e)[:350],flush=True)
