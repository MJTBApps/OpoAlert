#!/usr/bin/env python3
"""Precise source structure for north bulletin readers."""
import requests,re,json,urllib.parse
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
T=[
 ("PV-SPEC","https://opendata.euskadi.eus/contenidos/recurso_tecnico/data_apirest/es_def/adjuntos/bopv.json"),
 ("GI-DAY","https://egoitza.gipuzkoa.eus/gao-bog/castell/bog/2026/10/29/bc261029.htm"),
 ("GI-SEP","https://egoitza.gipuzkoa.eus/gao-bog/castell/bog/2026/09/30/bc260930.htm"),
 ("BI-DAY","https://www.bizkaia.eus/es/bob/resultados?p_p_id=IYBIWBCC&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_IYBIWBCC_mvcRenderCommandName=%2Fdetail&_IYBIWBCC_bdate=20261029&_IYBIWBCC_bnum=208"),
 ("AV-DAY","https://e-s.araba.eus/BOTHA/Inicio/SGBO5001.aspx?FechaBotha=28/10/2026"),
 ("PV-CAL","https://www.euskadi.eus/bopv2/datos/2026/10/index_c.shtml"),
]
def x(pair):
 n,u=pair
 try:
  r=requests.get(u,timeout=24,headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"},allow_redirects=False)
  if n=="PV-SPEC":
   try:
    d=r.json()
    return {"name":n,"http":r.status_code,"type":r.headers.get("Content-Type"),"keys":list(d),
      "servers":d.get("servers"),"paths":{k:v for k,v in d.get("paths",{}).items()},"info":d.get("info")}
   except Exception as e:return {"name":n,"http":r.status_code,"txt":r.text[:3000],"err":str(e)}
  h=BeautifulSoup(r.content,"html.parser")
  out={"name":n,"http":r.status_code,"bytes":len(r.content),"url":r.url,"heading":h.get_text(" ",strip=True)[:700]}
  if n.startswith("GI"):
   tags=h.find_all("a",href=True)
   outs=[a for a in tags if any(k in a.get("href","").lower() for k in (".pdf",".htm",".html"))]
   out["links_total"]=len(tags);out["html_links"]=len(outs)
   out["samples"]=[{"title":a.get_text(" ",strip=True)[:170],"href":a.get("href"),"ancestor":str(a.parent.parent)[:1300]} for a in outs[:9]]
   out["first3k"]=str(h.body)[:3200]
   out["texts"]=[x.get_text(" ",strip=True)[:300] for x in h.find_all(["b","strong","h1","h2","h3"])[:18]]
  if n=="BI-DAY":
   outs=[a for a in h.select("a[href]") if "_cas.pdf" in a.get("href","")]
   out["pdfCount"]=len(outs)
   out["samples"]=[{"href":a.get("href"),"parent":str(a.parent.parent)[:1800],"ancestor":str(a.parent.parent.parent)[:2600]} for a in outs[:5]]
   out["h2"]=[x.get_text(" ",strip=True) for x in h.select("h1,h2") if "Boletín" in x.get_text() or "anuncios" in x.get_text()][:5]
  if n=="AV-DAY":
   text=h.get_text(" ",strip=True);out["head"]=text[:600];out["pdfs"]=[(a.get("href"),a.parent.get_text(" ",strip=True)[:240]) for a in h.select('a[href*="_C.pdf"]')[:8]]
   out["calendar"]=[(a.get("href"),a.get("title"),a.get_text(" ",strip=True)) for a in h.select("a[href*='FechaBotha']")[:12]]
   out["notice_ancestors"]=[str(a.parent.parent)[:2000] for a in h.select('a[href*="2026_124_"][href*="_C.pdf"]')[:3]]
  return out
 except Exception as e:return {"name":n,"error":repr(e)[:400]}
with ThreadPoolExecutor(max_workers=5) as p:
 for row in p.map(x,T):print("STRUCT",json.dumps(row,ensure_ascii=False)[:32000],flush=True)
