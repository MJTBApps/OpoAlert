#!/usr/bin/env python3
"""Detect an official reachable publisher channel for Malaga 2026 BOP summaries.

Only public read-only links, and never bypass CAPTCHA / Turnstile.
"""
import json,requests,concurrent.futures,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
TARGETS={
"bop_main":"https://www.bopmalaga.es/sumario.php?fecha=28-10-2026",
"bop_dot":"https://www.bopmalaga.es/sumario.php.?fecha=28-10-2026",
"bop_www":"https://www.bopmalaga.es/",
"bop_apex":"https://bopmalaga.es/sumario.php?fecha=28-10-2026",
"bop_apex_root":"https://bopmalaga.es/",
"bop_http":"http://www.bopmalaga.es/sumario.php?fecha=28-10-2026",
"cedma":"https://www.cedma.es/",
"cedma_bop":"https://www.cedma.es/bop",
"cedma_bopma":"https://www.cedma.es/bopma",
"cedma_sum":"https://www.cedma.es/sumario.php?fecha=28-10-2026",
"malaga":"https://www.malaga.es/",
"malaga_bop":"https://www.malaga.es/bop",
"malaga_bopma":"https://www.malaga.es/bopma",
"malaga_pdf":"https://www.malaga.es/boletin-oficial-de-la-provincia",
"diputacion":"https://www.diputacionmalaga.es/",
"diputacion_bop":"https://www.diputacionmalaga.es/bop/",
"sede":"https://sede.malaga.es/",
"sede_bop":"https://sede.malaga.es/bop",
"cedma_editions":"https://www.cedma.es/acerca-de-cedma.php"
}
def test(p):
 key,url=p
 try:
  r=requests.get(url,timeout=(7,14),allow_redirects=True,stream=True,headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
  body=b""
  for part in r.iter_content(8192):
   body+=part
   if len(body)>100000:break
  r.close()
  h=BeautifulSoup(body,"html.parser")
  linked=[(x.get_text(" ",strip=True)[:70],urljoin(r.url,x.get("href",""))[:230]) for x in h.select("a[href]")
   if re.search(r"(bop|boletin|pdf|sumario|malaga|2026)",str(x),re.I)]
  return {"key":key,"http":r.status_code,"url":r.url,"size":len(body),
   "title":h.title.get_text(" ",strip=True)[:160] if h.title else "",
   "links":linked[:22],"head":h.get_text(" ",strip=True)[:280]}
 except Exception as e:return {"key":key,"error":type(e).__name__+": "+str(e)[:210]}
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
 for result in pool.map(test,TARGETS.items()):
  print("MALAGA_SOURCE",json.dumps(result,ensure_ascii=True)[:6000],flush=True)
