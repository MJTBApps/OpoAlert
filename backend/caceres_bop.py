#!/usr/bin/env python3
"""Cáceres BOP: official REST calendar, complete entries and signed original PDFs."""
from __future__ import annotations
import argparse,json,re,requests,threading
from pathlib import Path
from datetime import date,datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlencode,urlsplit,parse_qs
from clm_common import employment,publish_audit,invalid

SOURCE="https://bop.dip-caceres.es/bop/index.html"
API="https://bop.dip-caceres.es/bop/services/"
HOST="bop.dip-caceres.es"
ID_RE=re.compile(r"^BOP-(\d{4})-(\d{1,7})$")
TLS=threading.local()
def session():
    if not hasattr(TLS,"s"):
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es"})
        TLS.s=s
    return TLS.s
def load(service,params,pdf=False):
    if not re.fullmatch(r"(?:boletines/(?:bopMesCalendario|contenidoPdfIdBolentin)|anuncios/(?:anunciosAnunciantes|contenidoPdfIdAnuncio))",service):
        invalid("Cáceres: servicio BOP desconocido")
    url=API+service+"?"+urlencode(params)
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname!=HOST:invalid("Cáceres: no se usará un tercero")
    try:
        response=session().get(url,timeout=(12,30),stream=pdf,allow_redirects=False)
        if response.status_code not in ((200,206) if pdf else (200,)):
            invalid(f"Cáceres: HTTP {response.status_code} en {service}")
        if pdf:
            header=b""
            for chunk in response.iter_content(150):
                header+=chunk
                if len(header)>=5:break
            if not header.startswith(b"%PDF-") or "pdf" not in response.headers.get("Content-Type","").lower():
                invalid(f"Cáceres: documento original no es PDF, {url}")
            response.close()
            return url
        if not response.content or len(response.content)>4_000_000:
            invalid("Cáceres: respuesta del servicio vacía o desmesurada")
        result=response.json()
        if not isinstance(result,dict) or not isinstance(result.get("data"),list):
            invalid(f"Cáceres: JSON sin colección validable en {service}, valor {str(result)[:130]}")
        if result.get("total")!=len(result["data"]):
            invalid(f"Cáceres: paginación oculta o contador discrepante en {service}")
        return result["data"]
    except (requests.RequestException,ValueError) as ex:
        invalid("Cáceres: error de consulta oficial "+str(ex)[:190])
def archive(start,end):
    items={}
    for year,month in sorted({(start.year,start.month),(end.year,end.month)}):
        data=load("boletines/bopMesCalendario",{"mes":month,"anio":year})
        if len(data)<15:invalid(f"Cáceres: calendario {year}-{month} incompleto ({len(data)})")
        for row in data:
            try:day=date(year,month,int(row["diaBop"]));bid=int(row["idBoletin"])
            except (ValueError,KeyError,TypeError) as ex:invalid("Cáceres: fecha/id inválido "+str(ex))
            if bid<=0:invalid("Cáceres: código de boletín inválido")
            if start<=day<=end:
                if (day,bid) in items:invalid("Cáceres: registro duplicado")
                items[(day,bid)]=bid
    entries=sorted(items)
    days=[x[0] for x in entries]
    if (len(entries)<18 or (days[0]-start).days>4 or (end-days[-1]).days>4
        or len(set(days))!=len(days)):
        invalid("Cáceres: edición histórica ausente o fechas duplicadas")
    if any(b[1]!=a[1]+1 for a,b in zip(entries,entries[1:])):
        invalid("Cáceres: falta un código de edición en el intervalo")
    return entries
def parse_day(rows,day,id_bop):
    if not rows:invalid(f"Cáceres: BOP {day} sin anuncios")
    nums=set();seen=set();notices=[]
    for rec in rows:
        code=str(rec.get("csv",""))
        m=ID_RE.fullmatch(code)
        title_full=" ".join(str(rec.get("tituloAnuncio","")).split())
        title=title_full[len(code):].strip(" :-") if title_full.startswith(code) else ""
        agency=" ".join(str(rec.get("nombreEntidad","")).split())
        url_path=rec.get("urlPdf","")
        prefix="services/anuncios/contenidoPdfIdAnuncio?csv="
        number=rec.get("numBop")
        posted=rec.get("fechaPublicacion")
        pdf=API+"anuncios/contenidoPdfIdAnuncio?csv="+code
        if not (m and int(m[1])==day.year and title and agency and url_path==prefix+code
            and str(number).isdigit() and int(number)>0 and isinstance(posted,int)
            and int(posted)>1_700_000_000_000):
            invalid(f"Cáceres {day}: anuncio, autor, PDF o número inválido: {code}")
        utc=datetime.fromtimestamp(posted/1000,timezone.utc).date()
        if abs((utc-day).days)>1:invalid(f"Cáceres {day}: fecha distinta del anuncio {code}: {utc}")
        if code in seen:invalid("Cáceres: anuncio duplicado")
        seen.add(code);nums.add(int(number))
        role=employment(title)
        if role:
            notices.append({"id":f"CC-{day.year}-{int(m[2])}","province":"Cáceres",
                "title":title,"entity":agency,"date":day.strftime("%d/%m/%Y"),
                "bulletin":str(number),"type":role,"url":pdf})
    if len(nums)!=1:invalid(f"Cáceres {day}: sumario mezcla varios números de BOP")
    return {"day":day,"number":str(next(iter(nums))),"read":len(seen),"notices":notices}
def scan(item):
    day,bop_id=item
    rows=load("anuncios/anunciosAnunciantes",{"idBoletin":bop_id})
    data=parse_day(rows,day,bop_id)
    load("boletines/contenidoPdfIdBolentin",{"idBoletin":bop_id},pdf=True)
    for n in data["notices"]:
        code="BOP-"+str(day.year)+"-"+n["id"].split("-")[-1]
        load("anuncios/contenidoPdfIdAnuncio",{"csv":code},pdf=True)
    print("CACERES",day,"BOP",data["number"],"anuncios",data["read"],
        "candidatas",len(data["notices"]),flush=True)
    return data
def audit(today=None):
    end=today or date.today();start=end-timedelta(days=29)
    entries=archive(start,end)
    with ThreadPoolExecutor(max_workers=5) as pool:issue_data=list(pool.map(scan,entries))
    nums=[int(x["number"]) for x in issue_data]
    if any(b!=a+1 for a,b in zip(nums,nums[1:])):
        invalid("Cáceres: no están todos los números de boletín")
    return publish_audit(SOURCE,"Cáceres",issue_data,today=end)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path)
    a=p.parse_args();x=audit();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"CÁCERES AUDITADO: {x['historyCoverage']['issuesRead']} boletines, "
        f"{x['coverage']['announcementsRead']} anuncios, {len(x['notices'])} candidatas",flush=True)
