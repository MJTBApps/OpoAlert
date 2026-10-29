#!/usr/bin/env python3
"""Official BOIB 30-day audit for all Balearic islands, including extraordinary issues.

The BOIB is the shared journal for the Balearic administration, island councils,
municipal governments and public bodies. The official calendar shows every issue
including extraordinary issues; each issue's section pages list original
individual disposiciones. Do not infer island by ambiguous municipality names.
"""
from __future__ import annotations
import argparse,re,threading,requests
from urllib.parse import urljoin,urlsplit
from datetime import date,datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from clm_common import employment,publish_audit,write_output
from provincial_common import ProvincialCoverageError
HOST="www.caib.es"
ROOT=f"https://{HOST}/eboibfront/es"
SOURCE=ROOT
PROVINCE="Illes Balears (BOIB)"
END=date(2026,10,29)
BEGIN=date(2026,9,30)
MONTH_URL=ROOT+"/2026/mes/9"
ISSUE_RE=re.compile(r"^/eboibfront/es/2026/(\d{5})/?$")
SECTION_RE=re.compile(r"^/eboibfront/es/2026/(\d{5})/seccion-[a-z-]+/(\d{3})$")
NUM_RE=re.compile(r"BOIB\s+N[úu]m\.\s*(\d{1,3})\s*-\s*(\d{1,2})\s*/\s*(Octubre|Septiembre)\s*/\s*2026",re.I)
REG_RE=re.compile(r"N[úu]mero de (?:registro|edicto)\s+(\d{1,8})",re.I)
PDF_OLD_RE=re.compile(r"^/eboibfront/pdf/es/2026/(\d{1,3})/(\d{5,9})$")
PDF_ELI_RE=re.compile(r"^/eboibfront/eli/[a-zA-Z0-9_()/.+-]+/dof/spa/pdf$")
SESSION=threading.local()
def invalid(msg):
 raise ProvincialCoverageError("Illes Balears BOIB: "+str(msg))
def client():
 if not hasattr(SESSION,"client"):
  s=requests.Session()
  s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert BOIB official source audit/1.0)","Accept-Language":"es-ES,es;q=0.9"})
  SESSION.client=s
 return SESSION.client
def check_url(url):
 u=urlsplit(url)
 if (u.scheme!="https" or u.hostname!=HOST or u.username or u.password
     or u.fragment or u.port not in (None,443) or not u.path.startswith("/eboibfront/")):
  invalid("URL fuera de la sede oficial "+str(url)[:160])
 return u
def html_page(url):
 check_url(url)
 try:
  r=client().get(url,timeout=(12,42),allow_redirects=False)
  if (r.status_code!=200 or urlsplit(r.url).hostname!=HOST
      or not 9000<=len(r.content)<2500000):
   invalid(f"índice incompleto HTTP {r.status_code}: {url}")
  soup=BeautifulSoup(r.content,"html.parser")
  if not soup.select_one("h1") or "Boletín Oficial de las Illes Balears" not in soup.select_one("h1").get_text(" ",strip=True):
   invalid(f"no es BOIB oficial: {url}")
  return soup
 except requests.RequestException as e:invalid(f"sin acceso a índice oficial: {e}")
def validate_pdf_url(url,number):
 u=check_url(url)
 match=PDF_OLD_RE.fullmatch(u.path)
 if match:
  if int(match[1])!=number or u.query:
   invalid("PDF de otro boletín "+url)
  return
 if not PDF_ELI_RE.fullmatch(u.path) or u.query:
  invalid("versión PDF ELI no oficial "+url)
def check_pdf(url):
 try:
  r=client().get(url,timeout=(10,43),stream=True,allow_redirects=False,
                 headers={"Range":"bytes=0-127"})
  if (r.status_code not in (200,206) or
      "pdf" not in r.headers.get("Content-Type","").lower()):
   invalid(f"PDF no disponible / HTTP {r.status_code}: {url}")
  first=b""
  for piece in r.iter_content(130):
   first+=piece
   if len(first)>=5:break
  r.close()
  if not first.startswith(b"%PDF-"):invalid("archivo no es PDF original "+url)
 except requests.RequestException as e:invalid("error verificando PDF "+str(e)[:170])
def parse_calendar():
 html=html_page(MONTH_URL)
 result={}
 for a in html.select("a[href]"):
  u=urlsplit(urljoin(MONTH_URL,a.get("href","")))
  m=ISSUE_RE.fullmatch(u.path)
  text=a.get_text(" ",strip=True)
  if not m or not re.fullmatch(r"\d{1,2}(?:\*E)?",text):
   continue
  day=date(2026,10,int(text.split("*")[0]))
  uid=int(m[1])
  if uid in result:invalid(f"calendario contiene edición duplicada {uid}")
  result[uid]=(day,text.endswith("*E"))
 if len(result)!=16:invalid(f"el calendario oficial de octubre tiene {len(result)} ediciones, esperadas 16")
 if min(d for d,_ in result.values())!=date(2026,10,1) or max(d for d,_ in result.values())!=END:
  invalid("faltan fechas iniciales o finales del mes")
 if sum(1 for _,extra in result.values() if extra)!=3:
  invalid("no aparecen las 3 ediciones extraordinarias oficiales de octubre")
 if min(result)<12000 or max(result)>12400:invalid("IDs de ediciones fuera de rango 2026")
 return sorted(result.items(),key=lambda x:(x[1][0],x[0]))
