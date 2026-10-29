#!/usr/bin/env python3
"""Melilla BOME: complete 30-day official editions, originals and notice CVEs."""
from __future__ import annotations
import argparse,re,threading,requests
from datetime import date,datetime
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from clm_common import employment,publish_audit,write_output
from provincial_common import ProvincialCoverageError
HOST="bomemelilla.es"
SOURCE=f"https://{HOST}/bomes/2026"
PROVINCE="Melilla (BOME)"
START=date(2026,9,30);END=date(2026,10,29)
ED_RE=re.compile(r"^/bome/BOME-B(X?)-2026-(\d{1,4})$")
NAME_RE=re.compile(r"BOME\s+(EXTRA\s+)?N[º°]\s*(\d{1,4})\s+del\s+\w+,\s+(\d{1,2})\s+de\s+(septiembre|octubre)\s+de\s+2026",re.I)
ART_RE=re.compile(r"ART[IÍ]CULO\s+(\d{1,8})\s+\(CVE:\s*BOME-(AX|A)-2026-(\d{1,8})\)",re.I)
PDF_RE=re.compile(r"^/bome/descargar/BOME-(A|AX|B|BX|S|SX)-2026-(\d{1,8})\.pdf$")
HTTP=threading.local()
def invalid(message):raise ProvincialCoverageError("Melilla BOME: "+str(message))
def session():
 if not hasattr(HTTP,"session"):
  s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"});HTTP.session=s
 return HTTP.session
def get(url,pdf=False):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443) or u.username or u.fragment or u.query:
  invalid("enlace ajeno al BOME oficial "+url[:170])
 try:
  r=session().get(url,stream=pdf,timeout=(10,40),allow_redirects=False,
                  headers={"Range":"bytes=0-128"} if pdf else {})
  if r.status_code not in ((200,206) if pdf else (200,)):
   invalid(f"HTTP {r.status_code}: {url}")
  if pdf:
   if "pdf" not in r.headers.get("Content-Type","").lower():
    invalid("enlace no es PDF: "+url)
   first=b""
   for piece in r.iter_content(150):
    first+=piece
    if len(first)>=5:break
   r.close()
   if not first.startswith(b"%PDF-"):invalid("documento no es PDF original "+url)
   return None
  if not 1100<len(r.content)<2_500_000:invalid("sumario oficial vacío o truncado "+url)
  return BeautifulSoup(r.content,"html.parser")
 except requests.RequestException as e:invalid("acceso oficial fallido "+str(e)[:150])
def edition_day(label):
 m=NAME_RE.search(" ".join(label.split()))
 if not m:invalid("edición sin título o fecha inequívoca: "+label[:170])
 extra=bool(m[1]);n=int(m[2]);month=9 if m[4].lower()=="septiembre" else 10
 try:day=date(2026,month,int(m[3]))
 except ValueError:invalid("fecha de publicación imposible")
 return extra,n,day
def calendar():
 root=get(SOURCE)
 editions={}
 for a in root.select("a[href]"):
  url=urljoin(SOURCE,a["href"]);u=urlsplit(url)
  match=ED_RE.fullmatch(u.path)
  if not match or u.hostname!=HOST or u.query or u.fragment:continue
  label=a.get_text(" ",strip=True)
  if not any(x in label.lower() for x in ("de septiembre de 2026","de octubre de 2026")):
   continue
  extra,n,day=edition_day(label)
  if extra!=(match[1]=="X") or n!=int(match[2]):invalid("enlace BOME no coincide con número y tipo")
  if not START<=day<=END:continue
  if url in editions:invalid("edición duplicada en archivo oficial "+url)
  editions[url]=(extra,n,day)
 regular=sorted(n for extra,n,_ in editions.values() if not extra)
 extras=sorted(n for extra,n,_ in editions.values() if extra)
 if regular!=list(range(6419,6427)) or extras!=list(range(43,49)):
  invalid(f"30 días de BOME incompletos: ordinarios={regular}, extraordinarios={extras}")
 if len(editions)!=14 or max(day for _,_,day in editions.values())!=date(2026,10,27):
  invalid("archivo BOME sin todas las ediciones del histórico")
 if len([1 for extra,n,day in editions.values() if day==START])!=1:
  invalid("no está el BOME extraordinario 43 de 30/09")
 print(f"MELILLA: {len(editions)} boletines oficiales, 8 ordinarios y 6 extraordinarios, hasta 27/10",flush=True)
 return sorted(editions.items(),key=lambda x:(x[1][2],x[1][0],x[1][1]))
