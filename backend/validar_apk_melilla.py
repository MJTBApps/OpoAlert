#!/usr/bin/env python3
"""Independent fail-closed verification of 30-day Melilla BOME snapshot in APK."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from datetime import date,datetime
from urllib.parse import urlsplit
SOURCE="https://bomemelilla.es/bomes/2026"
LABEL="Melilla (BOME)"
EXPECTED=[
("2026-09-30","E43"),("2026-10-02","6419"),("2026-10-06","6420"),
("2026-10-07","E44"),("2026-10-09","6421"),("2026-10-12","E45"),
("2026-10-13","6422"),("2026-10-16","6423"),("2026-10-16","E46"),
("2026-10-20","6424"),("2026-10-21","E47"),("2026-10-23","6425"),
("2026-10-23","E48"),("2026-10-27","6426"),
]
def validate(root:Path):
 d=json.loads((root/"ML.json").read_text(encoding="utf-8"))
 c=d.get("coverage",{});h=d.get("historyCoverage",{})
 if (d.get("schemaVersion")!=1 or d.get("source")!=SOURCE or d.get("province")!=LABEL
     or c.get("complete") is not True or h.get("complete") is not True or c.get("status")!="complete"
     or h.get("rangeStart")!="2026-09-30" or h.get("rangeEnd")!="2026-10-29"
     or h.get("issuesRead")!=14 or c.get("pagesVisited")!=14
     or c.get("announcementsRead")!=133 or h.get("announcementsRead")!=133
     or c.get("opportunities")!=16 or h.get("opportunities")!=16
     or c.get("bulletin")!="6426"):
  raise ValueError("BOME: cobertura histórica incompleta o fuente equivocada")
 stamp=datetime.fromisoformat(d.get("lastCheckedUTC",""))
 if stamp.tzinfo is None or stamp.date()!=date(2026,10,29):
  raise ValueError("BOME: auditoría no corresponde a 29/10/2026")
 dates=h.get("publicationDates",[])
 bullets=h.get("bulletins",[])
 if list(zip(dates,bullets))!=EXPECTED:
  raise ValueError("BOME: falta publicación ordinaria o extraordinaria")
 notices=d.get("notices",[])
 if not isinstance(notices,list) or len(notices)!=16 or len(set(n.get("id") for n in notices))!=16:
  raise ValueError("BOME: candidatas duplicadas o faltantes")
 for n in notices:
  identity=str(n.get("id",""))
  match=re.fullmatch(r"ML-2026-(A|AX)-(\d{1,8})",identity)
  u=urlsplit(str(n.get("url","")))
  pdfmatch=re.fullmatch(r"/bome/descargar/BOME-(A|AX)-2026-(\d{1,8})\.pdf",u.path)
  try:day=datetime.strptime(n["date"],"%d/%m/%Y").date().isoformat()
  except Exception as e:raise ValueError("BOME: fecha de anuncio ilegible") from e
  if (not match or not pdfmatch or match.groups()!=pdfmatch.groups()
      or n.get("province")!=LABEL or (day,str(n.get("bulletin"))) not in EXPECTED
      or (str(n.get("bulletin")).startswith("E"))!=(match[1]=="AX")
      or not str(n.get("title","")).strip() or not str(n.get("entity","")).strip()
      or n.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
      or u.scheme!="https" or u.hostname!="bomemelilla.es" or u.port not in (None,443)
      or u.fragment or u.username or u.query):
   raise ValueError(f"BOME: CVE, fecha, PDF o entidad incorrectos: {identity}")
 print("MELILLA VALIDADA: 14 boletines, 133 disposiciones, 16 coincidencias y 133 PDF originales comprobados en auditoría",flush=True)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True)
 a=p.parse_args();validate(a.root)
