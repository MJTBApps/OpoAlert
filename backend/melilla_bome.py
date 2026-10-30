#!/usr/bin/env python3
"""Melilla BOME: complete 30-day official editions, originals and notice CVEs.

La ventana son los 30 días que acaban hoy (o `audit(today=...)`). El archivo
oficial es anual (/bomes/AAAA): se piden los años que toca la ventana, también
el anterior en enero. Hay dos series: ordinarios (martes y viernes, numeración
continua entre años) y extraordinarios (BOME EXTRA, vuelven a 1 cada enero).
"""
from __future__ import annotations
import argparse,re,threading,time,requests
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from clm_common import employment,publish_audit,write_output,numbering_ok
from provincial_common import ProvincialCoverageError
HOST="bomemelilla.es"
# Portada oficial: estable, siempre lista los boletines del año en curso.
SOURCE=f"https://{HOST}/"
PROVINCE="Melilla (BOME)"
DAYS=30
# Dos ordinarios por semana: unos 8-9 en 30 días (7 en Navidad).
MIN_REGULAR=6
WORKERS=3
MONTHS={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,"agosto":8,
        "septiembre":9,"setiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
ED_RE=re.compile(r"^/bome/BOME-B(X?)-(\d{4})-(\d{1,5})$")
NAME_RE=re.compile(r"BOME\s+(EXTRA\s+)?N[º°]\s*(\d{1,5})\s+del\s+\w+,\s+(\d{1,2})\s+de\s+([a-zé]+)\s+de\s+(\d{4})",re.I)
ART_RE=re.compile(r"ART[IÍ]CULO\s+(\d{1,8})\s+\(CVE:\s*BOME-(AX|A)-(\d{4})-(\d{1,8})\)",re.I)
HTTP=threading.local()
def invalid(message):raise ProvincialCoverageError("Melilla BOME: "+str(message))
def session():
 if not hasattr(HTTP,"session"):
  s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert BOME audit)","Accept-Language":"es-ES,es;q=0.9"});HTTP.session=s
 return HTTP.session
def get(url,pdf=False,attempts=3):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443) or u.username or u.fragment or u.query:
  invalid("enlace ajeno al BOME oficial "+url[:170])
 error=None
 for attempt in range(attempts):
  try:
   r=session().get(url,stream=pdf,timeout=(10,40),allow_redirects=False,
                   headers={"Range":"bytes=0-128"} if pdf else {})
   if r.status_code in ((200,206) if pdf else (200,)):break
   error=f"HTTP {r.status_code}: {url}";r.close()
  except requests.RequestException as e:error="acceso oficial fallido "+str(e)[:150]
  if attempt==attempts-1:invalid(f"{error} (tras {attempts} intentos)")
  time.sleep(1.5*(attempt+1))
 if pdf:
  try:
   if "pdf" not in r.headers.get("Content-Type","").lower():
    invalid("enlace no es PDF: "+url)
   first=b""
   for piece in r.iter_content(150):
    first+=piece
    if len(first)>=5:break
  finally:r.close()
  if not first.startswith(b"%PDF-"):invalid("documento no es PDF original "+url)
  return None
 if not 1100<len(r.content)<2_500_000:invalid("sumario oficial vacío o truncado "+url)
 return BeautifulSoup(r.content,"html.parser")
def edition_day(label):
 m=NAME_RE.search(" ".join(label.split()))
 if not m or m[4].lower() not in MONTHS:invalid("edición sin título o fecha inequívoca: "+label[:170])
 extra=bool(m[1]);n=int(m[2])
 try:day=date(int(m[5]),MONTHS[m[4].lower()],int(m[3]))
 except ValueError:invalid("fecha de publicación imposible: "+label[:170])
 return extra,n,day
def year_page(year):
 return f"https://{HOST}/bomes/{year}"
def archive(year):
 """Todas las ediciones del archivo anual oficial: {url: (extra, número, día)}."""
 page=year_page(year)
 root=get(page)
 editions={}
 for a in root.select("a[href]"):
  url=urljoin(page,a["href"]);u=urlsplit(url)
  match=ED_RE.fullmatch(u.path)
  if not match or u.hostname!=HOST or u.query or u.fragment:continue
  extra,n,day=edition_day(a.get_text(" ",strip=True))
  if extra!=(match[1]=="X") or n!=int(match[3]) or day.year!=int(match[2]) or day.year!=year:
   invalid("enlace BOME no coincide con número, tipo o año: "+url)
  if url in editions and editions[url]!=(extra,n,day):invalid("edición duplicada en archivo oficial "+url)
  editions[url]=(extra,n,day)
 if not editions:invalid(f"archivo oficial {year} sin boletines")
 return editions
def series_ok(entries):
 """Una serie (ordinaria o extraordinaria) sin huecos ni repeticiones."""
 entries=sorted(entries)
 keys=[(d.year,n) for d,n in entries]
 return len(set(keys))==len(keys) and numbering_ok(entries)
