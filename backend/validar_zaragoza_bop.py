#!/usr/bin/env python3
"""Independent integrity gate for official BOP Zaragoza 30-day records."""
from __future__ import annotations
import argparse
from datetime import date,datetime,timedelta,timezone
import json,re
from pathlib import Path
from provincial_common import ProvincialCoverageError
from zaragoza_bop import PROVINCE,SOURCE,safe_pdf

def validate(path:Path,expected_end:date|None=None)->dict:
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("source")!=SOURCE or data.get("province")!=PROVINCE:
        raise ProvincialCoverageError("Zaragoza: fuente oficial o provincia incorrecta")
    cov=data.get("coverage",{})
    hist=data.get("historyCoverage",{})
    if cov.get("complete") is not True or hist.get("complete") is not True or cov.get("status")!="complete":
        raise ProvincialCoverageError("Zaragoza: cobertura incompleta")
    start=date.fromisoformat(hist["rangeStart"])
    end=date.fromisoformat(hist["rangeEnd"])
    if (end-start).days!=29 or (expected_end is not None and end!=expected_end):
        raise ProvincialCoverageError("Zaragoza: el historico no comprende 30 fechas exactas")
    stamp=datetime.fromisoformat(data["lastCheckedUTC"])
    if stamp.tzinfo is None or not -timedelta(minutes=5)<=datetime.now(timezone.utc)-stamp<=timedelta(hours=3):
        raise ProvincialCoverageError("Zaragoza: fecha de auditoria no valida")
    pub=hist.get("publicationDates",[])
    absent=hist.get("nonPublicationDates",[])
    nums=hist.get("bulletins",[])
    if (not isinstance(pub,list) or len(pub)<20 or pub!=sorted(set(pub))
        or len(nums)!=len(pub)
        or not isinstance(absent,list) or len(absent)!=len(set(absent))
        or set(pub)&set(absent)
        or set(pub)|set(absent)!={(start+timedelta(days=i)).isoformat() for i in range(30)}
        or hist.get("issuesRead")!=len(pub)
        or end-date.fromisoformat(pub[-1])>timedelta(days=4)):
        raise ProvincialCoverageError("Zaragoza: calendario de boletines incompleto")
    numbers=[int(n) for n in nums]
    if (not all(1<=n<=366 for n in numbers) or cov.get("bulletin")!=nums[-1]):
        raise ProvincialCoverageError("Zaragoza: numero de BOP incorrecto")
    for i in range(1,len(numbers)):
        if date.fromisoformat(pub[i]).year==date.fromisoformat(pub[i-1]).year:
            if numbers[i]!=numbers[i-1]+1:
                raise ProvincialCoverageError("Zaragoza: hay saltos en la numeracion del BOP")
        elif numbers[i]!=1:
            raise ProvincialCoverageError("Zaragoza: reinicio de anualidad no validado")
    sections=hist.get("sectionsRead",{})
    if not isinstance(sections,dict) or len(sections)<2 or not any("SEXTA" in x.upper() for x in sections):
        raise ProvincialCoverageError("Zaragoza: solo parte de las secciones BOP auditadas")
    total=cov.get("announcementsRead")
    pages=cov.get("pagesVisited")
    notices=data.get("notices")
    if (not isinstance(notices,list) or len(notices)<1
        or not isinstance(total,int) or total<len(notices) or total<100
        or total!=hist.get("announcementsRead")
        or not isinstance(pages,int) or pages!=hist.get("pagesVisited")
        or pages!=2*len(pub)
        or cov.get("opportunities")!=len(notices)
        or hist.get("opportunities")!=len(notices)):
        raise ProvincialCoverageError("Zaragoza: totales o paginacion incoherentes")
    lookup=dict(zip(pub,nums))
    ids=set()
    for rec in notices:
        ident=rec.get("id","")
        if not re.fullmatch(r"ZA-\d{9}",ident) or ident in ids:
            raise ProvincialCoverageError("Zaragoza: identificador no unico")
        d=datetime.strptime(rec["date"],"%d/%m/%Y").date()
        if (d.isoformat() not in lookup or rec.get("bulletin")!=lookup[d.isoformat()]
            or rec.get("province")!=PROVINCE or not rec.get("title","").strip()
            or not rec.get("entity","").strip() or not safe_pdf(rec.get("url",""))
            or rec.get("type") not in ("Plaza / oposición","Bolsa de trabajo")):
            raise ProvincialCoverageError(f"Zaragoza: convocatoria no verificable {ident}")
        ids.add(ident)
    print(f"ZARAGOZA VALIDADA: {len(pub)} ediciones, {total} anuncios, {len(notices)} candidatas "
          f"entre {start} y {end}",flush=True)
    return data

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--file",type=Path,required=True)
    p.add_argument("--require-today",action="store_true")
    args=p.parse_args()
    validate(args.file,date.today() if args.require_today else None)
