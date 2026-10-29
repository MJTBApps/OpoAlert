import requests,json,re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
cases=[("PO29","https://boppo.depo.gal/detalle/-/boppo/2026/10/29"),("PO28","https://boppo.depo.gal/detalle/-/boppo/2026/10/28"),("PO30SEP","https://boppo.depo.gal/detalle/-/boppo/2026/09/30"),("PO03","https://boppo.depo.gal/detalle/-/boppo/2026/10/03"),("POPDF","https://boppo.depo.gal/web/boppo/detalle/-/boppo/2026/10/29/2026075474/an.bop.PONTEVEDRA.20261029.2026075474.pdf")]
def probe(row):
 n,u=row
 try:
  r=requests.get(u,timeout=(10,30),stream=True,headers={"User-Agent":"Mozilla/5.0"})
  b=b""
  for chunk in r.iter_content(70000):
   b+=chunk
   if len(b)>130000:break
  r.close()
  if b.startswith(b"%PDF-"):return {"n":n,"http":r.status_code,"pdf":True,"url":r.url,"mime":r.headers.get("Content-Type"),"bytes":len(b)}
  s=BeautifulSoup(b,"html.parser")
  return {"n":n,"http":r.status_code,"url":r.url,"size":len(b),
      "h2":[h.get_text(" ",strip=True)[:150] for h in s.select("h2")[:5]],
      "listings":len(s.select("ul.listadoSumario li")),
      "sample":[{"pub":i.select_one("span.pub").get_text(" ",strip=True) if i.select_one("span.pub") else None,
                 "title":i.select_one("p.sumario").get_text(" ",strip=True)[:200] if i.select_one("p.sumario") else None,
                 "pdf":i.select_one("a.botDescPDF").get("href") if i.select_one("a.botDescPDF") else None} for i in s.select("ul.listadoSumario li")[:3]],
      "text":s.get_text(" ",strip=True)[-350:]}
 except Exception as e:return {"n":n,"error":str(e)}
with ThreadPoolExecutor(max_workers=5) as p:
 for a in p.map(probe,cases):print("PO_DAILY",json.dumps(a,ensure_ascii=False)[:4800],flush=True)
