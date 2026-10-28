#!/usr/bin/env python3
"""Independent integrity gate for the 30-day BOP Teruel data file."""
from __future__ import annotations
import argparse,json,re
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from teruel_bop import HOME,PROVINCE,safe_detail_url
from provincial_common import ProvincialCoverageError

def validate(path:Path,required_day:date|None=None)->dict:
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("source")!=HOME or data.get("province")!=PROVINCE:
        raise ProvincialCoverageError("Teruel: fuente o provincia no oficial")
    cov=data.get("coverage",{})
    history=data.get("historyCoverage",{})
    if not (cov.get("complete") is True and history.get("complete") is True
            and cov.get("status")=="complete"):
        raise ProvincialCoverageError("Teruel: historial no auditado")
    start=date.fromisoformat(history["rangeStart"])
    end=date.fromisoformat(history["rangeEnd"])
    if (end-start).days!=29 or (required_day is not None and required_day!=end):
        raise ProvincialCoverageError("Teruel: no se han recorrido 30 dias exactos")
    published=history.get("publicationDates",[])
    absent=history.get("nonPublicationDates",[])
    if (not isinstance(published,list) or not isinstance(absent,list)
        or len(published)<15 or published!=sorted(set(published))
        or len(absent)!=len(set(absent))
        or set(published)&set(absent)
        or set(published)|set(absent)!={(start+timedelta(days=i)).isoformat() for i in range(30)}
        or history.get("issuesRead")!=len(published)):
        raise ProvincialCoverageError("Teruel: calendario de 30 dias sin cobertura completa")
    nums=[int(n) for n in history.get("bulletins",[])]
    if len(nums)!=len(published) or cov.get("bulletin")!=str(nums[-1]):
        raise ProvincialCoverageError("Teruel: numeros de boletin incongruentes")
    for i in range(1,len(nums)):
        if date.fromisoformat(published[i]).year==date.fromisoformat(published[i-1]).year:
            if nums[i]!=nums[i-1]+1:
                raise ProvincialCoverageError("Teruel: faltan numeros intermedios")
        elif nums[i]!=1:
            raise ProvincialCoverageError("Teruel: nuevo año sin reinicio de BOP")
    stamp=datetime.fromisoformat(data["lastCheckedUTC"])
    if stamp.tzinfo is None or not -timedelta(minutes=5)<=datetime.now(timezone.utc)-stamp<=timedelta(hours=3):
        raise ProvincialCoverageError("Teruel: auditoria no reciente")
    notices=data.get("notices")
    if not isinstance(notices,list) or not notices:
        raise ProvincialCoverageError("Teruel: no hay candidatas")
    ids=set()
    number_by_day=dict(zip(published,nums))
    for item in notices:
        ident=item.get("id","")
        d=datetime.strptime(item["date"],"%d/%m/%Y").date()
        if (not re.fullmatch(r"TE-\d{4}-\d{4}",ident)
            or ident in ids or d.isoformat() not in number_by_day
            or item.get("bulletin")!=str(number_by_day[d.isoformat()])
            or item.get("province")!=PROVINCE
            or not str(item.get("title","")).strip()
            or not str(item.get("entity","")).strip()
            or not safe_detail_url(item.get("url",""))
            or item.get("type") not in ("Bolsa de trabajo","Plaza / oposición")):
            raise ProvincialCoverageError(f"Teruel: candidato no validado {ident}")
        ids.add(ident)
    total=cov.get("announcementsRead")
    pages=cov.get("pagesVisited")
    if (not isinstance(total,int) or total<len(notices)
        or total!=history.get("announcementsRead")
        or cov.get("opportunities")!=len(notices)
        or history.get("opportunities")!=len(notices)
        or not isinstance(pages,int) or pages<len(published)
        or pages!=history.get("pagesVisited")):
        raise ProvincialCoverageError("Teruel: totales de auditoria inconsistentes")
    print(f"TERUEL VALIDADO: {len(published)} ediciones, {total} anuncios, "
          f"{len(notices)} candidatas, {start}..{end}",flush=True)
    return data

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--file",type=Path,required=True)
    p.add_argument("--require-today",action="store_true")
    args=p.parse_args()
    validate(args.file,date.today() if args.require_today else None)