def issue(item):
 url,(extra,num,day)=item
 h=get(url)
 heading=h.select_one("h1")
 if not heading:invalid(f"BOME {num}: sin título oficial")
 actual=edition_day(heading.get_text(" ",strip=True))
 if actual!=(extra,num,day):invalid("fecha / número del BOME no coincide con archivo oficial")
 issue_label=("E"+str(num)) if extra else str(num)
 target_label=f"BOME-{'BX' if extra else 'B'}-2026-{num}"
 if url!=f"https://{HOST}/bome/{target_label}":invalid("ruta canónica BOIB no coincide")
 edition_pdf=f"https://{HOST}/bome/descargar/{target_label}.pdf"
 summary_pdf=f"https://{HOST}/bome/descargar/BOME-{'SX' if extra else 'S'}-2026-{num}.pdf"
 links={urljoin(url,a["href"]) for a in h.select("a[href]")}
 if edition_pdf not in links or summary_pdf not in links:
  invalid("falta PDF original o sumario original de "+target_label)
 get(edition_pdf,pdf=True);get(summary_pdf,pdf=True)
 heads=h.select("h5")
 if not 1<=len(heads)<=200:invalid(f"BOME {num}: disposiciones ausentes o truncadas")
 notices=[];ids=set();all_pdfs=[]
 for heading in heads:
  m=ART_RE.fullmatch(" ".join(heading.get_text(" ",strip=True).split()))
  if not m or int(m[1])!=int(m[3]):
   invalid(f"BOME {num}: CVE no oficial {heading.get_text(' ',strip=True)[:160]}")
  article=int(m[1]);prefix=m[2].upper()
  if prefix!=("AX" if extra else "A"):
   invalid(f"BOME {num}: artículo ajeno a la edición {article}")
  ident=f"ML-2026-{prefix}-{article}"
  if ident in ids:invalid(f"BOME {num}: artículo duplicado {ident}")
  ids.add(ident)
  li=heading.find_parent("li")
  block=li.select_one("blockquote") if li else None
  title=" ".join(block.get_text(" ",strip=True).split()) if block else ""
  agency=heading.find_previous("h4")
  entity=" ".join(agency.get_text(" ",strip=True).split()) if agency else ""
  if not 12<len(title)<2800 or not 3<len(entity)<500:
   invalid(f"BOME {num}: título o organismo ausente en {ident}")
  doc_pdf=f"https://{HOST}/bome/descargar/BOME-{prefix}-2026-{article}.pdf"
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
def audit():
 items=calendar()
 with ThreadPoolExecutor(max_workers=6) as ex:
  all_issues=list(ex.map(issue,items))
 all_doc_urls=sorted({url for entry in all_issues for url in entry["pdfs"]})
 with ThreadPoolExecutor(max_workers=9) as ex:
  list(ex.map(lambda u:get(u,pdf=True),all_doc_urls))
 print(f"MELILLA: comprobados {len(all_doc_urls)} PDF originales de artículos, 14 boletines y 14 sumarios",flush=True)
 issues=[{key:row[key] for key in ("day","number","read","notices")} for row in all_issues]
 return publish_audit(SOURCE,PROVINCE,issues,today=END,min_issues=14)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
 a=p.parse_args();write_output(a.output,audit())
