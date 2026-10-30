#!/usr/bin/env python3
"""Both Canary provincial official BOP journals (Las Palmas, Santa Cruz de Tenerife).

Audit of the last 30 days, any day. The official sumario.php answers for ANY
date: with the issue number, institutions and article titles when there was a
publication, or with an empty number when there was none. Every day of the
window is asked; numbering must be consecutive (restarting at 1 in January),
including the issues just before and after the window, and must agree with the
official "últimos boletines" calendar of main1.php for the months it shows.
The PDF of EVERY edition is checked; notices link to that ORIGINAL whole-issue
PDF rather than inventing individual PDF URLs. Fail closed.
"""
from __future__ import annotations
import argparse,re,requests,threading,time
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urlsplit,urljoin,parse_qs
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from clm_common import employment,publish_audit,write_output,numbering_ok
from provincial_common import ProvincialCoverageError
CONFIG={
 "lp":("www.boplaspalmas.net","nbop2","Las Palmas (BOP)","LP"),
 "tf":("www.bopsantacruzdetenerife.es","bopsc2","Santa Cruz de Tenerife (BOP)","TF")
}
HEADING_RE=re.compile(r"SUMARIO\s+DEL\s+BOLET[IÍ]N\s+N[º°]\s*(\d*)\s*,\s*DE\s+FECHA\s*(\d{1,2})-(\d{1,2})-(\d{2}|\d{4})\b",re.I)
PDF_RE=re.compile(r"^/boletines/(\d{4})/(\d{1,2})-(\d{1,2})-(\d{2})/(\d{1,2})-(\d{1,2})-(\d{2})\.pdf$")
WORKERS=3        # respeto al portal: como mucho 3 conexiones a la vez
MIN_ISSUES=10    # lunes, miércoles y viernes: unas 13 en 30 días; menos en Navidad
CONTROL_DAYS=8   # días que se miran fuera de la ventana para enlazar la numeración
C=threading.local()
def invalid(msg):raise ProvincialCoverageError("BOP Canarias: "+str(msg))
def client():
 if not hasattr(C,"s"):
  s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
  C.s=s
 return C.s
def fetch(url,host,pdf=False,retries=3):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=host or u.port not in (None,443) or u.username or u.fragment:
  invalid("URL fuera del boletín oficial "+url[:180])
 error=None
 for attempt in range(retries):
  try:
   r=client().get(url,timeout=(10,40),stream=pdf,allow_redirects=False,
        headers={"Range":"bytes=0-130"} if pdf else {})
   if r.status_code>=500 or r.status_code==429:
    error=f"HTTP {r.status_code}: {url}";r.close();time.sleep(2*(attempt+1));continue
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
   return BeautifulSoup(r.content,"html.parser",from_encoding="utf-8")
  except requests.RequestException as e:
   error="sin acceso oficial "+str(e)[:160];time.sleep(2*(attempt+1))
 invalid(error)
def sumario_url(host,path,day):
 return f"https://{host}/{path}/sumario.php?codigopub=1&fecha_mas_reciente={day.isoformat()}"
def probe(day,config):
 """(day, número o None, página) según el sumario oficial de esa fecha."""
 host,path,province,code=config
 page=sumario_url(host,path,day)
 h=fetch(page,host)
 display=" ".join(h.get_text(" ",strip=True).split())
 m=HEADING_RE.search(display)
 if not m:invalid(f"{province}: sumario sin cabecera oficial {day}")
 yy=int(m[4]);year=yy if yy>=1000 else 2000+yy
 try:shown=date(year,int(m[3]),int(m[2]))
 except ValueError:invalid(f"{province}: fecha imposible en el sumario {day}")
 if shown!=day:invalid(f"{province}: el sumario de {day} muestra la fecha {shown}")
 boxes=[td for td in h.select("td") if td.select_one("b i")]
 # Sin número (o «Nº 0», que Tenerife muestra p. ej. el 1 de enero): no hubo boletín.
 if not m[1] or int(m[1])==0:
  if boxes:invalid(f"{province}: sumario sin número pero con anuncios {day}")
  return day,None,None
 return day,int(m[1]),h
def official_calendar(config):
 """Días con boletín del calendario «Últimos Boletines» (meses que muestra)."""
 host,path,province,code=config
 url=f"https://{host}/{path}/main1.php"
 h=fetch(url,host)
 result=set()
 for a in h.select('a[href]'):
  u=urlsplit(urljoin(url,a.get("href","")))
  if u.hostname!=host or u.path!=f"/{path}/sumario.php" or u.fragment:continue
  query=parse_qs(u.query)
  # Tenerife enlaza los lunes con «codigop=1» en vez de «codigopub=1».
  if (query.get("codigopub") or query.get("codigop"))!=["1"] or len(query.get("fecha_mas_reciente",[]))!=1:
   continue
  try:day=date.fromisoformat(query["fecha_mas_reciente"][0])
  except Exception:invalid("fecha de calendario oficial mal formada")
  if a.get_text(" ",strip=True)!=str(day.day):invalid("fecha del calendario inconsistente")
  result.add(day)
 if not result:invalid(f"{province}: calendario oficial vacío")
 return result
