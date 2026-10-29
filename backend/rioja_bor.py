#!/usr/bin/env python3
"""La Rioja BOR: audited 30-day local-government and regional employment feed.

Uses the documented OPEN DATA API, not the inaccessible public search portal.
Technical specification: https://ias1.larioja.org/opendata/download?r=Y2Q9MzIxfGNmPTE2
Never emits a completed feed if calendar, official article XML, or source identity disagree.
"""
from __future__ import annotations
import argparse
import hashlib
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlencode, urlsplit, parse_qs
import requests
from defusedxml import ElementTree as ET
from clm_common import employment, publish_audit, write_output
from provincial_common import ProvincialCoverageError

HOST="ias1.larioja.org"
API="https://ias1.larioja.org/boletin/ExportarBoletinServlet"
PDF="https://ias1.larioja.org/boletin/Bor_Boletin_visor_Servlet"
SOURCE=API
PROVINCE="La Rioja (BOR)"
START=date(2026,9,30)
END=date(2026,10,29)
HTTP=threading.local()
PREFER_PDF=False
REF_RE=re.compile(r"[A-Za-z0-9-]{6,90}")
def invalid(message):
    raise ProvincialCoverageError("La Rioja BOR: "+str(message))
def client():
    if not hasattr(HTTP,"client"):
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert BOR open data audit/1.0)",
                          "Accept-Language":"es-ES,es;q=0.9"})
        HTTP.client=s
    return HTTP.client
def validate_url(url):
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443) or u.username or u.password or u.fragment:
        invalid("URL fuera de la sede oficial "+url[:150])
    if u.path not in ("/boletin/ExportarBoletinServlet","/boletin/Bor_Boletin_visor_Servlet"):
        invalid("Ruta no corresponde a API BOR")
    return u
def fetch(url, pdf=False, attempts=4):
    validate_url(url)
    error=None
    for attempt in range(attempts):
        try:
            r=client().get(url,timeout=((7,18) if pdf else (12,35)),stream=pdf,allow_redirects=False,
                           headers={"Range":"bytes=0-128"} if pdf else {})
            if r.status_code in ((200,206) if pdf else (200,)):
                break
            error=f"HTTP {r.status_code} al consultar {url}"
            r.close()
        except requests.RequestException as ex:
            error=str(ex)[:190]
        if attempt==attempts-1:
            invalid(f"Sin acceso a contenido original tras {attempts} intentos: "+str(error))
        time.sleep((attempt+1)*1.7)
    if pdf:
        if "pdf" not in r.headers.get("Content-Type","").lower():
            r.close()
            invalid("La fuente no ha devuelto PDF, quizá autenticación o error")
        b=b""
        try:
            for block in r.iter_content(200):
                b+=block
                if len(b)>=5:break
        finally:r.close()
        if not b.startswith(b"%PDF-"):invalid("El documento original no es un PDF")
        return None
    if "xml" not in r.headers.get("Content-Type","").lower():
        invalid("La API oficial no ha devuelto XML")
    if not 60<len(r.content)<2_000_000:
        invalid("XML oficial vacío, truncado o desmesurado")
    try:root=ET.fromstring(r.content)
    except ET.ParseError as ex:invalid("XML inválido: "+str(ex)[:100])
    if root.tag!="aplication" or root.attrib.get("status")!="ok":
        invalid("La API rechaza la petición: "+r.text[:250])
    return root
def api_url(**args):
    return API+"?"+urlencode(args)
def pdf_url(ref):
    if not REF_RE.fullmatch(ref):invalid("Referencia de PDF mal formada: "+repr(ref))
    return PDF+"?"+urlencode({"referencia":ref})
def calendar():
    seen={}
    for month in (9,10):
        root=fetch(api_url(tipo=3,mes=month,anio=2026))
        rows=root.findall("./day")
        if len(rows)<18:invalid(f"Mes {month}: calendario insuficiente ({len(rows)})")
        for row in rows:
            try:d=datetime.strptime(row.attrib["value"],"%d/%m/%Y").date()
            except (KeyError,ValueError) as e:invalid(f"Fecha inválida del calendario: {e}")
            if d.year!=2026 or d.month!=month:invalid("Fecha oficial de otro mes en calendario")
            n=row.attrib.get("numero","")
            if not re.fullmatch(r"\d{1,4}",n):invalid("Número ilegible en calendario")
            if START<=d<=END:
                key=(d,int(n))
                if key in seen:invalid("Boletín repetido en calendario oficial")
                seen[key]=None
    items=sorted(seen)
    numbers=[n for _,n in items]
    dates=[d for d,_ in items]
    if not 20<=len(items)<=35 or dates[0]!=START or dates[-1]!=END:
        invalid(f"Histórico 30 días incompleto: {len(items)} boletines {dates[:1]}-{dates[-1:]}")
    if numbers!=list(range(numbers[0],numbers[-1]+1)):
        invalid("Huecos o repeticiones en numeración oficial de boletines")
    print(f"BOR: calendario 30 días, {len(items)} ediciones {numbers[0]}-{numbers[-1]}",flush=True)
    return items
def content_ref(element,kind):
    matches=[(x.text or "").strip() for x in element.findall("./contenido") if x.attrib.get("tipo")==kind]
    if len(matches)!=1 or not REF_RE.fullmatch(matches[0]):
        invalid("Referencia oficial de contenido "+kind+" ausente o ambigua")
    return matches[0]
