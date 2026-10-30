#!/usr/bin/env python3
"""BOIB (Illes Balears): auditoría diaria de los últimos 30 días, extraordinarios incluidos.

El BOIB es el diario común de la administración autonómica, consejos insulares,
ayuntamientos y organismos públicos de las Illes Balears. El calendario mensual
oficial muestra todas las ediciones (las extraordinarias con «*E»); cada sección
de cada edición lista sus edictos con el PDF original. Ventana: hoy-29 … hoy.
Si algo no cuadra, el lector falla: nunca se publican datos parciales.
"""
from __future__ import annotations
import argparse,re,threading,time,requests
from urllib.parse import urljoin,urlsplit
from datetime import date,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from clm_common import employment,numbering_ok,publish_audit,write_output
from provincial_common import ProvincialCoverageError
HOST="www.caib.es"
ROOT=f"https://{HOST}/eboibfront/es"
SOURCE=ROOT
PROVINCE="Illes Balears (BOIB)"
WORKERS=3
MIN_ISSUES=10        # 3 ediciones por semana (mar/jue/sáb) más extraordinarias; Navidad incluida
MIN_READ_PER_ISSUE=20 # media mínima de edictos por edición ordinaria (lo normal: 30-150)
MONTHS={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,
        "agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
ISSUE_RE=re.compile(r"^/eboibfront/es/(\d{4})/(\d{4,6})/?$")
SECTION_RE=re.compile(r"^/eboibfront/es/(\d{4})/(\d{4,6})/seccion-[a-z-]+/(\d{3})$")
NUM_RE=re.compile(r"BOIB\s+N[úu]m\.\s*(\d{1,3})\s*-\s*(\d{1,2})\s*/\s*([A-Za-zÁÉÍÓÚáéíóú]+)\s*/\s*(\d{4})",re.I)
REG_RE=re.compile(r"N[úu]mero de (?:registro|edicto)\s+(\d{1,8})",re.I)
PDF_OLD_RE=re.compile(r"^/eboibfront/pdf/es/(\d{4})/(\d{1,3})/(\d{5,9})$")
PDF_ELI_RE=re.compile(r"^/eboibfront/eli/[a-zA-Z0-9_()/.+-]+/dof/spa/pdf$")
# Notificaciones (edictos con datos personales): PDF oficial con clave opaca.
PDF_NOT_RE=re.compile(r"^/eboibfront/pdf/es/not/[A-Za-z0-9_=-]{16,120}$")
# Los edictos se numeran por año de registro (el contador vuelve a 1 a primeros
# de enero). En enero y febrero aún salen edictos registrados el año anterior,
# con números altos: el contador del año nuevo no llega a esta cifra hasta la
# primavera, y los del año anterior que se publican en enero ya la superan.
PREVIOUS_YEAR_EDICT_FROM=8000
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
def fetch(url,**kw):
 """GET con dos reintentos moderados ante errores de red, 429, 5xx o
 redirecciones esporádicas (el portal a veces responde 302 a un PDF que
 un instante después sirve con 200). Nunca se siguen redirecciones."""
 last=None
 for attempt in range(3):
  try:
   r=client().get(url,allow_redirects=False,**kw)
   if r.status_code<300 or 400<=r.status_code<500 and r.status_code!=429:return r
   last=f"HTTP {r.status_code}";r.close()
  except requests.RequestException as e:last=str(e)[:170]
  time.sleep(2+3*attempt)
 invalid(f"sin acceso a la sede oficial ({last}): {url}")
def html_page(url):
 check_url(url)
 r=fetch(url,timeout=(12,42))
 if (r.status_code!=200 or urlsplit(r.url).hostname!=HOST
     or not 9000<=len(r.content)<2500000):
  invalid(f"índice incompleto HTTP {r.status_code}: {url}")
 soup=BeautifulSoup(r.content,"html.parser")
 if not soup.select_one("h1") or "Boletín Oficial de las Illes Balears" not in soup.select_one("h1").get_text(" ",strip=True):
  invalid(f"no es BOIB oficial: {url}")
 return soup
def validate_pdf_url(url,number,day):
 u=check_url(url)
 match=PDF_OLD_RE.fullmatch(u.path)
 if match:
  # La ruta lleva el año del documento: en los primeros boletines del año
  # aparecen documentos del año anterior (p. ej. /pdf/es/2025/2/… en el BOIB 2/2026).
  years={day.year,day.year-1} if day.month<=2 else {day.year}
  if int(match[1]) not in years or int(match[2])!=number or u.query:
   invalid("PDF de otro boletín "+url)
  return
 if not (PDF_ELI_RE.fullmatch(u.path) or PDF_NOT_RE.fullmatch(u.path)) or u.query:
  invalid("versión PDF ELI no oficial "+url)
def check_pdf(url):
 r=fetch(url,timeout=(10,43),stream=True,headers={"Range":"bytes=0-127"})
 try:
  if (r.status_code not in (200,206) or
      "pdf" not in r.headers.get("Content-Type","").lower()):
   invalid(f"PDF no disponible / HTTP {r.status_code}: {url}")
  first=b""
  for piece in r.iter_content(130):
   first+=piece
   if len(first)>=5:break
 except requests.RequestException as e:invalid("error verificando PDF "+str(e)[:170])
 finally:r.close()
 if not first.startswith(b"%PDF-"):invalid("archivo no es PDF original "+url)
def months_between(start,end):
 y,m=start.year,start.month
 while (y,m)<=(end.year,end.month):
  yield y,m
  y,m=(y+1,1) if m==12 else (y,m+1)
def parse_month(year,month):
 """Ediciones del calendario oficial de un mes: {id: (fecha, extraordinaria)}."""
 url=f"{ROOT}/{year}/mes/{month-1}"   # el portal numera los meses desde 0
 html=html_page(url)
 result={}
 for a in html.select("a[href]"):
  u=urlsplit(urljoin(url,a.get("href","")))
  m=ISSUE_RE.fullmatch(u.path)
  text=a.get_text(" ",strip=True)
  if not m or u.query or not re.fullmatch(r"\d{1,2}(?:\*E)?",text):
   continue
  if int(m[1])!=year:invalid(f"el calendario de {month}/{year} enlaza una edición de {m[1]}")
  try:day=date(year,month,int(text.split("*")[0]))
  except ValueError:invalid(f"día inexistente en el calendario de {month}/{year}: {text}")
  uid=int(m[2])
  if uid in result:invalid(f"calendario contiene edición duplicada {uid}")
  result[uid]=(day,text.endswith("*E"))
 return result
def parse_calendar(start,end):
 items={}
 for y,m in months_between(start,end):
  month=parse_month(y,m)
  if not month:invalid(f"calendario de {m}/{y} sin ediciones")
  for uid,value in month.items():
   if uid in items:invalid(f"edición {uid} repetida en dos meses")
   items[uid]=value
 inside={uid:(d,e) for uid,(d,e) in items.items() if start<=d<=end}
 if not inside:invalid(f"el calendario no tiene ediciones entre {start} y {end}")
 return sorted(inside.items(),key=lambda x:(x[1][0],x[0]))
def edict_year(day,entry):
 return day.year-1 if day.month<=2 and entry>=PREVIOUS_YEAR_EDICT_FROM else day.year
def issue(item):
 uid,(day,extra)=item
 indexurl=f"{ROOT}/{day.year}/{uid}/"
 h=html_page(indexurl)
 title=h.title.get_text(" ",strip=True) if h.title else ""
 m=NUM_RE.search(title)
 if not m or m[3].lower() not in MONTHS:invalid(f"número/fecha de BOIB ausente en {uid}: {title[:150]}")
 number=int(m[1])
 try:official=date(int(m[4]),MONTHS[m[3].lower()],int(m[2]))
 except ValueError:invalid(f"fecha imposible en el BOIB {uid}: {title[:150]}")
 if official!=day:
  invalid(f"fecha del calendario ({day}) y del BOIB {number} ({official}) no coinciden")
 intro=h.get_text(" ",strip=True)[:650]
 if ("Extraordinario" in intro)!=extra:
  invalid(f"estado de edición extraordinaria no coincide, BOIB {number}")
 sections={}
 for a in h.select('a[href*="/seccion-"]'):
  target=urljoin(indexurl,a.get("href",""));p=urlsplit(target)
  match=SECTION_RE.fullmatch(p.path)
  if (not match or int(match[1])!=day.year or int(match[2])!=uid or p.hostname!=HOST
      or p.query or p.fragment):
   continue
  sections[match[3]]=target
 if not 1<=len(sections)<=5:
  invalid(f"BOIB {number}: índice sin listado completo de secciones: {sections}")
 count=0;found=[];seen=set()
 for code,path in sorted(sections.items()):
  page=html_page(path)
  ptitle=page.title.get_text(" ",strip=True) if page.title else ""
  pm=NUM_RE.search(ptitle)
  if not pm or int(pm[1])!=number or int(pm[4])!=day.year:
   invalid(f"BOIB {number}: página de sección ajena {path}")
  listed=page.select("ul.resolucions > li")
  records=[x for x in listed if x.select_one("p.registre")]
  pdf_count=len(page.select('a[aria-label="Exportar a PDF"]'))
  if not records or len(records)!=pdf_count:
   invalid(f"BOIB {number}: sección {code} contiene {len(records)} registros y {pdf_count} PDF oficiales")
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
   key=(edict_year(day,entry),entry)
   if key in seen:
    invalid(f"BOIB {number}: número edicto duplicado {entry}")
   seen.add(key);count+=1
   target=urljoin(path,pdfs[0]["href"])
   validate_pdf_url(target,number,day)
   kind=employment(title)
   if kind:
    found.append({"id":f"IB-{key[0]}-{entry}","province":PROVINCE,
       "title":title,"entity":label,"date":day.strftime("%d/%m/%Y"),
       "bulletin":str(number),"type":kind,"url":target})
 print(f"BALEARES BOIB {day} n.º {number} {'EXTRA' if extra else 'ordinario'}: {count} anuncios, {len(found)} candidatas, {len(sections)} secciones",flush=True)
 if count<1:invalid(f"BOIB {number}: boletín vacío")
 return {"day":day,"number":str(number),"read":count,"notices":found,"extra":extra}
def audit(today=None):
 end=today or date.today()
 start=end-timedelta(days=29)
 items=parse_calendar(start,end)
 with ThreadPoolExecutor(max_workers=WORKERS) as pool:
  issues=list(pool.map(issue,items))
 issues.sort(key=lambda x:(x["day"],int(x["number"])))
 # Ordinarias y extraordinarias comparten numeración; en enero vuelve a 1.
 seq=[(x["day"],int(x["number"])) for x in issues]
 if not numbering_ok(seq):
  invalid(f"BOIB: ediciones discontinuas dentro del calendario: {[n for _,n in seq]}")
 ordinary=sum(not x["extra"] for x in issues)
 if ordinary<MIN_ISSUES:
  invalid(f"BOIB: solo {ordinary} ediciones ordinarias en 30 días")
 if sum(x["read"] for x in issues)<MIN_READ_PER_ISSUE*ordinary:
  invalid("BOIB: volumen de avisos anormalmente bajo")
 candidates=[n["url"] for x in issues for n in x["notices"]]
 if not candidates:invalid("BOIB: no se identificaron convocatorias")
 with ThreadPoolExecutor(max_workers=WORKERS) as pool:
  list(pool.map(check_pdf,sorted(set(candidates))))
 print(f"BALEARES PDF VERIFICADOS: {len(set(candidates))} originales",flush=True)
 for x in issues:x.pop("extra")
 return publish_audit(SOURCE,PROVINCE,issues,today=end,min_issues=MIN_ISSUES)
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--output",type=Path,required=True)
 a=p.parse_args()
 write_output(a.output,audit())
