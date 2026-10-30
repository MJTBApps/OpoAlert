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
from clm_common import employment,numbering_ok,publish_audit,write_output
from provincial_common import ProvincialCoverageError,fold

SOURCE="https://www.dipsegovia.es/bop"
HOST="www.dipsegovia.es"
LABEL="Segovia"
MONTHS=("enero","febrero","marzo","abril","mayo","junio","julio","agosto",
        "septiembre","octubre","noviembre","diciembre")
WEEKDAYS=("lunes","martes","miercoles","jueves","viernes","sabado","domingo")
DATE_RE=re.compile(r"\b(\d{1,2}) de ("+"|".join(MONTHS)+r")(?: de)? (\d{4})\b")
# "AÑO 2026.— NÚMERO 8"; every PDF also carries a hidden template header of an
# old issue (AÑO 2025.— NÚMERO 127 ... LUNES, 3 DE NOVIEMBRE), so the real one
# is the header next to this edition's own weekday and date.
HEADER_RE=re.compile(r"ano\s+(\d{4})\W{0,8}numero\s+(\d{1,3}|extraordinario)\b")
EXTRA="EXTRAORDINARIO"
WORKERS=3
# Lunes, miércoles y viernes: unas 13 ediciones en 30 días; en Navidad, menos.
MIN_ISSUES=11
CONTROL_DAYS=10
PAGE_LIMIT=20  # the archive paginates from 20 cards on: never rely on page 1 then
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

def card_number(text):
    t=" ".join(text.split())
    if re.fullmatch(r"\d{1,3}",t):return int(t)
    if fold(t)=="extraordinario":return EXTRA
    fail("Número de edición ilegible: "+t[:40])

def pages_for_range(first,last):
    """Editions listed by the official archive between two dates (both included)."""
    query=urlencode({"p_r_p_startDate":f"{first:%d/%m/%Y}","p_r_p_endDate":f"{last:%d/%m/%Y}"})
    html=BeautifulSoup(get(SOURCE+"?"+query),"html.parser")
    if html.title is None or "Segovia" not in html.title.get_text(" ",strip=True):
        fail("Índice del archivo no pertenece a Diputación de Segovia")
    cards=html.select("div.card.card-box")
    if len(cards)>=PAGE_LIMIT:fail(f"Archivo paginado entre {first} y {last}: {len(cards)} ediciones")
    rows=[]
    for card in cards:
        numbernode=card.select_one("span.card-text")
        datednode=card.select_one("span.card-subtitle")
        detailnode=card.select_one('a[href*="articleId="]')
        if numbernode is None or datednode is None or detailnode is None:
            fail("Edición sin número, fecha o enlace")
        number=card_number(numbernode.get_text(" ",strip=True))
        title=datednode.get_text(" ",strip=True)
        match=DATE_RE.search(fold(title))
        if not match:fail("Fecha de edición ilegible: "+title)
        try:day=date(int(match.group(3)),MONTHS.index(match.group(2))+1,int(match.group(1)))
        except ValueError:fail("Fecha de edición imposible: "+title)
        if not first<=day<=last:fail(f"Edición fuera del intervalo pedido ({first}–{last}): {title}")
        url=urljoin(SOURCE,detailnode["href"])
        u=urlsplit(url)
        qs=parse_qs(u.query)
        if (u.scheme!="https" or u.hostname!=HOST or u.path!="/bop"
            or qs.get("p_p_id")!=["as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm"]
            or len(qs.get("_as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm_articleId",[]))!=1
            or not re.fullmatch(r"\d{6,10}",qs["_as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm_articleId"][0])):
            fail("Enlace de ficha no pertenece al archivo de Segovia")
        rows.append({"day":day,"number":number,"detail":url})
    return rows

def month_chunks(first,last):
    """[first, last] split by calendar month (each chunk stays far below PAGE_LIMIT)."""
    while first<=last:
        month_end=date(first.year,first.month,calendar.monthrange(first.year,first.month)[1])
        yield first,min(month_end,last)
        first=month_end+timedelta(days=1)

def listing(start,end):
    rows=[]
    for a,b in month_chunks(start,end):rows+=pages_for_range(a,b)
    rows.sort(key=lambda x:(x["day"],str(x["number"])))
    if len({(x["day"],str(x["number"])) for x in rows})!=len(rows):fail("Edición repetida en el archivo")
    return rows

def edition_pdf(row):
    doc=BeautifulSoup(get(row["detail"]),"html.parser")
    # The publisher formats days inconsistently (e.g. 7/10 versus 07/10).
    # The uniquely matched numbered-date PDF link and PDF cover are authoritative.
    found=[]
    month=MONTHS[row["day"].month-1]
    for a in doc.select("a[href]"):
        label=fold(" ".join(a.get_text(" ",strip=True).split()))
        if re.search(rf"\bn[ºo.]{{1,3}}\s*{str(row['number']).lower()}\s*\.\s*0?{row['day'].day}\s+{month}\s+{row['day'].year}\b",label):
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
      "boletin oficial de la provincia", "sumario",
      "oficialboletin","de la","provincia de segovia","num. ","pag. "))
      or re.match(r"ano \d{4}\b",n)
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
        # Guard against the hidden template header of an old issue: the text
        # taken as this edition's sumario may only name this edition.
        for year,num in HEADER_RE.findall(fold(t)):
            if num!=str(number).lower():
                fail(f"BOP {number}: el sumario leído contiene la cabecera de otra edición (nº {num} de {year})")
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
    if not (1 if number==EXTRA else 5)<=len(allrows)<=250:fail(f"BOP {number}: sumario demasiado corto o largo ({len(allrows)})")
    pages=[x["page"] for x in allrows]
    if pages!=sorted(pages) or pages[-1]>len(reader.pages):
        fail(f"BOP {number}: sumario con páginas fuera de orden")
    return allrows

