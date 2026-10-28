#!/usr/bin/env python3
"""Valida cobertura 30 dias del BOPT antes de hacer visible el feed en Android."""
import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from provincial_common import ProvincialCoverageError
from tarragona import SOURCE, PROVINCE, PDF_PREFIX


def validate(file: Path, expected_end: date | None = None):
    data = json.loads(file.read_text(encoding="utf-8"))
    if data.get("source") != SOURCE or data.get("province") != PROVINCE:
        raise ProvincialCoverageError("Tarragona: identificacion de fuente erronea")
    coverage = data.get("coverage", {})
    history = data.get("historyCoverage", {})
    if not coverage.get("complete") or not history.get("complete"):
        raise ProvincialCoverageError("Tarragona: auditoria incompleta")
    first = date.fromisoformat(history["rangeStart"])
    last = date.fromisoformat(history["rangeEnd"])
    if (last-first).days != 29 or expected_end is not None and last != expected_end:
        raise ProvincialCoverageError("Tarragona: calendario incorrecto")
    def parsed_unique(key):
        raw = history.get(key, [])
        values = [date.fromisoformat(x) for x in raw]
        if len(values) != len(set(values)):
            raise ProvincialCoverageError("Tarragona: fechas repetidas")
        return set(values)
    publication = parsed_unique("publicationDates")
    skipped = parsed_unique("nonPublicationDates")
    all_days = {first+timedelta(days=i) for i in range(30)}
    if publication & skipped or (publication | skipped) != all_days or len(publication) < 8:
        raise ProvincialCoverageError("Tarragona: falta alguna fecha de los 30 dias")
    if history.get("bulletins") != sorted(x.isoformat() for x in publication):
        raise ProvincialCoverageError("Tarragona: las ediciones no coinciden con las fechas")
    if history.get("issuesRead") != len(publication):
        raise ProvincialCoverageError("Tarragona: numero de ediciones incorrecto")
    notices = data.get("notices")
    if not isinstance(notices, list):
        raise ProvincialCoverageError("Tarragona: faltan anuncios")
    ids = set()
    for row in notices:
        ident = row.get("id", "")
        p = urlsplit(row.get("url", ""))
        posted = datetime.strptime(row["date"], "%d/%m/%Y").date()
        original = p.path.removeprefix(PDF_PREFIX)
        if (ident in ids or not re.fullmatch(r"TA-\d{4}-\d{5}", ident)
                or posted not in publication or row.get("province") != PROVINCE
                or row.get("bulletin") != row.get("date")
                or not str(row.get("title", "")).strip()
                or not str(row.get("entity", "")).strip()
                or not re.fullmatch(r"\d+", original)
                or p.scheme != "https" or p.hostname != "aplicacions.dipta.cat"
                or p.port not in (None,443) or p.query or p.fragment or p.username):
            raise ProvincialCoverageError(f"Tarragona: anuncio no verificado {ident!r}")
        ids.add(ident)
    read = history.get("announcementsRead")
    if (not isinstance(read, int) or read < len(notices)
            or read != coverage.get("announcementsRead")
            or len(notices) != history.get("opportunities")
            or len(notices) != coverage.get("opportunities")
            or not isinstance(history.get("pagesVisited"),int)
            or history["pagesVisited"] < 30):
        raise ProvincialCoverageError("Tarragona: contadores incoherentes")
    checked = datetime.fromisoformat(data["lastCheckedUTC"])
    now = datetime.now(timezone.utc)
    if checked.tzinfo is None or not -timedelta(minutes=5) <= now-checked <= timedelta(hours=3):
        raise ProvincialCoverageError("Tarragona: ultima revision sin validez")
    print(f"VALIDADO Tarragona: {len(publication)} dias publicados, "
          f"{read} edictos, {len(notices)} candidatas entre {first} y {last}", flush=True)
    return data


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--file",required=True,type=Path)
    parser.add_argument("--require-today",action="store_true")
    args=parser.parse_args()
    validate(args.file, date.today() if args.require_today else None)
