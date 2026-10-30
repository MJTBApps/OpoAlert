#!/usr/bin/env python3
"""Álava BOTHA: últimos 30 días según el calendario oficial y PDF originales en castellano.

El BOTHA se publica lunes, miércoles y viernes (salvo festivos). La ventana es
end-29 … end, con end = hoy (o el día pedido). Se piden los calendarios
mensuales que cubren la ventana (uno o dos meses, también del año anterior en
enero) y cada sumario. La numeración vuelve a 1 cada enero.
"""
from __future__ import annotations
import argparse,requests,threading,re,time
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit,urljoin,parse_qs
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from clm_common import employment,publish_audit,write_output,invalid,numbering_ok
SOURCE="https://e-s.araba.eus/BOTHA/Inicio/SGBO5001.aspx"
HOST="e-s.araba.eus"
PDF_RE=re.compile(r"^/BOTHA/Boletines/(?:pdfni/)?(\d{4})/(\d{2,3})/(\d{4})_(\d{2,3})_(\d{5})_C\.pdf$",re.I)
MONTHS=("enero","febrero","marzo","abril","mayo","junio","julio","agosto",
        "septiembre","octubre","noviembre","diciembre")
HEAD_RE=re.compile(r"Sumario del Bolet[ií]n\s+n[.º°]?\s*(\d{1,3})\s+del\s+\w+,\s+(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})",re.I)
MIN_ISSUES=10   # lunes, miércoles y viernes: 12-13 en 30 días; 11 en Navidad
MAX_ISSUES=16
EDGE_DAYS=3
S=threading.local()
def sess():
 if not hasattr(S,"s"):
  s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"});S.s=s
 return S.s
def fetch(url,pdf=False,retries=3):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=HOST or u.username or u.fragment or u.port not in (None,443):
  invalid("Álava: enlace no oficial")
 error=None
 for i in range(retries):
  try:
   r=sess().get(url,timeout=(12,35),stream=pdf,allow_redirects=False,headers={"Range":"bytes=0-100"} if pdf else {})
   if r.status_code in (429,500,502,503,504):
    r.close();error=f"HTTP {r.status_code}";time.sleep(2*(i+1));continue
   if r.status_code not in ((200,206) if pdf else (200,)):invalid(f"Álava: HTTP {r.status_code} en {url}")
   if pdf:
    start=b""
    for chunk in r.iter_content(110):
     start+=chunk
     if len(start)>=5:break
    r.close()
    if not start.startswith(b"%PDF-"):invalid("Álava: archivo no es PDF oficial")
    return None
   if len(r.content)<15000 or len(r.content)>3000000:invalid("Álava: HTML incompleto")
   return BeautifulSoup(r.content,"html.parser")
  except requests.RequestException as e:
   error=str(e)[:200];time.sleep(2*(i+1))
 invalid(f"Álava: error de conexión en {url}: {error}")
def page(day):
 return SOURCE+"?FechaBotha="+day.strftime("%d/%m/%Y")
def sumario(soup):
 """(número, fecha) del sumario mostrado en la página, o None si no hay sumario."""
 heads=[" ".join(x.get_text(" ",strip=True).split()) for x in soup.select("h2")]
 heads=[h for h in heads if re.search(r"Sumario del Bolet[ií]n",h,re.I)]
 if not heads:return None
 if len(heads)!=1:invalid(f"Álava: varias cabeceras de sumario {heads}")
 m=HEAD_RE.search(heads[0])
 if not m or m[3].lower() not in MONTHS:invalid(f"Álava: cabecera de sumario ilegible {heads[0]}")
 try:d=date(int(m[4]),MONTHS.index(m[3].lower())+1,int(m[2]))
 except ValueError:invalid(f"Álava: fecha de sumario imposible {heads[0]}")
 return int(m[1]),d
