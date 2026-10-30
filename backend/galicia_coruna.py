#!/usr/bin/env python3
"""A Coruña BOP official 30-day per-announcement PDF source audit."""
from __future__ import annotations
from datetime import date,timedelta,datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit,parse_qs,urljoin
from bs4 import BeautifulSoup
from clm_common import publish_audit,write_output,invalid,numbering_ok
from galicia_common import galicia_employment
import requests,re,threading,argparse,time
SOURCE="https://bop.dacoruna.gal/bopportal/ultimoBoletin"
HOST="bop.dacoruna.gal"
PDF_RE=re.compile(r"^/bopportal/publicado/(\d{4})/(\d{2})/(\d{2})/(\d{4})_(\d{10})\.pdf$")
MONTHS={"xaneiro":1,"febreiro":2,"marzo":3,"abril":4,"maio":5,"xuño":6,
"xullo":7,"agosto":8,"setembro":9,"outubro":10,"novembro":11,"decembro":12,
"enero":1,"febrero":2,"mayo":5,"junio":6,"julio":7,"septiembre":9,"octubre":10,
"noviembre":11,"diciembre":12}
HEAD=re.compile(r"Sumario d[oe]l? Bolet[ií]n N[º°.]*\s*(\d+)\s*-\s*[\wáéíóú]+,\s*(\d{1,2}) de (\w+) de (\d{4})",re.I)
S=threading.local()
def session():
 if not hasattr(S,"req"):
  q=requests.Session();q.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"});S.req=q
 return S.req
def get_html(day):
 url=f"https://{HOST}/bopportal/cambioBoletin?fechaInput={day:%d/%m/%Y}"
 try:
  for attempt in range(5):
   r=session().get(url,timeout=(9,32),allow_redirects=False)
   if r.status_code in (404,410) or (r.status_code==500 and day.weekday()>=5):return None
   if r.status_code==200 and 400<len(r.content)<500000:
    return BeautifulSoup(r.content,"html.parser")
   if attempt<4:time.sleep(0.7*(attempt+1))
  invalid(f"A Coruña: HTTP {r.status_code} / incompleto {day} tras cinco intentos")
 except requests.RequestException as e:invalid(f"A Coruña {day}: fallo de acceso a sede {e}")
def pdf_check(url):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=HOST or not PDF_RE.fullmatch(u.path) or u.query or u.fragment:
  invalid("A Coruña: PDF fuera de fuente")
 try:
  r=session().get(url,timeout=(10,35),allow_redirects=False,stream=True,headers={"Range":"bytes=0-128"})
  if r.status_code not in (200,206):invalid(f"A Coruña: PDF HTTP {r.status_code}")
  raw=b""
  for chunk in r.iter_content(140):
   raw+=chunk
   if len(raw)>=5:break
  valid=raw.startswith(b"%PDF-");r.close()
  if not valid:invalid(f"A Coruña: supuesto PDF no oficial {url}")
 except requests.RequestException as e:invalid(f"A Coruña: error PDF {e}")
