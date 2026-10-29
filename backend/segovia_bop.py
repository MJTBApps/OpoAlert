#!/usr/bin/env python3
"""OpoAlert — Segovia BOP, full 30-day official archive and original PDF audit.

Uses Diputación de Segovia's public Liferay month navigation and verified
original edition PDFs; never infers missing issue dates from a limited home
page or copies unofficial summaries. Classifier examines the edition's own
printed table of contents, not unrelated text in its notices.
"""
from __future__ import annotations
import argparse,calendar,hashlib,io,re,threading,time
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlencode,urljoin,urlsplit,parse_qs
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader
from clm_common import employment,publish_audit,write_output
from provincial_common import ProvincialCoverageError,fold

SOURCE="https://www.dipsegovia.es/bop"
HOST="www.dipsegovia.es"
LABEL="Segovia"
AS_OF=date(2026,10,29)
MONTH={"septiembre":9,"octubre":10}
DATE_RE=re.compile(r"(?i)\b(\d{1,2}) de (septiembre|octubre)(?: de)? 2026\b")
TOC_ENTRY=re.compile(r"^\s*(?P<last>.*?)\s*\.{4,}\s*(?P<page>\d{1,3})\s*$")
URL_RE=re.compile(r"^/documents/39512/[a-f0-9-]{20,80}$")
THREAD=threading.local()

def fail(message):raise ProvincialCoverageError("Segovia BOP: "+str(message))
def session():
    if not hasattr(THREAD,"session"):
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert BOP official historical reader/1.0)",
          "Accept-Language":"es-ES,es;q=0.9"})
        THREAD.session=s
    return THREAD.session
def get(url,pdf=False):
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443) or u.username or u.password or u.fragment:
        fail("Enlace no corresponde a sede oficial: "+url[:150])
    error=None
    for trial in range(3):
        try:
            r=session().get(url,timeout=(12,37),allow_redirects=False)
            if r.status_code!=200:
                error=f"HTTP {r.status_code} {url[:170]}"
                r.close()
            elif len(r.content)<80 or len(r.content)>(15_000_000 if pdf else 900_000):
                error="Documento vacío o de tamaño inverosímil"
                r.close()
            elif pdf and not r.content.startswith(b"%PDF-"):
                error="El documento original no es PDF"
                r.close()
            elif not pdf and "html" not in r.headers.get("content-type","").lower():
                error="Se esperaba HTML de sede oficial"
                r.close()
            else:
                return r.content
        except requests.RequestException as ex:error=str(ex)[:230]
        if trial<2:time.sleep(.7*(trial+1))
    fail("Sin acceso al original: "+str(error))

def pages_for_month(month):
    daylast=calendar.monthrange(2026,month)[1]
    query=urlencode({"p_r_p_startDate":f"01/{month:02d}/2026","p_r_p_endDate":f"{daylast:02d}/{month:02d}/2026"})
    html=BeautifulSoup(get(SOURCE+"?"+query),"html.parser")
    if html.title is None or "Segovia" not in html.title.get_text(" ",strip=True):
        fail("Índice mensual no pertenece a Diputación de Segovia")
    rows=[]
    for card in html.select("div.card.card-box"):
        numbernode=card.select_one("span.card-text")
        datednode=card.select_one("span.card-subtitle")
        detailnode=card.select_one('a[href*="articleId="]')
        if numbernode is None or datednode is None or detailnode is None:
            fail("Edición sin número, fecha o enlace")
        number=int(numbernode.get_text(" ",strip=True))
        title=datednode.get_text(" ",strip=True)
        match=DATE_RE.search(title)
        if not match or int(match.group(2) and MONTH[match.group(2).lower()])!=month:
            fail("Fecha fuera del mes solicitado: "+title)
        day=date(2026,month,int(match.group(1)))
        url=urljoin(SOURCE,detailnode["href"])
        u=urlsplit(url)
        qs=parse_qs(u.query)
        if (u.scheme!="https" or u.hostname!=HOST or u.path!="/bop"
            or qs.get("p_p_id")!=["as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm"]
            or len(qs.get("_as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm_articleId",[]))!=1
            or not re.fullmatch(r"\d{6,10}",qs["_as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm_articleId"][0])):
            fail("Enlace de ficha no pertenece al archivo de Segovia")
        if date(2026,9,30)<=day<=AS_OF:
            rows.append({"day":day,"number":number,"detail":url})
    return rows

