#!/usr/bin/env python3
"""Official BOC Canary Islands autonomous journal: full 30-day issue and signed PDF audit."""
from __future__ import annotations
import argparse,re,requests,threading
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit,urljoin
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from clm_common import employment,publish_audit,write_output
from provincial_common import ProvincialCoverageError,fold
SOURCE="https://www.gobiernodecanarias.org/boc/archivo/2026/"
PROVINCE="Canarias (BOC)"
START=date(2026,9,30);END=date(2026,10,29)
ARCHIVE_RE=re.compile(r"^/boc/2026/(\d{3})/index\.html$")
PDF_RE=re.compile(r"^/boc/boc-a-2026-(\d{3})-(\d{1,8})\.pdf$")
HEAD_RE=re.compile(r"BOC(?:\s+EXTRAORDINARIO)?\s*N[º°.]?\s*(\d+)\s*[-.]\s*(\d{1,2})\s+de\s+(septiembre|octubre)\s+de\s+2026",re.I)
SESS=threading.local()
def invalid(msg):raise ProvincialCoverageError("Canarias BOC: "+str(msg))
def client():
 if not hasattr(SESS,"s"):
  a=requests.Session()
  a.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
  SESS.s=a
 return SESS.s
def fetch(url,pdf=False):
 u=urlsplit(url)
 hosts={"www.gobiernodecanarias.org","sede.gobiernodecanarias.org"} if pdf else {"www.gobiernodecanarias.org"}
 if (u.scheme!="https" or u.hostname not in hosts or u.port not in (None,443)
     or u.username or u.password or u.fragment):
  invalid("enlace fuera de la sede oficial "+url[:135])
 try:
  r=client().get(url,stream=pdf,timeout=(10,38),allow_redirects=False,
                headers={"Range":"bytes=0-140"} if pdf else {})
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
 except requests.RequestException as e:invalid("acceso fallido "+str(e)[:180])
def calendar():
 h=fetch(SOURCE)
 d={}
 for a in h.select("a[href]"):
  u=urlsplit(urljoin(SOURCE,a.get("href","")))
  m=ARCHIVE_RE.fullmatch(u.path)
  if not m or u.hostname!="www.gobiernodecanarias.org" or u.query or u.fragment:continue
  n=int(m[1])
  if not 196<=n<=217:continue
  label=" ".join(a.get_text(" ",strip=True).split())
  x=HEAD_RE.search(label)
  if not x or int(x[1])!=n:invalid("boletín no corresponde a fecha oficial "+label[:130])
  month=9 if x[3].lower()=="septiembre" else 10
  try:day=date(2026,month,int(x[2]))
  except Exception:invalid("fecha imposible "+label[:120])
  if not START<=day<=END or n in d:invalid("edición fuera del histórico o duplicada")
  d[n]=day
 if sorted(d)!=list(range(196,218)):
  invalid("BOC: faltan uno o varios boletines del intervalo: "+str(sorted(d)))
 if d[196]!=START or d[217]!=END or d[212]!=date(2026,10,22):
  invalid("BOC: boletín inicial, último o extraordinario con fecha incorrecta")
 print(f"BOC CALENDARIO COMPLETO: {len(d)} ediciones (#196–217, incluido el extraordinario #212)",flush=True)
 return sorted(d.items())
def issue(row):
 number,day=row
 url=f"https://www.gobiernodecanarias.org/boc/2026/{number:03}/index.html"
 h=fetch(url)
 title=h.select_one("h2")
 header=" ".join(title.get_text(" ",strip=True).split()) if title else ""
 if (not re.search(r"\bN[º°.]?\s*"+str(number)+r"\b",header)
     or f"{day.day} de {'septiembre' if day.month==9 else 'octubre'} de 2026" not in header.lower()):
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
    if (int(m[1])!=number or u.hostname!="sede.gobiernodecanarias.org" or u.query or u.fragment):
     invalid("PDF de disposición fuera de boletín "+target)
    docs[target]=int(m[2])
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
  heading=item.find_previous(["h4","h3"])
  entity=" ".join(heading.get_text(" ",strip=True).split()) if heading else ""
  if not 2<len(entity)<450:invalid("BOC sin encabezado emisor "+str(article))
  kind=employment(article_title)
  if kind:
   notice.append({"id":f"IC-2026-{article}","province":PROVINCE,
    "title":article_title,"entity":entity,"date":day.strftime("%d/%m/%Y"),
    "bulletin":str(number),"type":kind,"url":link})
 print(f"CANARIAS BOC {day} n.º {number}: {len(rows)} anuncios, {len(notice)} candidatas",flush=True)
 return {"day":day,"number":str(number),"read":len(rows),"notices":notice}
def audit():
 with ThreadPoolExecutor(max_workers=5) as pool:
  issues=list(pool.map(issue,calendar()))
 if sum(x["read"] for x in issues)<250:invalid("BOC: sumarios incompletos")
 urls=sorted({n["url"] for issue in issues for n in issue["notices"]})
 if len(urls)<20:invalid("BOC: ninguna candidata validable")
 with ThreadPoolExecutor(max_workers=6) as p:list(p.map(lambda u:fetch(u,pdf=True),urls))
 print(f"BOC PDF OFICIALES FIRMADOS VERIFICADOS: {len(urls)}",flush=True)
 return publish_audit(SOURCE,PROVINCE,issues,today=END,min_issues=22)
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--output",type=Path,required=True)
 args=a.parse_args();write_output(args.output,audit())
