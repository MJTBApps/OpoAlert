#!/usr/bin/env python3
"""DOG Galicia 30-day official HTML daily sections with individual Xunta PDF originals."""
from __future__ import annotations
from datetime import date,timedelta,datetime
from pathlib import Path
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit,urljoin
from clm_common import publish_audit,write_output,invalid,numbering_ok
from galicia_common import galicia_employment
import argparse,requests,threading,re
SOURCE="https://www.xunta.gal/diario-oficial-galicia/Welcome.do?lang=es"
HOST="www.xunta.gal"
PDF_RE=re.compile(r"^/dog/Publicados/(\d{4})/(\d{8})/(Anuncio[A-Za-z0-9-]+)_es\.pdf$")
S=threading.local()
MONTH={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
DATE_RE=re.compile(r"(\d{1,2}) de (\w+) de (\d{4})",re.I)
def ses():
 if not hasattr(S,"q"):
  r=requests.Session();r.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"});S.q=r
 return S.q
def get(url,pdf=False):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443) or u.username or u.fragment or u.query:
  invalid("DOG: URL fuera de la Xunta")
 try:
  r=ses().get(url,timeout=(10,35),allow_redirects=False,stream=pdf,headers={"Range":"bytes=0-150"} if pdf else {})
  if r.status_code in (404,410) and not pdf:return None
  if r.status_code not in ((200,206) if pdf else (200,)):
   invalid(f"DOG: HTTP {r.status_code} {url}")
  if pdf:
   b=b""
   for chunk in r.iter_content(180):
    b+=chunk
    if len(b)>=5:break
   r.close()
   if not b.startswith(b"%PDF-"):invalid("DOG: documento PDF no autenticado "+url)
   return None
  if not 800<len(r.content)<900000:invalid(f"DOG: documento HTML truncado {len(r.content)}")
  return BeautifulSoup(r.content,"html.parser")
 except requests.RequestException as e:invalid("DOG: error de sede "+str(e)[:220])
def section(day,index):
 return f"https://{HOST}/dog/Publicados/{day:%Y/%Y%m%d}/Secciones{index}_es.html"
def read_day(day):
 htmls=[]
 for sec in range(4):
  h=get(section(day,sec))
  if h is not None:htmls.append((sec,h))
 if not htmls:return None
 nums=set();ids=set();found=0;notices=[]
 for sec,soup in htmls:
  bn=soup.select_one("#DOGNumero");bd=soup.select_one("#DOGData")
  mm=re.search(r"N[º°]\s*(\d{1,3})",bn.get_text(" ",strip=True) if bn else "",re.I)
  dm=DATE_RE.search(bd.get_text(" ",strip=True) if bd else "")
  if not mm or not dm or (int(dm[1]),MONTH.get(dm[2].lower()),int(dm[3]))!=(day.day,day.month,day.year):
   invalid(f"DOG {day}: cabecera incoherente sección {sec}")
  nums.add(int(mm[1]))
  for li in soup.select("li.dog-toc-sumario"):
   a=li.select_one('a[href*="Anuncio"]')
   if not a:invalid(f"DOG {day} {sec}: anuncio sin enlace")
   title=" ".join(a.get_text(" ",strip=True).split())
   u=urlsplit(urljoin(f"https://{HOST}",a.get("href","")))
   path=u.path
   im=re.fullmatch(r"/dog/Publicados/(\d{4})/(\d{8})/(Anuncio[A-Za-z0-9-]+)_es\.html",path)
   if not im or im[1]!=str(day.year) or im[2]!=day.strftime("%Y%m%d") or u.hostname!=HOST:
    invalid(f"DOG {day}: página anuncio no oficial {u.geturl()}")
   ident=im[3]
   if ident in ids:invalid(f"DOG: anuncio duplicado {ident}")
   ids.add(ident);found+=1
   org=li.find_previous("p",class_="dog-toc-organismo")
   agency=" ".join(org.get_text(" ",strip=True).split()) if org else "Organismo emisor: consultar DOG"
   if not title or len(title)>2800 or len(agency)>500:invalid("DOG: título o emisor no válido")
   pdf=f"https://{HOST}/dog/Publicados/{day:%Y/%Y%m%d}/{ident}_es.pdf"
   kind=galicia_employment(title)
   if kind:
    get(pdf,pdf=True)
    notices.append({"id":f"DG-{day.year}-{ident}","province":"Galicia (DOG)","title":title,
     "entity":agency,"date":day.strftime("%d/%m/%Y"),"bulletin":str(int(mm[1])),
     "type":kind,"url":pdf})
 if len(nums)!=1 or not found:invalid(f"DOG {day}: diario sin anuncios o números inconsistentes")
 num=nums.pop()
 print("DOG GALICIA",day,num,"anuncios",found,"candidatas",len(notices),flush=True)
 return {"day":day,"number":str(num),"read":found,"notices":notices}
def audit(today=None):
 end=today or date.today();start=end-timedelta(days=29)
 # A Xunta publicará un DOG en días inhábiles de manera excepcional; comprobar cada fecha
 # desde el HTML de la Xunta, no inferir únicamente días laborables.
 days=[start+timedelta(days=i) for i in range(30)]
 with ThreadPoolExecutor(max_workers=5) as p:issues=[x for x in p.map(read_day,days) if x]
 nums=[int(x["number"]) for x in issues]
 if len(issues)<18 or not numbering_ok([(x["day"],n) for x,n in zip(issues,nums)]):
  invalid(f"DOG: falta alguna edición {nums}")
 if (issues[0]["day"]-start).days>3 or (end-issues[-1]["day"]).days>3:
  invalid("DOG: extremos del periodo incompletos")
 return publish_audit(SOURCE,"Galicia (DOG)",issues,today=end)
if __name__=="__main__":
 a=argparse.ArgumentParser();a.add_argument("--output",type=Path,required=True)
 arg=a.parse_args();write_output(arg.output,audit())
