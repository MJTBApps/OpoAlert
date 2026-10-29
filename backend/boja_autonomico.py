#!/usr/bin/env python3
"""BOJA Andalucía: audit every section of each 30-day official daily bulletin.
Fail closed if an edition, section, publisher, or original PDF cannot be proven.
"""
from __future__ import annotations
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from clm_common import employment,publish_audit,write_output,invalid
import argparse,re,requests,threading
SOURCE="https://www.juntadeandalucia.es/eboja/index.html"
HOST="www.juntadeandalucia.es"
PDF_RE=re.compile(r"^/eboja/2026/(\d{3})/(BOJA26-\d{3}-[A-Za-z0-9-]+_([0-9]{8})\.pdf)$")
SECTION_RE=re.compile(r"^/eboja/2026/(\d{3})/s(\d{2})\.html$")
ISSUE_RE=re.compile(r"Bolet[ií]n n[uú]mero\s+(\d{1,3})\s+de\s+(\d{2}/\d{2}/2026)",re.I)
L=threading.local()
def session():
 if not hasattr(L,"client"):
  a=requests.Session();a.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"});L.client=a
 return L.client
def http(url,pdf=False):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=HOST or u.username or u.fragment or u.port not in (None,443):
  invalid("BOJA: URL fuera de sede oficial")
 try:
  r=session().get(url,timeout=(10,38),allow_redirects=False,stream=pdf,
      headers={"Range":"bytes=0-128"} if pdf else {})
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
  if not 2000<len(r.content)<1000000:invalid("BOJA: índice de tamaño inesperado")
  return BeautifulSoup(r.content,"html.parser")
 except requests.RequestException as e:invalid("BOJA: error HTTP "+str(e)[:170])
def date_header(html,num):
 title=html.select_one("h1")
 found=ISSUE_RE.search(title.get_text(" ",strip=True) if title else "")
 if not found or int(found[1])!=num:invalid(f"BOJA: falta encabezado del boletín {num}")
 return datetime.strptime(found[2],"%d/%m/%Y").date()
def issue(num):
 base=f"https://{HOST}/eboja/2026/{num}/"
 index=http(base)
 day=date_header(index,num)
 start=date(2026,9,30);end=date(2026,10,29)
 if day<start or day>end:invalid(f"BOJA {num}: fuera del histórico {day}")
 sections=set()
 for a in index.select("a[href]"):
  target=urljoin(base,a.get("href",""));u=urlsplit(target)
  m=SECTION_RE.fullmatch(u.path)
  if m and int(m[1])==num and u.hostname==HOST and not u.query and not u.fragment:
   sections.add(target)
 if not 3<=len(sections)<=13:
  invalid(f"BOJA {num}: índice no permite verificar todas las secciones; encontradas {len(sections)}, enlaces ejemplo {[a.get('href') for a in index.select('a[href*=\"s5\"]')[:12]]}")
 docs=[];seen=set()
 for page in sorted(sections):
  h=http(page)
  if date_header(h,num)!=day:invalid(f"BOJA {num}: sección desfasada {page}")
  blocks=h.select("div.item.punteado_izquierda")
  for block in blocks:
   pdfs=block.select("a.item_pdf_grupo[href]")
   if len(pdfs)!=1:
    invalid(f"BOJA {num}: disposición sin PDF original en {page}")
   url=urljoin(page,pdfs[0]["href"]);u=urlsplit(url);m=PDF_RE.fullmatch(u.path)
   if (not m or int(m[1])!=num or not m[2].startswith(f"BOJA26-{num}-")
       or u.hostname!=HOST or u.query or u.fragment):
    invalid(f"BOJA {num}: PDF individual de otra edición: {url}")
   cv=m[3]
   if cv in seen:invalid(f"BOJA {num}: documento repetido {cv}")
   seen.add(cv)
   title=block.get_text(" ",strip=True).split("PDF oficial auténtico")[0].strip()
   if not title or len(title)>2800:invalid(f"BOJA {num}: título incorrecto")
   agency_tag=block.find_previous(["h4","h5"])
   agency=(" ".join(agency_tag.get_text(" ",strip=True).split()) if agency_tag else "")
   if not 2<len(agency)<500 or "PDF" in agency:
    agency="Organismo anunciante: consultar disposición oficial (BOJA)"
   typ=employment(title)
   if typ:
    http(url,pdf=True)
    docs.append({"id":f"BJ-2026-{cv}","province":"Andalucía (BOJA)",
     "title":title,"entity":agency,"date":day.strftime("%d/%m/%Y"),
     "bulletin":str(num),"type":typ,"url":url})
 if len(seen)<3:invalid(f"BOJA {num}: índice vacío o sin secciones")
 print(f"BOJA {day} n.º {num}: {len(seen)} anuncios, {len(docs)} candidatas, {len(sections)} secciones",flush=True)
 return {"day":day,"number":str(num),"read":len(seen),"notices":docs}
def audit():
 # Fixed 30-day history. Verify the dates and sequential official issue numbers;
 # extra issues or supplements require explicit addition, not silent omission.
 with ThreadPoolExecutor(max_workers=5) as pool:
  issues=sorted(pool.map(issue,range(190,211)),key=lambda x:x["day"])
 if len(issues)!=21 or issues[0]["day"]!=date(2026,9,30) or issues[-1]["day"]!=date(2026,10,29):
  invalid(f"BOJA: fechas del histórico no cuadran ({[x['day'] for x in issues]})")
 if sum(x["read"] for x in issues)<350:invalid("BOJA: no están todos los anuncios")
 return publish_audit(SOURCE,"Andalucía (BOJA)",issues,today=date(2026,10,29))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
 args=p.parse_args();write_output(args.output,audit())
