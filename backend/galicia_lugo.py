#!/usr/bin/env python3
"""BOP de Lugo (Deputación): últimos 30 días según el índice oficial, anuncios de cada día y PDF.

Ventana end-29 … end, con end = hoy (o el día pedido). El índice oficial se
consulta con su filtro de fechas de publicación (sirve también para el año
anterior). La numeración vuelve a 1 cada enero.

El índice HTML trae a veces un número de boletín equivocado (p. ej. el sábado
03/10/2026 figura como 225 en vez de 227). Si un número rompe la secuencia y
sus vecinos indican otro, se corrige solo cuando la primera página del PDF
original de ese día lo confirma; si no, el lector falla.
"""
from __future__ import annotations
from datetime import date,datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin,urlsplit,unquote
from bs4 import BeautifulSoup
from clm_common import publish_audit,write_output,invalid,numbering_ok
from galicia_common import galicia_employment
import requests,re,threading,argparse,io,time
from pypdf import PdfReader
SOURCE="https://deputacionlugo.gal/gl/boletin-oficial-da-provincia-de-lugo/bop"
HOST="deputacionlugo.gal"
ROW_RE=re.compile(r"(\d{1,3})\s+BOP DE (\d{2}/\d{2}/\d{4})\b",re.I)
LINK_RE=re.compile(r"BOP DE (\d{2}/\d{2}/\d{4})",re.I)
REC_RE=re.compile(r"(?:\bR\.?\s*|\bREG\.?\s*)(\d{2,6})\s*\)",re.I)
PAGE_SUFFIX_RE=re.compile(r"\s*\(P[ÁA][XG]\.?\s*\d+(?:\s*,\s*R(?:EG)?\.?\s*\d+)?\)\s*$",re.I)
MONTHS={1:("ENERO","XANEIRO"),2:("FEBRERO","FEBREIRO"),3:("MARZO","MARZO"),4:("ABRIL","ABRIL"),
        5:("MAYO","MAIO"),6:("JUNIO","XUÑO"),7:("JULIO","XULLO"),8:("AGOSTO","AGOSTO"),
        9:("SEPTIEMBRE","SETEMBRO"),10:("OCTUBRE","OUTUBRO"),11:("NOVIEMBRE","NOVEMBRO"),12:("DICIEMBRE","DECEMBRO")}
MIN_ISSUES=20   # lunes a sábado: unas 25 ediciones en 30 días; menos en Navidad
MAX_ISSUES=28
EDGE_DAYS=3
MAX_INDEX_PAGES=8
S=threading.local()
def session():
 if not hasattr(S,"req"):
  q=requests.Session();q.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"gl-ES,gl;q=0.9"});S.req=q
 return S.req
def get(url,stream=False,headers=None,timeout=(10,32),retries=3):
 error=None
 for i in range(retries):
  try:
   r=session().get(url,timeout=timeout,stream=stream,allow_redirects=False,headers=headers or {})
   if r.status_code in (429,500,502,503,504):
    r.close();error=f"HTTP {r.status_code}";time.sleep(2*(i+1));continue
   return r
  except requests.RequestException as e:
   error=str(e)[:200];time.sleep(2*(i+1))
 invalid(f"Lugo: sede inaccesible {url}: {error}")
def check_url(url,pdf=False):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=HOST or u.username or u.port not in (None,443) or u.query and pdf:
  invalid(f"Lugo: enlace fuera de Diputación {url}")
def request(url,pdf=False):
 check_url(url,pdf)
 r=get(url,stream=pdf,headers={"Range":"bytes=0-160"} if pdf else None)
 if r.status_code not in ((200,206) if pdf else (200,)):invalid(f"Lugo HTTP {r.status_code}: {url}")
 if pdf:
  b=b""
  for block in r.iter_content(180):
   b+=block
   if len(b)>=5:break
  r.close()
  if not b.startswith(b"%PDF-"):invalid("Lugo: documento no es PDF oficial "+url)
  return None
 if not 6000<len(r.content)<3000000:invalid(f"Lugo: respuesta no válida {len(r.content)} bytes")
 return BeautifulSoup(r.content,"html.parser")