def cover_number(cover,day):
    """Number printed next to this edition's own weekday and date on page 1."""
    text=fold(cover)
    weekday=r"\s?".join(WEEKDAYS[day.weekday()])  # text extraction may split it: "miercol es"
    stamp=re.compile(rf"{weekday}\s*,\s*0?{day.day}\s+de\s+{MONTHS[day.month-1]}")  # PDF text may glue "diciembreAÑO"
    found=set()
    for m in HEADER_RE.finditer(text):
        if int(m.group(1))==day.year and stamp.search(text[max(0,m.start()-120):m.end()+120]):
            found.add(m.group(2))
    if len(found)!=1 or "segovia" not in text:
        fail(f"Cabecera del PDF de {day} ilegible o ambigua: {sorted(found)}")
    num=found.pop()
    return EXTRA if num=="extraordinario" else int(num)

def open_edition(row):
    pdf=edition_pdf(row)
    reader=PdfReader(io.BytesIO(get(pdf,pdf=True)))
    number=cover_number(reader.pages[0].extract_text() or "",row["day"])
    if (number==EXTRA)!=(row["number"]==EXTRA):
        fail(f"{row['day']}: el archivo y el PDF no coinciden en si la edición es extraordinaria")
    if number!=row["number"]:
        # Seen in January 2026: the archive card said 14 and 16 for editions
        # whose original PDFs are numbers 6 and 7. The original PDF is binding,
        # and the whole sequence of PDF numbers is checked afterwards.
        print(f"SEGOVIA_NUMERO_ARCHIVO {row['day']}: archivo nº {row['number']}, PDF original nº {number}",flush=True)
    return pdf,reader,number

def audit_issue(row):
    pdf,reader,number=open_edition(row)
    min_pages=2 if number==EXTRA else 6
    if not min_pages<=len(reader.pages)<=350:fail("PDF original número de páginas inverosímil")
    row=dict(row,number=number)
    allrows=identify_toc(reader,row["number"])
    selected=[]
    for notice in allrows:
        title_normalized=fold(notice["title"]).lower()
        if ("rectificacion de errores" in title_normalized
            or "se nombran funcionarios" in title_normalized
            or "sobre defectos insubsanables" in title_normalized
            or "relacion de personas aprobadas" in title_normalized
            or "publicacion de la relacion de aspirantes aprobados" in title_normalized):
            continue
        kind=employment(notice["title"])
        if not kind:continue
        uid=f"SG-{row['day'].year}-"+hashlib.sha256(
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

def control_edition(start):
    """Last ordinary edition before the window, numbered from its original PDF."""
    before=[x for x in listing(start-timedelta(days=CONTROL_DAYS),start-timedelta(days=1)) if x["number"]!=EXTRA]
    if not before:fail(f"Sin edición de control en los {CONTROL_DAYS} días previos a {start}")
    row=before[-1]
    return row["day"],open_edition(row)[2]

def check_sequence(results,control):
    """Ordinary editions numbered on from the control one (back to 1 in January)."""
    ordinary=[(x["day"],int(x["number"])) for x in results if x["number"]!=EXTRA]
    if len(ordinary)<MIN_ISSUES:fail(f"Solo {len(ordinary)} ediciones ordinarias en 30 días")
    seq=[control]+ordinary
    if not numbering_ok(seq):
        fail("Numeración de ediciones con huecos: "+str([f"{d:%d/%m}:{n}" for d,n in seq]))

def audit(today=None):
    end=today or date.today()
    start=end-timedelta(days=29)
    rows=listing(start,end)
    if not rows:fail(f"Ninguna edición entre {start} y {end}")
    control=control_edition(start)
    print(f"SEGOVIA_ARCHIVE: {len(rows)} ediciones entre {start} y {end} (control {control[0]} nº {control[1]})",flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results=list(pool.map(audit_issue,rows))
    check_sequence(results,control)
    total=sum(x["read"] for x in results)
    if total<5*len(results):fail(f"Archivo de {len(results)} sumarios incompleto: {total} anuncios")
    feed=publish_audit(SOURCE,LABEL,results,today=end,min_issues=MIN_ISSUES)
    feed["historyCoverage"]["editionPDFs"]=[x["editionPdf"] for x in results]
    feed["historyCoverage"]["originalPdfPagesRead"]=sum(x["pdfPages"] for x in results)
    feed["historyCoverage"]["editionArticleCounts"]=[x["read"] for x in results]
    print("SEGOVIA_AUDIT_SUMMARY",len(results),total,len(feed["notices"]),flush=True)
    return feed

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    ap.add_argument("--today",type=date.fromisoformat,default=None,help="fin de la ventana (pruebas)")
    args=ap.parse_args()
    write_output(args.output,audit(args.today))