def calendar(end):
 start=end-timedelta(days=DAYS-1)
 # El año anterior también si la ventana o la edición previa a ella caen en él.
 years=range((start-timedelta(days=15)).year,end.year+1)
 editions={}
 for year in years:
  editions.update(archive(year))
 if not any(end-timedelta(days=4)<=day<=end for _,_,day in editions.values()):
  invalid(f"el archivo oficial no llega al {end}: último BOME {max(d for _,_,d in editions.values())}")
 known=[(url,v) for url,v in editions.items() if v[2]<=end]
 regular=sorted((day,n) for _,(extra,n,day) in known if not extra)
 extras=sorted((day,n) for _,(extra,n,day) in known if extra)
 # Numeración seguida en la ventana y desde la última edición anterior a ella:
 # así se detecta también un boletín ausente justo al principio.
 def tail(series):
  before=[x for x in series if x[0]<start]
  return before[-1:]+[x for x in series if x[0]>=start]
 if not series_ok(tail(regular)):invalid(f"faltan BOME ordinarios: {tail(regular)}")
 if not series_ok(tail(extras)):invalid(f"faltan BOME extraordinarios: {tail(extras)}")
 items=sorted(((url,v) for url,v in known if v[2]>=start),key=lambda x:(x[1][2],x[1][0],x[1][1]))
 n_regular=sum(1 for _,v in items if not v[0])
 if n_regular<MIN_REGULAR:invalid(f"solo {n_regular} BOME ordinarios en 30 días")
 days=[v[2] for _,v in items]
 if (days[0]-start).days>4 or (end-days[-1]).days>4:
  invalid(f"faltan BOME al principio o al final: {days[0]}–{days[-1]} para {start}–{end}")
 print(f"MELILLA: {len(items)} boletines oficiales del {start} al {end}: {n_regular} ordinarios y "
       f"{len(items)-n_regular} extraordinarios",flush=True)
 return items
def issue(item):
 url,(extra,num,day)=item
 h=get(url)
 heading=h.select_one("h1")
 if not heading:invalid(f"BOME {num}: sin título oficial")
 actual=edition_day(heading.get_text(" ",strip=True))
 if actual!=(extra,num,day):invalid("fecha / número del BOME no coincide con archivo oficial")
 year=day.year
 issue_label=("E"+str(num)) if extra else str(num)
 target_label=f"BOME-{'BX' if extra else 'B'}-{year}-{num}"
 if url!=f"https://{HOST}/bome/{target_label}":invalid("ruta canónica BOME no coincide "+url)
 edition_pdf=f"https://{HOST}/bome/descargar/{target_label}.pdf"
 summary_pdf=f"https://{HOST}/bome/descargar/BOME-{'SX' if extra else 'S'}-{year}-{num}.pdf"
 links={urljoin(url,a["href"]) for a in h.select("a[href]")}
 if edition_pdf not in links or summary_pdf not in links:
  invalid("falta PDF original o sumario original de "+target_label)
 get(edition_pdf,pdf=True);get(summary_pdf,pdf=True)
 heads=h.select("h5")
 if not 1<=len(heads)<=200:invalid(f"BOME {num}: disposiciones ausentes o truncadas")
 notices=[];ids=set();all_pdfs=[]
 for heading in heads:
  m=ART_RE.fullmatch(" ".join(heading.get_text(" ",strip=True).split()))
  if not m or int(m[1])!=int(m[4]) or abs(int(m[3])-year)>1:
   invalid(f"BOME {num}: CVE no oficial {heading.get_text(' ',strip=True)[:160]}")
  article=int(m[1]);prefix=m[2].upper();cve_year=int(m[3])
  if prefix!=("AX" if extra else "A"):
   invalid(f"BOME {num}: artículo ajeno a la edición {article}")
  ident=f"ML-{cve_year}-{prefix}-{article}"
  if ident in ids:invalid(f"BOME {num}: artículo duplicado {ident}")
  ids.add(ident)
  li=heading.find_parent("li")
  block=li.select_one("blockquote") if li else None
  title=" ".join(block.get_text(" ",strip=True).split()) if block else ""
  agency=heading.find_previous("h4")
  entity=" ".join(agency.get_text(" ",strip=True).split()) if agency else ""
  if not 12<len(title)<2800 or not 3<len(entity)<500:
   invalid(f"BOME {num}: título o organismo ausente en {ident}")
  doc_pdf=f"https://{HOST}/bome/descargar/BOME-{prefix}-{cve_year}-{article}.pdf"
  if not li or not any(urljoin(url,a.get("href",""))==doc_pdf for a in li.select("a[href]")):
   invalid(f"BOME {num}: falta PDF original CVE {ident}")
  all_pdfs.append(doc_pdf)
  kind=employment(title)
  if kind:
   notices.append({"id":ident,"province":PROVINCE,"title":title,"entity":entity,
        "date":day.strftime("%d/%m/%Y"),"bulletin":issue_label,"type":kind,"url":doc_pdf})
 if len(all_pdfs)!=len(heads):invalid(f"BOME {num}: falta artículo del sumario")
 print(f"MELILLA BOME {day} {issue_label}: {len(heads)} anuncios, {len(notices)} candidatas",flush=True)
 return {"day":day,"number":issue_label,"read":len(heads),"notices":notices,"pdfs":all_pdfs}
def audit(today=None):
 end=today or date.today()
 items=calendar(end)
 with ThreadPoolExecutor(max_workers=WORKERS) as ex:
  all_issues=list(ex.map(issue,items))
 all_doc_urls=sorted({url for entry in all_issues for url in entry["pdfs"]})
 if len(all_doc_urls)!=sum(len(entry["pdfs"]) for entry in all_issues):
  invalid("un mismo artículo aparece en dos boletines")
 with ThreadPoolExecutor(max_workers=WORKERS) as ex:
  list(ex.map(lambda u:get(u,pdf=True),all_doc_urls))
 print(f"MELILLA: comprobados {len(all_doc_urls)} PDF originales de artículos, "
       f"{len(all_issues)} boletines y {len(all_issues)} sumarios",flush=True)
 issues=[{key:row[key] for key in ("day","number","read","notices")} for row in all_issues]
 return publish_audit(SOURCE,PROVINCE,issues,today=end,min_issues=MIN_REGULAR)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
 a=p.parse_args();write_output(a.output,audit())
