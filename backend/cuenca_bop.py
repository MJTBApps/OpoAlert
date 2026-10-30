#!/usr/bin/env python3
"""BOP Cuenca (Diputación de Cuenca): last 30 days from the official portal.

Portal oficial: https://www.dipucuenca.es/boletin1 (Liferay). La búsqueda por
intervalo de fechas devuelve una ficha por boletín con su número; cada ficha
lista todos los anuncios con su PDF individual (/documents/34525/<carpeta>/<n>.pdf).
Se comprueba:
  * que el buscador devuelve todos los resultados («1 - N de N») y coincide con
    los días marcados en el calendario oficial de cada mes;
  * números de boletín consecutivos;
  * que los PDF de cada boletín están en una sola carpeta, sin repetirse;
  * que la lista web coincide con el BOP completo firmado: con su sumario impreso
    o con sus cabeceras «NÚM.» (el portal a veces discrepa de uno de los dos, nunca
    de ambos a la vez en el último año);
  * que el PDF de cada candidata es un PDF real del mismo boletín, y de él se toma
    el número de anuncio (NÚM.) para el identificador CU-AAAA-N.
Si algo no cuadra se lanza ProvincialCoverageError y no se escribe el feed.
"""
from __future__ import annotations
import argparse,calendar as _cal,re
from datetime import date,timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urljoin,urlsplit,parse_qs,urlencode
from bs4 import BeautifulSoup
from clm_common import invalid,get,record,publish_audit,write_output,employment,numbering_ok
from provincial_common import fold

HOME="https://www.dipucuenca.es"
SOURCE=HOME+"/boletin1"
HOST={"www.dipucuenca.es"}
BULLETINS="_as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_LuthFM11tPwH"
PAGE_SIZE=60
NOTICE_PDF=re.compile(r"^/documents/34525/(\d{1,12})/(\d{1,4})(?:\+|%20)?\.pdf/[0-9a-f-]{36}$")
RESULTS=re.compile(r"Mostrando el intervalo\s+(\d+)\s*-\s*(\d+)\s+de\s+(\d+)\s+resultados",re.I)
SUBTITLE=re.compile(r"^\w+,\s*(\d{1,2})\s+de\s+([a-zñ]+)\s+(\d{4})$",re.I)
DETAIL_TITLE=re.compile(r"^Bolet[ií]n\s+(\d{4})-(\d{2})-(\d{2})(-[A-Z]+)?$")
# «73» boletín ordinario; «73-1» suplemento del 73 (la cabecera de su PDF dice «Núm. 73»).
CARD_NUMBER=re.compile(r"(\d{1,3})(?:-(\d{1,2}))?")
FULL_PDF=re.compile(r"^/documents/34525/[0-9a-f-]{36}$")
PDF_BULLETIN=re.compile(r"\bNúm\.\s*(\d{1,4})\b")
# Cabecera de cada anuncio: línea «NÚM. 2556». El original trae erratas («NÍM. 1886»,
# «NÚM 1891») y a veces el número en blanco («NÚM.»).
PDF_NOTICE=re.compile(r"^[ \t]*N[ÚUÍI]M\.?[ \t]*(\d{0,6})[ \t]*$",re.M)
# Entradas del sumario impreso: «Organismo.— Título».
SUMMARY_ENTRY=re.compile(r"\.[ \t]*—")
MAX_PDF=60_000_000
PDF_DATE=re.compile(r"\b(\d{1,2})\s+de\s+([a-zñ]+)\s+de\s+(\d{4})\b",re.I)
MONTHS=["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]

def search_url(start,end):
    # p_p_id del portlet de boletines: si no, ignora _delta y pagina de 20 en 20.
    q={"p_p_id":BULLETINS.strip("_"),"p_p_lifecycle":"0",
       "p_r_p_startDate":start.strftime("%d/%m/%Y"),"p_r_p_endDate":end.strftime("%d/%m/%Y"),
       BULLETINS+"_delta":str(PAGE_SIZE),BULLETINS+"_cur":"1"}
    return SOURCE+"?"+urlencode(q)

def month_url(year,month):
    return search_url(date(year,month,1),date(year,month,_cal.monthrange(year,month)[1]))

def spanish_date(d,m,y):
    m=fold(m)
    if m not in MONTHS:invalid("Cuenca: mes desconocido "+m)
    try:return date(int(y),MONTHS.index(m)+1,int(d))
    except ValueError:invalid("Cuenca: fecha imposible")

def calendar_days(html,year,month):
    """Días con boletín según el calendario oficial del mes (enlaces de un solo día)."""
    s=BeautifulSoup(html,"html.parser")
    found=set()
    for a in s.select('a[href*="p_r_p_startDate"]'):
        q=parse_qs(urlsplit(urljoin(SOURCE,a["href"])).query)
        st=q.get("p_r_p_startDate",[""])[0];en=q.get("p_r_p_endDate",[""])[0]
        if not st or st!=en:continue
        m=re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})",st)
        if not m:invalid("Cuenca: fecha de calendario ilegible")
        d=date(int(m[3]),int(m[2]),int(m[1]))
        if (d.year,d.month)!=(year,month):continue
        if a.get_text(strip=True)!=str(d.day):invalid("Cuenca: calendario incoherente")
        found.add(d)
    return found

