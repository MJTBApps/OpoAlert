#!/usr/bin/env python3
"""Independent verification of 30 days and official Huelva BOP announcement PDFs."""
import argparse,json,re
from pathlib import Path
from datetime import date,datetime,timedelta,timezone
from urllib.parse import urlsplit
from clm_common import invalid
from huelva_bop import SOURCE,NOTICE_RE,INDEX_RE
def validate(path,today=None):
    d=json.loads(Path(path).read_text(encoding="utf-8"))
    cov=d.get("coverage",{});hist=d.get("historyCoverage",{})
    if d.get("source")!=SOURCE or d.get("province")!="Huelva" or cov.get("complete") is not True or hist.get("complete") is not True:
        invalid("Huelva: procedencia o auditoría incompleta")
    start=date.fromisoformat(hist["rangeStart"]);end=date.fromisoformat(hist["rangeEnd"])
    if (end-start).days!=29 or (today and today!=end):invalid("Huelva: periodo incompleto")
    stamp=datetime.fromisoformat(d["lastCheckedUTC"])
    if stamp.tzinfo is None or not -timedelta(minutes=5)<=datetime.now(timezone.utc)-stamp<=timedelta(hours=5):
        invalid("Huelva: auditoría caducada")
    dates=hist.get("publicationDates",[]);numbers=hist.get("bulletins",[]);absent=hist.get("nonPublicationDates",[])
    pdfs=hist.get("editionPDFs",[])
    if (dates!=sorted(set(dates)) or len(dates)!=22 or len(numbers)!=len(dates)
       or len(pdfs)!=len(dates) or hist.get("issuesRead")!=len(dates)
       or not (set(dates)|set(absent))=={(start+timedelta(days=i)).isoformat() for i in range(30)}
       or set(dates)&set(absent) or len(set(absent))!=len(absent)
       or any(int(b)!=int(a)+1 for a,b in zip(numbers,numbers[1:]))):
        invalid("Huelva: fechas y números BOP incoherentes")
    for num,day,pdf in zip(numbers,dates,pdfs):
        m=INDEX_RE.fullmatch(urlsplit(pdf).path.rsplit("/",1)[-1])
        if urlsplit(pdf).scheme!="https" or urlsplit(pdf).hostname!="s2.diphuelva.es" or not m or m[1]!=num or m[2]!=str(date.fromisoformat(day).year):
            invalid("Huelva: índice PDF de edición no oficial")
    notices=d.get("notices",[])
    if (cov.get("announcementsRead")!=hist.get("announcementsRead") or
        cov.get("opportunities")!=len(notices) or hist.get("opportunities")!=len(notices) or
        cov.get("pagesVisited")!=len(dates) or len(notices)>5000 or not notices):
        invalid("Huelva: contadores incoherentes")
    expected=dict(zip(dates,numbers));seen=set()
    for n in notices:
        ident=n.get("id","");m=re.fullmatch(r"HB-(\d{4})-(\d{1,8})",ident)
        day=datetime.strptime(n.get("date",""),"%d/%m/%Y").date()
        u=urlsplit(n.get("url",""))
        file=NOTICE_RE.fullmatch(u.path.rsplit("/",1)[-1])
        if (m is None or ident in seen or int(m[1])!=day.year or day.isoformat() not in expected
            or n.get("bulletin")!=expected[day.isoformat()] or n.get("province")!="Huelva"
            or n.get("type") not in ("Plaza / oposición","Bolsa de trabajo")
            or not n.get("title") or not n.get("entity")
            or u.scheme!="https" or u.hostname!="s2.diphuelva.es" or u.query or u.fragment
            or not u.path.startswith("/portalweb/bope/anuncios/")
            or file is None or int(file[1])!=int(m[2]) or file[2]!=n["bulletin"] or int(file[3])!=day.year):
            invalid("Huelva: anuncio o PDF incoherente "+ident)
        seen.add(ident)
    print(f"HUELVA VALIDADO: {len(dates)} boletines, {cov['announcementsRead']} anuncios, {len(notices)} candidatas",flush=True)
    return d
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--file",required=True);p.add_argument("--require-today",action="store_true")
    a=p.parse_args();validate(a.file,date.today() if a.require_today else None)