def issue(item):
    day, number=item
    root=fetch(api_url(tipo=1,fecha=day.strftime("%Y/%m/%d"),numero=number))
    boletin=root.find("./boletin")
    if boletin is None or len(root.findall("./boletin"))!=1:invalid("Sumario sin un boletín único")
    header=boletin.find("./cabecera")
    if header is None:invalid("Sumario sin cabecera")
    try:
        actual=datetime.strptime(header.findtext("fecha",""),"%d-%m-%Y").date()
        n=int(header.findtext("numero",""))
        year=int(header.findtext("anio",""))
    except ValueError as ex:invalid("Cabecera corrupta: "+str(ex))
    if (actual,n,year)!=(day,number,2026):
        invalid(f"Sumario devuelto para otra fecha/número {(actual,n,year)} != {(day,number,2026)}")
    edition_pdf=content_ref(header,"pdf")
    found=[];count=0;seen=set()
    for roman in boletin.findall("./anuncios/romano"):
        for letter in roman.findall("./letra"):
            for organ in letter.findall("./organo"):
                agency=" ".join(organ.attrib.get("denominacion","").split())
                if not 2<len(agency)<500:invalid("Anuncio sin organismo publicador")
                for comite in organ.findall("./comite"):
                    for article in comite.findall("./anuncio"):
                        title=" ".join((article.findtext("titulo","") or "").split())
                        if not 6<len(title)<2800:invalid("Título vacío o anormal en sumario")
                        pdfref=content_ref(article,"pdf")
                        htmlref=content_ref(article,"html")
                        if pdfref in seen:invalid("PDF de anuncio repetido en sumario")
                        seen.add(pdfref)
                        count+=1
                        kind=employment(title)
                        if kind:
                            uid="RI-2026-"+hashlib.sha256(pdfref.encode("ascii")).hexdigest()[:18]
                            found.append({"id":uid,"province":PROVINCE,"title":title,"entity":agency,
                                          "date":day.strftime("%d/%m/%Y"),"bulletin":str(number),
                                          "type":kind,"url":pdf_url(pdfref),
                                          "officialHtml":api_url(tipo=2,fecha=day.strftime("%Y/%m/%d"),referencia=htmlref)})
    if not 1<=count<=500:invalid(f"BOR {number} vacío o truncado: {count}")
    print(f"BOR {day} n.º {number}: {count} anuncios, {len(found)} candidatas",flush=True)
    return {"day":day,"number":str(number),"read":count,"notices":found,"editionPdf":pdf_url(edition_pdf)}
def verify_notice(notice):
    """Verify full source article XML; choose PDF only if its bytes are accessible."""
    official=notice["officialHtml"]
    root=fetch(official)
    articles=root.findall("./anuncio")
    if len(articles)!=1:invalid("La API no devolvió un anuncio único "+notice["id"])
    heading=articles[0].find("./cabecera")
    body=articles[0].find("./contenido[@tipo='html']")
    if heading is None or body is None:invalid("Falta cabecera o texto íntegro del anuncio "+notice["id"])
    try:
        got_day=datetime.strptime(heading.findtext("fecha",""),"%d-%m-%Y").date()
        got_num=int(heading.findtext("numero_bor",""))
    except ValueError as ex:invalid("Identidad de anuncio ilegible "+str(ex))
    want_day=datetime.strptime(notice["date"],"%d/%m/%Y").date()
    title=" ".join(heading.findtext("titulo","").split())
    agency=" ".join(heading.findtext("organo","").split())
    if (got_day!=want_day or got_num!=int(notice["bulletin"])
        or title!=notice["title"] or agency!=notice["entity"]
        or len((body.text or "").strip())<80):
        invalid("Texto original del anuncio no concuerda con el sumario "+notice["id"])
    # The official PDF viewer is intermittently unresponsive. Do not send the user
    # to a PDF until its bytes have been positively verified. The same Government
    # XML API publishes the original full HTML body, a safe official fallback.
    if PREFER_PDF:
        try:
            fetch(notice["url"],pdf=True,attempts=1)
            notice["originalFormat"]="pdf"
        except ProvincialCoverageError:
            notice["url"]=official
            notice["originalFormat"]="official_xml"
    else:
        notice["url"]=official
        notice["originalFormat"]="official_xml"
    return notice

def audit():
    calendar_items=calendar()
    with ThreadPoolExecutor(max_workers=5) as ex:
        rows=list(ex.map(issue,calendar_items))
    total=sum(x["read"] for x in rows)
    if total<250:invalid(f"Histórico sospechosamente corto: {total} anuncios")
    notices=[n for row in rows for n in row["notices"]]
    if not notices:invalid("No se encontraron convocatorias candidatas")
    with ThreadPoolExecutor(max_workers=3) as ex:
        list(ex.map(verify_notice,notices))
    pdfs=sum(n["originalFormat"]=="pdf" for n in notices)
    xmls=sum(n["originalFormat"]=="official_xml" for n in notices)
    print(f"BOR: {total} sumarios oficiales, {len(notices)} textos íntegros cotejados, "
          f"{pdfs} PDF originales accesibles, {xmls} XML originales como alternativa",flush=True)
    issues=[{key:r[key] for key in ("day","number","read","notices")} for r in rows]
    return publish_audit(SOURCE,PROVINCE,issues,today=END,min_issues=20)
if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--output",type=Path,required=True)
    a.add_argument("--prefer-pdf",action="store_true",help="Use PDF when reachable; XML otherwise")
    args=a.parse_args()
    PREFER_PDF=args.prefer_pdf
    write_output(args.output,audit())
