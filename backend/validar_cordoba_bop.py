#!/usr/bin/env python3
"""Independent calendar and original PDF validation for Cordoba BOP."""
from __future__ import annotations
import argparse,json,re
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from provincial_common import ProvincialCoverageError
from cordoba_bop import HOME,PROVINCE,pdf_valid
def validate(path:Path,today:date|None=None)->dict:
 data=json.loads(path.read_text(encoding="utf-8"))
 cov=data.get("coverage",{})
 hist=data.get("historyCoverage",{})
 if data.get("province")!=PROVINCE or data.get("source")!=HOME:
  raise ProvincialCoverageError("Cordoba: fuente no oficial")
 if cov.get("complete") is not True or hist.get("complete") is not True or cov.get("status")!="complete":
  raise ProvincialCoverageError("Cordoba: auditoria incompleta")
 start=date.fromisoformat(hist["rangeStart"])
 end=date.fromisoformat(hist["rangeEnd"])
 if (end-start).days!=29 or (today and today!=end):
  raise ProvincialCoverageError("Cordoba: historico no cubre 30 dias")
 stamp=datetime.fromisoformat(data["lastCheckedUTC"])
 if stamp.tzinfo is None or not -timedelta(minutes=5)<=datetime.now(timezone.utc)-stamp<=timedelta(hours=4):
  raise ProvincialCoverageError("Cordoba: auditoria caducada")
 dates=hist.get("publicationDates",[])
 absent=hist.get("nonPublicationDates",[])
 nums=hist.get("bulletins",[])
 pdfs=hist.get("editionPDFs",[])
 if (not isinstance(dates,list) or dates!=sorted(set(dates)) or len(dates)<15
  or len(set(absent))!=len(absent) or set(absent)&set(dates)
  or set(absent)|set(dates)!={(start+timedelta(days=i)).isoformat() for i in range(30)}
  or len(nums)!=len(dates) or len(pdfs)!=len(dates)
  or len(set(pdfs))!=len(pdfs) or hist.get("issuesRead")!=len(dates)
  or (end-date.fromisoformat(dates[-1])).days>4):
  raise ProvincialCoverageError("Cordoba: faltan boletines o fechas")
 if any(int(b)!=int(a)+1 for a,b in zip(nums,nums[1:])):
  raise ProvincialCoverageError("Cordoba: salto de número BOP")
 if cov.get("bulletin")!=nums[-1]:
  raise ProvincialCoverageError("Cordoba: ultimo BOP diferente")
 for x,d in zip(pdfs,dates):
  day=date.fromisoformat(d)
  valid,code=pdf_valid(x,day,"S")
  if not valid or int(code)!=int(dict(zip(dates,nums))[d]):
   raise ProvincialCoverageError("Cordoba: PDF sumario incorrecto")
 notices=data.get("notices",[])
 if not notices or len(notices)>5000:raise ProvincialCoverageError("Cordoba: faltan convocatorias")
 if (cov.get("announcementsRead")!=hist.get("announcementsRead")
  or not isinstance(cov.get("announcementsRead"),int)
  or cov["announcementsRead"]<len(notices)
  or cov.get("opportunities")!=len(notices)
  or hist.get("opportunities")!=len(notices)
  or cov.get("pagesVisited")!=hist.get("pagesVisited")
  or hist.get("pagesVisited")!=len(dates)):
  raise ProvincialCoverageError("Cordoba: recuentos de anuncios no coinciden")
 numbers=dict(zip(dates,nums))
 seen=set()
 for row in notices:
  ident=row.get("id","")
  day=datetime.strptime(row["date"],"%d/%m/%Y").date()
  m=re.fullmatch(r"CO-(\d{4})-(\d{1,7})",ident)
  valid,pdf_id=pdf_valid(row.get("url",""),day)
  if (m is None or ident in seen or int(m.group(1))!=day.year
   or int(m.group(2))!=int(pdf_id or "-1") or not valid
   or day.isoformat() not in numbers
   or row.get("bulletin")!=numbers[day.isoformat()]
   or row.get("province")!=PROVINCE or not row.get("entity","").strip()
   or not row.get("title","").strip()
   or row.get("type") not in ("Plaza / oposición","Bolsa de trabajo")):
   raise ProvincialCoverageError(f"Cordoba: anuncio o PDF no valido {ident}")
  seen.add(ident)
 print(f"CORDOBA VALIDADO: {len(dates)} ediciones, {cov['announcementsRead']} anuncios, "
   f"{len(notices)} candidatas",flush=True)
 return data
if __name__=="__main__":
 p=argparse.ArgumentParser()
 p.add_argument("--file",type=Path,required=True)
 p.add_argument("--require-today",action="store_true")
 args=p.parse_args()
 validate(args.file,date.today() if args.require_today else None)
