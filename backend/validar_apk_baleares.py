#!/usr/bin/env python3
"""Independent fail-closed validation before bundling audited Balearic BOIB JSON."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from datetime import date,datetime
from urllib.parse import urlsplit
SOURCE="https://www.caib.es/eboibfront/es"
PROVINCE="Illes Balears (BOIB)"
DOC_RE=re.compile(r"^/eboibfront/pdf/es/2026/(\d{1,3})/(\d{5,9})$")
ELI_RE=re.compile(r"^/eboibfront/eli/[a-zA-Z0-9_()/.+-]+/dof/spa/pdf$")
def audit(directory:Path):
 d=json.loads((directory/"IB.json").read_text(encoding="utf-8"))
 c=d.get("coverage",{});h=d.get("historyCoverage",{})
 if (d.get("schemaVersion")!=1 or d.get("source")!=SOURCE
     or d.get("province")!=PROVINCE or c.get("complete") is not True
     or c.get("status")!="complete" or h.get("complete") is not True
     or h.get("rangeStart")!="2026-09-30" or h.get("rangeEnd")!="2026-10-29"
     or h.get("issuesRead")!=16 or c.get("pagesVisited")!=16
     or c.get("bulletin")!="138"):
  raise ValueError("BOIB: fuente / periodo / auditoría incorrectos")
 t=datetime.fromisoformat(d.get("lastCheckedUTC",""))
 if t.tzinfo is None or t.date()!=date(2026,10,29):
  raise ValueError("BOIB: fecha de validación antigua")
 nums=h.get("bulletins",[]);days=h.get("publicationDates",[])
 if (nums!=[str(n) for n in range(123,139)] or len(days)!=16
     or days!=sorted(days) or days[0]!="2026-10-01" or days[-1]!="2026-10-29"):
  raise ValueError("BOIB: número o secuencia de publicaciones incompleta")
 expected=[("2026-10-01",2),("2026-10-12",1),("2026-10-21",1)]
 for val,count in expected:
  if days.count(val)!=count:raise ValueError(f"BOIB: falta calendario ordinario/extras {val}")
 rowcount=c.get("announcementsRead");notices=d.get("notices",[])
 if (rowcount!=1076 or h.get("announcementsRead")!=1076
     or not isinstance(notices,list) or len(notices)!=158
     or c.get("opportunities")!=158 or h.get("opportunities")!=158
     or len({x.get("id") for x in notices})!=len(notices)):
  raise ValueError("BOIB: anuncios de las 16 ediciones incompletos")
 seen=set()
 for n in notices:
  ident=n.get("id");u=urlsplit(n.get("url",""))
  try:when=datetime.strptime(n["date"],"%d/%m/%Y").date().isoformat()
  except Exception as e:raise ValueError("BOIB: fecha inválida en aviso") from e
  m=DOC_RE.fullmatch(u.path)
  valid_pdf=bool((m and str(int(m[1]))==str(n.get("bulletin"))) or ELI_RE.fullmatch(u.path))
  if (not re.fullmatch(r"IB-2026-\d{1,8}",str(ident))
      or ident in seen or n.get("province")!=PROVINCE
      or n.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
      or not n.get("title","").strip() or not n.get("entity","").strip()
      or when not in days or str(n.get("bulletin")) not in nums
      or u.scheme!="https" or u.hostname!="www.caib.es" or u.port not in (None,443)
      or u.fragment or u.query or u.username or not valid_pdf):
   raise ValueError(f"BOIB: enlace oficial o registro inválido {ident}")
  seen.add(ident)
 print("BOIB VALIDADO: 16 ediciones #123–138 (incluidas 3 extraordinarias), "
       "1076 anuncios, 158 PDF de coincidencias originales",flush=True)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--root",required=True,type=Path)
 a=p.parse_args();audit(a.root)
