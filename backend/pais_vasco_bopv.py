#!/usr/bin/env python3
"""30-day official Euskadi BOPV REST archive with original signed PDF validation."""
from __future__ import annotations
import argparse,re,requests,threading
from datetime import date,datetime,timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from clm_common import employment,publish_audit,write_output,invalid
SOURCE="https://api.euskadi.eus/bopv/administrative-acts"
PROVINCE="País Vasco (BOPV)"
PDF_RE=re.compile(r"^/bopv2/datos/2026/(\d{2})/(26\d{5})a\.pdf$",re.I)
ID_RE=re.compile(r"^2026/(\d{1,2})/(\d{1,6})$")
LOCAL=ZoneInfo("Europe/Madrid")
S=threading.local()
def session():
 if not hasattr(S,"client"):
  q=requests.Session()
  q.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert official bulletin reader)","Accept-Language":"es-ES,es;q=0.9"})
  S.client=q
 return S.client
def month_data(year,month):
 url=f"{SOURCE}/{year}/{month}?itemsOfPage=500&currentPage=1&lang=SPANISH"
 try:
  r=session().get(url,timeout=(15,70),allow_redirects=False)
  if r.status_code!=200 or r.url!=url or len(r.content)<180 or len(r.content)>15_000_000:
   invalid(f"BOPV: HTTP {r.status_code} o respuesta inválida para {month}")
  j=r.json()
  if not isinstance(j,dict) or not isinstance(j.get("items"),list) or not isinstance(j.get("totalItems"),int):
   invalid("BOPV: estructura API distinta")
  if (j["totalItems"]!=len(j["items"]) or j.get("totalPages")!=1 or
      j.get("itemsOfPage")!=len(j["items"]) or j.get("currentPage")!=1):
   invalid(f"BOPV: índice incompleto, total {j.get('totalItems')}, recibido {len(j['items'])}")
  if len(j["items"])<150:invalid("BOPV: hemeroteca mensual inesperadamente corta")
  print("BOPV MES",month,"anuncios",len(j["items"]),flush=True)
  return j["items"]
 except (requests.RequestException,ValueError) as e:invalid(f"BOPV: error de API oficial {e}")
def read_data(records,start,end):
 grouped={}
 seen=set()
 for row in records:
  if not isinstance(row,dict):invalid("BOPV: datos API no son registros")
  ident=str(row.get("id",""));match=ID_RE.fullmatch(ident)
  if not match or not isinstance(row.get("publishDate"),str):
   invalid("BOPV: código o fecha sin verificar")
  try:day=datetime.fromisoformat(row["publishDate"].replace("Z","+00:00")).astimezone(LOCAL).date()
  except Exception:invalid("BOPV: marca temporal incorrecta")
  if day<start or day>end:continue
  month=int(match[1]);num=int(match[2])
  if int(match[1])!=day.month or not (1<=num<=999999):
   invalid(f"BOPV: número fuera del mes {ident} {day}")
  number=str(row.get("numBulletin",""))
  if not number.isdigit() or int(number)>366 or int(number)<1:
   invalid("BOPV: número de edición incorrecto")
  title=" ".join(str(row.get("name") or "").split())
  agency=" ".join(str(row.get("department") or row.get("issuingBody") or "").split())
  if not title or not agency or len(title)>2800 or len(agency)>500:
   invalid("BOPV: título/emisor vacío")
  files=row.get("downloadable",[])
  originals=[o["url"] for o in files if isinstance(o,dict) and str(o.get("format","")).lower()=="pdf" and "url" in o]
  if len(originals)!=1:invalid(f"BOPV: PDF no identificado {ident}")
  url=originals[0];u=urlsplit(url);pm=PDF_RE.fullmatch(u.path)
  if (u.scheme!="https" or u.hostname!="www.euskadi.eus" or u.port not in (None,443)
      or u.username or u.fragment or u.query or not pm or int(pm[1])!=day.month
      or int(pm[2][-5:])!=num):
   invalid(f"BOPV: PDF no pertenece al anuncio {ident}: {url}")
  if ident in seen:invalid(f"BOPV: documento duplicado {ident}")
  seen.add(ident)
  key=(day,int(number))
  if key not in grouped:grouped[key]={"day":day,"number":number,"read":0,"notices":[]}
  grouped[key]["read"]+=1
  kind=employment(title)
  if kind:
   grouped[key]["notices"].append({"id":f"PV-2026-{num}","province":PROVINCE,"title":title,
    "entity":agency,"date":day.strftime("%d/%m/%Y"),"bulletin":number,
    "type":kind,"url":url})
 if not grouped:invalid("BOPV: sin boletines en 30 días")
 issues=[grouped[k] for k in sorted(grouped)]
 nums=[int(x["number"]) for x in issues]
 if len(issues)<18 or any(b!=a+1 for a,b in zip(nums,nums[1:])):
  invalid(f"BOPV: numeración ordinaria discontinua {nums}")
 return issues
def verify_pdf(url):
 u=urlsplit(url)
 if u.scheme!="https" or u.hostname!="www.euskadi.eus" or not PDF_RE.fullmatch(u.path):
  invalid("BOPV: documento fuera de sitio oficial")
 try:
  r=session().get(url,timeout=(12,35),stream=True,headers={"Range":"bytes=0-120"},allow_redirects=False)
  if r.status_code not in (200,206):invalid(f"BOPV PDF HTTP {r.status_code}: {url}")
  data=b""
  for block in r.iter_content(140):
   data+=block
   if len(data)>=5:break
  good=data.startswith(b"%PDF-")
  r.close()
  if not good:invalid("BOPV: archivo PDF no auténtico")
 except requests.RequestException as e:invalid("BOPV: no se puede comprobar PDF "+str(e)[:200])
def audit(today=None):
 end=today or date.today();start=end-timedelta(days=29)
 months=sorted({(start.year,start.month),(end.year,end.month)})
 data=[]
 for y,m in months:data.extend(month_data(y,m))
 issues=read_data(data,start,end)
 checks=[n["url"] for issue in issues for n in issue["notices"]]
 with ThreadPoolExecutor(max_workers=5) as p:list(p.map(verify_pdf,checks))
 for x in issues:print("BOPV",x["day"],x["number"],"anuncios",x["read"],"candidatas",len(x["notices"]),flush=True)
 return publish_audit(SOURCE,PROVINCE,issues,today=end)
if __name__=="__main__":
 parser=argparse.ArgumentParser();parser.add_argument("--output",type=Path,required=True)
 a=parser.parse_args();write_output(a.output,audit())
