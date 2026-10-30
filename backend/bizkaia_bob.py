#!/usr/bin/env python3
"""Bizkaia BOB official daily HTML bulletin index and signed PDFs (30 days)."""
from __future__ import annotations
import argparse,re,requests,threading,time
from datetime import date,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from clm_common import employment,publish_audit,write_output,invalid
SOURCE="https://www.bizkaia.eus/es/bob"
HOST="www.bizkaia.eus"
PDF_RE=re.compile(r"^/lehendakaritza/Bao_bob/(\d{4})/(\d{2})/(\d{2})/([IVX]{1,5}-\d{1,7})_cas\.pdf$",re.I)
S=threading.local()
def session():
 if not hasattr(S,"r"):
  s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"});S.r=s
 return S.r
def request(url,pdf=False):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443) or u.username or u.fragment:invalid("Bizkaia: URL no oficial")
 try:
  r=session().get(url,timeout=(12,29),stream=pdf,allow_redirects=False,headers={"Range":"bytes=0-130"} if pdf else {})
  if pdf:
   if r.status_code not in (200,206):invalid(f"Bizkaia: PDF {r.status_code} {url}")
   v=b""
   for chunk in r.iter_content(180):
    v+=chunk
    if len(v)>5:break
   ok=v.startswith(b"%PDF-")
   r.close()
   if not ok:invalid(f"Bizkaia: PDF no autenticado {url}")
   return None
  if r.status_code!=200 or not 12000<len(r.content)<850000:invalid(f"Bizkaia: índice HTTP {r.status_code}")
  return r.content
 except requests.RequestException as e:invalid("Bizkaia: error de sede "+str(e)[:180])
def issue_url(day,n):
 return ("https://www.bizkaia.eus/es/bob/resultados?p_p_id=IYBIWBCC"
         "&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view"
         "&_IYBIWBCC_mvcRenderCommandName=%2Fdetail"
         +f"&_IYBIWBCC_bdate={day:%Y%m%d}&_IYBIWBCC_bnum={n}")
def latest_issue():
 """Último BOB enlazado desde la portada oficial: (fecha, número)."""
 html=request(SOURCE).decode("utf-8","replace")
 found={(m[1],int(m[2])) for m in re.finditer(r"bdate=(\d{8})&(?:amp;)?_IYBIWBCC_bnum=(\d{1,3})",html)}
 if not found:invalid("Bizkaia: la portada no enlaza el último boletín")
 raw,n=max(found)
 return date(int(raw[:4]),int(raw[4:6]),int(raw[6:])),n
def read_day(item,allow_missing=False):
 day,n=item
 url=issue_url(day,n)
 soup=None;title=None
 for attempt in range(3):
  soup=BeautifulSoup(request(url),"html.parser")
  title=next((x.get_text(" ",strip=True) for x in soup.select("h1") if "Boletín" in x.get_text(" ",strip=True)),None)
  if title==f"Boletín {n}":break
  time.sleep(0.5*(attempt+1))
 if title!=f"Boletín {n}":
  if allow_missing:return None
  invalid(f"Bizkaia {day}: cabecera no coincide con BOB {n}, encontrada={title}")
 pdfs=[a for a in soup.select("a[href]") if PDF_RE.fullmatch(urlsplit(a["href"]).path)]
 expected=next((x.get_text(" ",strip=True) for x in soup.select("h2") if re.search(r"\d+\s+anuncios",x.get_text(" ",strip=True),re.I)),None)
 m=re.search(r"(\d+)\s+anuncios",expected or "",re.I)
 if not m or int(m[1])!=len(pdfs) or not pdfs:invalid(f"Bizkaia {day}: número de anuncios no coincide {m[1] if m else None}/{len(pdfs)}")
 issues=set();notices=[]
 for a in pdfs:
  link=urlsplit(a["href"]);mm=PDF_RE.fullmatch(link.path)
  if (link.hostname!=HOST or not mm or int(mm[1])!=day.year or int(mm[2])!=day.month
      or int(mm[3])!=day.day or link.query or link.fragment):invalid("Bizkaia: enlace PDF ajeno al BOB del día")
  row=a.find_parent("li",class_="row")
  p=row.select_one('p[id^="emisorResumen"]') if row else None
  title=" ".join(p.get_text(" ",strip=True).split()) if p else ""
  heading=row.find_previous(["h4","h3"]) if row else None
  agency=" ".join(heading.get_text(" ",strip=True).split()) if heading else ""
  if not title or not agency:invalid(f"Bizkaia {day}: anuncio sin título o emisor")
  nid=f"BI-{day.year}-{mm[4].upper()}"
  if nid in issues:invalid("Bizkaia: anuncio duplicado")
  issues.add(nid)
  kind=employment(title)
  if kind:
   pdf="https://www.bizkaia.eus"+link.path
   request(pdf,pdf=True)
   notices.append({"id":nid,"province":"Bizkaia","title":title,
    "entity":agency,"date":day.strftime("%d/%m/%Y"),"bulletin":str(n),
    "type":kind,"url":pdf})
 print("BIZKAIA",day,n,"anuncios",len(issues),"candidatas",len(notices),flush=True)
 return {"day":day,"number":str(n),"read":len(issues),"notices":notices}
def has_issue(day,n):
 soup=BeautifulSoup(request(issue_url(day,n)),"html.parser")
 return any(x.get_text(" ",strip=True)==f"Boletín {n}" for x in soup.select("h1"))
def find_number(day):
 """Número del BOB de un día: la sede deja la página vacía si el número no es el suyo.

 Se parte de los días laborables transcurridos del año (cota superior: los
 festivos no tienen BOB) y se baja hasta encontrarlo. None si ese día no hubo BOB.
 """
 guess=sum(1 for i in range(day.timetuple().tm_yday) if (date(day.year,1,1)+timedelta(days=i)).weekday()<5)
 for n in range(guess,max(guess-25,0),-1):
  if has_issue(day,n):return n
 return None
def audit(today=None):
 end=today or date.today();start=end-timedelta(days=29)
 if today is None:
  last_day,n=latest_issue()
 else:
  # Prueba con una fecha pasada: localizar el último BOB hasta ese día.
  last_day=end;n=None
  while n is None and (end-last_day).days<=4:
   n=find_number(last_day) if last_day.weekday()<5 else None
   if n is None:last_day-=timedelta(days=1)
  if n is None:invalid("Bizkaia: no se localiza el último boletín del periodo")
 if last_day>end or (end-last_day).days>4:invalid(f"Bizkaia: último boletín {n} del {last_day} fuera del periodo")
 # Recorrer hacia atrás los días laborables: cada BOB tiene el número anterior.
 # Un día laborable sin boletín (festivo) no consume número; se admiten pocos.
 # Al pasar al año anterior la numeración no sigue: se localiza de nuevo.
 items=[];holidays=[];day=last_day;year=last_day.year
 while day>=start:
  if day.weekday()<5:
   if day.year!=year:
    found=find_number(day)
    if found is None:
     holidays.append(day);day-=timedelta(days=1);continue
    n=found;year=day.year
   item=read_day((day,n),allow_missing=bool(items))
   if item is None:holidays.append(day)
   else:
    items.append(item);n-=1
  day-=timedelta(days=1)
 if len(holidays)>5:invalid(f"Bizkaia: demasiados días laborables sin boletín {holidays}")
 if not 16<=len(items)<=23:invalid("Bizkaia: calendario laboral incoherente")
 return publish_audit(SOURCE,"Bizkaia",items,today=end)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
 args=p.parse_args();write_output(args.output,audit())
