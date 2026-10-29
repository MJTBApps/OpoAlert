#!/usr/bin/env python3
"""Verify all 4 Basque 30-day official snapshot assets before packaging Android APK."""
from __future__ import annotations
import argparse,json,re
from datetime import date,datetime
from pathlib import Path
from urllib.parse import urlsplit
SOURCE={
 "AR":("Álava","https://e-s.araba.eus/BOTHA/Inicio/SGBO5001.aspx",13,301,13,"e-s.araba.eus"),
 "BI":("Bizkaia","https://www.bizkaia.eus/es/bob",22,700,55,"www.bizkaia.eus"),
 "GP":("Gipuzkoa","https://egoitza.gipuzkoa.eus/es/bog",22,737,32,"egoitza.gipuzkoa.eus"),
 "PV":("País Vasco (BOPV)","https://api.euskadi.eus/bopv/administrative-acts",21,None,None,"www.euskadi.eus"),
}
def pdf_auth(code,row,url):
 p=url.path
 tail=row["id"].split("2026-",1)[-1]
 if code=="AR":
  m=re.fullmatch(r"/BOTHA/Boletines/(?:pdfni/)?2026/(\d{2,3})/2026_(\d{2,3})_(\d{5})_C\.pdf",p,re.I)
  return bool(m and m[1]==m[2] and m[3]==tail and m[1]==str(row["bulletin"]))
 if code=="BI":
  m=re.fullmatch(r"/lehendakaritza/Bao_bob/2026/(\d{2})/(\d{2})/([IVX]{1,5}-\d{1,7})_cas\.pdf",p,re.I)
  return bool(m and m[3].upper()==tail and int(m[1])==int(row["date"][3:5]) and int(m[2])==int(row["date"][:2]))
 if code=="GP":
  m=re.fullmatch(r"/gao-bog/castell/bog/2026/(\d{2})/(\d{2})/c(26\d{5})\.pdf",p,re.I)
  return bool(m and m[3]==tail and int(m[1])==int(row["date"][3:5]) and int(m[2])==int(row["date"][:2]))
 if code=="PV":
  m=re.fullmatch(r"/bopv2/datos/2026/(\d{2})/(26\d{5})a\.pdf",p,re.I)
  return bool(m and int(m[2][2:])==int(tail) and int(m[1])==int(row["date"][3:5]))
 return False
def validate(directory:Path):
 total_read=total_issues=total_candidates=0
 unique=set()
 for code,(province,source,expected_issues,expected_read,expected_candidates,host) in SOURCE.items():
  d=json.loads((directory/(code+".json")).read_text(encoding="utf-8"))
  h=d.get("historyCoverage",{});c=d.get("coverage",{})
  if (d.get("schemaVersion")!=1 or d.get("province")!=province or d.get("source")!=source
      or c.get("complete") is not True or h.get("complete") is not True or c.get("status")!="complete"
      or h.get("rangeStart")!="2026-09-30" or h.get("rangeEnd")!="2026-10-29"
      or c.get("pagesVisited")!=expected_issues or h.get("issuesRead")!=expected_issues):
   raise ValueError(f"{code}: edición o fuente no comprobadas")
  checked=datetime.fromisoformat(d.get("lastCheckedUTC",""))
  if checked.tzinfo is None or checked.date()!=date(2026,10,29):
   raise ValueError(f"{code}: auditoría de otra fecha")
  read=c.get("announcementsRead")
  if (read!=h.get("announcementsRead") or (expected_read is not None and read!=expected_read)
       or (code=="PV" and read<330)):
   raise ValueError(f"{code}: anuncios sin cobertura del día 29")
  issue_dates=h.get("publicationDates",[])
  numbers=h.get("bulletins",[])
  if (len(issue_dates)!=expected_issues or len(numbers)!=expected_issues or len(set(issue_dates))!=expected_issues
      or issue_dates!=sorted(issue_dates)
      or issue_dates[0]!="2026-09-30" or issue_dates[-1]<("2026-10-28" if code=="AR" else "2026-10-29")
      or len(set(numbers))!=expected_issues):
   raise ValueError(f"{code}: calendario incompleto")
  if code=="PV" and (numbers[0]!="187" or numbers[-1]!="207"):
   raise ValueError("BOPV: falta último boletín publicado")
  if code=="AR" and (numbers[0]!="112" or numbers[-1]!="124"):
   raise ValueError("Álava: falta algún BOTHA")
  if code=="BI" and (numbers[0]!="187" or numbers[-1]!="208"):
   raise ValueError("Bizkaia: falta algún BOB")
  if code=="GP" and (numbers[0]!="186" or numbers[-1]!="207"):
   raise ValueError("Gipuzkoa: falta algún BOG")
  docs=d.get("notices",[])
  if (not isinstance(docs,list) or len(docs)!=c.get("opportunities")
      or len(docs)!=h.get("opportunities")
      or expected_candidates is not None and len(docs)!=expected_candidates
      or code=="PV" and len(docs)<27):
   raise ValueError(f"{code}: número de candidatas inválido")
  for row in docs:
   u=urlsplit(row.get("url",""))
   try:dt=datetime.strptime(row["date"],"%d/%m/%Y").date().isoformat()
   except Exception as e:raise ValueError("Fecha de anuncio incorrecta") from e
   if (not row.get("id","").startswith(code+"-2026-")
      or row["id"] in unique
      or row.get("province")!=province
      or row.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
      or not row.get("title","").strip() or not row.get("entity","").strip()
      or dt not in issue_dates or str(row.get("bulletin")) not in numbers
      or u.scheme!="https" or u.hostname!=host or u.port not in (None,443)
      or u.username or u.query or u.fragment or not pdf_auth(code,row,u)):
    raise ValueError(f"{code}: identidad, fecha o PDF del anuncio no cotejables: {row.get('id')}")
   unique.add(row["id"])
  print(f"NORTE VALIDADO: {code} {expected_issues} boletines, {read} anuncios, {len(docs)} posibles convocatorias",flush=True)
  total_read+=read;total_issues+=expected_issues;total_candidates+=len(docs)
 print(f"NORTE PRIVADO OK: 4 fuentes de Euskadi, {total_issues} boletines, {total_read} anuncios, {total_candidates} candidatas",flush=True)
if __name__=="__main__":
 ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True)
 args=ap.parse_args();validate(args.root)
