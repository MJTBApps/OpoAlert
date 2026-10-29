#!/usr/bin/env python3
"""Strict common output for Castilla-La Mancha bulletins; fail closed."""
from __future__ import annotations
import json,re,requests,time,threading
from pathlib import Path
from datetime import date,datetime,timedelta,timezone
from urllib.parse import urlsplit
from provincial_common import ProvincialCoverageError,fold,classify
_HTTP_THREADS=threading.local()
def http_session():
    if not hasattr(_HTTP_THREADS,"client"):
        _HTTP_THREADS.client=requests.Session()
        _HTTP_THREADS.client.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert research crawler)","Accept-Language":"es"})
    return _HTTP_THREADS.client

def invalid(message):
    raise ProvincialCoverageError("Castilla-La Mancha: "+str(message))

def get(url,allowed,stream=False,timeout=(12,28),verify=True,retries=3):
    u=urlsplit(url)
    if (u.scheme!="https" or u.hostname not in allowed or u.username or u.password
        or u.fragment or (u.port not in (None,443) and not (u.hostname=="se1.dipucr.es" and u.port==4443))):
        invalid("URL fuera de la fuente oficial: "+url[:200])
    error=None
    for i in range(retries):
        try:
            r=http_session().get(url,timeout=timeout,stream=stream,allow_redirects=True,verify=verify)
            final=urlsplit(r.url)
            if r.status_code!=200 or final.hostname not in allowed:
                n=r.status_code;r.close()
                invalid(f"HTTP {n} desde {url}")
            if not stream and (not r.content or len(r.content)>4_000_000):
                invalid("página vacía o desmesurada: "+url)
            return r
        except (requests.RequestException,ProvincialCoverageError) as ex:
            error=ex
            if i<retries-1:time.sleep(.7*(i+1))
    invalid(f"sin acceso seguro a {url}: {error}")

def pdf_header(url,allowed):
    r=get(url,allowed,stream=True)
    try:
        data=next(r.iter_content(chunk_size=80),b"")
        if not data.startswith(b"%PDF-") or "pdf" not in r.headers.get("Content-Type","").lower():
            invalid("enlace oficial no es PDF: "+url)
    finally:r.close()

def employment(title):
    t=" ".join(fold(title).split())
    if any(w in t for w in ("lista definitiva","lista provisional","admitidos","excluidos",
        "tribunal calificador","nombramiento","correccion de errores","resultados",
        "resolucion definitiva","concurso de traslados","juez de paz",
        "jueza de paz","subvencion","licitacion","beca","aprobacion del presupuesto")):
        return None
    if "bolsa" in t and any(w in t for w in ("seleccion","selectiv","convocatoria","bases","constitucion","trabajo","empleo","personal")):
        return "Bolsa de trabajo"
    result=classify(title)
    if result:return result
    if any(w in t for w in ("oferta de empleo","proceso selectivo","pruebas selectivas",
        "bases de seleccion","seleccion de personal")) and any(w in t for w in
        ("convoca","proceso","plaza","puesto","personal","bolsa","seleccion")):
        return "Plaza / oposición"
    return None

def record(code,province,nid,title,agency,day,bulletin,pdf):
    if not (title and agency and len(title)<=2800 and len(agency)<=500):
        invalid("título u organismo oficial ausente")
    if not re.fullmatch(r"[A-Z]{2}-\d{4}-\d{1,8}",nid):
        invalid("identificador fuera del catálogo: "+nid)
    if not pdf or urlsplit(pdf).scheme!="https":invalid("PDF original no verificado")
    return {"id":nid,"province":province,"title":title.strip(),"entity":agency.strip(),
      "date":day.strftime("%d/%m/%Y"),"bulletin":str(bulletin),"type":employment(title),"url":pdf}

def publish_audit(source,province,issue_data,days=30,today=None,min_issues=18):
    if days!=30:invalid("histórico mínimo 30 días")
    end=today or date.today()
    start=end-timedelta(days=29)
    if not issue_data:invalid("no hay boletines")
    issue_data=sorted(issue_data,key=lambda x:(x["day"],str(x["number"])))
    if any(x["day"]<start or x["day"]>end for x in issue_data):
        invalid("edición fuera del intervalo de 30 días")
    if len(issue_data)<min_issues or (end-issue_data[-1]["day"]).days>4 or (issue_data[0]["day"]-start).days>4:
        invalid("intervalo incompleto o boletines ausentes")
    seen=set()
    notices=[]
    for x in issue_data:
        if (not isinstance(x["read"],int) or x["read"]<1 or
            not isinstance(x["notices"],list) or x["read"]<len(x["notices"])):
            invalid("edición sin anuncios o contadores incoherentes")
        key=(x["day"],str(x["number"]))
        if key in seen:invalid("edición duplicada")
        seen.add(key)
        for n in x["notices"]:
            if n.get("type") not in ("Bolsa de trabajo","Plaza / oposición"):invalid("tipo inválido")
            if n.get("province")!=province or n.get("date")!=x["day"].strftime("%d/%m/%Y"):
                invalid("provincia o fecha incorrecta")
            if n.get("bulletin")!=str(x["number"]):invalid("número de boletín incorrecto")
            notices.append(n)
    if len({n["id"] for n in notices})!=len(notices):
        invalid("candidatas duplicadas")
    if not notices:invalid("ninguna candidatura válida encontrada")
    notices.sort(key=lambda n:(datetime.strptime(n["date"],"%d/%m/%Y"),n["id"]),reverse=True)
    dates=sorted(set(x["day"] for x in issue_data))
    total=sum(x["read"] for x in issue_data)
    return {
      "schemaVersion":1,"province":province,"source":source,
      "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
      "coverage":{"complete":True,"status":"complete","bulletin":str(issue_data[-1]["number"]),
        "pagesVisited":len(issue_data),"announcementsRead":total,"opportunities":len(notices)},
      "historyCoverage":{"complete":True,"rangeStart":start.isoformat(),"rangeEnd":end.isoformat(),
        "bulletins":[str(x["number"]) for x in issue_data],
        "publicationDates":[x["day"].isoformat() for x in issue_data],
        "nonPublicationDates":[(start+timedelta(days=i)).isoformat() for i in range(30)
          if start+timedelta(days=i) not in dates],
        "issuesRead":len(issue_data),"announcementsRead":total,"opportunities":len(notices)},
      "notices":notices
    }

def write_output(output,feed):
    p=Path(output);p.parent.mkdir(exist_ok=True,parents=True)
    p.write_text(json.dumps(feed,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"AUDITADO {feed['province']}: {feed['historyCoverage']['issuesRead']} boletines, "
          f"{feed['coverage']['announcementsRead']} anuncios y {len(feed['notices'])} candidatas",flush=True)
