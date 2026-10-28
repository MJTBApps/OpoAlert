#!/usr/bin/env python3
"""Independently reject incomplete BOP Cadiz coverage or non-official links."""
from __future__ import annotations
import argparse,json,re
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from provincial_common import ProvincialCoverageError
from cadiz_bop import HOME,PROVINCE,validate_doc

def validate(path:Path,required_end:date|None=None)->dict:
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("source")!=HOME or data.get("province")!=PROVINCE:
        raise ProvincialCoverageError("Cadiz: origen o provincia incorrectos")
    coverage=data.get("coverage",{})
    history=data.get("historyCoverage",{})
    if (coverage.get("complete") is not True or coverage.get("status")!="complete"
        or history.get("complete") is not True):
        raise ProvincialCoverageError("Cadiz: auditoria incompleta")
    start=date.fromisoformat(history["rangeStart"])
    end=date.fromisoformat(history["rangeEnd"])
    if (end-start).days!=29 or (required_end is not None and end!=required_end):
        raise ProvincialCoverageError("Cadiz: no constan 30 dias exactos")
    pub=history.get("publicationDates",[])
    absent=history.get("nonPublicationDates",[])
    if (not isinstance(pub,list) or len(pub)<15 or pub!=sorted(set(pub))
        or not isinstance(absent,list) or len(absent)!=len(set(absent))
        or set(pub)&set(absent) or set(pub)|set(absent)!={
            (start+timedelta(days=i)).isoformat() for i in range(30)}):
        raise ProvincialCoverageError("Cadiz: faltan fechas del intervalo")
    nums=history.get("bulletins",[])
    if (len(nums)!=len(pub) or history.get("issuesRead")!=len(pub)
        or coverage.get("bulletin")!=nums[-1]):
        raise ProvincialCoverageError("Cadiz: numeros de ediciones incorrectos")
    for a,b in zip(nums,nums[1:]):
        if not a.isdigit() or not b.isdigit() or int(b)!=int(a)+1:
            raise ProvincialCoverageError("Cadiz: saltos en boletines")
    stamp=datetime.fromisoformat(data["lastCheckedUTC"])
    if (stamp.tzinfo is None or not -timedelta(minutes=5)<=
        datetime.now(timezone.utc)-stamp<=timedelta(hours=3)):
        raise ProvincialCoverageError("Cadiz: auditoria no reciente")
    notices=data.get("notices",[])
    if not isinstance(notices,list) or not notices:
        raise ProvincialCoverageError("Cadiz: candidatas vacias")
    day_number=dict(zip(pub,nums))
    ids=set()
    for n in notices:
        ident=n.get("id","")
        day=datetime.strptime(n["date"],"%d/%m/%Y").date()
        if (not re.fullmatch(r"CA-\d{4}-\d{4,7}",ident) or ident in ids
            or day.isoformat() not in day_number
            or n.get("bulletin")!=day_number[day.isoformat()]
            or n.get("province")!=PROVINCE
            or not n.get("entity","").strip()
            or not n.get("title","").strip()
            or n.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
            or not validate_doc(n.get("url",""))):
            raise ProvincialCoverageError(f"Cadiz: anuncio irregular {ident}")
        ids.add(ident)
    count=coverage.get("announcementsRead")
    pages=coverage.get("pagesVisited")
    if (not isinstance(count,int) or count<len(notices)
        or count!=history.get("announcementsRead")
        or not isinstance(pages,int) or pages!=len(pub)
        or pages!=history.get("pagesVisited")
        or coverage.get("opportunities")!=len(notices)
        or history.get("opportunities")!=len(notices)
        or not history.get("sectionsRead")):
        raise ProvincialCoverageError("Cadiz: estadisticas de auditoria inconsistentes")
    print(f"CADIZ VERIFICADO: {len(pub)} boletines y {count} anuncios, "
          f"{len(notices)} candidatas entre {start} y {end}",flush=True)
    return data

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--file",required=True,type=Path)
    parser.add_argument("--require-today",action="store_true")
    args=parser.parse_args()
    validate(args.file,date.today() if args.require_today else None)
