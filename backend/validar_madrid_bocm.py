#!/usr/bin/env python3
"""Independent validation of a Madrid 30-day BOCM feed, including extraordinary issues."""
from __future__ import annotations
import argparse,json,re
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from provincial_common import ProvincialCoverageError
from madrid_bocm import CATALOG,PROVINCE,pdf_ok

def bad(msg):raise ProvincialCoverageError("Madrid BOCM: "+msg)

def validate(path:Path,today:date|None=None)->dict:
    d=json.loads(path.read_text(encoding="utf-8"))
    c=d.get("coverage",{})
    h=d.get("historyCoverage",{})
    if d.get("source")!=CATALOG or d.get("province")!=PROVINCE:bad("fuente incorrecta")
    if c.get("complete") is not True or h.get("complete") is not True or c.get("status")!="complete":
        bad("auditoría incompleta")
    start=date.fromisoformat(h["rangeStart"])
    end=date.fromisoformat(h["rangeEnd"])
    if (end-start).days!=29 or (today is not None and end!=today):bad("período no cubre 30 días exactos")
    stamp=datetime.fromisoformat(d["lastCheckedUTC"])
    age=datetime.now(timezone.utc)-stamp
    if stamp.tzinfo is None or not -timedelta(minutes=5)<=age<=timedelta(hours=5):
        bad("auditoría no reciente")
    dates=h.get("publicationDates",[])
    absent=h.get("nonPublicationDates",[])
    numbers=h.get("bulletins",[])
    pdfs=h.get("editionPDFs",[])
    methods=h.get("parseMethods",[])
    if (not isinstance(dates,list) or len(dates)<20 or
        len(numbers)!=len(dates) or len(pdfs)!=len(dates) or len(methods)!=len(dates)
        or h.get("issuesRead")!=len(dates) or len(set(numbers))!=len(numbers)
        or len(set(pdfs))!=len(pdfs) or sorted(dates)!=dates):
        bad("números, fechas o PDF de las ediciones incompletos")
    unique_dates=set(dates)
    if (not isinstance(absent,list) or len(absent)!=len(set(absent))
        or unique_dates & set(absent)
        or unique_dates | set(absent)!={(start+timedelta(days=i)).isoformat() for i in range(30)}):
        bad("días publicados/no publicados no suman 30")
    if (end-date.fromisoformat(dates[-1])).days>4:
        bad("falta la publicación más reciente")
    if any(int(n)<1 or int(n)>366 for n in numbers):bad("números imposibles")
    if any(int(b)!=int(a)+1 for a,b in zip(numbers,numbers[1:])):
        bad("salto en numeración consecutiva de los boletines")
    for p,dt,n,method in zip(pdfs,dates,numbers,methods):
        if (not pdf_ok(p,date.fromisoformat(dt),int(n))
            or method not in ("xml","html")):
            bad(f"boletín {n} carece de PDF oficial correcto")
    if c.get("bulletin")!=numbers[-1]:bad("último número incorrecto")
    notices=d.get("notices")
    if not isinstance(notices,list) or not notices or len(notices)>5000:
        bad("avisos ausentes o excesivos")
    if (c.get("announcementsRead")!=h.get("announcementsRead")
        or not isinstance(c.get("announcementsRead"),int) or c["announcementsRead"]<len(notices)
        or c.get("opportunities")!=len(notices) or h.get("opportunities")!=len(notices)
        or c.get("pagesVisited")!=len(numbers) or h.get("pagesVisited")!=len(numbers)):
        bad("contadores no coinciden")
    issue_by_date={}
    for day,num in zip(dates,numbers):
        issue_by_date.setdefault(day,set()).add(str(num))
    ids=set()
    for n in notices:
        ident=n.get("id","")
        m=re.fullmatch(r"MD-(\d{8})-(\d{1,5})",ident)
        try:day=datetime.strptime(n["date"],"%d/%m/%Y").date()
        except (KeyError,ValueError,TypeError):bad("fecha inválida")
        if (not m or m.group(1)!=day.strftime("%Y%m%d") or ident in ids
           or day.isoformat() not in issue_by_date
           or n.get("bulletin") not in issue_by_date[day.isoformat()]
           or n.get("province")!=PROVINCE
           or not n.get("title","").strip() or len(n["title"])>2800
           or not n.get("entity","").strip() or len(n["entity"])>400
           or n.get("type") not in ("Plaza / oposición","Bolsa de trabajo")
           or not pdf_ok(n.get("url",""),day)
           or not n["url"].endswith(f"BOCM-{day:%Y%m%d}-{int(m.group(2))}.PDF")):
            bad(f"identificador, emisor o PDF no comprobados: {ident}")
        ids.add(ident)
    print(f"MADRID VALIDADO: {len(numbers)} boletines, "
          f"{c['announcementsRead']} anuncios, {len(notices)} candidatas "
          f"({methods.count('html')} ediciones con respaldo HTML)",flush=True)
    return d

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--file",type=Path,required=True)
    p.add_argument("--require-today",action="store_true")
    a=p.parse_args()
    validate(a.file,date.today() if a.require_today else None)