def read_day(day):
 soup=get_html(day)
 if soup is None:return None
 head=soup.find(string=HEAD)
 if head is None:
  txt=soup.get_text(" ",strip=True)
  if any(x in txt.lower() for x in ("no existe bolet", "non existe bolet","no se ha publicado bolet","non se publicou bolet","sen boletin","sin boletín")):
   return None
  invalid(f"A Coruña: fecha {day}, edición ausente de sumario inesperadamente")
 m=HEAD.search(str(head))
 if not m or int(m[2])!=day.day or MONTHS.get(m[3].lower())!=day.month or int(m[4])!=day.year:
  invalid(f"A Coruña: sumario corresponde a otra fecha {day}: {str(head)[:150]}")
 n=int(m[1])
 blocks=soup.select("div.bloqueAnuncio")
 if not blocks:invalid(f"A Coruña {day}: sumario vacío")
 seen=set();notices=[]
 for b in blocks:
  p=b.select_one("p.resumenSumario")
  anchors=p.select('a[title="Ver texto completo"]') if p else []
  if len(anchors)<2:invalid(f"A Coruña {day}: anuncio sin código o título")
  idmatch=re.fullmatch(r"(\d{4})/(\d{1,8})",anchors[0].get_text(" ",strip=True))
  title=" ".join(anchors[1].get_text(" ",strip=True).split())
  heading=next((x for x in reversed(b.find_all(re.compile(r"^h[2-5]$"))) if x.get_text(" ",strip=True)),None)
  # Algunos anuncios de particulares (comunidades de usuarios...) no llevan
  # encabezado de organismo: no se inventa, se remite al anuncio oficial.
  entity=" ".join(heading.get_text(" ",strip=True).split()) if heading else "Emisor: consultar anuncio oficial (BOP A Coruña)"
  if not idmatch or not title:invalid(f"A Coruña {day}: título o código inválido")
  # El código lleva el año de registro: en enero puede ser el del año anterior.
  year,k=int(idmatch[1]),int(idmatch[2]);nid=f"AC-{year}-{k}"
  if nid in seen:invalid(f"A Coruña {day}: código duplicado {nid}")
  seen.add(nid)
  official=f"https://{HOST}/bopportal/publicado/{day:%Y/%m/%d}/{year}_{k:010d}.pdf"
  kind=galicia_employment(title)
  if kind:
   pdf_check(official)
   notices.append({"id":nid,"province":"A Coruña","title":title,"entity":entity,
    "date":day.strftime("%d/%m/%Y"),"bulletin":str(n),"type":kind,"url":official})
 prevlink=next((a for a in soup.select('a[href*="cambioBoletin"]')
               if "anterior" in a.get_text(" ",strip=True).lower()),None)
 if not prevlink:
  invalid(f"A Coruña {day}: no tiene navegación oficial al boletín anterior")
 prev=parse_qs(urlsplit(urljoin(SOURCE,prevlink["href"])).query).get("fechaInput",[])
 if len(prev)!=1:invalid("A Coruña: no se recupera fecha anterior oficial")
 try:previous=datetime.strptime(prev[0],"%d/%m/%Y").date()
 except ValueError:invalid("A Coruña: fecha anterior incoherente")
 if not previous<day or (day-previous).days>6:
  invalid(f"A Coruña: fecha anterior no consecutiva {day} / {previous}")
 print("CORUNA",day,n,len(blocks),"anuncios",len(notices),"candidatas",flush=True)
 return ({"day":day,"number":str(n),"read":len(blocks),"notices":notices},previous)
def audit(today=None):
 end=today or date.today();start=end-timedelta(days=29)
 issues=[];day=end
 # Fines de semana y festivos no hay BOP: empezar por la última edición publicada.
 result=read_day(day)
 while result is None:
  day-=timedelta(days=1)
  if (end-day).days>3:invalid("A Coruña: sin boletín en los últimos cuatro días")
  result=read_day(day)
 for i in range(30):
  if day<start:break
  if i:result=read_day(day)
  if result is None:invalid("A Coruña: enlace anterior lleva a boletín inexistente")
  issue,previous=result
  issues.append(issue)
  day=previous
 if day>=start:invalid("A Coruña: no se pudo recorrer 30 días del archivo oficial")
 issues.sort(key=lambda x:x["day"])
 seq=[int(x["number"]) for x in issues]
 if not 19<=len(issues)<=27 or not numbering_ok([(x["day"],n) for x,n in zip(issues,seq)]):
  invalid(f"A Coruña: numeración de boletines incompleta {seq}")
 if (issues[0]["day"]-start).days>3 or (end-issues[-1]["day"]).days>3:
  invalid("A Coruña: faltan boletines inicial/final")
 return publish_audit(SOURCE,"A Coruña",issues,today=end)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
 args=p.parse_args();write_output(args.output,audit())