def calendar_30d():
    rows=sorted(pages_for_month(9)+pages_for_month(10),key=lambda x:x["day"])
    if len(rows)!=13:fail(f"Se esperan 13 ediciones ordinarias entre 30/09 y 29/10; recibidas {len(rows)}")
    days=[x["day"] for x in rows]
    numbers=[x["number"] for x in rows]
    if (days[0]!=date(2026,9,30) or days[-1]!=date(2026,10,28)
        or len(set(days))!=len(rows) or numbers!=list(range(117,130))):
        fail(f"Histórico provincial con huecos de fecha o numeración: {days[0]}–{days[-1]} {numbers}")
    expected=[date(2026,9,30)+timedelta(days=i) for i in range(30)
              if (date(2026,9,30)+timedelta(days=i)).weekday() in (0,2,4)]
    if days!=expected:fail("Falta una edición ordinaria de lunes/miércoles/viernes")
    print(f"SEGOVIA_ARCHIVE: {len(rows)} ediciones continuas (117–129)",flush=True)
    return rows

def edition_pdf(row):
    doc=BeautifulSoup(get(row["detail"]),"html.parser")
    text=doc.get_text(" ",strip=True)
    expected=f"BOP-{row['number']}-{row['day']:%d/%m/%Y}"
    if expected not in text:
        fail(f"Ficha provincial sin número y fecha {expected}")
    found=[]
    for a in doc.select("a[href]"):
        label=" ".join(a.get_text(" ",strip=True).split())
        if re.search(rf"(?i)\bN[ºo.]{{1,3}}\s*{row['number']}\s*\.\s*0?{row['day'].day}\s+{('septiembre' if row['day'].month==9 else 'octubre')}\s+2026",label):
            url=urljoin(row["detail"],a["href"])
            u=urlsplit(url)
            if u.scheme!="https" or u.hostname!=HOST or not URL_RE.fullmatch(u.path):
                fail("Documento de boletín no corresponde a original publicado")
            found.append(url)
    if len(set(found))!=1:
        fail(f"BOP {row['number']}: ficha sin PDF original único; hallados {len(found)}")
    return found[0]

def agency_line(line):
    n=fold(line).strip()
    return (n.startswith("ayuntamiento de ") or n.startswith("entidad local menor de ")
            or n.startswith("mancomunidad ") or n.startswith("comunidad de villa ")
            or n.startswith("comunidad de pinares ") or n.startswith("diputacion de segovia")
            or n.startswith("junta de castilla y leon")
            or n.startswith("universidad de ") or n.startswith("comunidad de regantes")
            or n.startswith("consorcio ") or n.startswith("delegacion territorial"))

def skip_line(line):
    n=fold(line).strip()
    return (not n or n.startswith(("www.dipsegovia.es","bopsegovia@","d. l.:",
      "verificacion:","codigo de validacion:","cod. validacion:","documento firmado","pagina  ",
      "boletin oficial de la provincia", "sumario","ano 2026","ano 2025",
      "oficialboletin","de la","provincia de segovia","num. ","pag. "))
      or "administracion municipal"==n
      or "particulares y otros anunciantes"==n
      or "administracion de justicia"==n
      or "administracion local"==n
      or "jueves, " in n[:9] or "miercoles, " in n[:13] or "viernes, " in n[:10]
      or "lunes, " in n[:8] or "martes, " in n[:9])