def issue(item):
 uid,(day,extra)=item
 indexurl=f"{ROOT}/2026/{uid}/"
 h=html_page(indexurl)
 title=h.title.get_text(" ",strip=True) if h.title else ""
 m=NUM_RE.search(title)
 if not m:invalid(f"número/fecha de BOIB ausente en {uid}: {title[:150]}")
 number=int(m[1])
 if date(2026,10 if m[3].lower()=="octubre" else 9,int(m[2]))!=day:
  invalid(f"fecha del calendario y del BOIB {number} no coincide")
 intro=h.get_text(" ",strip=True)[:650]
 if ("Extraordinario" in intro)!=extra:
  invalid(f"estado de edición extraordinaria no coincide, BOIB {number}")
 sections={}
 for a in h.select('a[href*="/seccion-"]'):
  target=urljoin(indexurl,a.get("href",""));p=urlsplit(target)
  match=SECTION_RE.fullmatch(p.path)
  if not match or int(match[1])!=uid or p.hostname!=HOST or p.query or p.fragment:
   continue
  sections[match[2]]=target
 if not 1<=len(sections)<=5:
  invalid(f"BOIB {number}: índice sin listado completo de secciones: {sections}")
 count=0;found=[];seen=set()
 for code,path in sorted(sections.items()):
  page=html_page(path)
  if ("BOIB Núm. "+str(number)) not in (page.title.get_text(" ",strip=True) if page.title else ""):
   invalid(f"BOIB {number}: página de sección ajena {path}")
  records=page.select("ul.resolucions > li")
  if not records:invalid(f"BOIB {number}: sección {code} sin disposiciones")
  for item in records:
   paragraph=item.find("p",recursive=False)
   reg=item.select_one("p.registre")
   agency_box=item.find_parent("div",class_="caja")
   agency=agency_box.select_one("h3.organisme") if agency_box else None
   pdfs=item.select('a[aria-label="Exportar a PDF"][href]')
   title=paragraph.get_text(" ",strip=True) if paragraph else ""
   label=agency.get_text(" ",strip=True) if agency else ""
   code_match=REG_RE.search(reg.get_text(" ",strip=True) if reg else "")
   if (not title or not 6<len(title)<2800 or not 2<len(label)<500
       or not code_match or len(pdfs)!=1):
    invalid(f"BOIB {number}: anuncio sin título, registro, emisor o PDF {str(item)[:500]}")
   entry=int(code_match[1])
   if entry in seen:
    invalid(f"BOIB {number}: número edicto duplicado {entry}")
   seen.add(entry);count+=1
   target=urljoin(path,pdfs[0]["href"])
   validate_pdf_url(target,number)
   kind=employment(title)
   if kind:
    found.append({"id":f"IB-2026-{entry}","province":PROVINCE,
       "title":title,"entity":label,"date":day.strftime("%d/%m/%Y"),
       "bulletin":str(number),"type":kind,"url":target})
 print(f"BALEARES BOIB {day} n.º {number} {'EXTRA' if extra else 'ordinario'}: {count} anuncios, {len(found)} candidatas, {len(sections)} secciones",flush=True)
 if count<1:invalid(f"BOIB {number}: boletín vacío")
 return {"day":day,"number":str(number),"read":count,"notices":found}
def audit():
 items=parse_calendar()
 with ThreadPoolExecutor(max_workers=5) as pool:
  issues=list(pool.map(issue,items))
 nums=[int(x["number"]) for x in issues]
 if nums!=list(range(123,139)):
  invalid(f"BOIB: ediciones discontinuas dentro del calendario: {nums}")
 if sum(x["read"] for x in issues)<350:invalid("BOIB: volumen de avisos anormalmente bajo")
 candidates=[n["url"] for x in issues for n in x["notices"]]
 if not candidates:invalid("BOIB: no se identificaron convocatorias")
 with ThreadPoolExecutor(max_workers=6) as pool:
  list(pool.map(check_pdf,sorted(set(candidates))))
 print(f"BALEARES PDF VERIFICADOS: {len(set(candidates))} originales",flush=True)
 return publish_audit(SOURCE,PROVINCE,issues,today=END,min_issues=16)
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--output",type=Path,required=True)
 a=p.parse_args()
 write_output(a.output,audit())
