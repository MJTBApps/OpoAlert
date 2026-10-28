#!/usr/bin/env python3
"""CIDO feed validator: complete API pagination and exact 30-day record window.

Unlike BOP readers this validates a public jobs catalogue, not every bulletin.
"""
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit
import argparse
import json
import re
from cido_cataluna import BASE, PROVINCES, CidoCoverageError


def validate(folder:Path, today:date|None=None):
    checked=set()
    for pid,(province,slug) in PROVINCES.items():
        data=json.loads((folder/(slug+".json")).read_text(encoding="utf-8"))
        if data.get("source")!=BASE or data.get("province")!=province or not data.get("scope","").startswith("CIDO:"):
            raise CidoCoverageError(f"Fuente CIDO {province} incorrecta")
        cov=data.get("coverage",{})
        history=data.get("historyCoverage",{})
        if (not cov.get("complete") or cov.get("status")!="api_filtered_full_pagination"
              or not history.get("complete") or history.get("basis")!="CIDO_API_LAST_DOCUMENT_30_DAYS"):
            raise CidoCoverageError(f"{province}: no se ha validado paginacion/fuente")
        first=date.fromisoformat(history["rangeStart"])
        end=date.fromisoformat(history["rangeEnd"])
        if (end-first).days!=29 or today is not None and end!=today:
            raise CidoCoverageError(f"{province}: periodo invalido")
        published=[date.fromisoformat(x) for x in history.get("publicationDates",[])]
        other=[date.fromisoformat(x) for x in history.get("nonPublicationDates",[])]
        if (len(published)!=len(set(published)) or len(other)!=len(set(other))
              or set(published)&set(other)
              or set(published)|set(other)!={first+timedelta(days=i) for i in range(30)}):
            raise CidoCoverageError(f"{province}: faltan fechas")
        notices=data.get("notices")
        if not isinstance(notices,list):
            raise CidoCoverageError(f"{province}: no hay datos")
        if len(notices)!=cov.get("opportunities") or len(notices)!=cov.get("announcementsRead") or len(notices)!=history.get("announcementsRead"):
            raise CidoCoverageError(f"{province}: contadores incoherentes")
        for row in notices:
            ident=row.get("id","")
            url=row.get("url","")
            date_row=datetime.strptime(row["date"],"%d/%m/%Y").date()
            match=re.fullmatch(r"CIDO"+str(pid)+r"-(\d+)",ident)
            if (ident in checked or not match or url!=f"https://cido.diba.cat/oposicions/{match.group(1)}"
                  or row.get("province")!=province or row.get("bulletin")!="CIDO"
                  or row.get("type") not in ("Plaza / oposición","Bolsa de trabajo")
                  or date_row not in set(published)
                  or not str(row.get("entity","")).strip() or not str(row.get("title","")).strip()):
                raise CidoCoverageError(f"{province}: registro alterado {ident}")
            checked.add(ident)
        when=datetime.fromisoformat(data["lastCheckedUTC"])
        now=datetime.now(timezone.utc)
        if when.tzinfo is None or not -timedelta(minutes=5)<=now-when<=timedelta(hours=3):
            raise CidoCoverageError(f"{province}: auditoria desactualizada")
        print(f"VALIDADO CIDO {province}: {len(notices)} procesos en {first}..{end}",flush=True)
    if not checked:
        raise CidoCoverageError("CIDO: cuatro regiones sin ninguna convocatoria")
    return checked


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--directory",type=Path,required=True)
    parser.add_argument("--require-today",action="store_true")
    args=parser.parse_args()
    validate(args.directory,date.today() if args.require_today else None)
