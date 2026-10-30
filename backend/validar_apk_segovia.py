#!/usr/bin/env python3
"""Independent offline validation of a full official 30-day Segovia BOP snapshot."""
from __future__ import annotations
import argparse,json,re
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit
SOURCE="https://www.dipsegovia.es/bop"
def check(root:Path):
    x=json.loads((root/"SG.json").read_text(encoding="utf-8"))
    c=x.get("coverage",{});h=x.get("historyCoverage",{})
    if x.get("schemaVersion")!=1 or x.get("source")!=SOURCE or x.get("province")!="Segovia":
        raise ValueError("Segovia: fuente, versión o provincia incorrecta")
    if c.get("complete") is not True or h.get("complete") is not True:
        raise ValueError("Segovia: fuente no auditada")
    if (h.get("rangeStart"),h.get("rangeEnd"))!=("2026-09-30","2026-10-29"):
        raise ValueError("Segovia: no cubre los 30 días naturales completos")
    dates=[date.fromisoformat(x) for x in h.get("publicationDates",[])]
    expected=[date(2026,9,30)+timedelta(days=i) for i in range(30)
              if (date(2026,9,30)+timedelta(days=i)).weekday() in (0,2,4)]
    if dates!=expected or h.get("issuesRead")!=13 or c.get("pagesVisited")!=13:
        raise ValueError("Segovia: falta una edición ordinaria en el calendario")
    nums=list(map(int,h.get("bulletins",[])))
    if nums!=list(range(117,130)) or c.get("bulletin")!="129":
        raise ValueError("Segovia: falta o se repite una edición numerada")
    articles=h.get("editionArticleCounts",[])
    if len(articles)!=13 or any(not isinstance(n,int) or n<5 for n in articles):
        raise ValueError("Segovia: no se han comprobado todos los sumarios")
    if sum(articles)!=c.get("announcementsRead") or sum(articles)<180:
        raise ValueError("Segovia: recuento de sumarios no coincide")
    pdfs=h.get("editionPDFs",[])
    if len(pdfs)!=13 or len(set(pdfs))!=13 or h.get("originalPdfPagesRead",0)<150:
        raise ValueError("Segovia: no se verificaron todos los PDF originales")
    for u in pdfs:
        p=urlsplit(u)
        if (p.scheme!="https" or p.hostname!="www.dipsegovia.es" or
            not re.fullmatch(r"/documents/39512/[a-f0-9-]{20,80}",p.path) or
            p.query or p.fragment):
            raise ValueError("Segovia: edición PDF fuera de sede oficial")
    notices=x.get("notices",[])
    if len(notices)<1 or len(notices)!=c.get("opportunities") or len({n["id"] for n in notices})!=len(notices):
        raise ValueError("Segovia: candidatas vacías, duplicadas o incoherentes")
    for n in notices:
        day=datetime.strptime(n["date"],"%d/%m/%Y").date()
        if (not re.fullmatch(r"SG-2026-[0-9a-f]{18}",n.get("id",""))
            or n.get("province")!="Segovia"
            or day not in dates or int(n["bulletin"])!=nums[dates.index(day)]
            or n.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
            or not 5<len(str(n.get("title","")))<1000
            or not 4<len(str(n.get("entity","")))<500
            or n.get("url")!=pdfs[dates.index(day)]
            or not isinstance(n.get("pageInPdf"),int) or n["pageInPdf"]<2):
            raise ValueError("Segovia: aviso no vinculado a edición original "+repr(n.get("id")))
    print("SEGOVIA VALIDADA: 13 boletines, "+str(sum(articles))+" anuncios, "
        +str(len(notices))+" candidatas, PDF originales de las 13 ediciones",flush=True)
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--root",type=Path,required=True)
    args=a.parse_args()
    check(args.root)