def parse_index(soup,url):
 """Filas del índice: [(fecha, número del índice, página del boletín)]."""
 rows=[]
 for a in soup.select('a[href*="/node/"]'):
  match=LINK_RE.fullmatch(" ".join(a.get_text(" ",strip=True).split()))
  if not match:continue
  day=datetime.strptime(match[1],"%d/%m/%Y").date()
  row=a.find_parent("tr")
  raw=" ".join((row.get_text(" ",strip=True) if row else a.parent.parent.get_text(" ",strip=True)).split())
  m=ROW_RE.search(raw)
  if not m or m[2]!=match[1]:invalid("Lugo: boletín sin código "+raw[:200])
  link=urljoin(url,a["href"])
  if not re.fullmatch(r"https://deputacionlugo\.gal/gl/node/\d+",link):
   invalid("Lugo: página de boletín no oficial "+link)
  rows.append((day,int(m[1]),link))
 return rows
def index(start,end):
 """Ediciones del índice oficial publicadas entre start y end (ambos incluidos)."""
 base=(SOURCE+f"?fecha_publicacion%5Bmin%5D={start.isoformat()}&fecha_publicacion%5Bmax%5D={end.isoformat()}"
       "&field_ail_codigo_value=&field_ail_bop_contenido_value=")
 entries={}
 for page in range(MAX_INDEX_PAGES+1):
  if page==MAX_INDEX_PAGES:invalid("Lugo: el índice filtrado tiene demasiadas páginas")
  url=base+(f"&page={page}" if page else "")
  h=request(url)
  rows=parse_index(h,url)
  for day,number,link in rows:
   if not start<=day<=end:invalid(f"Lugo: el filtro de fechas del índice devuelve {day}")
   if day in entries and entries[day]!=(number,link):invalid(f"Lugo: duplicidad de fecha {day}")
   entries[day]=(number,link)
  print("LUGO INDEX PAGE",page,"ediciones",len(rows),flush=True)
  if not rows or not h.select(f'a[href*="page={page+1}"]'):break
 return sorted((d,n,u) for d,(n,u) in entries.items())
def step_ok(a,b):
 return b[1]==a[1]+1 or (b[0].year!=a[0].year and b[1]==1)
def original_pdf(day,url):
 """PDF completo del día enlazado desde la página del boletín."""
 soup=request(url)
 for a in soup.select('a[href$=".pdf"]'):
  u=urlsplit(urljoin(url,a["href"]))
  if re.fullmatch(rf"/sites/deputacionlugo\.org/files/\d{{4}}-\d{{2}}/{day:%d-%m-%Y} spa(?:_\d{{1,3}})?\.pdf",unquote(u.path)):
   return f"https://{HOST}{u.path}"
 invalid(f"Lugo {day}: no se encuentra el PDF original para verificar su número")
def pdf_confirms(day,url,number):
 pdfurl=original_pdf(day,url);check_url(pdfurl,pdf=True)
 r=get(pdfurl,stream=True,timeout=(12,48))
 if r.status_code!=200:invalid(f"Lugo: HTTP {r.status_code} en {pdfurl}")
 data=b""
 for block in r.iter_content(65536):
  data+=block
  if len(data)>12000000:r.close();invalid("Lugo: PDF original desmesurado")
 if not data.startswith(b"%PDF-"):invalid("Lugo: el original no es PDF")
 first=" ".join(PdfReader(io.BytesIO(data)).pages[0].extract_text().split())
 months="|".join(re.escape(m) for m in MONTHS[day.month])
 ok=re.search(rf"\b{day.day} DE (?:{months}) DE {day.year}\s+N\.?\s*[.º°]?\s*{number}\b",first,re.I)
 print(f"LUGO PDF ORIGINAL {day}: número {number} {'confirmado' if ok else 'NO confirmado'}",flush=True)
 return bool(ok)
def fix_numbers(items):
 """Corrige números del índice que rompen la secuencia, solo con el PDF original como prueba."""
 items=[list(x) for x in items]
 def interior(i):
  p,c,n=items[i-1],items[i],items[i+1]
  if step_ok(p,c) or step_ok(c,n):return None
  exp=1 if c[0].year!=p[0].year else p[1]+1
  if not step_ok((c[0],exp),n):return None
  return exp
 for i in range(1,len(items)-1):
  exp=interior(i)
  if exp is None:continue
  if not pdf_confirms(items[i][0],items[i][2],exp):
   invalid(f"Lugo: el índice dice {items[i][1]} el {items[i][0]} y el original no respalda {exp}")
  print(f"LUGO ÍNDICE CORREGIDO {items[i][0]}: {items[i][1]} -> {exp} (PDF original)",flush=True)
  items[i][1]=exp
 # Extremos: el vecino de dentro debe encajar con el resto.
 if len(items)>=3 and not step_ok(items[0],items[1]) and step_ok(items[1],items[2]) and items[1][1]>1:
  exp=items[1][1]-1
  if pdf_confirms(items[0][0],items[0][2],exp):items[0][1]=exp
 if len(items)>=3 and not step_ok(items[-2],items[-1]) and step_ok(items[-3],items[-2]):
  exp=1 if items[-1][0].year!=items[-2][0].year else items[-2][1]+1
  if pdf_confirms(items[-1][0],items[-1][2],exp):items[-1][1]=exp
 pairs=[(d,n) for d,n,_ in items]
 if not numbering_ok(pairs):invalid("Lugo: numeración interrumpida "+str([n for _,n in pairs]))
 return [tuple(x) for x in items]
