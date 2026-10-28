#!/usr/bin/env python3
"""Reject incomplete Barcelona BOP feeds before GitHub Pages deployment."""
from __future__ import annotations
import argparse
from datetime import date,datetime,timedelta,timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from provincial_common import ProvincialCoverageError
from barcelona_bop import BASE, PROVINCE, PDF_PREFIX,publishes


def validate(path:Path,expected_end:date|None=None)->dict:
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("source")!=BASE or data.get("province")!=PROVINCE:
        raise ProvincialCoverageError("Barcelona: identificacion o portal BOPB incorrecto")
    history=data.get("historyCoverage",{})
    cov=data.get("coverage",{})
    if not history.get("complete") or not cov.get("complete") or cov.get("status")!="complete":
        raise ProvincialCoverageError("Barcelona: auditoria de 30 dias incompleta")
    first=date.fromisoformat(history["rangeStart"]);last=date.fromisoformat(history["rangeEnd"])
    if (last-first).days!=29 or expected_end is not None and last!=expected_end:
        raise ProvincialCoverageError("Barcelona: 30 dias o fecha final incorrecta")
    pub=history.get("publicationDates",[])
    no=history.get("nonPublicationDates",[])
    if (len(pub)!=len(set(pub)) or len(no)!=len(set(no))
            or set(pub)&set(no) or set(pub)|set(no)!={(first+timedelta(days=i)).isoformat() for i in range(30)}
            or len(pub)<8 or pub!=sorted(pub) or history.get("bulletins")!=pub):
        raise ProvincialCoverageError("Barcelona: fechas no verificadas")
    if set(pub)!={(first+timedelta(days=i)).isoformat() for i in range(30) if publishes(first+timedelta(days=i))}:
        raise ProvincialCoverageError("Barcelona: calendario oficial incoherente")
    if history.get("issuesRead")!=len(pub):
        raise ProvincialCoverageError("Barcelona: numero de boletines incoherente")
    notices=data.get("notices")
    if not isinstance(notices,list) or not notices:
        raise ProvincialCoverageError("Barcelona: sin convocatorias")
    ids=set()
    for item in notices:
        ident=item.get("id","")
        u=urlsplit(item.get("url",""))
        day=datetime.strptime(item["date"],"%d/%m/%Y").date()
        if (not re.fullmatch(r"BA-\d{12}",ident) or ident in ids
                or item.get("province")!=PROVINCE or day.isoformat() not in pub
                or item.get("bulletin")!=item.get("date")
                or not str(item.get("title","")).strip() or not str(item.get("entity","")).strip()
                or u.scheme!="https" or u.hostname!="bop.diba.cat" or u.port not in (None,443)
                or not u.path.startswith(PDF_PREFIX) or not re.fullmatch(r"\d+",u.path.removeprefix(PDF_PREFIX))
                or u.query or u.fragment or u.username):
            raise ProvincialCoverageError(f"Barcelona: ficha candidata invalida: {ident}")
        ids.add(ident)
    total=history.get("announcementsRead")
    pages=history.get("pagesVisited")
    if (not isinstance(total,int) or total<len(notices) or total!=cov.get("announcementsRead")
           or not isinstance(pages,int) or pages<len(pub) or cov.get("pagesVisited")!=pages
           or history.get("opportunities")!=len(notices) or cov.get("opportunities")!=len(notices)):
        raise ProvincialCoverageError("Barcelona: recuento de boletines y edictos incoherente")
    checked=datetime.fromisoformat(data["lastCheckedUTC"])
    if checked.tzinfo is None or not -timedelta(minutes=5)<=datetime.now(timezone.utc)-checked<=timedelta(hours=3):
        raise ProvincialCoverageError("Barcelona: auditoria anticuada")
    print(f"VALIDADO BARCELONA: {len(pub)} ediciones, {total} edictos y {len(notices)} candidatas en {first}..{last}",flush=True)
    return data


if __name__=="__main__":
    cli=argparse.ArgumentParser()
    cli.add_argument("--file",type=Path,required=True)
    cli.add_argument("--require-today",action="store_true")
    args=cli.parse_args()
    validate(args.file,date.today() if args.require_today else None)
