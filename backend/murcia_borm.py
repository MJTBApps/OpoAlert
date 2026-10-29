#!/usr/bin/env python3
"""BORM Murcia: 30 days of official 2026 open-data indexes, with original PDF checks.

The BORM is both the regional and provincial publication in the uniprovincial
Región de Murcia. Never publish or bundle partial or outdated official data.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date,datetime,timedelta
from urllib.parse import urlsplit
from pathlib import Path
import argparse,json,re,requests,time,threading
from clm_common import employment,publish_audit,write_output,invalid

SOURCE="https://transparencia.carm.es/rest-services/services/restFile/BORMIndice.json"
ORIGINAL="https://www.borm.es/"
PROVINCE="Región de Murcia (BORM)"
ID_RE=re.compile(r"^[0-9]{1,8}$")
NPE_RE=re.compile(r"^A-(\d{2})(\d{2})(\d{2})-(\d{1,8})$")
PDF_RE=re.compile(r"^/services/anuncio/([0-9]{5,9})/pdf$")
TLS=threading.local()
def session():
    if not hasattr(TLS,"client"):
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert official open data audit)",
                           "Accept-Language":"es-ES,es;q=0.9"})
        TLS.client=s
    return TLS.client

def get_index():
    try:
        r=session().get(SOURCE,timeout=(12,90),allow_redirects=False)
        if (r.status_code!=200 or r.url!=SOURCE or len(r.content)<100_000
            or len(r.content)>45_000_000 or "json" not in r.headers.get("Content-Type","").lower()):
            invalid(f"Murcia: índice BORM oficial inaccesible, HTTP {r.status_code} o contenido incorrecto")
        obj=r.json()
        if not isinstance(obj,list) or len(obj)<1000 or any(not isinstance(x,list) or len(x)!=21 for x in obj):
            invalid("Murcia: índice oficial incompleto o columnas modificadas")
        return obj
    except (requests.RequestException,ValueError) as ex:
        invalid("Murcia: no pudo leerse el índice oficial "+str(ex)[:180])

def parse_index(records,today):
    start=today-timedelta(days=29)
    by_issue=defaultdict(list)
    unique=set()
    year_all=[]
    for row in records:
        if not isinstance(row[4],str):
            invalid("Murcia: fecha de índice no válida")
        try:day=datetime.strptime(row[4],"%Y-%m-%d %H:%M:%S").date()
        except ValueError:invalid("Murcia: fecha de boletín mal formada")
        if day.year==today.year:year_all.append(day)
        if day<start or day>today:continue
        kind,annid,digital,number,rawdate,title,administration,section,apartado,entity=row[:10]
        npe,pdf,html=row[16],row[18],row[17]
        if kind not in ("BOLETIN","SUPLEMENTO","EXTRAORDINARIO"):
            invalid(f"Murcia: clase de publicación no reconocida {kind!r}")
        m=NPE_RE.fullmatch(str(npe));p=urlsplit(str(pdf))
        agency=" ".join(str(entity or administration or "").split())
        title=" ".join(str(title or "").split())
        original=f"https://www.borm.es/services/anuncio/{digital}/pdf"
        notice_url=f"https://www.borm.es/#/home/anuncio/{day.strftime('%d-%m-%Y')}/{annid}"
        if (not ID_RE.fullmatch(str(annid)) or not ID_RE.fullmatch(str(digital))
            or not str(number).isdigit() or not (1<=int(number)<=366)
            or not title or not agency or len(title)>2800 or len(agency)>500
            or not m or m[1]+m[2]+m[3]!=day.strftime("%d%m%y")
            or int(m[4])!=int(annid)
            or p.scheme!="https" or p.hostname!="www.borm.es" or p.port is not None
            or p.username or p.query or p.fragment or not PDF_RE.fullmatch(p.path)
            or original!=str(pdf) or str(html)!=notice_url):
            invalid(f"Murcia {day}: documento oficial o NPE incoherente ({str(npe)[:70]})")
        key=f"MU-{today.year}-{annid}"
        if key in unique:invalid(f"Murcia: código de anuncio repetido {key}")
        unique.add(key)
        role=employment(title)
        if role:
            by_issue[(day,int(number))].append({"id":key,"province":PROVINCE,"title":title,
                "entity":agency,"date":day.strftime("%d/%m/%Y"),"bulletin":str(int(number)),
                "type":role,"url":pdf})
        # Count every official publication, not just candidate notices.
        by_issue[(day,int(number))].append(None)
    if not year_all or max(year_all)<today:
        invalid(f"Murcia: índice público no llega al día auditado {today}")
    if len(unique)<350 or len(by_issue)<20:
        invalid(f"Murcia: histórico sin suficiente cobertura, {len(unique)} anuncios / {len(by_issue)} ediciones")
    sequence=sorted(by_issue)
    if len({x[1] for x in sequence})!=len(sequence):
        invalid("Murcia: número de BORM duplicado en fechas diferentes")
    if any(b[1]!=a[1]+1 for a,b in zip(sequence,sequence[1:])):
        invalid("Murcia: falta algún número consecutivo del BORM")
    issues=[]
    for day,number in sequence:
        all_items=by_issue[(day,number)]
        notices=[x for x in all_items if x is not None]
        read=sum(x is None for x in all_items)
        if read==0 or len(notices)>read:invalid("Murcia: sumario desajustado")
        issues.append({"day":day,"number":str(number),"read":read,"notices":notices})
    if issues[0]["day"]>start+timedelta(days=3) or issues[-1]["day"]!=today:
        invalid("Murcia: faltan los primeros o últimos BORM de los 30 días")
    return issues

def assert_pdf(url):
    u=urlsplit(url)
    if (u.scheme!="https" or u.hostname!="www.borm.es" or
        not PDF_RE.fullmatch(u.path) or u.query or u.fragment):
        invalid("Murcia: PDF de sede ajena")
    try:
        r=session().get(url,timeout=(10,24),stream=True,allow_redirects=False,
                        headers={"Range":"bytes=0-128"})
        if r.status_code not in (200,206) or not r.headers.get("Content-Type","").lower().startswith("application/pdf"):
            invalid(f"Murcia: PDF original no accesible ({r.status_code}): {url}")
        prefix=b""
        for chunk in r.iter_content(180):
            prefix+=chunk
            if len(prefix)>=5:break
        r.close()
        if not prefix.startswith(b"%PDF-"):invalid(f"Murcia: documento no es PDF: {url}")
    except requests.RequestException as ex:invalid(f"Murcia: error al verificar PDF {url}: {ex}")

def audit(today=None,verify_pdf=True):
    end=today or date.today()
    issues=parse_index(get_index(),end)
    for i,issue in enumerate(issues,1):
        for note in issue["notices"]:
            if verify_pdf:
                assert_pdf(note["url"])
                # Avoid overloading BORM public services while verifying original documents.
                time.sleep(0.12)
        print(f"MURCIA BORM {issue['day']} n.º {issue['number']}: "
              f"{issue['read']} anuncios, {len(issue['notices'])} candidatas (edición {i}/{len(issues)})",flush=True)
    return publish_audit(SOURCE,PROVINCE,issues,today=end)

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--skip-pdf",action="store_true",help="Local diagnostics only; never publish as verified")
    args=p.parse_args()
    report=audit(verify_pdf=not args.skip_pdf)
    if args.skip_pdf:
        print("MURCIA SIN VALIDAR: prueba sin autenticar PDFs; no se publica",flush=True)
    else:
        write_output(args.output,report)
