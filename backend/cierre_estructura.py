#!/usr/bin/env python3
"""Inspect official dynamic archive structures of reachable, previously missing sources."""
import requests,re,json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from concurrent.futures import ThreadPoolExecutor
CHECKS=[
 ("SG","https://www.dipsegovia.es/bop"),
 ("SA","https://www.lasalina.es/Aplicaciones/GestorInter.jsp?funcion=MenuIzquierda&prestacion=Boletines"),
 ("BOJA","https://www.juntadeandalucia.es/eboja/2026/210/"),
 ("BOJA-OLD","https://www.juntadeandalucia.es/eboja/2026/189/"),
 ("DOGV","https://dogv.gva.es/"),
 ("DOGC","https://dogc.gencat.cat/"),
 ("BOA","https://www.boa.aragon.es/"),
]
def deep(p):
 name,url=p
 try:
  r=requests.get(url,timeout=(9,27),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
  h=BeautifulSoup(r.content,"html.parser")
  d={"n":name,"http":r.status_code,"size":len(r.content),"title":h.title.get_text(" ",strip=True)[:130] if h.title else "",
     "heads":[(x.name,x.get_text(" ",strip=True)[:150]) for x in h.select("h1,h2,h3")[:18]],
     "forms":[(x.get("action"),x.get("method"),[(y.get("name"),y.get("value"),y.get("id")) for y in x.select("input,select")[:12]]) for x in h.select("form")[:4]],
     "scripts":[x.get("src") for x in h.select("script[src]")[-12:]]}
  if name=="SG":
   ls=[a for a in h.select('a[href]') if "articleId=" in a.get("href","") or "BulletinsWebPortlet" in a.get("href","")]
   d["dates"]=[(a.get_text(" ",strip=True)[:80],a.get("href","")[:350]) for a in ls[:12]]
   d["firstDetails"]=[str(a.parent.parent.parent)[:4500] for a in ls[:2]]
   d["page"]=[str(x)[:2100] for x in h.select(".pagination,.lfr-pagination,.pagination-bar")[:3]]
   d["pdfs"]=[(a.get_text(" ",strip=True)[:80],urljoin(url,a.get("href",""))) for a in h.select('a[href*=".pdf"]')[:10]]
  elif name=="SA":
   anchors=[a for a in h.select('a[href]') if any(t in a.get("href","") for t in ("2026","Boletines","BOP","GestorInter"))]
   d["samples"]=[(a.get_text(" ",strip=True)[:80],a.get("href"),str(a.parent)[:300]) for a in anchors[:50]]
   d["dates"]=[(a.get("href"),a.get("onclick"),a.get_text(" ",strip=True)[:22]) for a in h.select("a") if a.get("onclick") and re.search(r"2026|10|Bop|bolet",a.get("onclick"),re.I)][:15]
   d["calendarDom"]=[str(x)[:2300] for x in h.select("table")[:4]]
  elif name.startswith("BOJA"):
   ls=[a for a in h.select("a[href]") if re.search(r"\.pdf|verificacion|\/s\d+\.html|\/2\d+\/|\/sumario",a.get("href",""),re.I)]
   d["links"]=[(a.get_text(" ",strip=True)[:100],urljoin(url,a.get("href",""))) for a in ls[:22]]
   d["elements"]=[str(a.parent.parent)[:2100] for a in ls if ".pdf" in a.get("href","")][:3]
   d["firstArticle"]=[str(x)[:3300] for x in h.select("article,.disposicion,.item")[:2]]
   d["text"]=h.get_text(" ",strip=True)[:850]
  else:
   keys=r"(?:pdf|2026|ultimo|último|bolet[ií]n|sumario|BOP|DOGV|DOGC|BOA)"
   links=[(a.get_text(" ",strip=True)[:70],urljoin(url,a.get("href",""))[:260]) for a in h.select("a[href]") if re.search(keys,a.get("href","")+" "+a.get_text(" ",strip=True),re.I)]
   d["links"]=links[:40]
   d["iframes"]=[(x.get("src"),x.get("name")) for x in h.select("iframe,frame")[:7]]
   d["text"]=h.get_text(" ",strip=True)[:900]
  return d
 except Exception as e:return {"n":name,"error":repr(e)[:330]}
with ThreadPoolExecutor(max_workers=6) as p:
 for x in p.map(deep,CHECKS):print("DEEP_CLOSE",json.dumps(x,ensure_ascii=False)[:18000],flush=True)
