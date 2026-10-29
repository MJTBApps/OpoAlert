#!/usr/bin/env python3
"""Lugo Diputación BOP 30 days: official index, per-day announcements and PDFs."""
from __future__ import annotations
from datetime import date,datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin,urlsplit,unquote
from bs4 import BeautifulSoup
from clm_common import publish_audit,write_output,invalid
from galicia_common import galicia_employment
import requests,re,threading,argparse
SOURCE="https://deputacionlugo.gal/gl/boletin-oficial-da-provincia-de-lugo/bop"
HOST="deputacionlugo.gal"
PDF_RE=re.compile(r"^/sites/deputacionlugo\.org/files/(?:inline-files|\d{4}-\d{2})/(\d{2}-\d{2}-\d{4})(?:%20spa)?\.pdf$",re.I)
DATE_RE=re.compile(r"BOP DE (\d{2}/\d{2}/2026)",re.I)
REC_RE=re.compile(r"(?:\bR\.?\s*|\bREG\.?\s*)(\d{2,6})\s*\)",re.I)
S=threading.local()
def session():
 if not hasattr(S,"req"):
  q=requests.Session();q.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"gl-ES,gl;q=0.9"});S.req=q
 return S.req
def request(url,pdf=False):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=HOST or u.username or u.port not in (None,443) or u.query and pdf:
  invalid(f"Lugo: enlace fuera de Diputación {url}")
 try:
  r=session().get(url,timeout=(10,32),stream=pdf,allow_redirects=False,headers={"Range":"bytes=0-160"} if pdf else {})
  if r.status_code not in ((200,206) if pdf else (200,)):invalid(f"Lugo HTTP {r.status_code}: {url}")
  if pdf:
   b=b""
   for block in r.iter_content(180):
    b+=block
    if len(b)>=5:break
   r.close()
   if not b.startswith(b"%PDF-"):invalid("Lugo: documento no es PDF oficial "+url)
   return None
  if not 6000<len(r.content)<1000000:invalid(f"Lugo: respuesta no válida {len(r.content)} bytes")
  return BeautifulSoup(r.content,"html.parser")
 except requests.RequestException as e:invalid("Lugo: sede inaccesible "+str(e)[:200])
def index():
 entries={}
 for page in range(3):
  url=SOURCE+("?page="+str(page) if page else "")
  h=request(url)
  found=0
  for a in h.select('a[href*="/node/"]'):
   match=DATE_RE.fullmatch(" ".join(a.get_text(" ",strip=True).split()))
   if not match:continue
   day=datetime.strptime(match[1],"%d/%m/%Y").date()
   if not date(2026,9,30)<=day<=date(2026,10,29):continue
   row=a.find_parent("tr")
   raw=row.get_text(" ",strip=True) if row else a.parent.parent.get_text(" ",strip=True)
   nums=[int(z) for z in re.findall(r"\b\d{3}\b",raw)]
   if not nums:invalid("Lugo: boletín sin código "+raw[:200])
   number=nums[0]
   urlpath=urljoin(url,a["href"])
   if not re.fullmatch(r"https://deputacionlugo\.gal/gl/node/\d+",urlpath):
    invalid("Lugo: página de boletín no oficial")
   if day in entries and entries[day]!=(number,urlpath):invalid("Lugo: duplicidad de fecha")
   entries[day]=(number,urlpath);found+=1
  print("LUGO INDEX PAGE",page,"días en rango",found,flush=True)
 if len(entries)<23 or len(entries)>27:invalid(f"Lugo: rango incompleto ({len(entries)} días)")
 all_items=sorted(entries.items())
 numbers=[x[0] for _,x in all_items]
 if any(b!=a+1 for a,b in zip(numbers,numbers[1:])):
  invalid("Lugo: numeración interrumpida "+str(numbers))
 if all_items[0][0]!=date(2026,9,30) or all_items[-1][0]!=date(2026,10,29):
  invalid("Lugo: faltan los extremos de 30 días")
 return all_items
def read_day(it):
 day,(number,url)=it
 soup=request(url)
 heading=next((h.get_text(" ",strip=True) for h in soup.select("h2") if re.search("BOP DE",h.get_text(" ",strip=True),re.I)),None)
 if heading!=f"BOP DE {day:%d/%m/%Y}":invalid(f"Lugo: fecha de edición incorrecta {heading}")
 links=[]
 for a in soup.select('a[href*="/sites/deputacionlugo.org/files/inline-files/"]'):
  u=urlsplit(urljoin(url,a["href"]))
  if not u.path.endswith(".pdf"):continue
  text=" ".join(a.get_text(" ",strip=True).split())
  if not text:continue
  links.append((a,u,text))
 if not links:invalid(f"Lugo {day}: BOP sin anuncios")
 seen=set();notices=[]
 for a,u,text in links:
  if (u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443)
      or u.query or not re.fullmatch(r"/sites/deputacionlugo\.org/files/inline-files/\d{2}-\d{2}-2026\.pdf",unquote(u.path))
      or not unquote(u.path).endswith(f"/{day:%d-%m-%Y}.pdf")):
   invalid(f"Lugo {day}: PDF ajeno a la edición {u.geturl()}")
  mm=REC_RE.search(text)
  if not mm:
   invalid(f"Lugo {day}: anuncio sin registro en índice oficial {text[:200]}")
  code=mm[1]
  if code in seen:invalid(f"Lugo {day}: registro duplicado R. {code}")
  seen.add(code)
  title=re.sub(r"\s*\(P[ÁA]X\.?\s*\d+(?:\s*,\s*R\.?\s*\d+)?\)\s*$","",text,flags=re.I).strip()
  if not title or len(title)>2800:invalid("Lugo: título vacío")
  typ=galicia_employment(title)
  if typ:
   pdf=f"https://{HOST}"+u.path
   request(pdf,pdf=True)
   agency=a.find_previous(["h3","h4","h5","strong","b"])
   entity=" ".join(agency.get_text(" ",strip=True).split()) if agency else "Organismo anunciante (consultar BOP de Lugo)"
   if len(entity)>490:entity="Organismo anunciante (consultar BOP de Lugo)"
   notices.append({"id":f"LU-2026-{code}","province":"Lugo","title":title,"entity":entity,
    "date":day.strftime("%d/%m/%Y"),"bulletin":str(number),"type":typ,"url":pdf})
 print("LUGO",day,number,len(links),"anuncios",len(notices),"candidatas",flush=True)
 return {"day":day,"number":str(number),"read":len(links),"notices":notices}
def audit():
 days=index()
 with ThreadPoolExecutor(max_workers=5) as pool:issues=list(pool.map(read_day,days))
 return publish_audit(SOURCE,"Lugo",issues,today=date(2026,10,29))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
 a=p.parse_args();write_output(a.output,audit())
