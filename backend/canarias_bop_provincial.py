#!/usr/bin/env python3
"""Both Canary provincial official BOP journals — 13 regular issues in 30 days.

Original province websites publish the article titles and institutions in a
complete HTML abstract (sumario) and one signed/scanned PDF for each edition.
We validate the PDF of EVERY edition before extracting articles; notices link
to that ORIGINAL whole-issue PDF rather than inventing individual PDF URLs.
"""
from __future__ import annotations
import argparse,re,requests,threading
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit,urljoin,parse_qs
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from clm_common import employment,publish_audit,write_output
from provincial_common import ProvincialCoverageError
CONFIG={
 "lp":("www.boplaspalmas.net","nbop2","Las Palmas (BOP)","LP"),
 "tf":("www.bopsantacruzdetenerife.es","bopsc2","Santa Cruz de Tenerife (BOP)","TF")
}
START=date(2026,9,30);END=date(2026,10,29)
EXPECTED_DAYS=[date(2026,9,30)]+[date(2026,10,d) for d in (2,5,7,9,12,14,16,19,21,23,26,28)]
HEADING_RE=re.compile(r"SUMARIO\s+DEL\s+BOLET[IÍ]N\s+N[º°]\s*(\d+)\s*,\s*DE\s+FECHA\s*(\d{1,2})-(\d{1,2})-(26|2026)",re.I)
PDF_RE=re.compile(r"^/boletines/2026/(\d{1,2})-(\d{1,2})-26/(\d{1,2})-(\d{1,2})-26\.pdf$")
C=threading.local()
def invalid(msg):raise ProvincialCoverageError("BOP Canarias: "+str(msg))
def client():
 if not hasattr(C,"s"):
  s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
  C.s=s
 return C.s
def fetch(url,host,pdf=False):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=host or u.port not in (None,443) or u.username or u.fragment:
  invalid("URL fuera del boletín oficial "+url[:180])
 try:
  r=client().get(url,timeout=(10,40),stream=pdf,allow_redirects=False,
       headers={"Range":"bytes=0-130"} if pdf else {})
  if r.status_code not in ((200,206) if pdf else (200,)):
   invalid(f"HTTP {r.status_code}, sin original {url}")
  if pdf:
   if "pdf" not in r.headers.get("Content-Type","").lower():
    invalid("documento no es PDF: "+url)
   hdr=b""
   for chunk in r.iter_content(150):
    hdr+=chunk
    if len(hdr)>=5:break
   r.close()
   if not hdr.startswith(b"%PDF-"):invalid("PDF original inválido "+url)
   return None
  if not 3000<len(r.content)<1200000:invalid("sumario/tramitación oficial incompleta "+url)
  h=BeautifulSoup(r.content,"html.parser",from_encoding="utf-8")
  return h
 except requests.RequestException as e:invalid("sin acceso oficial "+str(e)[:160])
def archive(host,path):
 url=f"https://{host}/{path}/main1.php"
 h=fetch(url,host)
 result={}
 for a in h.select('a[href]'):
  u=urlsplit(urljoin(url,a.get("href","")))
  if u.hostname!=host or u.path!=f"/{path}/sumario.php" or u.fragment:continue
  query=parse_qs(u.query)
  if query.get("codigopub")!=["1"] or len(query.get("fecha_mas_reciente",[]))!=1:
   continue
  try:day=date.fromisoformat(query["fecha_mas_reciente"][0])
  except Exception:invalid("fecha de calendario oficial mal formada")
  if START<=day<=END:
   if day in result:invalid("dos ediciones con misma fecha en el calendario: "+str(day))
   if a.get_text(" ",strip=True)!=str(day.day):
    invalid("fecha del calendario inconsistente")
   result[day]=urljoin(url,a["href"])
 if host=="www.bopsantacruzdetenerife.es":
  # The Tenerife "latest" calendar only links Wednesday/Friday numbers.
  # Its Monday issues are nevertheless publicly accessible through its
  # own official sumario.php; demand that every reconstructed issue match
  # the independently known contiguous number #117-129 and own PDF.
  expected_visible=[d for d in EXPECTED_DAYS if d.weekday()!=0]
  if sorted(result)!=expected_visible:
   invalid(f"calendario parcial Tenerife incoherente: {[str(x) for x in sorted(result)]}")
  missing=[d for d in EXPECTED_DAYS if d not in result]
  for day in missing:
   result[day]=f"https://{host}/{path}/sumario.php?codigopub=1&fecha_mas_reciente={day.isoformat()}"
  print(f"CALENDARIO TENERIFE: {len(expected_visible)} enlaces visibles y {len(missing)} boletines de lunes recuperables por consulta oficial",flush=True)
 elif sorted(result)!=EXPECTED_DAYS:
  invalid(f"calendario oficial {host} incompleto: {[str(x) for x in sorted(result)]}")
 print(f"CALENDARIO {host}: {len(result)} ediciones (30/09 a 28/10; 29/10 sin publicación)",flush=True)
 return sorted(result.items())