def parse_listing(html):
    """Fichas de boletín del buscador: [(día, número, url ficha)]; exige la lista completa.
    El número es la etiqueta oficial: «125» o, para un suplemento, «73-1»."""
    s=BeautifulSoup(html,"html.parser")
    counters=[RESULTS.search(x.get_text(" ",strip=True)) for x in s.select(".pagination-results")]
    counters=[m for m in counters if m]
    cards=s.select("div.card.card-box")
    if not counters:
        if cards:invalid("Cuenca: buscador sin contador de resultados")
        return []
    first,last,total=map(int,counters[0].groups())
    if first!=1 or last!=total or total>=PAGE_SIZE:invalid(f"Cuenca: buscador paginado {first}-{last} de {total}")
    if len(cards)!=total:invalid(f"Cuenca: {len(cards)} fichas frente a {total} resultados")
    out=[]
    for c in cards:
        num=c.select_one(".card-text");sub=c.select_one(".card-subtitle");link=c.select_one(".card-body a[href]")
        if not (num and sub and link):invalid("Cuenca: ficha de boletín incompleta")
        n=num.get_text(strip=True)
        nm=CARD_NUMBER.fullmatch(n)
        if not nm or not 1<=int(nm[1])<=400 or nm[2]=="0":invalid("Cuenca: número de boletín inválido: "+n)
        m=SUBTITLE.fullmatch(" ".join(sub.get_text(" ",strip=True).split()))
        if not m:invalid("Cuenca: fecha de boletín ilegible")
        day=spanish_date(*m.groups())
        url=urljoin(SOURCE,link["href"])
        u=urlsplit(url)
        q=parse_qs(u.query)
        if (u.hostname not in HOST or u.path!="/boletin1"
            or not q.get(BULLETINS+"_articleId",[""])[0].isdigit()):
            invalid("Cuenca: enlace de ficha fuera del portal")
        out.append((day,n,url))
    return out

def main_number(label):
    """(número del boletín, nº de suplemento o 0)."""
    m=CARD_NUMBER.fullmatch(str(label))
    if not m:invalid(f"Cuenca: número de boletín inválido: {label}")
    return int(m[1]),int(m[2] or 0)

