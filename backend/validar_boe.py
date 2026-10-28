#!/usr/bin/env python3
"""Revalidación independiente de un feed BOE antes de su publicación."""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path

from boe_nacional import SOURCE, PROVINCE, ID_RE, official_pdf, BoeCoverageError


def validate(path: Path, today: date | None = None) -> dict:
    value=json.loads(path.read_text(encoding="utf-8"))
    if value.get("source")!=SOURCE or value.get("province")!=PROVINCE:
        raise BoeCoverageError("Origen nacional inesperado")
    history=value.get("historyCoverage") or {}
    coverage=value.get("coverage") or {}
    if history.get("complete") is not True or coverage.get("complete") is not True:
        raise BoeCoverageError("BOE nacional no auditado")
    start=date.fromisoformat(history["rangeStart"])
    end=date.fromisoformat(history["rangeEnd"])
    if (end-start).days!=29 or (today is not None and end!=today):
        raise BoeCoverageError("BOE: historico distinto de 30 dias exactos")
    pubs=history.get("publicationDates",[])
    nopubs=history.get("nonPublicationDates",[])
    dates=set(date.fromisoformat(x) for x in pubs+nopubs)
    if (len(pubs)+len(nopubs)!=30 or len(dates)!=30 or
        dates!={start+timedelta(days=i) for i in range(30)}):
        raise BoeCoverageError("BOE: calendario incompleto o repetido")
    if any(date.fromisoformat(day).weekday()!=6 for day in nopubs):
        raise BoeCoverageError("BOE: se ha marcado como no publicado un dia no domingo")
    issues=history.get("bulletins",[])
    if len(issues)<len(pubs) or len(issues)!=history.get("issuesRead") or not all(str(i).isdigit() for i in issues):
        raise BoeCoverageError("BOE: falta al menos un diario")
    if not isinstance(value.get("notices"),list):
        raise BoeCoverageError("BOE: lista de anuncios ausente")
    seen=set()
    for n in value["notices"]:
        identifier=n["id"]
        day=datetime.strptime(n["date"],"%d/%m/%Y").date()
        if (not ID_RE.fullmatch(identifier) or identifier in seen or
            day.isoformat() not in pubs or n.get("province")!=PROVINCE or
            not n.get("title","").strip() or not n.get("entity","").strip() or
            not official_pdf(n["url"],identifier,day) or
            str(n.get("bulletin","")) not in [str(x) for x in issues]):
            raise BoeCoverageError(f"BOE: ficha no verificable {identifier}")
        seen.add(identifier)
    read=coverage.get("announcementsRead")
    if (not isinstance(read,int) or read < len(seen) or
        coverage.get("opportunities")!=len(seen) or
        history.get("announcementsRead")!=read or
        history.get("opportunities")!=len(seen)):
        raise BoeCoverageError("BOE: totales no coinciden")
    stamp=datetime.fromisoformat(value["lastCheckedUTC"].replace("Z","+00:00"))
    if (stamp.tzinfo is None or stamp > datetime.now(timezone.utc)+timedelta(minutes=5)
        or stamp < datetime.now(timezone.utc)-timedelta(hours=4)):
        raise BoeCoverageError("BOE: verificacion antigua")
    print(f"VALIDADO BOE: {len(pubs)} dias publicados, "
          f"{len(issues)} diarios, {read} anuncios II.B, "
          f"{len(seen)} candidatos, {start} a {end}",flush=True)
    return value


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--file",type=Path,required=True)
    parser.add_argument("--require-today",action="store_true")
    args=parser.parse_args()
    validate(args.file,date.today() if args.require_today else None)


if __name__=="__main__":
    main()