def parse_day(info,config):
 (day,page), (host,path,province,code)=info,config
 h=fetch(page,host)
 display=" ".join(h.get_text(" ",strip=True).split())
 m=HEADING_RE.search(display)
 if not m:
  invalid(f"{province}: sin número de boletín {day} (posible día no publicado)")
 n=int(m[1]);shown=date(2026,int(m[3]),int(m[2]))
 if n!=117+EXPECTED_DAYS.index(day) or shown!=day:
  invalid(f"{province}: número/fecha incorrectos {day}: n.º {n}, fecha {shown}")
 urls={urljoin(page,a["href"]) for a in h.select('a[href]') if "Descargar Bolet" in a.get_text(" ",strip=True)}
 if len(urls)!=1:
  invalid(f"{province}: el sumario carece de único PDF original {day}: {urls}")
 pdf=next(iter(urls));u=urlsplit(pdf)
 m=PDF_RE.fullmatch(u.path)
 if (not m or u.hostname!=host or u.query or u.fragment or
     (int(m[1]),int(m[2]),int(m[3]),int(m[4]))!=(day.day,day.month,day.day,day.month)):
  invalid(f"{province}: PDF externo o desfasado {pdf}")
 fetch(pdf,host,pdf=True)
 boxes=[td for td in h.select("td") if td.select_one("b i")]
 if not 1<=len(boxes)<=7:invalid(f"{province}: tabla de avisos ausente {day}")
 candidates=[];read=0
 for td in boxes:
  agency_names={" ".join(a.get_text(" ",strip=True).split()) for a in td.select("b i")}
  lines=[" ".join(x.split()) for x in td.get_text("\n",strip=True).splitlines() if x.strip()]
  current=None
  for line in lines:
   if line in agency_names:
    current=line;continue
   if line.startswith("- "):
    title=line[2:].strip()
    if not current or not 10<len(title)<2800 or len(current)<4:
     invalid(f"{province}: anuncio sin emisor/título {day}: {title[:150]}")
    read+=1
    kind=employment(title)
    if kind:
     candidates.append({"id":f"{code}-2026{day:%m%d}-{read:03}",
       "province":province,"title":title,"entity":current,
       "date":day.strftime("%d/%m/%Y"),"bulletin":str(n),"type":kind,"url":pdf})
 if read<5:invalid(f"{province}: boletín sin contenidos suficientes {day} ({read})")
 print(f"{province} {day} n.º {n}: {read} anuncios, {len(candidates)} candidatas; PDF oficial verificado",flush=True)
 return {"day":day,"number":str(n),"read":read,"notices":candidates}
def audit(which):
 if which not in CONFIG:invalid("provincia no autorizada")
 config=CONFIG[which];host,path,province,code=config
 records=archive(host,path)
 with ThreadPoolExecutor(max_workers=5) as pool:
  issues=list(pool.map(lambda item:parse_day(item,config),records))
 if [int(x["number"]) for x in issues]!=list(range(117,130)):
  invalid(f"faltan ediciones provinciales: {issues}")
 if sum(x["read"] for x in issues)<150:invalid("recuento oficial demasiado bajo")
 return publish_audit(f"https://{host}/{path}/main1.php",province,issues,
                      today=END,min_issues=13)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--province",choices=["lp","tf"],required=True)
 p.add_argument("--output",type=Path,required=True)
 x=p.parse_args();write_output(x.output,audit(x.province))
