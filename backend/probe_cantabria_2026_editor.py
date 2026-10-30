#!/usr/bin/env python3
"""Cantabria BOC: inspect first-party official public archive transports.

Diagnostic only. No login, no CAPTCHA bypass. A 200 response without a
specific issue/date and independently checked sumario is not coverage.
"""
import concurrent.futures,json,re,requests,platform,time
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlsplit
targets={
"calendar":"https://boc.cantabria.es/boces/",
"initial":"https://boc.cantabria.es/boces/inicioCargaInicialBoletines.do",
"search":"https://boc.cantabria.es/boces/menu.do?dir=%2FinicioCargaInicialBoletines.do",
"datequery":"https://boc.cantabria.es/boces/boletines.do?fechaBoletin=29%2F10%2F2026&tipoBoletin=ORD&boton=Buscar",
"datequery2":"https://boc.cantabria.es/boces/verBoletin.do?fecha=29%2F10%2F2026",
"datequery3":"https://boc.cantabria.es/boces/boletines.do?boton=fecha&fecha=29%2F10%2F2026",
"originalsample":"https://boc.cantabria.es/boces/verAnuncioAction.do?idAnuBlob=431949",
"originalsample2":"https://boc.cantabria.es/boces/verBoletin.do?idBolOrd=39643",
"pdfcatalog":"https://boc.cantabria.es/boces/menu.do?dir=%2FdescargaBoletines.do",
"searchads":"https://boc.cantabria.es/boces/menu.do?dir=%2FinicioBusquedaAnuncios.do",
"rss":"https://boc.cantabria.es/boces/rss.xml",
"alternate":"https://boc.gobcantabria.es/boces/",
"www":"https://www.boc.cantabria.es/boces/",
"portal":"https://www.cantabria.es/web/boc",
"backup":"https://www.cantabria.es/web/boc/boletin-oficial-de-cantabria",
}
def probe(item):
 name,url=item;start=time.monotonic()
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert public bulletin audit)",
     "Accept-Language":"es-ES,es;q=0.9"})
   with s.get(url,timeout=(6,12),allow_redirects=True,stream=True) as r:
    buf=b""
    for x in r.iter_content(8192):
     buf+=x
     if len(buf)>110000:break
    content=r.headers.get("Content-Type","")
    dest=r.url
    if b"%PDF-" in buf[:30]:
     return {"key":name,"status":r.status_code,"final":dest,"pdf":True,
      "bytes":len(buf),"mime":content}
    soup=BeautifulSoup(buf,"html.parser")
    forms=[{"action":urljoin(dest,f.get("action","")),"method":f.get("method","GET"),
      "controls":[{"name":x.get("name",""),"tag":x.name,"type":x.get("type",""),
       "value":(x.get("value") or "")[:60]} for x in f.select("input[name],select[name],button[name]")][:40]}
      for f in soup.select("form")[:10]]
    links=[{"text":a.get_text(" ",strip=True)[:100],"url":urljoin(dest,a.get("href",""))[:280]}
      for a in soup.select("a[href]") if re.search(r"bol|anun|2026|xml|pdf|descarg|boc|cve",a.get("href","")+" "+a.get_text(" ",strip=True),re.I)][:40]
    scripts=[urljoin(dest,a.get("src","")) for a in soup.select("script[src]")][:20]
    return {"key":name,"status":r.status_code,"final":dest,"mime":content,
      "sizeSample":len(buf),"title":soup.title.get_text(" ",strip=True)[:150] if soup.title else "",
      "text":soup.get_text(" ",strip=True)[:1000],"forms":forms,
      "links":links,"scripts":scripts,"elapsed":round(time.monotonic()-start,1)}
 except Exception as e:return {"key":name,"error":type(e).__name__+":"+str(e)[:170],"elapsed":round(time.monotonic()-start,1)}
print("BOC_RUNNER",platform.platform(),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
 for row in pool.map(probe,targets.items()):
  print("BOC_OFFICIAL_PROBE",json.dumps(row,ensure_ascii=True),flush=True)