def parse_issue(html,day,supplement=False):
    """Ficha de un boletín: (url del BOP completo, [(organismo, título, url PDF, posición)])."""
    s=BeautifulSoup(html,"html.parser")
    art=s.select_one("article.template-boletin-detail")
    if art is None:invalid(f"Cuenca {day}: ficha de boletín ausente")
    t=art.select_one(".portlet-title")
    m=DETAIL_TITLE.fullmatch(t.get_text(" ",strip=True) if t else "")
    if not m or date(*map(int,m.groups()[:3]))!=day:invalid(f"Cuenca {day}: ficha de otra fecha")
    if bool(m[4])!=supplement:invalid(f"Cuenca {day}: ficha de suplemento no coincide con el buscador")
    full=[urljoin(SOURCE,a["href"]) for a in art.select(".image-wrapper-panel-info a[href]")]
    full=[u for u in full if urlsplit(u).hostname in HOST and FULL_PDF.fullmatch(urlsplit(u).path)]
    if len(set(urlsplit(u).path for u in full))!=1:invalid(f"Cuenca {day}: falta el BOP completo firmado")
    full=HOME+urlsplit(full[0]).path
    rows=[];folders=set();numbers=[]
    for card in art.select("div.card"):
        section=card.select_one(".card-title")
        section=section.get_text(" ",strip=True) if section else ""
        agency=section
        body=card.select_one("div.collapse") or card
        for el in body.find_all(["div","li"]):
            cls=el.get("class") or []
            if el.name=="div" and "h5" in cls:
                agency=el.get_text(" ",strip=True).rstrip(".").strip()
            elif el.name=="li" and "document-entry" in cls:
                a=el.select_one("a[href]")
                if a is None:invalid(f"Cuenca {day}: anuncio sin enlace")
                ti=a.select_one(".title")
                title=" ".join((ti.get_text(" ",strip=True) if ti else a.get("title","")).split())
                url=urljoin(SOURCE,a["href"])
                u=urlsplit(url)
                pm=NOTICE_PDF.fullmatch(u.path)
                if u.scheme!="https" or u.hostname not in HOST or not pm:
                    invalid(f"Cuenca {day}: PDF de anuncio fuera de la ruta oficial: {url[:160]}")
                folders.add(pm[1]);numbers.append(int(pm[2]))
                if not title or not agency:invalid(f"Cuenca {day}: anuncio sin título u organismo")
                rows.append((agency,title,HOME+u.path,int(pm[2])))
    if not rows:invalid(f"Cuenca {day}: boletín sin anuncios")
    if len(folders)!=1 or len(set(numbers))!=len(numbers):
        invalid(f"Cuenca {day}: PDF de anuncios repetidos o en varias carpetas")
    return full,rows

def pdf_pages(url,pages=1):
    """Texto de las primeras páginas (todas si pages=None) de un PDF oficial."""
    r=get(url,HOST,stream=True,timeout=(12,120))
    try:
        ctype=r.headers.get("Content-Type","").lower()
        data=bytearray()
        for chunk in r.iter_content(1<<16):
            data+=chunk
            if len(data)>MAX_PDF:invalid("Cuenca: PDF desmesurado: "+url)
    finally:r.close()
    if not data.startswith(b"%PDF-") or "pdf" not in ctype:
        invalid("Cuenca: enlace oficial no es PDF: "+url)
    import pymupdf
    try:
        doc=pymupdf.open(stream=bytes(data),filetype="pdf")
        try:return [doc[i].get_text() for i in range(min(pages or doc.page_count,doc.page_count))]
        finally:doc.close()
    except Exception as ex:invalid(f"Cuenca: PDF ilegible {url}: {ex}")

def pdf_text(url,pages=1):
    return "\n".join(pdf_pages(url,pages))

def full_pdf_counts(pages):
    """(entradas del sumario impreso, cabeceras «NÚM.») del BOP completo firmado."""
    first=next((i for i,t in enumerate(pages) if PDF_NOTICE.search(t)),None)
    if first is None:invalid("Cuenca: BOP completo sin anuncios")
    summary="\n".join(pages[:first])
    if first==0 or "SUMARIO" not in summary:invalid("Cuenca: BOP completo sin sumario")
    return len(SUMMARY_ENTRY.findall(summary)),sum(len(PDF_NOTICE.findall(t)) for t in pages)

