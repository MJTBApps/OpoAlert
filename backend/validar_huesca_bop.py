#!/usr/bin/env python3
"""Validate Huesca BOP 30-day feed independently before any publication."""
from __future__ import annotations
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit
import argparse,json,re
from provincial_common import ProvincialCoverageError
from huesca_bop import HOME,PROVINCE,PDF_PATH


def validate(path:Path,required_day:date|None=None)->dict:
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("source")!=HOME or data.get("province")!=PROVINCE:
        raise ProvincialCoverageError("BOP Huesca: source o provincia incorrecta")
    cov=data.get("coverage",{})
    his=data.get("historyCoverage",{})
    if cov.get("complete") is not True or his.get("complete") is not True or cov.get("status")!="complete":
        raise ProvincialCoverageError("BOP Huesca: historial incompleto")
    first=date.fromisoformat(his["rangeStart"])
    last=date.fromisoformat(his["rangeEnd"])
    if (last-first).days!=29 or (required_day is not None and last!=required_day):
        raise ProvincialCoverageError("BOP Huesca: periodo no es 30 dias")
    published=his.get("publicationDates",[])
    absent=his.get("nonPublicationDates",[])
    if (not isinstance(published,list) or published!=sorted(set(published))
            or len(published)<15 or len(absent)!=len(set(absent))
            or set(published)&set(absent)
            or set(published)|set(absent)!={(first+timedelta(days=i)).isoformat() for i in range(30)}
            or his.get("issuesRead")!=len(published)):
        raise ProvincialCoverageError("BOP Huesca: calendario oficial incompleto")
    numbered=[int(n) for n in his.get("bulletins",[])]
    if len(numbered)!=len(published):
        raise ProvincialCoverageError("BOP Huesca: recuento numeros incorrecto")
    for i in range(1,len(numbered)):
        if date.fromisoformat(published[i]).year==date.fromisoformat(published[i-1]).year:
            if numbered[i]!=numbered[i-1]+1:
                raise ProvincialCoverageError("BOP Huesca: salto de numero")
        elif numbered[i]!=1:
            raise ProvincialCoverageError("BOP Huesca: cambio de año no validado")
    if cov.get("bulletin")!=str(numbered[-1]):
        raise ProvincialCoverageError("BOP Huesca: ultimo BOP no coincide")
    notices=data.get("notices")
    if not isinstance(notices,list) or not notices:
        raise ProvincialCoverageError("BOP Huesca: ninguna convocatoria candidata")
    ids=set()
    for item in notices:
        identity=re.fullmatch(r"HU-(\d{4})-(\d{3})(\d{3})",item.get("id",""))
        day=datetime.strptime(item["date"],"%d/%m/%Y").date()
        p=urlsplit(item.get("url",""))
        if (identity is None or item["id"] in ids or day.isoformat() not in published
              or day.year!=int(identity.group(1))
              or item.get("bulletin")!=str(int(identity.group(2)))
              or item.get("province")!=PROVINCE
              or not str(item.get("title","")).strip() or not str(item.get("entity","")).strip()
              or p.scheme!="https" or p.hostname!="bop.dphuesca.es"
              or p.port not in (None,443) or not p.path.startswith(PDF_PATH)
              or not p.path.lower().endswith(".pdf") or p.query or p.fragment or p.username):
            raise ProvincialCoverageError(f"BOP Huesca: candidato no verificado: {item.get('id')}")
        ids.add(item["id"])
    read=cov.get("announcementsRead")
    pages=cov.get("pagesVisited")
    if (not isinstance(read,int) or read<len(notices)
            or read!=his.get("announcementsRead")
            or cov.get("opportunities")!=len(notices)
            or his.get("opportunities")!=len(notices)
            or not isinstance(pages,int) or pages<len(published)
            or pages!=his.get("pagesVisited")):
        raise ProvincialCoverageError("BOP Huesca: recuentos incongruentes")
    stamp=datetime.fromisoformat(data["lastCheckedUTC"])
    if stamp.tzinfo is None or not -timedelta(minutes=5)<=datetime.now(timezone.utc)-stamp<=timedelta(hours=3):
        raise ProvincialCoverageError("BOP Huesca: auditoria obsoleta")
    print(f"HUESCA VALIDADO: {len(published)} ediciones, {read} anuncios, "
          f"{len(notices)} candidatas, {first}..{last}",flush=True)
    return data


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--file",required=True,type=Path)
    p.add_argument("--require-today",action="store_true")
    args=p.parse_args()
    validate(args.file,date.today() if args.require_today else None)
