#!/usr/bin/env python3
"""Huelva BOP 30 day official AJAX archive reader, original PDF links."""
from __future__ import annotations
import argparse,re,requests
from datetime import date,datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit
from clm_common import invalid,employment,publish_audit,write_output,numbering_ok

ROOT="https://s2.diphuelva.es"
SOURCE=ROOT+"/servicios/bope_web/busquedaCalendario"
ENDPOINT=ROOT+"/lib/bope/anuncios_bop/ajaxAnuncios.php"
NOTICE_RE=re.compile(r"^Anuncio_(\d{1,8})_BOP-(\d{1,4})_(\d{4})\.pdf$")
INDEX_RE=re.compile(r"^IndiceBOP_(\d{1,4})_(\d{4})\.pdf$")
def original_pdf(filename):
    if "/" in filename or "\\" in filename or not re.fullmatch(r"[a-zA-Z0-9_.-]+\.pdf",filename):
        invalid("Huelva: archivo PDF oficial inseguro")
    return ROOT+"/portalweb/bope/anuncios/"+filename

def request(day):
    if not isinstance(day,date):invalid("Huelva: fecha no válida")
    try:
        r=requests.post(ENDPOINT,data={"tipo":"2","fecha":day.isoformat()},
           timeout=(12,27),headers={"User-Agent":"Mozilla/5.0","Referer":SOURCE,
           "X-Requested-With":"XMLHttpRequest","Accept":"application/json"})
        if r.status_code!=200 or r.url!=ENDPOINT:invalid("Huelva: AJAX fuera del endpoint oficial")
        return r.json()
    except (requests.RequestException,ValueError) as e:
        invalid("Huelva: AJAX no disponible: "+str(e)[:180])

def parse_day(data,day):
    if (data.get("success") is False and data.get("fecha_elegida")==day.isoformat()
        and data.get("Indice") is None and data.get("Anuncios") is None):
        return None
    if data.get("success") is not True or data.get("TieneAnuncios") is not True:
        invalid(f"Huelva {day}: índice sin anuncios")
    if data.get("fecha_publicacion")!=day.isoformat() or data.get("fecha_elegida")!=day.isoformat():
        invalid(f"Huelva: fecha AJAX distinta de {day}")
    index=data.get("Indice") or {}
    number=str(index.get("num_bop",""))
    if not number.isdigit() or not 1<=int(number)<=366:
        invalid("Huelva: número BOP inválido")
    index_name=index.get("documento","")
    im=INDEX_RE.fullmatch(index_name)
    if not im or int(im[1])!=int(number) or int(im[2])!=day.year:
        invalid("Huelva: sumario PDF no corresponde al boletín")
    all_rows=data.get("Anuncios")
    if not isinstance(all_rows,list) or not all_rows:
        invalid("Huelva: lista de anuncios vacía")
    rows=[]
    ids=set()
    for row in all_rows:
        if not isinstance(row,dict):invalid("Huelva: ficha corrupta")
        idcode=row.get("num_expe")
        if not isinstance(idcode,int) or idcode<1 or idcode>99999999 or idcode in ids:
            invalid("Huelva: expediente de anuncio inválido o duplicado")
        ids.add(idcode)
        pdf=row.get("documento","")
        match=NOTICE_RE.fullmatch(pdf)
        if not match or int(match[1])!=idcode or int(match[2])!=int(number) or int(match[3])!=day.year:
            invalid(f"Huelva: PDF anuncio {idcode} no pertenece al BOP {number}")
        reported=row.get("fecha_publicacion","")
        if not reported.startswith(day.isoformat()+"T"):
            invalid("Huelva: anuncio de fecha distinta")
        if not isinstance(row.get("trabajo_firma"),int) or row["trabajo_firma"]<=0:
            invalid("Huelva: falta trabajo de firma")
        title=" ".join(row.get("titulo","").split())
        entity=" ".join(row.get("entidad_anunciante","").split())
        if not title or not entity or len(title)>3000 or len(entity)>400:
            invalid("Huelva: ficha de anuncio sin título u organismo")
        kind=employment(title)
        if kind:
            rows.append({"id":f"HB-{day.year}-{idcode}","province":"Huelva",
                "title":title,"entity":entity,"date":day.strftime("%d/%m/%Y"),
                "bulletin":number,"type":kind,"url":original_pdf(pdf)})
    return {"day":day,"number":number,"read":len(all_rows),
        "notices":rows,"edition":original_pdf(index_name)}

def scan(day):
    info=parse_day(request(day),day)
    if info:
        print("HUELVA",day,"BOP",info["number"],"anuncios",info["read"],
          "candidatas",len(info["notices"]),flush=True)
    return info

def audit(today=None):
    end=today or date.today()
    start=end-timedelta(days=29)
    days=[start+timedelta(days=x) for x in range(30)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(scan,days))
    rows=[x for x in results if x is not None]
    if len(rows)<15:invalid("Huelva: faltan demasiados días del BOP en 30 días")
    if not numbering_ok([(x["day"],int(x["number"])) for x in rows]):
        invalid(f"Huelva: salto de boletines {[x['number'] for x in rows]}")
    feed=publish_audit(SOURCE,"Huelva",rows,today=end)
    feed["historyCoverage"]["editionPDFs"]=[r["edition"] for r in rows]
    return feed

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    write_output(args.output,audit())
