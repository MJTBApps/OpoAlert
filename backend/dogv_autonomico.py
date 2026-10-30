#!/usr/bin/env python3
"""DOGV Comunitat Valenciana: official 30-day archive including all 'bis' editions.

The current DOGV exposes full original indexes on
 https://dogv.gva.es/dogv-portal/dogv?date=YYYY-MM-DD&lang=es_es
and a calendar at /dogv/calendar. An issue can have multiple official
versions ('bis'), which must never be silently omitted.
"""
from __future__ import annotations
import argparse,re,requests,threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit
from clm_common import employment,publish_audit,write_output,invalid
HOST="dogv.gva.es"
BASE="https://dogv.gva.es/dogv-portal/dogv"
SOURCE=BASE
PDF_RE=re.compile(r"^/datos/2026/(\d{2})/(\d{2})/pdf/2026_(\d{1,8})_es\.pdf$")
SUM_RE=re.compile(r"^/datos/2026/(\d{2})/(\d{2})/pdf/sumario_2026_(\d{4,6})(?:_bis|_ter|_quarter)?_es\.pdf$")
ID_RE=re.compile(r"2026/(\d{1,8})")
S=threading.local()
END=date.today();START=END-timedelta(days=29)
def req():
    if not hasattr(S,"s"):
        r=requests.Session()
        r.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
        S.s=r
    return S.s
def read_json(url,params=None):
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname!=HOST or not u.path.startswith("/dogv-portal/dogv") or u.username or u.fragment:
        invalid("DOGV: solicitud no autorizada")
    try:
        r=req().get(url,params=params,timeout=(10,38),allow_redirects=False,
                    headers={"Accept":"application/json"})
        if r.status_code!=200 or len(r.content)>2600000 or not r.content:
            invalid(f"DOGV: HTTP {r.status_code} / índice no disponible: {r.url}")
        return r.json()
    except (requests.RequestException,ValueError) as e:invalid("DOGV: error de API oficial "+str(e)[:200])
def validate_pdf(path,day,num=None):
    if not isinstance(path,str) or not path.startswith(f"/2026/{day:%m/%d}/pdf/"):
        invalid(f"DOGV: ruta PDF ajena a la edición {day}: {path}")
    url=f"https://{HOST}/datos"+path
    parts=urlsplit(url)
    if parts.hostname!=HOST or parts.query or parts.fragment:invalid("DOGV: PDF externo")
    m=SUM_RE.fullmatch(parts.path) if num is not None else PDF_RE.fullmatch(parts.path)
    if not m or int(m[1])!=day.month or int(m[2])!=day.day or (num is not None and int(m[3])!=num):
        invalid("DOGV: PDF fuera del sumario o edición")
    try:
        response=req().get(url,timeout=(10,36),stream=True,allow_redirects=False,
          headers={"Range":"bytes=0-150"})
        if response.status_code not in (200,206) or "pdf" not in response.headers.get("Content-Type","").lower():
            invalid(f"DOGV: documento sin PDF original, HTTP {response.status_code}: {url}")
        prefix=b""
        for piece in response.iter_content(175):
            prefix+=piece
            if len(prefix)>=5:break
        response.close()
        if not prefix.startswith(b"%PDF-"):invalid(f"DOGV: respuesta no es PDF {url}")
    except requests.RequestException as e:invalid("DOGV: PDF no disponible: "+str(e)[:190])
    return url
def calendar():
    records=read_json(BASE+"/calendar",
        {"startDate":START.isoformat(),"endDate":END.isoformat()})
    if not isinstance(records,list) or not 19<=len(records)<=24:
        invalid(f"DOGV: calendario oficial incompleto {len(records) if isinstance(records,list) else '?'}")
    days=[];is_bis={}
    for row in records:
        if not isinstance(row,dict) or not isinstance(row.get("esBis"),bool):
            invalid("DOGV: calendario sin fechas/esBis")
        try:day=date.fromisoformat(row["fecha"])
        except Exception as e:invalid("DOGV: fecha del calendario mal formada")
        if day<START or day>END or day in is_bis:invalid("DOGV: calendario duplicado o externo")
        days.append(day);is_bis[day]=row["esBis"]
    if days!=sorted(days) or (days[0]-START).days>3 or (END-days[-1]).days>3:
        invalid("DOGV: faltan primera/última edición")
    return days,is_bis
def original_path_from_export(did,day,code):
    """Retrieve original publication PDF through the Generalitat export API."""
    url=f"https://{HOST}/dogv-portal/export/disposicion/{did}/pdf"
    try:
        r=req().get(url,params={"lang":"es_es"},timeout=(12,37),allow_redirects=False,
                    headers={"Accept":"application/pdf,text/plain"})
        if r.status_code!=200 or not 10<len(r.content)<1000:
            invalid(f"DOGV: export oficial no disponible para {did}, HTTP {r.status_code}")
        path=r.text.strip()
        match=PDF_RE.fullmatch("/datos"+path)
        if match and path.startswith(f"/2026/{day:%m/%d}/pdf/") and int(match[3])==code:
            return path
        # Some legal texts have already been consolidated in the public
        # metadata and export. The official original publication follows the
        # stable DOGV filename convention. Demand a real signed PDF response.
        consolidated=re.fullmatch(r"/consolidacion/2026/2026_(\d{1,8})_(\d{8})_es\.pdf",path)
        if consolidated and int(consolidated[1])==code:
            original=f"/2026/{day:%m/%d}/pdf/2026_{code}_es.pdf"
            validate_pdf(original,day)
            print(f"DOGV ORIGINAL VERIFICADO: fecha {day}, inserción {code}; metadatos consolidados",flush=True)
            return original
        invalid(f"DOGV: export no permite acreditar PDF original del registro {did}: {path[:150]}")
    except requests.RequestException as e:invalid(f"DOGV: export original inaccesible {e}")

