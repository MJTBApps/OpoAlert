#!/usr/bin/env python3
"""Independent 30-day audit of the official Almeria/Jaen Pandora BOP feeds."""
from __future__ import annotations
import argparse,json,re
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit
from provincial_common import ProvincialCoverageError
from pandora_bop import GAZETTES,archive_url,is_almeria_edict,pdf_url

def validate(path:Path,province:str,required_day:date|None=None)->dict:
    if province not in GAZETTES:raise ProvincialCoverageError("BOP andaluz desconocido")
    g=GAZETTES[province]
    data=json.loads(path.read_text(encoding="utf-8"))
    if data.get("source")!=archive_url(g) or data.get("province")!=g.name:
        raise ProvincialCoverageError(f"{g.name}: identificador de fuente inesperado")
    cov=data.get("coverage",{})
    hist=data.get("historyCoverage",{})
    if not (cov.get("complete") is True and hist.get("complete") is True
            and cov.get("status")=="complete"):
        raise ProvincialCoverageError(f"{g.name}: sin cobertura auditada")
    start=date.fromisoformat(hist["rangeStart"])
    end=date.fromisoformat(hist["rangeEnd"])
    if (end-start).days!=29 or (required_day is not None and end!=required_day):
        raise ProvincialCoverageError(f"{g.name}: no hay 30 dias naturales")
    checked=datetime.fromisoformat(data["lastCheckedUTC"])
    if (checked.tzinfo is None
        or not -timedelta(minutes=5)<=datetime.now(timezone.utc)-checked<=timedelta(hours=4)):
        raise ProvincialCoverageError(f"{g.name}: consulta desactualizada o invalida")
    pub=hist.get("publicationDates",[])
    absent=hist.get("nonPublicationDates",[])
    nums=hist.get("bulletins",[])
    pdfs=hist.get("editionPDFs",[])
    if (not isinstance(pub,list) or len(pub)<15 or pub!=sorted(set(pub))
        or not isinstance(absent,list) or len(absent)!=len(set(absent))
        or len(nums)!=len(pub) or len(pdfs)!=len(pub)
        or hist.get("issuesRead")!=len(pub)
        or set(pub)&set(absent)
        or set(pub)|set(absent)!={(start+timedelta(days=i)).isoformat() for i in range(30)}
        or end-date.fromisoformat(pub[-1])>timedelta(days=4)
        or date.fromisoformat(pub[0])-start>timedelta(days=4)):
        raise ProvincialCoverageError(f"{g.name}: archivo mensual tiene fechas incompletas")
    numbers=[int(x) for x in nums]
    for i in range(1,len(numbers)):
        if date.fromisoformat(pub[i]).year==date.fromisoformat(pub[i-1]).year:
            if numbers[i]!=numbers[i-1]+1:
                raise ProvincialCoverageError(f"{g.name}: falta un número oficial de boletín")
        elif numbers[i]!=1:
            raise ProvincialCoverageError(f"{g.name}: año nuevo sin reinicio")
        if date.fromisoformat(pub[i])-date.fromisoformat(pub[i-1])>timedelta(days=5):
            raise ProvincialCoverageError(f"{g.name}: faltan ediciones entre fechas")
    if cov.get("bulletin")!=nums[-1]:
        raise ProvincialCoverageError(f"{g.name}: el ultimo numero BOP no coincide")
    for u in pdfs:
        pdf_url(g,u)
    if len(set(pdfs))!=len(pdfs):
        raise ProvincialCoverageError(f"{g.name}: se repiten documentos de ediciones")
    total=cov.get("announcementsRead")
    pages=cov.get("pagesVisited")
    notices=data.get("notices")
    if (not isinstance(notices,list) or not notices
        or not isinstance(total,int) or total<len(notices) or total<50
        or total!=hist.get("announcementsRead")
        or not isinstance(pages,int) or pages<len(pub)
        or pages!=hist.get("pagesVisited")
        or hist.get("opportunities")!=len(notices)
        or cov.get("opportunities")!=len(notices)
        or not isinstance(hist.get("archiveIndexPagesRead"),int)
        or hist["archiveIndexPagesRead"]<1
        or not isinstance(hist.get("archiveTotalIssues"),int)
        or hist["archiveTotalIssues"]<1000):
        raise ProvincialCoverageError(f"{g.name}: estadísticas de anuncios o páginas incoherentes")
    seen=set()
    lookup=dict(zip(pub,nums))
    for notice in notices:
        ident=notice.get("id","")
        day=datetime.strptime(notice["date"],"%d/%m/%Y").date()
        url=notice.get("url","")
        if (not re.fullmatch(re.escape(g.code)+r"-\d{4}-\d{5}",ident)
            or ident in seen or day.isoformat() not in lookup
            or int(ident.split("-")[1])!=day.year
            or notice.get("bulletin")!=lookup[day.isoformat()]
            or notice.get("province")!=g.name
            or not str(notice.get("title","")).strip()
            or not str(notice.get("entity","")).strip()
            or notice.get("type") not in ("Plaza / oposición","Bolsa de trabajo")
            or not (is_almeria_edict(url) if g.almeria and "/bop/services/manager/edicto/" in url else pdf_url_ok(g,url))):
            raise ProvincialCoverageError(f"{g.name}: anuncio o PDF original no valido {ident}")
        seen.add(ident)
    print(f"{g.name.upper()} VALIDADO: {len(pub)} ediciones, {total} anuncios, "
          f"{len(notices)} candidatas, {start} a {end}",flush=True)
    return data

def pdf_url_ok(g,u:str)->bool:
    try:pdf_url(g,u);return True
    except ProvincialCoverageError:return False

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--province",choices=list(GAZETTES),required=True)
    p.add_argument("--file",type=Path,required=True)
    p.add_argument("--require-today",action="store_true")
    args=p.parse_args()
    validate(args.file,args.province,date.today() if args.require_today else None)