def parse_day(day,n,h,config):
 host,path,province,code=config
 page=sumario_url(host,path,day)
 urls={urljoin(page,a["href"]) for a in h.select('a[href]') if "Descargar Bolet" in a.get_text(" ",strip=True)}
 if len(urls)!=1:
  invalid(f"{province}: el sumario carece de único PDF original {day}: {urls}")
 pdf=next(iter(urls));u=urlsplit(pdf)
 m=PDF_RE.fullmatch(u.path);yy=day.year%100
 if (not m or u.hostname!=host or u.query or u.fragment or
     tuple(int(x) for x in m.groups())!=(day.year,day.day,day.month,yy,day.day,day.month,yy)):
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
     candidates.append({"id":f"{code}-{day:%Y%m%d}-{read:03}",
       "province":province,"title":title,"entity":current,
       "date":day.strftime("%d/%m/%Y"),"bulletin":str(n),"type":kind,"url":pdf})
 if read<1:invalid(f"{province}: boletín sin contenidos {day}")
 print(f"{province} {day} n.º {n}: {read} anuncios, {len(candidates)} candidatas; PDF oficial verificado",flush=True)
 return {"day":day,"number":str(n),"read":read,"notices":candidates}
def neighbour(config,first_day,step,limit):
 """Primera edición fuera de la ventana (hacia atrás o hacia delante)."""
 for i in range(1,CONTROL_DAYS+1):
  day=first_day+timedelta(days=step*i)
  if step>0 and day>limit:return None
  _,n,_=probe(day,config)
  if n is not None:return day,n
 return None
def audit(which,today=None):
 if which not in CONFIG:invalid("provincia no autorizada")
 config=CONFIG[which];host,path,province,code=config
 end=today or date.today()
 start=end-timedelta(days=29)
 window=[start+timedelta(days=i) for i in range(30)]
 with ThreadPoolExecutor(max_workers=WORKERS) as pool:
  probes=list(pool.map(lambda d:probe(d,config),window))
 found=[(d,n,h) for d,n,h in probes if n is not None]
 if len(found)<MIN_ISSUES:invalid(f"{province}: solo {len(found)} ediciones en 30 días")
 pairs=[(d,n) for d,n,_ in found]
 if not numbering_ok(pairs):invalid(f"{province}: numeración no consecutiva {[n for _,n in pairs]}")
 # Enlace con la edición anterior a la ventana: no falta ninguna al principio.
 before=neighbour(config,start,-1,None)
 if not before:invalid(f"{province}: ninguna edición en los {CONTROL_DAYS} días anteriores a {start}")
 if not numbering_ok([before,pairs[0]]):
  invalid(f"{province}: la edición anterior a la ventana ({before}) no enlaza con {pairs[0]}")
 # Y con la siguiente (si la ventana acaba antes de hoy) o con el calendario oficial.
 real_today=date.today()
 if end<real_today:
  after=neighbour(config,end,1,real_today)
  if after and not numbering_ok([pairs[-1],after]):
   invalid(f"{province}: la edición posterior a la ventana ({after}) no enlaza con {pairs[-1]}")
 shown=official_calendar(config)
 months={(d.year,d.month) for d in shown};latest=max(shown)
 checked=0
 for d,n,_ in probes:
  if (d.year,d.month) in months and d<=latest:
   checked+=1
   if (n is not None)!=(d in shown):
    invalid(f"{province}: el calendario oficial y el sumario no coinciden el {d}")
 print(f"CALENDARIO {host}: {len(found)} ediciones {start}–{end} (n.º {pairs[0][1]}–{pairs[-1][1]}); "
       f"anterior {before[1]} del {before[0]}; {checked} días cotejados con main1.php",flush=True)
 with ThreadPoolExecutor(max_workers=WORKERS) as pool:
  issues=list(pool.map(lambda x:parse_day(*x,config),found))
 if sum(x["read"] for x in issues)<4*len(issues):invalid("recuento oficial demasiado bajo")
 return publish_audit(f"https://{host}/{path}/main1.php",province,issues,
                      today=end,min_issues=MIN_ISSUES)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--province",choices=["lp","tf"],required=True)
 p.add_argument("--output",type=Path,required=True)
 x=p.parse_args();write_output(x.output,audit(x.province))
