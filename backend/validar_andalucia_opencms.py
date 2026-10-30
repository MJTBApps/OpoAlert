#!/usr/bin/env python3
"""Independent consistency gate for Granada and Sevilla 30-day BOP archives."""
from __future__ import annotations
import argparse,json,re
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from provincial_common import ProvincialCoverageError
from andalucia_opencms_bop import SOURCES,home,pdf_url_ok
from clm_common import numbering_ok

def validate(path:Path,province:str,today:date|None=None)->dict:
    if province not in SOURCES:raise ProvincialCoverageError("Provincia no admitida")
    s=SOURCES[province]
    data=json.loads(path.read_text(encoding="utf-8"))
    history=data.get("historyCoverage",{})
    cov=data.get("coverage",{})
    if data.get("source")!=home(s) or data.get("province")!=s.province:
        raise ProvincialCoverageError(f"{s.province}: origen incorrecto")
    if (cov.get("complete") is not True or history.get("complete") is not True
        or cov.get("status")!="complete"):
        raise ProvincialCoverageError(f"{s.province}: auditoria no completa")
    start=date.fromisoformat(history["rangeStart"])
    end=date.fromisoformat(history["rangeEnd"])
    if (end-start).days!=29 or (today is not None and end!=today):
        raise ProvincialCoverageError(f"{s.province}: periodo de 30 dias incorrecto")
    stamp=datetime.fromisoformat(data["lastCheckedUTC"])
    if stamp.tzinfo is None or not -timedelta(minutes=5)<=datetime.now(timezone.utc)-stamp<=timedelta(hours=4):
        raise ProvincialCoverageError(f"{s.province}: auditoria caducada")
    published=history.get("publicationDates",[])
    absent=history.get("nonPublicationDates",[])
    numbers=history.get("bulletins",[])
    pdfs=history.get("editionPDFs",[])
    expected={(start+timedelta(days=i)).isoformat() for i in range(30)}
    if (not isinstance(published,list) or len(published)<15 or published!=sorted(set(published))
        or not isinstance(absent,list) or len(absent)!=len(set(absent))
        or set(published)&set(absent) or set(published)|set(absent)!=expected
        or not isinstance(numbers,list) or len(numbers)!=len(published)
        or len(pdfs)!=len(published) or len(set(pdfs))!=len(pdfs)
        or history.get("issuesRead")!=len(published)
        or (end-date.fromisoformat(published[-1])).days>4):
        raise ProvincialCoverageError(f"{s.province}: historial o PDF faltantes")
    for x in pdfs:
        if not pdf_url_ok(s,x,True):raise ProvincialCoverageError(f"{s.province}: PDF de boletin no oficial")
    if not numbering_ok([(date.fromisoformat(d),int(n)) for d,n in zip(published,numbers)]):
        raise ProvincialCoverageError(f"{s.province}: saltos en la numeracion")
    if cov.get("bulletin")!=numbers[-1]:
        raise ProvincialCoverageError(f"{s.province}: ultimo numero inconsistente")
    notices=data.get("notices")
    if not isinstance(notices,list) or not notices or len(notices)>5000:
        raise ProvincialCoverageError(f"{s.province}: candidatas ausentes o excesivas")
    if (not isinstance(cov.get("announcementsRead"),int)
        or cov["announcementsRead"]<len(notices)
        or cov["announcementsRead"]!=history.get("announcementsRead")
        or cov.get("opportunities")!=len(notices)
        or history.get("opportunities")!=len(notices)
        or cov.get("pagesVisited")!=history.get("pagesVisited")
        or not isinstance(cov.get("pagesVisited"),int)
        or cov["pagesVisited"]<len(published)):
        raise ProvincialCoverageError(f"{s.province}: recuentos incoherentes")
    ids=set()
    nums=dict(zip(published,numbers))
    for n in notices:
        m=re.fullmatch(re.escape(s.code)+r"-(\d{4})-(\d{3})(\d{3})",n.get("id",""))
        d=datetime.strptime(n["date"],"%d/%m/%Y").date()
        if (m is None or n["id"] in ids or d.isoformat() not in nums
            or int(m.group(1))!=d.year or int(m.group(2))!=int(nums[d.isoformat()])
            or n.get("bulletin")!=nums[d.isoformat()]
            or n.get("province")!=s.province
            or not n.get("entity","").strip() or not n.get("title","").strip()
            or n.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
            or not pdf_url_ok(s,n.get("url",""))):
            raise ProvincialCoverageError(f"{s.province}: registro o PDF no valido {n.get('id')}")
        ids.add(n["id"])
    print(f"{s.province.upper()} VALIDADO: {len(published)} boletines, "
      f"{cov['announcementsRead']} anuncios, {len(notices)} convocatorias candidatas",flush=True)
    return data

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--province",required=True,choices=list(SOURCES))
    p.add_argument("--file",type=Path,required=True)
    p.add_argument("--require-today",action="store_true")
    args=p.parse_args()
    validate(args.file,args.province,date.today() if args.require_today else None)
