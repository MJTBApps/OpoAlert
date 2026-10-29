#!/usr/bin/env python3
"""Validate the autonomous BOA from independent official XML and JSON exports."""
from __future__ import annotations
import argparse,html,json,re,requests,xml.etree.ElementTree as ET
from urllib.parse import urlsplit,parse_qs
from datetime import date,datetime,timedelta
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from clm_common import employment,publish_audit,write_output,invalid
from provincial_common import fold
from zaragoza_bop import BASE,SOURCE
END=date(2026,10,29);START=END-timedelta(days=29)
URL_RE=re.compile(r"https://www\.boa\.aragon\.es/cgi-bin/EBOA/BRSCGI\?CMD=VEROBJ&MLKOB=\d{9,18}")
def urls(value):
 if not isinstance(value,str):invalid("BOA: enlace no textual")
 found=URL_RE.findall(value)
 remainder=URL_RE.sub("",value).strip(" \r\n\t"+chr(96)+"´")
 if not 1<=len(found)<=3 or remainder or len(found)!=len(set(found)):
  invalid(f"BOA: PDF irregular, {value[:135]}")
 for target in found:
  u=urlsplit(target)
  if u.hostname!="www.boa.aragon.es" or set(parse_qs(u.query))!={"CMD","MLKOB"}:
   invalid("BOA: enlace ajeno al BOA")
 return found
def download(xml=False):
 q=dict(BASE)
 q.update({"BASE":"BOLE","SECC-C":"","OUTPUTMODE":"XML" if xml else "JSON",
           "SEC":"OPENDATABOAXML" if xml else "OPENDATABOAJSON",
           "@PUBL-GE":START.strftime("%Y%m%d"),"@PUBL-LE":END.strftime("%Y%m%d")})
 try:
  r=requests.get(SOURCE,params=q,timeout=(12,80),headers={"User-Agent":"Mozilla/5.0"})
  if r.status_code!=200 or not 12000<len(r.content)<25000000:
   invalid(f"BOA: exportación incompleta HTTP {r.status_code}")
  return r.content
 except requests.RequestException as e:invalid(f"BOA: API no responde: {e}")
def read_json(raw):
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
 if not isinstance(items,list) or not 350<=len(items)<10000:
  invalid(f"BOA: exportación JSON incompleta: {len(items)}")
 out={};counts=set()
 for i,r in enumerate(items,1):
  order=re.fullmatch(r"(\d+) de (\d+)",str(r.get("NOrden","")))
  ident=str(r.get("DOCN",""));dt=str(r.get("FechaPublicacion",""))
  title=html.unescape(str(r.get("Titulo") or "")).strip()
  agency=str(r.get("Emisor") or "").strip();body=str(r.get("Texto") or "").strip()
  num=str(r.get("Numeroboletin",""))
  if (not order or int(order[1])!=i or not re.fullmatch(r"\d{9}",ident)
      or ident in out or not re.fullmatch(r"2026(?:0930|10(?:0[1-9]|[12]\d))",dt)
      or not num.isdigit() or not title or not agency or not body
      or not str(r.get("Seccion","")).strip()):
   invalid(f"BOA: fila JSON corrupta {i}, doc={ident}, fecha={dt}")
  counts.add(int(order[2]))
  out[ident]={"date":dt,"num":num,"title":title,"agency":agency,
              "pdfs":urls(r.get("UrlPdf",""))}
 if counts!={len(items)}:invalid("BOA: exportación JSON truncada")
 return out
def read_xml(raw):
 try:root=ET.fromstring(raw)
 except ET.ParseError as e:invalid(f"BOA: XML no válido: {e}")
 if root.tag!="documento":invalid("BOA: respuesta no es XML de datos abiertos")
 out={}
 for reg in root.findall("registro"):
  ident=(reg.findtext("docn") or "").strip()
  if not re.fullmatch(r"\d{9}",ident) or ident in out:
   invalid("BOA: XML con código duplicado")
  out[ident]={"date":(reg.findtext("fecha") or "").strip(),
              "title":html.unescape(reg.findtext("titulo") or "").strip(),
              "agency":(reg.findtext("emisor") or "").strip(),
              "pdfs":urls((reg.findtext("url") or "").strip())}
 return out
def check_pdf(url):
 if urls(url)!=[url]:invalid("BOA: documento PDF no oficial")
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
 except requests.RequestException as e:invalid(f"BOA: PDF inaccesible: {e}")
def audit():
 data=read_json(download())
 other=read_xml(download(xml=True))
 if set(data)!=set(other):
  invalid(f"BOA: diferente número de anuncios JSON/XML: {len(data)}/{len(other)}")
 grouped=defaultdict(list)
 for ident,r in data.items():
  x=other[ident]
  if x["date"]!=r["date"] or fold(x["title"])!=fold(r["title"]) or fold(x["agency"])!=fold(r["agency"]) or x["pdfs"]!=r["pdfs"]:
   invalid(f"BOA: XML difiere del JSON en {ident}")
  day=datetime.strptime(r["date"],"%Y%m%d").date()
  grouped[(day,int(r["num"]))].append((ident,r))
 keys=sorted(grouped)
 if (len(keys)!=21 or keys[0]!=(START,190) or keys[-1]!=(END,210)
    or any(b[1]!=a[1]+1 for a,b in zip(keys,keys[1:]))):
  invalid(f"BOA: números ordinarios no continuos {keys}")
 checks=[];issues=[]
 for (day,num),rows in keys:
  notices=[]
  for ident,r in rows:
   kind=employment(r["title"])
   if kind:
    target=r["pdfs"][0]
    checks.append(target)
    notices.append({"id":f"AO-2026-{ident}","province":"Aragón (BOA)",
      "title":r["title"][:2800],"entity":r["agency"][:500],
      "date":day.strftime("%d/%m/%Y"),"bulletin":str(num),"type":kind,"url":target})
  print(f"BOA {day}: n.º {num}, {len(rows)} anuncios, {len(notices)} candidatas",flush=True)
  issues.append({"day":day,"number":str(num),"read":len(rows),"notices":notices})
 if not checks:invalid("BOA: sin anuncios de empleo público")
 with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(check_pdf,sorted(set(checks))))
 return publish_audit(SOURCE,"Aragón (BOA)",issues,today=END)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path)
 args=p.parse_args();write_output(args.output,audit())