def calendar(soup,target):
 """Ediciones {fecha: número} del calendario mensual de la página pedida para `target`."""
 days={}
 for a in soup.select('a[href*="FechaBotha="]'):
  u=urlsplit(urljoin(SOURCE,a["href"]))
  q=parse_qs(u.query).get("FechaBotha",[])
  if len(q)!=1:continue
  try:d=datetime.strptime(q[0],"%d/%m/%Y").date()
  except ValueError:continue
  if d.year!=target.year or d.month!=target.month:continue
  title=a.get("title")
  if title:
   m=re.search(r"Bolet[ií]n\s+N[.º°]?\s*(\d{1,3})",title,re.I)
   if not m:invalid(f"Álava: calendario sin número de boletín {d}: {title}")
   num=int(m[1])
  else:
   # La edición más reciente sale en el calendario sin título: su número se toma
   # después de la cabecera de su propio sumario (ver archive).
   num=None
  if d in days and days[d]!=num:invalid(f"Álava: dos números para {d}")
  days[d]=num
 return days
def archive(end):
 start=end-timedelta(days=29)
 targets=[end] if (start.year,start.month)==(end.year,end.month) else [start,end]
 all_days={}
 for target in targets:
  cal=calendar(fetch(page(target)),target)
  print("ALAVA CALENDARIO",target.strftime("%m/%Y"),len(cal),"ediciones en el mes",flush=True)
  for d,n in cal.items():
   if start<=d<=end:all_days[d]=n
 untitled=[d for d,n in all_days.items() if n is None]
 if len(untitled)>1:invalid(f"Álava: varias ediciones sin número en el calendario {untitled}")
 for d in untitled:
  head=sumario(fetch(page(d)))
  if not head or head[1]!=d:invalid(f"Álava: edición {d} sin sumario propio")
  all_days[d]=head[0]
 entries=sorted(all_days.items())
 if not MIN_ISSUES<=len(entries)<=MAX_ISSUES:
  invalid(f"Álava: histórico incompleto ({len(entries)} ediciones entre {start} y {end})")
 if (entries[0][0]-start).days>EDGE_DAYS or (end-entries[-1][0]).days>EDGE_DAYS:
  invalid(f"Álava: faltan ediciones en los extremos {entries[0][0]}–{entries[-1][0]}")
 if not numbering_ok(entries):
  invalid(f"Álava: números de boletín discontinuos {entries}")
 return entries
def parse_sumario(soup,day,num):
 head=sumario(soup)
 if not head or head!=(num,day):invalid(f"Álava {day}: cabecera incorrecta, {head}")
 links=soup.select('a[id$="_panPdf"][href$="_C.pdf"]')
 if not links:invalid(f"Álava {day}: sumario sin PDF de anuncios")
 seen=set();notices=[]
 for link in links:
  pdf=urljoin(SOURCE,link["href"]);u=urlsplit(pdf);m=PDF_RE.fullmatch(u.path)
  if (not m or u.hostname!=HOST or u.query or int(m[1])!=day.year or int(m[3])!=day.year
      or int(m[2])!=num or int(m[4])!=num):
   invalid(f"Álava {day}: código de documento fuera del número {pdf}")
  td=link.find_parent("td")
  txt=td.select_one('span[id$="_lblAnuResumen"] a') if td else None
  title=" ".join(txt.get_text(" ",strip=True).split()) if txt else ""
  heading=link.find_previous("div",class_="titulo_bloque_resultados")
  agency=" ".join(heading.get_text(" ",strip=True).split()) if heading else ""
  if not title or not agency:invalid("Álava: publicación sin título o emisor "+pdf)
  nid=f"AR-{day.year}-{m[5]}"
  if nid in seen:invalid("Álava: aviso duplicado "+nid)
  seen.add(nid)
  typ=employment(title)
  if typ:notices.append({"id":nid,"province":"Álava","title":title,"entity":agency,
    "date":day.strftime("%d/%m/%Y"),"bulletin":str(num),"type":typ,"url":pdf})
 return {"day":day,"number":str(num),"read":len(seen),"notices":notices}
def scan(pair):
 day,num=pair
 issue=parse_sumario(fetch(page(day)),day,num)
 for n in issue["notices"]:fetch(n["url"],pdf=True)
 print("ALAVA",day,num,issue["read"],"anuncios",len(issue["notices"]),"candidatas",flush=True)
 return issue
def audit(today=None):
 end=today or date.today()
 days=archive(end)
 with ThreadPoolExecutor(max_workers=3) as pool:issues=list(pool.map(scan,days))
 return publish_audit(SOURCE,"Álava",issues,today=end,min_issues=MIN_ISSUES)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path)
 args=p.parse_args();write_output(args.output,audit())
