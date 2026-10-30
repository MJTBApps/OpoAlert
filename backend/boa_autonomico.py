#!/usr/bin/env python3
"""Validate the autonomous BOA from independent official XML and JSON exports."""
from __future__ import annotations
import argparse,html,json,re,requests,time,xml.etree.ElementTree as ET
from urllib.parse import urlsplit,parse_qs
from datetime import date,datetime,timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from clm_common import employment,numbering_ok,publish_audit,write_output,invalid
from provincial_common import fold
from zaragoza_bop import BASE,SOURCE
PROVINCE="Aragón (BOA)"
DAYS=30
# Fines de semana y festivos: la primera y la última edición pueden caer
# hasta 3 días dentro de la ventana.
EDGE_DAYS=3
# Diario de lunes a viernes: unas 21 ediciones en 30 días, 15 con la Navidad.
MIN_ISSUES=15
# Unos 25-40 anuncios por edición: por debajo, exportación incompleta.
MIN_ROWS=150
MAX_WORKERS=3
def window(today=None):
 end=today or date.today()
 return end-timedelta(days=DAYS-1),end
# Número ordinario («211») o extraordinario («2 Extraordinario», con su propia
# numeración, que también empieza en 1 cada enero).
NUM_RE=re.compile(r"([1-9]\d{0,3})( Extraordinario)?")
URL_RE=re.compile(r"https://www\.boa\.aragon\.es/cgi-bin/EBOA/BRSCGI\?CMD=VEROBJ&MLKOB=\d{9,18}")
def urls(value):
 if not isinstance(value,str):invalid("BOA: enlace no textual")
 found=URL_RE.findall(value)
 remainder=re.sub(r"</?enlace>", "",URL_RE.sub("",value),flags=re.I).strip(" \r\n\t"+chr(96)+"´")
 if not 1<=len(found)<=3 or remainder or len(found)!=len(set(found)):
  invalid(f"BOA: PDF irregular, {value[:135]}")
 for target in found:
  u=urlsplit(target)
  if u.hostname!="www.boa.aragon.es" or set(parse_qs(u.query))!={"CMD","MLKOB"}:
   invalid("BOA: enlace ajeno al BOA")
 return found
def download(start,end,xml=False):
 q=dict(BASE)
 q.update({"BASE":"BOLE","SECC-C":"","OUTPUTMODE":"XML" if xml else "JSON",
           "SEC":"OPENDATABOAXML" if xml else "OPENDATABOAJSON",
           "@PUBL-GE":start.strftime("%Y%m%d"),"@PUBL-LE":end.strftime("%Y%m%d")})
 for attempt in range(3):
  try:
   r=requests.get(SOURCE,params=q,timeout=(12,80),headers={"User-Agent":"Mozilla/5.0"})
   if r.status_code!=200 or not 12000<len(r.content)<25000000:
    invalid(f"BOA: exportación incompleta HTTP {r.status_code}")
   return r.content
  except requests.RequestException as e:
   if attempt==2:invalid(f"BOA: API no responde: {e}")
   time.sleep(3*(attempt+1))
def in_window(value,start,end):
 """Fecha AAAAMMDD de publicación dentro de la ventana."""
 if not re.fullmatch(r"\d{8}",value):return False
 try:day=datetime.strptime(value,"%Y%m%d").date()
 except ValueError:return False
 return start<=day<=end
def read_json(raw,start,end):
 try:
  s=raw.decode("ISO-8859-1")
  try:items=json.loads(s)
  except json.JSONDecodeError as e:
   if "Invalid \\escape" not in str(e):raise
   repaired=re.sub(r"\\(?![\"\\/bfnrtu])",r"\\\\",s)
   if len(repaired)-len(s)>150:invalid("BOA: demasiadas alteraciones JSON")
   items=json.loads(repaired)
   print("BOA: escapado excepcional JSON cotejado íntegramente con XML",flush=True)
 except (ValueError,UnicodeError) as e:invalid(f"BOA: JSON no es válido: {e}")
 if not isinstance(items,list) or not MIN_ROWS<=len(items)<10000:
  invalid(f"BOA: exportación JSON incompleta: {len(items)}")
 out={};counts=set()
 for i,r in enumerate(items,1):
  order=re.fullmatch(r"(\d+) de (\d+)",str(r.get("NOrden","")))
  ident=str(r.get("DOCN",""));dt=str(r.get("FechaPublicacion",""))
  title=html.unescape(str(r.get("Titulo") or "")).strip()
  agency=str(r.get("Emisor") or "").strip();body=str(r.get("Texto") or "").strip()
  num=str(r.get("Numeroboletin",""))
  if (not order or int(order[1])!=i or not re.fullmatch(r"\d{9}",ident)
      or ident in out or not in_window(dt,start,end)
      or not NUM_RE.fullmatch(num) or not title or not agency or not body
      or not str(r.get("Seccion","")).strip()):
   invalid(f"BOA: fila JSON corrupta {i}, doc={ident}, fecha={dt}")
  counts.add(int(order[2]))
  out[ident]={"date":dt,"num":num,"title":title,"agency":agency,
              "pdfs":urls(r.get("UrlPdf",""))}
 if counts!={len(items)}:invalid("BOA: exportación JSON truncada")
 return out
