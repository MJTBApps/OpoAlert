#!/usr/bin/env python3
"""Official BOP Ourense 30-day API audit, original PDF verification for candidates."""
from __future__ import annotations
from datetime import date,timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlsplit
import requests,threading,re,argparse
from clm_common import publish_audit,write_output,invalid
from galicia_common import galicia_employment

SOURCE="https://bop.depourense.es/portalapi/api/boletin/getFecha"
HOST="bop.depourense.es"
PDF_RE=re.compile(r"^/portalapi/api/edicto/descargar/pdf/(\d{3,9})/idioma/gl$")
S=threading.local()
def session():
    if not hasattr(S,"req"):
        x=requests.Session()
        x.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert official bulletin audit)","Accept-Language":"es-ES,es;q=0.9","Accept":"application/json,application/pdf;q=0.9,*/*;q=0.5"})
        S.req=x
    return S.req

def pdf_check(url):
    p=urlsplit(url)
    if p.scheme!="https" or p.hostname!=HOST or p.query or p.fragment or p.port not in (None,443) or not PDF_RE.fullmatch(p.path):
        invalid("Ourense: PDF fuera del portal oficial")
    try:
        r=session().get(url,timeout=(12,35),stream=True,allow_redirects=False,headers={"Range":"bytes=0-180"})
        if r.status_code not in (200,206):
            invalid(f"Ourense: PDF oficial HTTP {r.status_code}")
        start=b""
        for chunk in r.iter_content(200):
            start+=chunk
            if len(start)>=5:break
        valid=start.startswith(b"%PDF-")
        r.close()
        if not valid:invalid(f"Ourense: respuesta de PDF no válida {url}")
    except requests.RequestException as e:
        invalid("Ourense: error al consultar PDF "+str(e)[:190])

def read_day(day):
    url=f"{SOURCE}/{day:%Y%m%d}"
    try:
        r=session().get(url,timeout=(12,37),allow_redirects=False)
        if r.status_code!=200 or r.url!=url or len(r.content)>1500000:
            invalid(f"Ourense: fallo de API o exceso de tamaño {day}, HTTP {r.status_code}")
        data=r.json()
    except (requests.RequestException,ValueError) as e:
        invalid(f"Ourense: API oficial inaccesible {day}: {e}")
    if not isinstance(data,list):invalid(f"Ourense {day}: JSON inesperado")
    if not data:return []
    records=[]
    for g in data:
        if not isinstance(g,dict) or set(("boletin","edictos"))-set(g):
            invalid(f"Ourense {day}: boletín sin índice de edictos")
        meta=g["boletin"];docs=g["edictos"]
        if not isinstance(meta,dict) or not isinstance(docs,list):
            invalid(f"Ourense {day}: boletín no estructurado")
        if (meta.get("fechaPublicacion")!=day.strftime("%Y%m%d") or
            not isinstance(meta.get("numeroBop"),int) or meta["numeroBop"]<1 or meta["numeroBop"]>366 or
            not isinstance(meta.get("id"),int) or meta["id"]<1 or meta.get("maquetadosn")!="S" or
            meta.get("excepcional") not in ("S","N")):
            invalid(f"Ourense {day}: fecha, edición o estado de maquetación incorrecto")
        original=meta.get("edictos")
        if not isinstance(original,list) or not docs:
            invalid(f"Ourense {day}: no están listos todos los edictos")
        ids1=[x.get("id") for x in original if isinstance(x,dict)]
        ids2=[x.get("id") for x in docs if isinstance(x,dict)]
        if len(ids1)!=len(original) or len(ids2)!=len(docs) or len(ids1)!=len(ids2) or set(ids1)!=set(ids2):
            invalid(f"Ourense {day}: índices de edictos no coinciden (maquetados={len(ids1)}, publicados={len(ids2)})")
        seen=set();notices=[]
        for item in docs:
            ident=item.get("id")
            if not isinstance(ident,int) or not 1<=ident<=999999999 or ident in seen:
                invalid(f"Ourense {day}: id oficial duplicado o incorrecto")
            seen.add(ident)
            title=" ".join(str(item.get("sumario") or item.get("sumarioRemGal") or "").split())
            procedente=item.get("procedente")
            agency=" ".join(str(procedente.get("nombre") or "").split()) if isinstance(procedente,dict) else ""
            if not title or not agency or len(title)>2800 or len(agency)>500:
                invalid(f"Ourense {day}: anuncio {ident} sin título u organismo")
            kind=galicia_employment(title)
            if kind:
                pdf=f"https://{HOST}/portalapi/api/edicto/descargar/pdf/{ident}/idioma/gl"
                pdf_check(pdf)
                notices.append({"id":f"OU-2026-{ident}","province":"Ourense",
                  "title":title,"entity":agency,"date":day.strftime("%d/%m/%Y"),
                  "bulletin":str(meta["numeroBop"])+("E" if meta["excepcional"]=="S" else ""),
                  "type":kind,"url":pdf})
        number=str(meta["numeroBop"])+("E" if meta["excepcional"]=="S" else "")
        print("OURENSE",day,number,"anuncios",len(docs),"candidatas",len(notices),flush=True)
        records.append({"day":day,"number":number,"read":len(docs),"notices":notices})
    return records

def audit():
    end=date(2026,10,29);start=end-timedelta(days=29)
    days=[start+timedelta(days=i) for i in range(30)]
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows=list(pool.map(read_day,days))
    editions=[issue for group in rows for issue in group]
    ordinarias=[x for x in editions if not x["number"].endswith("E")]
    numbers=[int(x["number"]) for x in ordinarias]
    if (len(editions)<20 or len(editions)>28 or
        ordinarias[0]["day"]!=start or ordinarias[-1]["day"]!=end or
        any(b!=a+1 for a,b in zip(numbers,numbers[1:]))):
        invalid(f"Ourense: BOP ordinarios no cubren 30 días: {numbers}")
    return publish_audit(SOURCE,"Ourense",editions,today=end)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();write_output(a.output,audit())
