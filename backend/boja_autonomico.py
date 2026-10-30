#!/usr/bin/env python3
"""BOJA Andalucía: auditoría diaria de cada sección de los boletines de los últimos 30 días.

Las ediciones salen del calendario anual oficial («Boletines por fecha»,
/eboja/AAAA.html). Cada día enlaza a un boletín o, si hay varios, a la página
del día (/eboja/AAAAMMDD.html) con el ordinario, sus complementarios y los
extraordinarios. Se leen todos. Ventana: hoy-29 … hoy (con el calendario del
año anterior en enero). Falla si una edición, sección, emisor o PDF original no
se puede comprobar: nunca se publican datos parciales.
"""
from __future__ import annotations
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from clm_common import employment,numbering_ok,publish_audit,write_output,invalid
import argparse,re,requests,threading,time
SOURCE="https://www.juntadeandalucia.es/eboja/index.html"
HOST="www.juntadeandalucia.es"
PROVINCE="Andalucía (BOJA)"
WORKERS=3
MIN_ORDINARY=15          # diario de lunes a viernes: ~21 en 30 días, menos en Navidad/Semana Santa
MIN_READ_PER_ORDINARY=8  # media mínima de disposiciones por boletín ordinario (lo normal: 15-40)
EXTRA_BASE=500           # los extraordinarios usan la ruta /eboja/AAAA/5NN/ (n.º NN)
MONTHS={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,
        "agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
DATE=r"(\d{2}/\d{2}/\d{4})"
H1_ORD=re.compile(r"Bolet[ií]n n[uú]mero\s+(\d{1,3})\s+de\s+"+DATE,re.I)
H1_COMP=re.compile(r"Bolet[ií]n\s+(\d{1,3})\s+Complementario\s+n\S{0,2}\s*(\d{1,2})\s+de\s+"+DATE,re.I)
H1_EXTRA=re.compile(r"Bolet[ií]n Extraordinario n[uú]mero\s+(\d{1,3})\s+de\s+"+DATE,re.I)
CAL_ISSUE_RE=re.compile(r"^/eboja/(\d{4})/(\d{1,3})/index\.html$")
CAL_DAY_RE=re.compile(r"^/eboja/(\d{4})(\d{2})(\d{2})\.html$")
DAY_LINK_RE=re.compile(r"^/eboja/(\d{4})/(\d{1,3})/(?:c(\d{2})/)?$")
SECTION_RE=re.compile(r"^/eboja/(\d{4})/(\d{1,3})/(?:c(\d{2})/)?s(\d{2})(?:\.html)?$")
L=threading.local()
def session():
 if not hasattr(L,"client"):
  a=requests.Session();a.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"});L.client=a
 return L.client
def http(url,pdf=False):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=HOST or u.username or u.fragment or u.port not in (None,443):
  invalid("BOJA: URL fuera de sede oficial")
 last=None
 for attempt in range(3):   # reintentos moderados ante fallos de red, 429 o 5xx
  try:
   r=session().get(url,timeout=(10,38),allow_redirects=False,stream=pdf,
       headers={"Range":"bytes=0-128"} if pdf else {})
   if r.status_code==429 or r.status_code>=500:
    last=f"HTTP {r.status_code}";r.close();time.sleep(2+3*attempt);continue
   if r.status_code not in ((200,206) if pdf else (200,)):
    invalid(f"BOJA: error HTTP {r.status_code} en {url}")
   if pdf:
    b=b""
    for chunk in r.iter_content(140):
     b+=chunk
     if len(b)>=5:break
    r.close()
    if not b.startswith(b"%PDF-"):invalid(f"BOJA: PDF no auténtico {url}")
    return None
   if not 2000<len(r.content)<1500000:invalid(f"BOJA: página de tamaño inesperado {url}")
   return BeautifulSoup(r.content,"html.parser")
  except requests.RequestException as e:
   last=str(e)[:170];time.sleep(2+3*attempt)
 invalid(f"BOJA: sin acceso a {url} ({last})")

# --- Calendario -------------------------------------------------------------
def label(ed):
 kind,year,num,comp=ed
 return {"O":str(num),"C":f"{num}-C{comp}","E":f"E{num-EXTRA_BASE}"}[kind]
def calendar(year):
 """{fecha: url} del calendario anual oficial."""
 url=f"https://{HOST}/eboja/{year}.html"
 h=http(url)
 tables=h.select("table.calendario_tabla")
 if len(tables)!=12:invalid(f"BOJA: el calendario de {year} no tiene los 12 meses ({len(tables)})")
 days={}
 for t in tables:
  cap=t.select_one("caption");month=MONTHS.get(cap.get_text(strip=True).lower() if cap else "")
  if not month or str(year) not in t.get("summary",""):invalid(f"BOJA: mes ilegible en el calendario de {year}")
  for a in t.select("a[href]"):
   target=urljoin(url,a["href"]);p=urlsplit(target)
   try:day=date(year,month,int(a.get_text(strip=True)))
   except ValueError:invalid(f"BOJA: día imposible en el calendario de {year}")
   m=CAL_ISSUE_RE.fullmatch(p.path);d=CAL_DAY_RE.fullmatch(p.path)
   if p.hostname!=HOST or p.query or p.fragment or not (m or d):
    invalid(f"BOJA: enlace inesperado en el calendario {target}")
   if m and int(m[1])!=year:invalid(f"BOJA: {target} en el calendario de {year}")
   if d and date(int(d[1]),int(d[2]),int(d[3]))!=day:invalid(f"BOJA: {target} no es del {day}")
   if day in days:invalid(f"BOJA: día {day} repetido en el calendario")
   days[day]=target
 return days
def editions_of_day(day,url):
 """Ediciones (tipo, año, número de ruta, complementario) publicadas un día."""
 p=urlsplit(url)
 m=CAL_ISSUE_RE.fullmatch(p.path)
 if m:
  num=int(m[2])
  return [("E" if num>EXTRA_BASE else "O",day.year,num,None)]
 h=http(url)
 found=set()
 for a in h.select("a[href]"):
  target=urljoin(url,a["href"]);q=urlsplit(target)
  x=DAY_LINK_RE.fullmatch(q.path)
  if not x or q.hostname!=HOST or q.query or q.fragment:continue
  if int(x[1])!=day.year:invalid(f"BOJA: la página del {day} enlaza un boletín de {x[1]}")
  num=int(x[2])
  if x[3]:found.add(("C",day.year,num,int(x[3])))
  else:found.add(("E" if num>EXTRA_BASE else "O",day.year,num,None))
 if not found:invalid(f"BOJA: la página del {day} no enlaza ningún boletín")
 return sorted(found,key=lambda e:(e[0]!="O",e[2],e[3] or 0))

# --- Boletines ---------------------------------------------------------------
def header(html,ed):
 kind,year,num,comp=ed
 title=html.select_one("h1")
 text=" ".join(title.get_text(" ",strip=True).split()) if title else ""
 if kind=="O":
  m=H1_ORD.search(text);ok=m and int(m[1])==num and not H1_COMP.search(text)
 elif kind=="C":
  m=H1_COMP.search(text);ok=m and int(m[1])==num and int(m[2])==comp
 else:
  m=H1_EXTRA.search(text);ok=m and int(m[1])+EXTRA_BASE==num
 if not ok:invalid(f"BOJA {label(ed)}: falta el encabezado oficial ({text[-90:]})")
 day=datetime.strptime(m.groups()[-1],"%d/%m/%Y").date()
 if day.year!=year:invalid(f"BOJA {label(ed)}: boletín de otro año ({day})")
 return day
def pdf_pattern(ed):
 kind,year,num,comp=ed
 code=f"2{num:03d}{comp:02d}" if kind=="C" else f"{num:03d}"
 folder=f"/eboja/{year}/{num}/"+(f"c{comp:02d}/" if kind=="C" else "")
 return re.compile("^"+re.escape(folder)+f"(BOJA{year%100:02d}-{code}-[A-Za-z0-9-]+_([0-9]{{8}})\\.pdf)$")
def issue(job):
 ed,expected=job
 kind,year,num,comp=ed
 base=f"https://{HOST}/eboja/{year}/{num}/"+(f"c{comp:02d}/" if kind=="C" else "")
 index=http(base)
 day=header(index,ed)
 if day!=expected:invalid(f"BOJA {label(ed)}: fecha {day} distinta del calendario ({expected})")
 sections=set()
 for a in index.select("a[href]"):
  target=urljoin(base,a.get("href",""));u=urlsplit(target)
  m=SECTION_RE.fullmatch(u.path)
  if (m and int(m[1])==year and int(m[2])==num and (int(m[3]) if m[3] else None)==comp
      and u.hostname==HOST and not u.query and not u.fragment):
   sections.add(f"{base}s{m[4]}.html")
 if not 1<=len(sections)<=13:
  invalid(f"BOJA {label(ed)}: índice no permite verificar todas las secciones; encontradas {len(sections)}")
 pdf_re=pdf_pattern(ed)
 docs=[];seen=set()
 for page in sorted(sections):
  h=http(page)
  if header(h,ed)!=day:invalid(f"BOJA {label(ed)}: sección desfasada {page}")
  blocks=h.select("div.item.punteado_izquierda")
  if not blocks:invalid(f"BOJA {label(ed)}: sección vacía {page}")
  for block in blocks:
   pdfs=block.select("a.item_pdf_grupo[href]")
   if not 1<=len(pdfs)<=5:
    invalid(f"BOJA {label(ed)}: disposición sin PDF original verificable en {page}")
   files=[];cves=set()
   for pdf in pdfs:
    original=urljoin(page,pdf["href"]);parts=urlsplit(original);match=pdf_re.fullmatch(parts.path)
    if not match or parts.hostname!=HOST or parts.query or parts.fragment:
     invalid(f"BOJA {label(ed)}: PDF individual de otra edición: {original}")
    files.append(original);cves.add(match[2])
   if len(cves)!=1 or len(set(files))!=len(files):
    invalid(f"BOJA {label(ed)}: documentos en varias partes no coinciden en CVE")
   cv=cves.pop();url=files[0]
   if cv in seen:invalid(f"BOJA {label(ed)}: disposición repetida {cv}")
   seen.add(cv)
   title=block.get_text(" ",strip=True).split("PDF oficial auténtico")[0].strip()
   if not title or len(title)>2800:invalid(f"BOJA {label(ed)}: título incorrecto")
   agency_tag=block.find_previous(["h4","h5"])
   agency=(" ".join(agency_tag.get_text(" ",strip=True).split()) if agency_tag else "")
   if not 2<len(agency)<500 or "PDF" in agency:
    agency="Organismo anunciante: consultar disposición oficial (BOJA)"
   typ=employment(title)
   if typ:
    for original in files:http(original,pdf=True)
    docs.append({"id":f"BJ-{year}-{cv}","province":PROVINCE,
     "title":title,"entity":agency,"date":day.strftime("%d/%m/%Y"),
     "bulletin":label(ed),"type":typ,"url":url})
 if not seen:invalid(f"BOJA {label(ed)}: boletín sin disposiciones")
 print(f"BOJA {day} n.º {label(ed)}: {len(seen)} anuncios, {len(docs)} candidatas, {len(sections)} secciones",flush=True)
 return {"day":day,"number":label(ed),"read":len(seen),"notices":docs,"ed":ed}
def audit(today=None):
 end=today or date.today()
 start=end-timedelta(days=29)
 days={}
 for year in range(start.year,end.year+1):days.update(calendar(year))
 window=sorted((d,u) for d,u in days.items() if start<=d<=end)
 if not window:invalid(f"BOJA: el calendario no tiene boletines entre {start} y {end}")
 with ThreadPoolExecutor(max_workers=WORKERS) as pool:
  per_day=list(pool.map(lambda x:editions_of_day(*x),window))
 jobs=[(ed,d) for (d,_),eds in zip(window,per_day) for ed in eds]
 if len({ed for ed,_ in jobs})!=len(jobs):invalid("BOJA: boletín enlazado en dos días")
 with ThreadPoolExecutor(max_workers=WORKERS) as pool:
  issues=sorted(pool.map(issue,jobs),key=lambda x:(x["day"],x["ed"][0]!="O",x["ed"][2],x["ed"][3] or 0))
 ordinary=[(x["day"],x["ed"][2]) for x in issues if x["ed"][0]=="O"]
 extras=[(x["day"],x["ed"][2]-EXTRA_BASE) for x in issues if x["ed"][0]=="E"]
 if len({d for d,_ in ordinary})!=len(ordinary):invalid("BOJA: dos boletines ordinarios el mismo día")
 if not numbering_ok(ordinary):invalid(f"BOJA: falta algún boletín ordinario ({[n for _,n in ordinary]})")
 if extras and not numbering_ok(extras):invalid(f"BOJA: falta algún extraordinario ({extras})")
 if len(ordinary)<MIN_ORDINARY:invalid(f"BOJA: solo {len(ordinary)} boletines ordinarios en 30 días")
 parents={(n,d) for d,n in ordinary}
 comps={}
 for x in issues:
  kind,year,num,comp=x["ed"]
  if kind=="C":
   if (num,x["day"]) not in parents:invalid(f"BOJA: complementario {label(x['ed'])} sin su boletín del mismo día")
   comps.setdefault(num,[]).append(comp)
 for num,cs in comps.items():
  if sorted(cs)!=list(range(1,len(cs)+1)):invalid(f"BOJA: complementarios del {num} incompletos: {sorted(cs)}")
 if sum(x["read"] for x in issues)<MIN_READ_PER_ORDINARY*len(ordinary):
  invalid("BOJA: no están todos los anuncios")
 for x in issues:x.pop("ed")
 return publish_audit(SOURCE,PROVINCE,issues,today=end,min_issues=MIN_ORDINARY)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
 args=p.parse_args();write_output(args.output,audit())
