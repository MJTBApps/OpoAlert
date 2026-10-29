#!/usr/bin/env python3
"""Independent strict verification of the three Extremadura private APK snapshots."""
from __future__ import annotations
import argparse,json,re
from datetime import datetime,date
from pathlib import Path
from urllib.parse import parse_qs,urlsplit

SOURCES={
 "BD":("Badajoz","https://www.dip-badajoz.es/bop/","www.dip-badajoz.es",
       r"^BD-2026-\d{5,9}$",22,516,45),
 "CC":("Cáceres","https://bop.dip-caceres.es/bop/index.html","bop.dip-caceres.es",
       r"^CC-2026-\d{1,7}$",22,548,34),
 "EX":("Extremadura (DOE)","https://doe.juntaex.es/","doe.juntaex.es",
       r"^EX-2026-[A-Z0-9]{8}$",22,527,50),
}
def pdf_is_official(code,record,url):
    path=url.path
    if code=="BD":
        return (bool(re.fullmatch(r"/ficheros/bop/bopedictos/2026-(?:09|10)-\d{2}(?:000000|150000)_[Rr]?\d{1,8}\.pdf",path))
           and not url.query)
    if code=="CC":
        return (path=="/bop/services/anuncios/contenidoPdfIdAnuncio"
            and parse_qs(url.query)=={"csv":["BOP-2026-"+record["id"].split("-")[-1]]})
    if code=="EX":
        suffix=record["id"].split("-")[-1]
        return (bool(re.fullmatch(r"/pdfs/doe/2026/\d{1,4}0[oe]/[A-Z0-9]{8}\.pdf",path,re.I))
            and path.rsplit("/",1)[-1].upper()==suffix+".PDF" and not url.query)
    return False

def validate(root:Path):
    total_issues=total_read=total_candidates=0
    seen_all=set()
    for code,(province,source,host,identifier,issues_expected,read_expected,candidates_expected) in SOURCES.items():
        d=json.loads((root/(code+".json")).read_text(encoding="utf-8"))
        c=d.get("coverage",{});h=d.get("historyCoverage",{})
        if (d.get("schemaVersion")!=1 or d.get("province")!=province or d.get("source")!=source
            or c.get("complete") is not True or h.get("complete") is not True or c.get("status")!="complete"
            or h.get("rangeStart")!="2026-09-30" or h.get("rangeEnd")!="2026-10-29"
            or c.get("announcementsRead")!=read_expected or h.get("announcementsRead")!=read_expected
            or h.get("issuesRead")!=issues_expected or c.get("pagesVisited")!=issues_expected):
            raise ValueError(f"{code}: fuente, fechas o contadores no validados")
        stamp=datetime.fromisoformat(d["lastCheckedUTC"])
        if stamp.tzinfo is None or stamp.date()!=date(2026,10,29):
            raise ValueError(f"{code}: fecha auditoría incorrecta")
        dates=h.get("publicationDates",[]);numbers=h.get("bulletins",[])
        if len(dates)!=issues_expected or len(numbers)!=issues_expected or dates!=sorted(dates):
            raise ValueError(f"{code}: calendario del mes incompleto")
        if len(set(zip(dates,numbers)))!=issues_expected:
            raise ValueError(f"{code}: ediciones duplicadas")
        rows=d.get("notices",[])
        if (len(rows)!=candidates_expected or c.get("opportunities")!=len(rows)
            or h.get("opportunities")!=len(rows) or len({x.get("id") for x in rows})!=len(rows)):
            raise ValueError(f"{code}: avisos ausentes o repetidos")
        for n in rows:
            u=urlsplit(n.get("url",""))
            if (not re.fullmatch(identifier,n.get("id",""))
                or n.get("id") in seen_all
                or n.get("province")!=province or n.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
                or not n.get("entity","").strip() or not n.get("title","").strip()
                or n.get("bulletin") not in numbers
                or u.scheme!="https" or u.hostname!=host or u.port not in (None,443)
                or u.username or u.fragment or not pdf_is_official(code,n,u)):
                raise ValueError(f"{code}: anuncio o PDF sin procedencia confirmada: {n.get('id')}")
            try:
                announced=datetime.strptime(n["date"],"%d/%m/%Y").date().isoformat()
            except Exception as e:raise ValueError(f"{code}: fecha del anuncio inválida") from e
            if announced not in dates:raise ValueError(f"{code}: anuncio fuera de auditoría")
            seen_all.add(n["id"])
        total_issues+=issues_expected;total_read+=read_expected;total_candidates+=len(rows)
        print(f"EXTREMADURA {code}: {issues_expected} ediciones, {read_expected} anuncios, {len(rows)} candidatas",flush=True)
    print(f"EXTREMADURA OK: {total_issues} ediciones, {total_read} anuncios y {total_candidates} candidatas verificadas",flush=True)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    args=p.parse_args()
    validate(args.root)
