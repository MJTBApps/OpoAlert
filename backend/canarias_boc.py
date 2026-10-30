#!/usr/bin/env python3
"""Boletín Oficial de Canarias (BOC): audit of the last 30 days, any day.

The official archive (https://www.gobiernodecanarias.org/boc/archivo/) lists
one page per year with EVERY issue (ordinary and extraordinary) and its date.
Numbering restarts at 1 every January, so each yearly list must be complete
(1..N, dates in order). Each issue summary lists every provision with its own
signed PDF in the official sede; candidate PDFs are checked to be real PDFs.
Fail closed: any inconsistency raises and nothing is published.
"""
from __future__ import annotations
import argparse,re,requests,threading,time
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urlsplit,urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from clm_common import employment,publish_audit,write_output,numbering_ok
from provincial_common import ProvincialCoverageError
SOURCE="https://www.gobiernodecanarias.org/boc/archivo/"
PROVINCE="Canarias (BOC)"
HOST="www.gobiernodecanarias.org"
SEDE="sede.gobiernodecanarias.org"
MONTHS={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,
        "agosto":8,"septiembre":9,"setiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
MONTH_NAME={v:k for k,v in MONTHS.items() if k!="setiembre"}
YEAR_LINK_RE=re.compile(r"^/boc/archivo/(\d{4})/?$")
ARCHIVE_RE=re.compile(r"^/boc/(\d{4})/(\d{3})/index\.html$")
PDF_RE=re.compile(r"^/boc/boc-a-(\d{4})-(\d{3})-(\d{1,8})\.pdf$")
HEAD_RE=re.compile(r"BOC(?:\s+EXTRAORDINARIO)?\s*N[º°.]?\s*(\d+)\s*[-.]\s*(\d{1,2})\s+de\s+([a-zé]+)\s+de\s+(\d{4})",re.I)
WORKERS=3          # respeto al portal: como mucho 3 conexiones a la vez
MIN_ISSUES=15      # ~21 en 30 días laborables; Navidad y festivos dejan unas 18-19
SESS=threading.local()
def invalid(msg):raise ProvincialCoverageError("Canarias BOC: "+str(msg))
def client():
 if not hasattr(SESS,"s"):
  a=requests.Session()
  a.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
  SESS.s=a
 return SESS.s
def fetch(url,pdf=False,retries=3):
 u=urlsplit(url)
 hosts={HOST,SEDE} if pdf else {HOST}
 if (u.scheme!="https" or u.hostname not in hosts or u.port not in (None,443)
     or u.username or u.password or u.fragment):
  invalid("enlace fuera de la sede oficial "+url[:135])
 error=None
 for attempt in range(retries):
  try:
   r=client().get(url,stream=pdf,timeout=(10,40),allow_redirects=False,
                 headers={"Range":"bytes=0-140"} if pdf else {})
   if r.status_code>=500 or r.status_code==429:
    error=f"HTTP {r.status_code}: {url}";r.close();time.sleep(2*(attempt+1));continue
   if r.status_code not in ((200,206) if pdf else (200,)):
    invalid(f"HTTP {r.status_code}: {url}")
   if pdf:
    if "pdf" not in r.headers.get("Content-Type","").lower():
     invalid("documento oficial no es PDF "+url)
    p=b""
    for piece in r.iter_content(145):
     p+=piece
     if len(p)>=5:break
    r.close()
    if not p.startswith(b"%PDF-"):invalid("no se puede autenticar PDF "+url)
    return None
   if not 2500<len(r.content)<1_900_000:invalid("sumario oficial incompleto "+url)
   return BeautifulSoup(r.content,"html.parser")
  except requests.RequestException as e:
   error="acceso fallido "+str(e)[:180];time.sleep(2*(attempt+1))
 invalid(error)
def year_issues(year):
 """Every issue of one year from its official archive page: {number: date}."""
 url=urljoin(SOURCE,f"{year}/")
 h=fetch(url)
 d={}
 for a in h.select("a[href]"):
  u=urlsplit(urljoin(url,a.get("href","")))
  m=ARCHIVE_RE.fullmatch(u.path)
  if not m or u.hostname!=HOST or u.query or u.fragment:continue
  if int(m[1])!=year:invalid(f"archivo {year} enlaza un boletín de otro año: {u.path}")
  n=int(m[2])
  label=" ".join(a.get_text(" ",strip=True).split())
  x=HEAD_RE.search(label)
  if not x or int(x[1])!=n or int(x[4])!=year or x[3].lower() not in MONTHS:
   invalid("boletín no corresponde a fecha oficial "+label[:130])
  try:day=date(year,MONTHS[x[3].lower()],int(x[2]))
  except ValueError:invalid("fecha imposible "+label[:120])
  if n in d and d[n]!=day:invalid(f"boletín {year}/{n} con dos fechas")
  d[n]=day
 if not d:invalid(f"archivo {year} sin boletines")
 if sorted(d)!=list(range(1,max(d)+1)):
  missing=sorted(set(range(1,max(d)+1))-set(d))
  invalid(f"archivo {year} con huecos en la numeración: faltan {missing[:20]}")
 days=[d[n] for n in sorted(d)]
 if days!=sorted(days):invalid(f"archivo {year}: números y fechas desordenados")
 return d
def calendar(start,end):
 root=fetch(SOURCE)
 years=set()
 for a in root.select("a[href]"):
  u=urlsplit(urljoin(SOURCE,a.get("href","")))
  m=YEAR_LINK_RE.fullmatch(u.path)
  if m and u.hostname==HOST and not u.query:years.add(int(m[1]))
 rows=[]
 for year in range(start.year,end.year+1):
  if year not in years:invalid(f"el archivo oficial no ofrece el año {year}")
  d=year_issues(year)
  if year<end.year and max(d.values())<date(year,12,27):
   invalid(f"archivo {year} sin los boletines de final de diciembre (último {max(d.values())})")
  rows+=[(day,n) for n,day in d.items() if start<=day<=end]
 rows.sort()
 if not numbering_ok([(day,n) for day,n in rows]):
  invalid("numeración no consecutiva en la ventana: "+str([n for _,n in rows]))
 print(f"BOC CALENDARIO COMPLETO {start}–{end}: {len(rows)} ediciones "
       f"(n.º {rows[0][1] if rows else '-'}–{rows[-1][1] if rows else '-'})",flush=True)
 return [(n,day) for day,n in rows]
def issue(row):
 number,day=row
 url=f"https://{HOST}/boc/{day.year}/{number:03}/index.html"
 h=fetch(url)
 title=h.select_one("h2")
 header=" ".join(title.get_text(" ",strip=True).split()) if title else ""
 if (not re.search(r"\bN[º°.]?\s*"+str(number)+r"\b",header)
     or f"{day.day} de {MONTH_NAME[day.month]} de {day.year}" not in header.lower()):
  invalid(f"BOC {number}: cabecera de fecha incorrecta {header[:180]}")
 rows=h.select("li.justificado_boc")
 if not 1<=len(rows)<=300:invalid(f"BOC {number}: número de disposiciones no verosímil {len(rows)}")
 seen=set();notice=[]
 for item in rows:
  anchors=item.select("a[href]")
  docs={}
  for a in anchors:
   target=urljoin(url,a["href"]);u=urlsplit(target)
   m=PDF_RE.fullmatch(u.path)
   if m:
    if (int(m[1])!=day.year or int(m[2])!=number or u.hostname!=SEDE or u.query or u.fragment):
     invalid("PDF de disposición fuera de boletín "+target)
    docs[target]=int(m[3])
  if len(docs)!=1:invalid(f"BOC {number}: disposición sin PDF original único")
  link,article=next(iter(docs.items()))
  if article in seen:invalid(f"BOC {number}: disposición repetida {article}")
  seen.add(article)
  text_links=[a.get_text(" ",strip=True) for a in anchors
              if urljoin(url,a["href"])==link and a.get_text(" ",strip=True) and not a.get_text(" ",strip=True).isdigit()
              and len(a.get_text(" ",strip=True))>25]
  if not text_links:invalid(f"BOC {number}: título no publicado {article}")
  article_title=" ".join(text_links[0].split())
  if not 15<len(article_title)<=2800:invalid("título BOC no válido")
  # Organismo emisor: el encabezado más cercano con texto (h5 = organismo;
  # algunos sumarios llevan un h4 de sección vacío antes del primer h5).
  entity=""
  for heading in item.find_all_previous(["h5","h4","h3"],limit=6):
   entity=" ".join(heading.get_text(" ",strip=True).split())
   if entity:break
  if not 2<len(entity)<450:invalid("BOC sin encabezado emisor "+str(article))
  kind=employment(article_title)
  if kind:
   notice.append({"id":f"IC-{day.year}-{article}","province":PROVINCE,
    "title":article_title,"entity":entity,"date":day.strftime("%d/%m/%Y"),
    "bulletin":str(number),"type":kind,"url":link})
 print(f"CANARIAS BOC {day} n.º {number}: {len(rows)} anuncios, {len(notice)} candidatas",flush=True)
 return {"day":day,"number":str(number),"read":len(rows),"notices":notice}
def audit(today=None):
 end=today or date.today()
 start=end-timedelta(days=29)
 rows=calendar(start,end)
 if len(rows)<MIN_ISSUES:invalid(f"solo {len(rows)} boletines en 30 días")
 with ThreadPoolExecutor(max_workers=WORKERS) as pool:
  issues=list(pool.map(issue,rows))
 if sum(x["read"] for x in issues)<6*len(issues):invalid("BOC: sumarios incompletos")
 urls=sorted({n["url"] for issue in issues for n in issue["notices"]})
 if len(urls)<5:invalid(f"BOC: solo {len(urls)} candidatas validables")
 with ThreadPoolExecutor(max_workers=WORKERS) as p:list(p.map(lambda u:fetch(u,pdf=True),urls))
 print(f"BOC PDF OFICIALES FIRMADOS VERIFICADOS: {len(urls)}",flush=True)
 return publish_audit(SOURCE,PROVINCE,issues,today=end,min_issues=MIN_ISSUES)
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--output",type=Path,required=True)
 args=a.parse_args();write_output(args.output,audit())