def identify_toc(reader,number):
    parts=[]
    for i in range(min(6,len(reader.pages))):
        t=reader.pages[i].extract_text() or ""
        if i==0:
            if "SUMARIO" not in t:fail("No se ha encontrado el sumario oficial")
            t=t.rsplit("SUMARIO",1)[-1]
        elif not re.search(r"\.{5,}\s*\d{1,3}\s*$",t,re.M):
            break
        parts.append(t)
    if not parts:fail("Sumario original vacío")
    lines="\n".join(parts).splitlines()
    agency="Diputación de Segovia"
    hold=[]
    allrows=[]
    for raw in lines:
        line=" ".join(raw.split())
        if skip_line(line):continue
        if agency_line(line):
            agency=line
            hold=[]
            continue
        match=TOC_ENTRY.match(line)
        if match:
            part=match.group("last").strip()
            page=int(match.group("page"))
            if not 2<=page<=len(reader.pages):
                fail("Número de página de sumario fuera de PDF oficial")
            title=" ".join((hold[-5:]+[part]))
            title=" ".join(title.split())
            if not 5<len(title)<1000:fail("Entrada de sumario ilegible")
            allrows.append({"title":title,"agency":agency,"page":page})
            hold=[]
        elif (line and len(line)>2 and "................................" not in line and
              not line.startswith(("Cód. Validación","Documento firmado"))):
            hold.append(line)
    if not 5<=len(allrows)<=250:fail(f"BOP {number}: sumario demasiado corto o largo ({len(allrows)})")
    pages=[x["page"] for x in allrows]
    if pages!=sorted(pages) or pages[-1]>len(reader.pages):
        fail(f"BOP {number}: sumario con páginas fuera de orden")
    return allrows

def audit_issue(row):
    pdf=edition_pdf(row)
    data=get(pdf,pdf=True)
    reader=PdfReader(io.BytesIO(data))
    if not 6<=len(reader.pages)<=350:fail("PDF original número de páginas inverosímil")
    cover=reader.pages[0].extract_text() or ""
    if not (re.search(rf"(?i)AÑO\s+2026.+NÚMERO\s+{row['number']}\b",cover)
            and "SEGOVIA" in cover.upper()):
        fail(f"BOP {row['number']}: cabecera PDF de otra edición")
    allrows=identify_toc(reader,row["number"])
    selected=[]
    for notice in allrows:
        kind=employment(notice["title"])
        if not kind:continue
        uid="SG-2026-"+hashlib.sha256(
           f"{row['number']}|{notice['page']}|{notice['agency']}|{notice['title']}".encode("utf-8")
           ).hexdigest()[:18]
        selected.append({"id":uid,"province":LABEL,"title":notice["title"],"entity":notice["agency"],
           "date":row["day"].strftime("%d/%m/%Y"),"bulletin":str(row["number"]),
           "type":kind,"url":pdf,"pageInPdf":notice["page"]})
    print(f"SEGOVIA_ISSUE {row['day']} BOP {row['number']} PDF {len(reader.pages)} páginas "
          f"{len(allrows)} anuncios {len(selected)} candidatas",flush=True)
    for n in selected:print("SEGOVIA_CANDIDATE",n["id"],repr(n["title"][:150]),n["pageInPdf"],flush=True)
    return {"day":row["day"],"number":str(row["number"]),"read":len(allrows),"notices":selected,
            "editionPdf":pdf,"pdfPages":len(reader.pages)}

def audit():
    rows=calendar_30d()
    with ThreadPoolExecutor(max_workers=3) as pool:
        results=list(pool.map(audit_issue,rows))
    total=sum(x["read"] for x in results)
    if total<180:fail(f"Archivo de 13 sumarios incompleto: {total} anuncios")
    feed=publish_audit(SOURCE,LABEL,results,today=AS_OF,min_issues=13)
    feed["historyCoverage"]["editionPDFs"]=[x["editionPdf"] for x in results]
    feed["historyCoverage"]["originalPdfPagesRead"]=sum(x["pdfPages"] for x in results)
    feed["historyCoverage"]["editionArticleCounts"]=[x["read"] for x in results]
    print("SEGOVIA_AUDIT_SUMMARY",len(results),total,len(feed["notices"]),flush=True)
    return feed

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    write_output(args.output,audit())