def read_xml(raw,start,end):
 try:root=ET.fromstring(raw)
 except ET.ParseError as e:invalid(f"BOA: XML no válido: {e}")
 if root.tag!="documento":invalid("BOA: respuesta no es XML de datos abiertos")
 out={}
 for reg in root.findall("registro"):
  ident=(reg.findtext("docn") or "").strip()
  if not re.fullmatch(r"\d{9}",ident) or ident in out:
   invalid("BOA: XML con código duplicado")
  if not in_window((reg.findtext("fecha") or "").strip(),start,end):
   invalid(f"BOA: XML con fecha fuera de la ventana en {ident}")
  out[ident]={"date":(reg.findtext("fecha") or "").strip(),
              "title":html.unescape(reg.findtext("titulo") or "").strip(),
              "agency":(reg.findtext("emisor") or "").strip(),
              "pdfs":urls((reg.findtext("url") or "").strip())}
 return out
def check_pdf(url):
 if urls(url)!=[url]:invalid("BOA: documento PDF no oficial")
 for attempt in range(3):
  try:
   r=requests.get(url,timeout=(10,35),stream=True,allow_redirects=False,
                  headers={"Range":"bytes=0-120"})
   if r.status_code not in (200,206):invalid(f"BOA: PDF HTTP {r.status_code}")
   head=b""
   for chunk in r.iter_content(140):
    head+=chunk
    if len(head)>=5:break
   good=head.startswith(b"%PDF-");r.close()
   if not good:invalid("BOA: PDF original no recuperable")
   return
  except requests.RequestException as e:
   if attempt==2:invalid(f"BOA: PDF inaccesible: {e}")
   time.sleep(1.5*(attempt+1))
def comparable(value):
 return " ".join(fold(value).split())
def check_issues(keys,start,end):
 """(fecha, número) de las ediciones, ordenadas: ventana y numeración completas.

 Los ordinarios deben cubrir la ventana sin huecos; los extraordinarios llevan
 su propia serie, que tampoco puede tener huecos entre los leídos."""
 ordinary=[(d,int(n)) for d,n in keys if NUM_RE.fullmatch(n)[2] is None]
 extra=[(d,int(NUM_RE.fullmatch(n)[1])) for d,n in keys if NUM_RE.fullmatch(n)[2]]
 if (len(ordinary)<MIN_ISSUES or (ordinary[0][0]-start).days>EDGE_DAYS
    or (end-ordinary[-1][0]).days>EDGE_DAYS or not numbering_ok(ordinary)
    or not numbering_ok(extra)):
  invalid(f"BOA: números no continuos o ediciones ausentes {[(d.isoformat(),n) for d,n in keys]}")
def audit(today=None):
 start,end=window(today)
 data=read_json(download(start,end),start,end)
 other=read_xml(download(start,end,xml=True),start,end)
 if set(data)!=set(other):
  invalid(f"BOA: diferente número de anuncios JSON/XML: {len(data)}/{len(other)}")
 grouped=defaultdict(list)
 for ident,r in data.items():
  x=other[ident]
  if x["date"]!=r["date"] or comparable(x["title"])!=comparable(r["title"]) or comparable(x["agency"])!=comparable(r["agency"]) or x["pdfs"]!=r["pdfs"]:
   invalid(f"BOA: XML difiere del JSON en {ident}; dates={x['date']==r['date']}, titles={fold(x['title'])==fold(r['title'])}, agencies={fold(x['agency'])==fold(r['agency'])}, urls={x['pdfs']==r['pdfs']}; titulo_xml={x['title'][:280]!r}, titulo_json={r['title'][:280]!r}, pdf_xml={x['pdfs']}, pdf_json={r['pdfs']}")
  day=datetime.strptime(r["date"],"%Y%m%d").date()
  grouped[(day,r["num"])].append((ident,r))
 # Por fecha y, en el mismo día, el ordinario antes que el extraordinario.
 keys=sorted(grouped,key=lambda k:(k[0],NUM_RE.fullmatch(k[1])[2] is not None,int(NUM_RE.fullmatch(k[1])[1])))
 check_issues(keys,start,end)
 checks=[];issues=[]
 for day,num in keys:
  rows=grouped[(day,num)]
  notices=[]
  for ident,r in rows:
   kind=employment(r["title"])
   if kind:
    target=r["pdfs"][0]
    checks.append(target)
    notices.append({"id":f"AO-{day.year}-{ident}","province":PROVINCE,
      "title":r["title"][:2800],"entity":r["agency"][:500],
      "date":day.strftime("%d/%m/%Y"),"bulletin":str(num),"type":kind,"url":target})
  print(f"BOA {day}: n.º {num}, {len(rows)} anuncios, {len(notices)} candidatas",flush=True)
  issues.append({"day":day,"number":str(num),"read":len(rows),"notices":notices})
 if not checks:invalid("BOA: sin anuncios de empleo público")
 with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:list(pool.map(check_pdf,sorted(set(checks))))
 return publish_audit(SOURCE,PROVINCE,issues,today=end,min_issues=MIN_ISSUES)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path)
 args=p.parse_args();write_output(args.output,audit())