def notice_number(text,day,bulletin):
    """Comprueba boletín (y fecha, si figura) en la cabecera del PDF del anuncio y
    devuelve su NÚM.; None si el boletín lo publicó con el número en blanco."""
    head=PDF_NOTICE.search(text)
    m=re.search(r"\bPág\.\s*\d+",text)
    header=text[:m.start()] if m else text[:head.start() if head else 400]
    b=PDF_BULLETIN.search(header);d=PDF_DATE.search(header)
    if not b or int(b[1])!=bulletin:invalid(f"Cuenca {day}: el PDF no es del boletín {bulletin}")
    # Algunas cabeceras salen sin fecha; si la hay, debe ser la del boletín.
    if d and spanish_date(*d.groups())!=day:invalid(f"Cuenca {day}: el PDF es de otra fecha")
    return int(head[1]) if head and head[1] else None

def kind(title):
    """employment() de CLM, sin presupuestos: en Cuenca «presupuesto general, bases de
    ejecución y plantilla de personal» es un anuncio presupuestario, no una convocatoria."""
    if "presupuesto" in fold(title):return None
    return employment(title)

def scan_issue(item):
    day,number,url=item
    main,sub=main_number(number)
    full,rows=parse_issue(get(url,HOST,timeout=(12,60)).text,day,supplement=sub>0)
    # El BOP completo firmado es la referencia: la ficha web debe cuadrar con su sumario
    # impreso o con sus cabeceras de anuncio.
    summary,heads=full_pdf_counts(pdf_pages(full,pages=None))
    if len(rows) not in (summary,heads):
        invalid(f"Cuenca {day}: la web lista {len(rows)} anuncios; el BOP {number} trae {summary} en el sumario y {heads} cabeceras")
    if not summary==heads==len(rows):
        print(f"AVISO Cuenca {day} BOP {number}: web {len(rows)}, sumario {summary}, cabeceras {heads}",flush=True)
    notices=[]
    for agency,title,pdf,pos in rows:
        if not kind(title):continue
        nid=notice_number(pdf_text(pdf),day,main)
        if nid is None:
            # Número de anuncio en blanco o ausente en el original: identificador estable que no
            # puede coincidir con un NÚM. real (9 + boletín + suplemento + posición).
            nid=int(f"9{main:03d}{sub:01d}{pos:03d}")
        row=record("CU","Cuenca",f"CU-{day.year}-{nid}",title,agency,day,number,pdf)
        if row["type"]:notices.append(row)
    print("CUENCA",day,"boletín",number,"anuncios",len(rows),"candidatas",len(notices),flush=True)
    return {"day":day,"number":number,"read":len(rows),"notices":notices}

def months(start,end):
    y,m=start.year,start.month
    while (y,m)<=(end.year,end.month):
        yield y,m
        y,m=(y+1,1) if m==12 else (y,m+1)

def audit(today=None):
    end=today or date.today()
    start=end-timedelta(days=29)
    listing=parse_listing(get(search_url(start,end),HOST,timeout=(12,60)).text)
    listing=[x for x in listing if start<=x[0]<=end]
    days=set()
    for y,m in months(start,end):
        days|={d for d in calendar_days(get(month_url(y,m),HOST,timeout=(12,60)).text,y,m) if start<=d<=end}
    if {x[0] for x in listing}!=days:
        invalid(f"Cuenca: buscador y calendario no coinciden {sorted({x[0] for x in listing}^days)}")
    listing.sort(key=lambda x:(x[0],main_number(x[1])))
    if len({x[1] for x in listing})!=len(listing):invalid("Cuenca: boletín repetido")
    ordinary=[(d,main_number(n)[0]) for d,n,_ in listing if main_number(n)[1]==0]
    if not numbering_ok(ordinary):
        invalid(f"Cuenca: BOP omitido {[n for _,n,_ in listing]}")
    for d,n,_ in listing:
        main,sub=main_number(n)
        if sub and (d,main) not in ordinary:invalid(f"Cuenca: suplemento {n} sin su boletín ordinario")
    with ThreadPoolExecutor(max_workers=3) as pool:
        issues=list(pool.map(scan_issue,listing))
    # Lunes, miércoles y viernes: unas 12-13 ediciones en 30 días (menos con festivos).
    return publish_audit(SOURCE,"Cuenca",issues,today=end,min_issues=10)

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    write_output(args.output,audit())
