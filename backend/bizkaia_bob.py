#!/usr/bin/env python3
"""Bizkaia BOB official daily HTML bulletin index and signed PDFs (30 days)."""
from __future__ import annotations
import argparse,re,requests,threading
from datetime import date,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from clm_common import employment,publish_audit,write_output,invalid
SOURCE="https://www.bizkaia.eus/es/bob"
HOST="www.bizkaia.eus"
PDF_RE=re.compile(r"^/lehendakaritza/Bao_bob/2026/(\d{2})/(\d{2})/([IVX]{1,5}-\d{1,7})_cas\.pdf$",re.I)
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
def read_day(item):
 day,n=item
 url=issue_url(day,n)
 soup=BeautifulSoup(request(url),"html.parser")
 title=next((x.get_text(" ",strip=True) for x in soup.select("h1") if "Boletín" in x.get_text(" ",strip=True)),None)
 if title!=f"Boletín {n}":invalid(f"Bizkaia {day}: cabecera no coincide con BOB {n}, encontrada={title}")
 pdfs=[a for a in soup.select("a[href]") if PDF_RE.fullmatch(urlsplit(a["href"]).path)]
 expected=next((x.get_text(" ",strip=True) for x in soup.select("h2") if re.search(r"\d+\s+anuncios",x.get_text(" ",strip=True),re.I)),None)
 m=re.search(r"(\d+)\s+anuncios",expected or "",re.I)
 if not m or int(m[1])!=len(pdfs) or not pdfs:invalid(f"Bizkaia {day}: número de anuncios no coincide {m[1] if m else None}/{len(pdfs)}")
 issues=set();notices=[]
 for a in pdfs:
  link=urlsplit(a["href"]);mm=PDF_RE.fullmatch(link.path)
  if (link.hostname!=HOST or not mm or int(mm[1])!=day.month or int(mm[2])!=day.day
      or link.query or link.fragment):invalid("Bizkaia: enlace PDF ajeno al BOB del día")
  row=a.find_parent("li",class_="row")
  p=row.select_one('p[id^="emisorResumen"]') if row else None
  title=" ".join(p.get_text(" ",strip=True).split()) if p else ""
  heading=row.find_previous(["h4","h3"]) if row else None
  agency=" ".join(heading.get_text(" ",strip=True).split()) if heading else ""
  if not title or not agency:invalid(f"Bizkaia {day}: anuncio sin título o emisor")
  nid=f"BI-2026-{mm[3].upper()}"
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
def audit(today=None):
 end=today or date.today();start=end-timedelta(days=29)
 days=[start+timedelta(days=i) for i in range(30) if (start+timedelta(days=i)).weekday()<5]
 if not 20<=len(days)<=23:invalid("Bizkaia: calendario laboral incoherente")
 first=208-len(days)+1
 with ThreadPoolExecutor(max_workers=4) as pool:items=list(pool.map(read_day,[(d,n) for n,d in enumerate(days,first)]))
 return publish_audit(SOURCE,"Bizkaia",items,today=end)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
 args=p.parse_args();write_output(args.output,audit())
