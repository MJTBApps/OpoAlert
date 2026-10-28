#!/usr/bin/env python3
"""Validate Girona BOP 30-day feed. Fail closed before publication."""
from __future__ import annotations
import argparse
from datetime import date,datetime,timedelta,timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from provincial_common import ProvincialCoverageError
from girona_bop import BASE, PROVINCE, PDF_PATH


def validate(file:Path,expected_end:date|None=None)->dict:
    data=json.loads(file.read_text(encoding="utf-8"))
    if data.get("source")!=BASE or data.get("province")!=PROVINCE:
        raise ProvincialCoverageError("Girona: provincia/fuente incorrecta")
    history=data.get("historyCoverage",{})
    coverage=data.get("coverage",{})
    if not history.get("complete") or not coverage.get("complete") or coverage.get("status")!="complete":
        raise ProvincialCoverageError("Girona: auditoria incompleta")
    start=date.fromisoformat(history["rangeStart"])
    end=date.fromisoformat(history["rangeEnd"])
    if (end-start).days !=29 or expected_end is not None and end!=expected_end:
        raise ProvincialCoverageError("Girona: periodo no corresponde a 30 dias")
    def dates(key):
        rows=[date.fromisoformat(x) for x in history.get(key,[])]
        if len(rows)!=len(set(rows)):raise ProvincialCoverageError("Girona: fechas duplicadas")
        return set(rows)
    pub=dates("publicationDates")
    no=dates("nonPublicationDates")
    days={start+timedelta(days=i) for i in range(30)}
    if pub & no or pub | no != days or len(pub)<8:
        raise ProvincialCoverageError("Girona: calendario de publicaciones incompleto")
    nums=[int(x) for x in history.get("bulletins",[])]
    if len(nums)!=len(pub) or sorted(nums)!=list(range(min(nums),max(nums)+1)):
        raise ProvincialCoverageError("Girona: numeracion de BOP discontinua")
    if history.get("issuesRead")!=len(nums):
        raise ProvincialCoverageError("Girona: numero de ediciones incoherente")
    notices=data.get("notices")
    if not isinstance(notices,list) or not notices:
        raise ProvincialCoverageError("Girona: no hay anuncios candidatos")
    ids=set()
    for item in notices:
        ident=item.get("id","")
        m=re.fullmatch(r"GI-(\d{4})-(\d{3})-(\d{5})",ident)
        date_=datetime.strptime(item["date"],"%d/%m/%Y").date()
        p=urlsplit(item.get("url",""))
        pdf=PDF_PATH.fullmatch(p.path)
        if (not m or ident in ids or date_ not in pub or item.get("province")!=PROVINCE
                or not str(item.get("entity","")).strip() or not str(item.get("title","")).strip()
                or item.get("bulletin")!=str(int(m.group(2)))
                or p.scheme!="https" or p.hostname!="ssl4.ddgi.cat" or p.port not in (None,443)
                or p.query or p.fragment or p.username or not pdf
                or pdf.group(1)!=m.group(1) or int(pdf.group(2))!=int(m.group(2))
                or pdf.group(3)!="".join(m.groups())
                or int(m.group(2)) not in nums):
            raise ProvincialCoverageError(f"Girona: ficha o PDF no verificable {ident}")
        ids.add(ident)
    total=coverage.get("announcementsRead")
    if (not isinstance(total,int) or total<len(notices)
          or coverage.get("opportunities")!=len(notices)
          or history.get("opportunities")!=len(notices)
          or history.get("announcementsRead")!=total):
        raise ProvincialCoverageError("Girona: recuentos incoherentes")
    last=datetime.fromisoformat(data["lastCheckedUTC"])
    age=datetime.now(timezone.utc)-last
    if last.tzinfo is None or age>timedelta(hours=3) or age < -timedelta(minutes=5):
        raise ProvincialCoverageError("Girona: auditoria obsoleta")
    print(f"VALIDADO GIRONA: {len(nums)} ediciones, {total} edictos, {len(notices)} candidatos, {start}..{end}",flush=True)
    return data


if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--file",type=Path,required=True)
    cli.add_argument("--require-today",action="store_true")
    a=cli.parse_args()
    validate(a.file,date.today() if a.require_today else None)
