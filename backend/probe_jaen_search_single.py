#!/usr/bin/env python3
"""One cautious official Jaen Pandora search with browser-form payload.

Previous parallel attempts were throttled. This single read-only public
search respects timeouts and never asserts missing editions are recovered.
"""
import json,requests,re,sys
from bs4 import BeautifulSoup
ROOT="https://bophistorico.dipujaen.es/"
with requests.Session() as s:
 s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert official catalog research)","Accept-Language":"es-ES,es;q=0.9"})
 try:
  r=s.get(ROOT,timeout=(9,28))
  print("JAEN_HOME",r.status_code,len(r.content),flush=True)
  r.raise_for_status()
  h=BeautifulSoup(r.content,"html.parser")
  f=h.select_one("form#sheet")
  if f is None:raise RuntimeError("Missing public search form")
  print("JAEN_FORM",f.get("method"),f.get("action"),flush=True)
  fields=[("field",(None,"name")),("words",(None,"13/10/2026")),
          ("operator",(None,"")),("field",(None,"")),("words",(None,"")),
          ("operator",(None,"")),("field",(None,"")),("words",(None,"")),
          ("parameter-hidden-level31b",(None,"")),
          ("back",(None,""))]
  target=requests.compat.urljoin(ROOT,f.get("action","tools/setQuery.vm"))
  res=s.post(target,files=fields,timeout=(10,40),allow_redirects=True)
  soup=BeautifulSoup(res.content,"html.parser")
  cards=[{"name":x.get_text(" ",strip=True)[:250],
          "pdf":x.find("a",href=re.compile("high.raw")).get("href")[:180] if x.find("a",href=re.compile("high.raw")) else "",
          "id":x.get("id")} for x in soup.select("div.list-frame")[:15]]
  print("JAEN_SEARCH_RAW",repr(res.text[:1600]),flush=True)
  # Pandora returns a JavaScript navigation rather than HTTP Location.
  # Follow its declared public destination using the same session cookies.
  js = "window.location" in res.text
  if js:
   dest="../index.vm"
   for next_name,next_url in (("index_vm",requests.compat.urljoin(res.url,dest)),
                             ("results_vm",requests.compat.urljoin(ROOT,"results.vm"))):
    follow=s.get(next_url,timeout=(8,30))
    soup2=BeautifulSoup(follow.content,"html.parser")
    results2=[{"id":c.get("id"),"text":c.get_text(" ",strip=True)[:320]} for c in soup2.select("div.list-frame")[:15]]
    print("JAEN_FOLLOW",json.dumps({"step":next_name,"status":follow.status_code,
       "url":follow.url,"size":len(follow.content),
       "results":results2,"text":soup2.get_text(" ",strip=True)[:350]},ensure_ascii=True),flush=True)

  print("JAEN_SEARCH_ONE",json.dumps({"http":res.status_code,"url":res.url,"len":len(res.content),
    "title":soup.title.get_text(" ",strip=True) if soup.title else "",
    "count":re.search(r"Resultados:\s*[\d.]+",soup.get_text(" ",strip=True)).group(0)
            if re.search(r"Resultados:\s*[\d.]+",soup.get_text(" ",strip=True)) else "",
    "cards":cards},ensure_ascii=True),flush=True)
 except Exception as e:
  print("JAEN_SEARCH_FAILED",type(e).__name__,str(e)[:240],flush=True)
  sys.exit(0)
