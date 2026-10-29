#!/usr/bin/env python3
"""Try the official archive search form for Jaen missing October 2026 issues.

No authentication or security challenge is bypassed. The form supports public
text/year search; matches must have original PDF and an authentic issue header.
"""
import requests, concurrent.futures, json, re
from bs4 import BeautifulSoup
ROOT="https://bophistorico.dipujaen.es/"
POST=ROOT+"tools/setQuery.vm"
ITEMS=[
 ("name_13oct","name","13/10/2026"),
 ("name_14oct","name","14/10/2026"),
 ("name_16oct","name","16/10/2026"),
 ("name_198","name","198"),
 ("text_198","text","BOP-2026-198"),
 ("title_2026","name","2026"),
 ("filter_year","", "boletin"),
]
def one(p):
 label,field,words=p
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0","Referer":ROOT,"Accept-Language":"es-ES,es;q=0.9"})
   start=s.get(ROOT,timeout=(6,15))
   h=BeautifulSoup(start.content,"html.parser")
   form=h.select_one("form#sheet")
   action=POST if form is None else requests.compat.urljoin(ROOT,form.get("action","tools/setQuery.vm"))
   # Build the same multipart fields as the public form without privileged inputs
   fields=[("field",(None,field)),("words",(None,words)),
           ("operator",(None,"")),("field",(None,"")),("words",(None,"")),
           ("operator",(None,"")),("field",(None,"")),("words",(None,"")),
           ("parameter-hidden-level31b",(None,"2026" if label=="filter_year" else "")),
           ("back",(None,""))]
   r=s.post(action,files=fields,timeout=(8,25),allow_redirects=True)
   soup=BeautifulSoup(r.content,"html.parser")
   cards=[]
   for card in soup.select("div.list-frame")[:15]:
    a=card.select_one('a[href*="high.raw"]')
    cards.append((card.get("id"),card.get_text(" ",strip=True)[:200],a.get("href","")[:160] if a else ""))
   text=soup.get_text(" ",strip=True)
   return {"q":label,"http":r.status_code,"url":r.url,"size":len(r.content),
      "title":soup.title.get_text(" ",strip=True)[:80] if soup.title else "",
      "cards":cards,"result":re.search(r"Resultados: ?[\d.]+",text).group(0) if re.search(r"Resultados: ?[\d.]+",text) else "",
      "head":text[:340],"forms":len(soup.select("form"))}
 except Exception as ex:return {"q":label,"error":type(ex).__name__+": "+str(ex)[:210]}
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 for result in pool.map(one,ITEMS):
  print("JAEN_POST",json.dumps(result,ensure_ascii=False)[:11000],flush=True)