def inspect(day):
    first=read_json(BASE,{"date":day.isoformat(),"lang":"es_es"})
    cab=first.get("cabecera",{})
    try:num=int(cab["numeroDogv"])
    except Exception as e:invalid("DOGV: boletín sin número")
    if first.get("fechaSumario")!=day.strftime("%d-%m-%Y") or first.get("esBis") is not False:
        invalid(f"DOGV: edición principal no corresponde a {day}")
    versions=read_json(BASE+f"/{num}/versionesSumario")
    if not isinstance(versions,list) or not versions or versions!=list(range(1,len(versions)+1)) or len(versions)>4:
        invalid(f"DOGV {day}: no se pueden validar todas las versiones de sumario")
    editions=[];unique=set()
    for version in versions:
        data=read_json(BASE+f"/{num}",{"ordenSumario":version,"lang":"es_es"})
        header=data.get("cabecera",{})
        if (header.get("numeroDogv")!=num or data.get("fechaSumario")!=day.strftime("%d-%m-%Y")
            or data.get("esBis") is not (version==2) or data.get("existeUrl") is not True):
            invalid(f"DOGV {day}: sumario {version} no corresponde al día")
        docs=data.get("disposiciones",[])
        if not isinstance(docs,list) or not 1<=len(docs)<=250:invalid(f"DOGV {day}: índice vacío o truncado")
        validate_pdf(data.get("urlPdf"),day,num)
        notices=[];local=set()
        for obj in docs:
            if not isinstance(obj,dict):invalid("DOGV: disposición no es objeto")
            did=obj.get("id")
            mm=ID_RE.fullmatch(str(obj.get("codigoInsercion") or ""))
            title=" ".join(str(obj.get("titulo") or "").split())
            organ=" ".join(str(obj.get("organismo") or "").split())
            section=obj.get("seccion",{})
            if (not isinstance(did,int) or did<1 or not mm or not title or not organ
                or len(title)>2800 or len(organ)>500
                or obj.get("fechaPublicacion")!=day.strftime("%d/%m/%Y")
                or not isinstance(section,dict) or not section.get("descripcion")):
                invalid(f"DOGV {day}: disposición incompleta o ajena al calendario {obj.get('codigoInsercion')}")
            code=int(mm[1]);ident=f"DV-2026-{code}"
            path=obj.get("urlPdf")
            # A consolidated legal version may replace the publication PDF in metadata.
            # In that case retrieve the original from the Generalitat's export endpoint.
            if not isinstance(path,str) or not PDF_RE.fullmatch("/datos"+path):
                path=original_path_from_export(did,day,code)
            m=PDF_RE.fullmatch("/datos"+path)
            if (not m or int(m[3])!=code or int(m[1])!=day.month
                or int(m[2])!=day.day):
                invalid(f"DOGV {day}: PDF original incoherente con el sumario {path}")
            if ident in unique or ident in local:invalid(f"DOGV {day}: documento repetido {ident}")
            local.add(ident);unique.add(ident)
            kind=employment(title)
            if kind:
                url=validate_pdf(path,day)
                notices.append({"id":ident,"province":"Comunidad Valenciana (DOGV)",
                    "title":title,"entity":organ,"date":day.strftime("%d/%m/%Y"),
                    "bulletin":str(num)+({1:"",2:"B",3:"T",4:"Q"}[version]),
                    "type":kind,"url":url})
        print(f"DOGV {day} n.º {num} versión {version}: {len(docs)} anuncios, {len(notices)} candidatas",flush=True)
        editions.append({"day":day,"number":str(num)+({1:"",2:"B",3:"T",4:"Q"}[version]),"read":len(docs),"notices":notices})
    return num,editions,len(versions)
def audit():
    days,flags=calendar()
    with ThreadPoolExecutor(max_workers=5) as pool:
        batches=list(pool.map(inspect,days))
    nums=[r[0] for r in batches]
    if len(set(nums))!=len(nums) or any(b!=a+1 for a,b in zip(nums,nums[1:])):
        invalid(f"DOGV: boletines incompletos o discontinuos {nums}")
    for day,(number,items,count) in zip(days,batches):
        if (count>1)!=flags[day]:invalid(f"DOGV {day}: calendario oficial discrepa de versiones bis")
    issues=[x for (_,group,_) in batches for x in group]
    print(f"DOGV total: {len(days)} fechas, {len(issues)} sumarios incluidos",flush=True)
    return publish_audit(SOURCE,"Comunidad Valenciana (DOGV)",issues,today=END)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path)
    args=p.parse_args();write_output(args.output,audit())
