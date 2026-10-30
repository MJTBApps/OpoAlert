#!/usr/bin/env python3
"""BOP Albacete (bop.dipualba.es): calendario oficial de publicaciones,
sumario completo de cada boletín y PDF original de cada anuncio.

- Calendario: servicesajax/obtenerdiaspublicacion?a=AAAA-MM-01 (JSON con
  la lista de boletines del mes en base64).
- Sumario: servicesajax/busquedapornumbop?a=<número>&b=<año> (HTML con la
  cabecera «Boletín Número N (dd/mm/aaaa)» y un enlace por anuncio a
  servicesajax/descargararchivopaginaBOP/<id>).

Falla cerrado: cualquier incoherencia lanza ProvincialCoverageError.
"""
from __future__ import annotations
import argparse,base64,json,re
from datetime import date,datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode,urljoin,urlsplit
from bs4 import BeautifulSoup
from clm_common import invalid,get,pdf_header,record,publish_audit,write_output,numbering_ok

HOME="https://bop.dipualba.es"
SOURCE=HOME+"/"
AJAX=HOME+"/servicesajax/"
HOST={"bop.dipualba.es"}
PAGE_PATH=re.compile(r"^/servicesajax/descargararchivopaginaBOP/(\d{1,8})$")
HEADER=re.compile(r"Bolet[ií]n\s+N[uú]mero\s+(\d{1,4})\s*\((\d{2}/\d{2}/\d{4})\)",re.I)
# Boletines ordinarios: lunes, miércoles y viernes (unos 13 en 30 días; 10 en Semana Santa).
MIN_ISSUES=10

def month_url(first):
    return AJAX+"obtenerdiaspublicacion?"+urlencode({"a":first.strftime("%Y-%m-01")})

def issue_url(number,year):
    return AJAX+"busquedapornumbop?"+urlencode({"a":str(number),"b":str(year)})

def envelope(text,what):
    try:data=json.loads(text)
    except ValueError:invalid(f"Albacete: respuesta no JSON en {what}")
    if not isinstance(data,dict) or {"codigoError","descripcionError","yedata"}-set(data):
        invalid(f"Albacete: respuesta inesperada en {what}")
    if data["codigoError"] or data["descripcionError"]:
        invalid(f"Albacete: error del portal en {what}: {str(data['descripcionError'])[:150]}")
    return data["yedata"]

def parse_calendar(text,month):
    """Boletines (fecha, número) que el calendario oficial da para el mes."""
    payload=envelope(text,f"calendario {month:%Y-%m}")
    if not payload:return []
    try:events=json.loads(base64.b64decode(payload,validate=True))
    except Exception:invalid(f"Albacete: calendario ilegible {month:%Y-%m}")
    if not isinstance(events,list):invalid("Albacete: calendario sin lista")
    out=[]
    for e in events:
        try:
            day=date.fromisoformat(e["start"]);number=e["idbop"]
            shown=datetime.strptime(e["fechabop"],"%d/%m/%Y").date()
        except Exception:invalid(f"Albacete: evento de calendario ilegible {str(e)[:120]}")
        if not re.fullmatch(r"\d{1,4}",str(number)) or shown!=day or (day.year,day.month)!=(month.year,month.month):
            invalid(f"Albacete: evento de calendario incoherente {str(e)[:120]}")
        if e.get("extra"):invalid(f"Albacete: boletín con marca desconocida {str(e)[:120]}")
        out.append((day,int(number)))
    if len({d for d,_ in out})!=len(out):invalid(f"Albacete: dos boletines el mismo día en {month:%Y-%m}")
    return sorted(out)

def entity_of(link):
    """Organismo: cabecera del grupo (p. ej. «Ayuntamientos») y subgrupo (el municipio)."""
    names=[]
    for p in link.parents:
        span=None
        if p.name=="ul":
            first=p.find("li",recursive=False)
            if first is not None and first.find("ul") is None and not any(x is link for x in first.descendants):
                span=first.find("span",class_="fw-bold",recursive=False)
        elif p.name=="li":
            span=p.find("span",class_="fw-bold",recursive=False)
        if span is not None:
            name=" ".join(span.get_text(" ",strip=True).split())
            if name and name not in names:names.append(name)
    # names va del más cercano al más lejano.
    if not names:return ""
    near,top=names[0],names[-1]
    if len(names)==1:return near
    if top=="Ayuntamientos":return "Ayuntamiento de "+near
    return top+". "+near

