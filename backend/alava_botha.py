#!/usr/bin/env python3
"""Alava BOTHA 30-day archive with official day calendar and bilingual original PDFs."""
from __future__ import annotations
import argparse,requests,threading,re
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit,urljoin,parse_qs
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from clm_common import employment,publish_audit,write_output,invalid
SOURCE="https://e-s.araba.eus/BOTHA/Inicio/SGBO5001.aspx"
HOST="e-s.araba.eus"
PDF_RE=re.compile(r"^/BOTHA/Boletines/2026/(\d{2,3})/2026_(\d{2,3})_(\d{5})_C\.pdf$",re.I)
S=threading.local()
def sess():
 if not hasattr(S,"s"):
  s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"});S.s=s
 return S.s
def fetch(url,pdf=False):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=HOST or u.username or u.fragment or u.port not in (None,443):
  invalid("Álava: enlace no oficial")
 try:
  r=sess().get(url,timeout=(12,35),stream=pdf,allow_redirects=False,headers={"Range":"bytes=0-100"} if pdf else {})
  if r.status_code not in ((200,206) if pdf else (200,)):invalid(f"Álava: HTTP {r.status_code} en {url}")
  if pdf:
   start=b""
   for chunk in r.iter_content(110):
    start+=chunk
    if len(start)>=5:break
   r.close()
   if not start.startswith(b"%PDF-"):invalid("Álava: archivo no es PDF oficial")
   return None
  if len(r.content)<15000 or len(r.content)>900000:invalid("Álava: HTML incompleto")
  return BeautifulSoup(r.content,"html.parser")
 except requests.RequestException as e:invalid("Álava: error de conexión "+str(e)[:200])
def archive(end):
 start=end-timedelta(days=29)
 all_days={}
 for target in [date(2026,9,30),date(2026,10,28)]:
  root=fetch(SOURCE+"?FechaBotha="+target.strftime("%d/%m/%Y"))
  found=0
  for a in root.select('a[href*="FechaBotha="]'):
   u=urlsplit(urljoin(SOURCE,a["href"]))
   q=parse_qs(u.query).get("FechaBotha",[])
   if len(q)!=1:continue
   try:d=datetime.strptime(q[0],"%d/%m/%Y").date()
   except ValueError:continue
   if d.year!=target.year or d.month!=target.month:continue
   m=re.search(r"Bolet[ií]n\s+N[.º°]?\s*(\d{1,3})",a.get("title",""),re.I)
   if not m:invalid("Álava: calendario sin número de boletín")
   if start<=d<=end:all_days[d]=int(m[1])
   found+=1
  if found<11:invalid(f"Álava: calendario mensual no recuperado {target}, {found}")
 entries=sorted(all_days.items())
 if len(entries)<12 or len(entries)>15 or entries[0][0]>start+timedelta(days=2) or (end-entries[-1][0]).days>3:
  invalid("Álava: histórico incompleto")
 if any(b[1]!=a[1]+1 for a,b in zip(entries,entries[1:])):
  invalid(f"Álava: números de boletín discontinuos {entries}")
 return entries
def scan(pair):
 day,num=pair
 soup=fetch(SOURCE+"?FechaBotha="+day.strftime("%d/%m/%Y"))
 headings=[x.get_text(" ",strip=True) for x in soup.select("h2") if "Sumario del Boletin" in x.get_text(" ",strip=True)]
 if len(headings)!=1 or not re.search(rf"n[.º°]\s*{num}\b",headings[0],re.I):
  invalid(f"Álava {day}: cabecera incorrecta, {headings}")
 links=soup.select('a[id$="_panPdf"][href$="_C.pdf"]')
 if not links:invalid(f"Álava {day}: sumario sin PDF de anuncios")
 seen=set();notices=[]
 for link in links:
  pdf=urljoin(SOURCE,link["href"]);u=urlsplit(pdf);m=PDF_RE.fullmatch(u.path)
  if not m or u.hostname!=HOST or int(m[1])!=num or int(m[2])!=num or u.query:
   invalid(f"Álava {day}: código de documento fuera del número {pdf}")
  td=link.find_parent("td")
  txt=td.select_one('span[id$="_lblAnuResumen"] a') if td else None
  title=" ".join(txt.get_text(" ",strip=True).split()) if txt else ""
  heading=link.find_previous("div",class_="titulo_bloque_resultados")
  agency=" ".join(heading.get_text(" ",strip=True).split()) if heading else ""
  if not title or not agency:invalid("Álava: publicación sin título o emisor "+pdf)
  nid="AR-2026-"+m[3]
  if nid in seen:invalid("Álava: aviso duplicado")
  seen.add(nid)
  typ=employment(title)
  if typ:notices.append({"id":nid,"province":"Álava","title":title,"entity":agency,
    "date":day.strftime("%d/%m/%Y"),"bulletin":str(num),"type":typ,"url":pdf})
 for n in notices:fetch(n["url"],pdf=True)
 print("ALAVA",day,num,len(seen),"anuncios",len(notices),"candidatas",flush=True)
 return {"day":day,"number":str(num),"read":len(seen),"notices":notices}
def audit(today=None):
 end=today or date.today()
 days=archive(end)
 with ThreadPoolExecutor(max_workers=4) as pool:issues=list(pool.map(scan,days))
 return publish_audit(SOURCE,"Álava",issues,today=end,min_issues=12)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path)
 args=p.parse_args();write_output(args.output,audit())
