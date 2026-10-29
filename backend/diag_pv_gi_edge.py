#!/usr/bin/env python3
"""Inspect precise BOPV JSON object and Gipuzkoa weekend behavior."""
import requests,json
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
P=[
 ("PV","https://api.euskadi.eus/bopv/administrative-acts/2026/10?itemsOfPage=2&currentPage=1&lang=SPANISH"),
 ("PVSEP","https://api.euskadi.eus/bopv/administrative-acts/2026/9?itemsOfPage=2&currentPage=1&lang=SPANISH"),
 ("GI03","https://egoitza.gipuzkoa.eus/gao-bog/castell/bog/2026/10/03/bc261003.htm"),
 ("GI04","https://egoitza.gipuzkoa.eus/gao-bog/castell/bog/2026/10/04/bc261004.htm"),
 ("GI29","https://egoitza.gipuzkoa.eus/gao-bog/castell/bog/2026/10/29/bc261029.htm"),
 ("BI22","https://www.bizkaia.eus/es/bob/resultados?p_p_id=IYBIWBCC&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view&_IYBIWBCC_mvcRenderCommandName=%2Fdetail&_IYBIWBCC_bdate=20261022&_IYBIWBCC_bnum=203"),
]
def run(p):
 name,url=p
 try:
  r=requests.get(url,timeout=31)
  if name.startswith("PV"):
   j=r.json()
   out={"name":name,"http":r.status_code,"totalItems":j.get("totalItems"),"totalPages":j.get("totalPages"),"currentPage":j.get("currentPage"),"itemsOfPage":j.get("itemsOfPage"),
    "keys":list(j),"filter":str(j.get("filter"))[:700]}
   for k,v in j.items():
    if isinstance(v,list):
     out["collection"]=k;out["count"]=len(v)
     out["records"]=[{"keys":list(x),"fields":{a:(s[:450] if isinstance(s,str) else s) for a,s in x.items() if not isinstance(s,(list,dict))},"nested":{a:(list(s) if isinstance(s,dict) else "array "+str(len(s))) for a,s in x.items() if isinstance(s,(list,dict))}} for x in v[:2]]
   return out
  soup=BeautifulSoup(r.content,"html.parser");root=soup.select_one("#sumario")
  if name=="BI22":return {"name":name,"http":r.status_code,"final":r.url,"bytes":len(r.content),"h1":[h.get_text(" ",strip=True) for h in soup.select("h1")][:15], "h2":[h.get_text(" ",strip=True) for h in soup.select("h2")][:10],"pdfs":[a.get("href") for a in soup.select('a[href$="_cas.pdf"]')[:5]],"title":soup.title.get_text(" ",strip=True) if soup.title else "", "snippet":soup.get_text(" ",strip=True)[3000:4700]}
  return {"name":name,"status":r.status_code,"bytes":len(r.content),"h2":[x.get_text(" ",strip=True)[:260] for x in soup.select("h2")],
    "root":root.get_text(" ",strip=True)[:500] if root else None,
    "pdfs":[(x.get_text(" ",strip=True)[:35],x.get("href")) for x in soup.select("a[href$='.pdf']")[:5]],
    "ads":len(soup.select("ul.anuncios > li"))}
 except Exception as e:return {"name":name,"error":repr(e)[:200]}
with ThreadPoolExecutor(max_workers=5) as pool:
 for x in pool.map(run,P):print("EDGE",json.dumps(x,ensure_ascii=False)[:9000],flush=True)