def parse_issue(html,day,number):
    s=BeautifulSoup(html,"html.parser")
    head=s.find("h1")
    m=HEADER.search(head.get_text(" ",strip=True) if head else "")
    if not m:invalid(f"Albacete {day}: sumario sin cabecera de boletín")
    if int(m[1])!=number or datetime.strptime(m[2],"%d/%m/%Y").date()!=day:
        invalid(f"Albacete: el sumario es del BOP {m[1]} ({m[2]}), se esperaba {number} ({day:%d/%m/%Y})")
    full=[a for a in s.select("a[href]") if "descararchivobopcompleto" in a["href"]]
    if len(full)!=1:invalid(f"Albacete {day}: sin enlace único al boletín completo")
    rows=s.select("li.list-group-item div.row")
    links=s.select("a.enlace_documento_bop_principal[href]")
    if not links or len(rows)!=len(links):
        invalid(f"Albacete {day}: sumario incompleto ({len(rows)} anuncios, {len(links)} enlaces)")
    seen=set();notices=[]
    for row in rows:
        found=row.select("a.enlace_documento_bop_principal[href]")
        title_div=row.find("div",class_="col-12")
        if len(found)!=1 or title_div is None or title_div.find("a") is not None:
            invalid(f"Albacete {day}: anuncio sin título o sin enlace único")
        a=found[0]
        url=urljoin(SOURCE,a["href"])
        u=urlsplit(url)
        pm=PAGE_PATH.fullmatch(u.path)
        if (u.scheme!="https" or u.hostname not in HOST or u.port not in (None,443)
            or u.username or u.query or u.fragment or not pm):
            invalid(f"Albacete {day}: enlace fuera del documento oficial {url[:150]}")
        doc=int(pm[1])
        if doc in seen:invalid(f"Albacete {day}: anuncio repetido {doc}")
        seen.add(doc)
        title=" ".join(title_div.get_text(" ",strip=True).split())
        agency=entity_of(a)
        if not title or not agency:invalid(f"Albacete {day}: anuncio {doc} sin título u organismo")
        row_data=record("AB","Albacete",f"AB-{day.year}-{doc}",title,agency,day,number,url)
        if row_data["type"]:notices.append(row_data)
    return {"day":day,"number":number,"read":len(rows),"notices":notices}

def scan_issue(pair):
    day,number=pair
    html=envelope(get(issue_url(number,day.year),HOST).text,f"BOP {number}/{day.year}")
    if not html:invalid(f"Albacete: BOP {number}/{day.year} sin sumario")
    issue=parse_issue(html,day,number)
    if issue["notices"]:pdf_header(issue["notices"][0]["url"],HOST)
    print("ALBACETE",day,"boletín",number,"anuncios",issue["read"],"candidatas",len(issue["notices"]),flush=True)
    return issue

def months_between(start,end):
    m=start.replace(day=1)
    while m<=end:
        yield m
        m=(m+timedelta(days=32)).replace(day=1)

def audit(today=None):
    end=today or date.today()
    start=end-timedelta(days=29)
    # Se lee también el mes anterior para comprobar que la numeración enlaza
    # con el boletín previo a la ventana.
    calendar=[]
    for month in months_between((start.replace(day=1)-timedelta(days=1)).replace(day=1),end):
        calendar.extend(parse_calendar(get(month_url(month),HOST).text,month))
    calendar.sort()
    if not numbering_ok(calendar):invalid(f"Albacete: numeración del calendario con huecos {[n for _,n in calendar]}")
    before=[x for x in calendar if x[0]<start]
    window=[x for x in calendar if start<=x[0]<=end]
    if not before:invalid("Albacete: calendario sin boletines anteriores a la ventana")
    if len(window)<MIN_ISSUES:invalid(f"Albacete: calendario con solo {len(window)} boletines")
    with ThreadPoolExecutor(max_workers=3) as pool:
        issues=list(pool.map(scan_issue,window))
    return publish_audit(SOURCE,"Albacete",issues,today=end,min_issues=MIN_ISSUES)

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    write_output(args.output,audit())
