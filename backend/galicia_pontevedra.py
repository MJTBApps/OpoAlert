#!/usr/bin/env python3
"""BOPPO Pontevedra official daily notices, 30 days with original PDFs."""
from __future__ import annotations
from datetime import date,timedelta,datetime
from pathlib import Path
from urllib.parse import urlsplit,urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from clm_common import publish_audit,write_output,invalid
from galicia_common import galicia_employment
import argparse,requests,re,threading,time
SOURCE="https://boppo.depo.gal/es/consulta-do-boppo"
HOST="boppo.depo.gal"
PDF_RE=re.compile(r"^/web/boppo/detalle/-/boppo/2026/(\d{2})/(\d{2})/(2026\d{6,8})/an\.bop\.PONTEVEDRA\.(2026\d{4})\.(2026\d{6,8})\.pdf$",re.I)
MONTHS={"enero":1,"xaneiro":1,"febrero":2,"febreiro":2,"marzo":3,"abril":4,"mayo":5,"maio":5,
"junio":6,"xuño":6,"julio":7,"xullo":7,"agosto":8,"septiembre":9,"setembro":9,"octubre":10,"outubro":10,
"noviembre":11,"novembro":11,"diciembre":12,"decembro":12}
S=threading.local()
def client():
 if not hasattr(S,"c"):
  r=requests.Session();r.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"});S.c=r
 return S.c
def request(url,pdf=False):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443) or u.username or u.fragment or u.query:
  invalid("Pontevedra: URL ajena al sitio oficial")
 try:
  r=client().get(url,timeout=(12,35),stream=pdf,allow_redirects=pdf,
                 headers={"Range":"bytes=0-160"} if pdf else {})
  if r.status_code!=200 and not(pdf and r.status_code==206):
   invalid(f"Pontevedra HTTP {r.status_code}: {url}")
  if urlsplit(r.url).hostname!=HOST:invalid("Pontevedra: PDF redirigido fuera de la Diputación")
  if pdf:
   buf=b""
   for chunk in r.iter_content(150):
    buf+=chunk
    if len(buf)>=5:break
   r.close()
   if not buf.startswith(b"%PDF-"):invalid(f"Pontevedra: no es PDF firmado {url}")
   return None
  if not 500<len(r.content)<1000000:invalid("Pontevedra: respuesta incompleta")
  return BeautifulSoup(r.content,"html.parser")
 except requests.RequestException as e:invalid("Pontevedra: error de sede "+str(e)[:190])
def read_day(day):
 # El portal sirve a veces la página de otra fecha: reintentar antes de rendirse.
 for attempt in range(4):
  try:return read_day_once(day)
  except Exception as ex:
   if "fecha impresa no coincide" not in str(ex) or attempt==3:raise
   time.sleep(2*(attempt+1))
def read_day_once(day):
 url=f"https://{HOST}/detalle/-/boppo/{day:%Y/%m/%d}"
 soup=request(url)
 headers=[h.get_text(" ",strip=True) for h in soup.select("h2") if h.get_text(" ",strip=True).startswith("BOPPO número")]
 if not headers:
  text=soup.get_text(" ",strip=True)
  if "publicación que solicita non se puido encontrar" in text or "publicación que solicita no se pudo encontrar" in text:
   return None
  invalid(f"Pontevedra {day}: no se puede acreditar la edición")
 if len(headers)!=1:invalid("Pontevedra: encabezado duplicado")
 m=re.fullmatch(r"BOPPO número\s+(\d{1,3})",headers[0],re.I)
 if not m:invalid("Pontevedra: número no reconocido")
 num=int(m[1])
 text=soup.get_text(" ",strip=True)
 pos=text.find(headers[0])
 sub=text[pos:pos+180]
 date_match=re.search(r"\b(\d{1,2}) de (\w+) de (\d{4})\b",sub,re.I)
 if (not date_match or int(date_match[1])!=day.day or MONTHS.get(date_match[2].lower())!=day.month
     or int(date_match[3])!=day.year):
  invalid(f"Pontevedra {day}: fecha impresa no coincide: {sub[:130]}")
 items=soup.select("ul.listadoSumario > li")
 if not items:invalid("Pontevedra: edición sin anuncios")
 seen=set();notices=[]
 for it in items:
  title_tag=it.select_one("p.sumario a")
  entity_tag=it.select_one("span.pub")
  pdf_tag=it.select_one("a.botDescPDF[href]")
  title=" ".join(title_tag.get_text(" ",strip=True).split()) if title_tag else ""
  agency=" ".join(entity_tag.get_text(" ",strip=True).split()) if entity_tag else ""
  if not title or not agency or not pdf_tag:invalid(f"Pontevedra {day}: anuncio no identificable")
  pdf=urljoin("https://"+HOST,pdf_tag["href"]);u=urlsplit(pdf)
  mt=PDF_RE.fullmatch(u.path)
  if (not mt or u.hostname!=HOST or u.query or u.fragment or int(mt[1])!=day.month or
      int(mt[2])!=day.day or mt[3]!=mt[5] or
      abs((datetime.strptime(mt[4],"%Y%m%d").date()-day).days)>10):
   invalid(f"Pontevedra {day}: PDF no corresponde al anuncio {pdf}")
  ident=mt[3];noticeid="PO-"+ident
  if noticeid in seen:invalid(f"Pontevedra {day}: documento duplicado")
  seen.add(noticeid)
  kind=galicia_employment(title)
  if kind:
   request(pdf,pdf=True)
   notices.append({"id":noticeid,"province":"Pontevedra","title":title,"entity":agency,
      "date":day.strftime("%d/%m/%Y"),"bulletin":str(num),"type":kind,"url":pdf})
 print("PONTEVEDRA",day,num,len(items),"anuncios",len(notices),"candidatas",flush=True)
 return {"day":day,"number":str(num),"read":len(items),"notices":notices}
def audit(today=None):
 end=today or date.today();start=end-timedelta(days=29)
 with ThreadPoolExecutor(max_workers=2) as pool:
  items=[x for x in pool.map(read_day,[start+timedelta(days=i) for i in range(30)]) if x]
 seq=[int(x["number"]) for x in items]
 if not 19<=len(items)<=25 or any(b!=a+1 for a,b in zip(seq,seq[1:])):
  invalid(f"Pontevedra: número de boletines incompleto: {seq}")
 if (items[0]["day"]-start).days>3 or (end-items[-1]["day"]).days>3:
  invalid("Pontevedra: fechas inicial/final sin validar")
 return publish_audit(SOURCE,"Pontevedra",items,today=end)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
 args=p.parse_args();write_output(args.output,audit())