def announcement_links(soup,url,day):
 links=[]
 for a in soup.select('a[href*="/sites/deputacionlugo.org/files/inline-files/"]'):
  u=urlsplit(urljoin(url,a["href"]))
  if not u.path.endswith(".pdf"):continue
  text=" ".join(a.get_text(" ",strip=True).split())
  if not text:continue
  links.append((a,u,text))
 return links
def parse_day(soup,day,number,url):
 heading=next((h.get_text(" ",strip=True) for h in soup.select("h2") if re.search("BOP DE",h.get_text(" ",strip=True),re.I)),None)
 if heading!=f"BOP DE {day:%d/%m/%Y}":invalid(f"Lugo: fecha de edición incorrecta {heading}")
 links=announcement_links(soup,url,day)
 if not links:invalid(f"Lugo {day}: BOP sin anuncios")
 seen=set();notices=[]
 for a,u,text in links:
  if (u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443) or u.query
      or not re.fullmatch(rf"/sites/deputacionlugo\.org/files/inline-files/{day:%d-%m-%Y}(?:_\d{{1,3}})?\.pdf",unquote(u.path))):
   invalid(f"Lugo {day}: PDF ajeno a la edición {u.geturl()}")
  mm=REC_RE.search(text)
  if not mm:
   invalid(f"Lugo {day}: anuncio sin registro en índice oficial {text[:200]}")
  code=mm[1]
  if code in seen:invalid(f"Lugo {day}: registro duplicado R. {code}")
  seen.add(code)
  title=PAGE_SUFFIX_RE.sub("",text).strip()
  if not title or len(title)>2800:invalid("Lugo: título vacío")
  typ=galicia_employment(title)
  if typ:
   pdf=f"https://{HOST}"+u.path
   agency=a.find_previous(["h3","h4","h5","strong","b"])
   entity=" ".join(agency.get_text(" ",strip=True).split()) if agency else "Organismo anunciante (consultar BOP de Lugo)"
   if len(entity)>490:entity="Organismo anunciante (consultar BOP de Lugo)"
   notices.append({"id":f"LU-{day.year}-{code}","province":"Lugo","title":title,"entity":entity,
    "date":day.strftime("%d/%m/%Y"),"bulletin":str(number),"type":typ,"url":pdf})
 return {"day":day,"number":str(number),"read":len(links),"notices":notices}
def read_day(it):
 day,number,url=it
 issue=parse_day(request(url),day,number,url)
 for n in issue["notices"]:request(n["url"],pdf=True)
 print("LUGO",day,number,issue["read"],"anuncios",len(issue["notices"]),"candidatas",flush=True)
 return issue
def audit(today=None):
 end=today or date.today()
 rows=index(end-timedelta(days=30),end)
 # La edición de hoy aparece en el índice antes de que se carguen sus anuncios.
 # Mientras no los tenga, la ventana termina ayer (el validador lo admite) y no
 # se da por leída una edición vacía.
 if end==date.today() and rows and rows[-1][0]==end and not announcement_links(request(rows[-1][2]),rows[-1][2],end):
  print("LUGO: la edición de hoy aún no tiene índice de anuncios; la ventana termina ayer",flush=True)
  end-=timedelta(days=1)
 start=end-timedelta(days=29)
 items=[r for r in rows if start<=r[0]<=end]
 if not MIN_ISSUES<=len(items)<=MAX_ISSUES:invalid(f"Lugo: rango incompleto ({len(items)} ediciones)")
 if (items[0][0]-start).days>EDGE_DAYS or (end-items[-1][0]).days>EDGE_DAYS:
  invalid(f"Lugo: faltan los extremos de 30 días ({items[0][0]}–{items[-1][0]})")
 items=fix_numbers(items)
 with ThreadPoolExecutor(max_workers=3) as pool:issues=list(pool.map(read_day,items))
 return publish_audit(SOURCE,"Lugo",issues,today=end,min_issues=MIN_ISSUES)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
 a=p.parse_args();write_output(a.output,audit())
