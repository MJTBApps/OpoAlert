#!/usr/bin/env python3
"""BOP Teruel official 30-day reader with full XPages pagination and HTML notices.

The official PDF redirect points to a different host and is not independently
accessible from our runner. Use complete original announcement HTML served by
the Diputacion's official BOP portal; never publish unverified PDF links.
XPages only displays 10 results per page and caps searches at 100 results:
each calendar day must be searched separately, and every page must be read.
"""
from __future__ import annotations
import argparse
from datetime import date,datetime,timedelta,timezone
import json
from concurrent.futures import ThreadPoolExecutor
from math import ceil
from pathlib import Path
import re
from urllib.parse import urlsplit
import requests
from bs4 import BeautifulSoup
from provincial_common import ProvincialCoverageError,classify,fold

HOME="https://bender.dpteruel.es/dpt/bopt.nsf/inicio.xsp"
SEARCH="https://bender.dpteruel.es/dpt/bopt.nsf/busquedas.xsp"
NOTICE_PREFIX="https://bender.dpteruel.es/dpt/bopt.nsf/0/"
PROVINCE="Teruel"
FORM="Busquedas:_id1"
PREFIX=FORM+":_id53:"
ENTRY_RE=re.compile(r"Anuncio\s*#\s*(\d{4}-\d{4})\s*\.?\s*\((\d{2})/([^/]+)/(\d{4})\)",re.I)
FOUND_RE=re.compile(r"Se (?:han|ha) encontrado\s+(\d+)\s+anuncios?",re.I)
DETAIL_RE=re.compile(r"Anuncio\s*#\s*(\d{4}-\d{4}).*?Publicado el\s+(\d{1,2}/\d{1,2}/\d{2,4})\s*,?\s*BOP\s+n[uú]mero\s+(\d+)",re.I|re.S)
HEADER_RE=re.compile(r"BOP del d[ií]a\s+(\d{1,2}) de\s+([A-Za-záéíóúñ]+) de\s+(\d{4}).*?BOP n[uú]mero\s+(\d+)",re.I|re.S)
MONTHS={
 "enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
 "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,
 "noviembre":11,"diciembre":12,
}
TIMEOUT=28


def official(url:str)->bool:
    p=urlsplit(url)
    return (p.scheme=="https" and p.hostname=="bender.dpteruel.es"
            and p.port in (None,443) and p.username is None and p.password is None
            and not p.fragment and not p.query
            and p.path.lower().startswith("/dpt/bopt.nsf/"))


def safe_detail_url(url:str)->bool:
    return bool(official(url) and re.fullmatch(re.escape(NOTICE_PREFIX)+r"[0-9a-fA-F]{32}",url))


def request(session:requests.Session,url:str,data:dict|None=None)->str:
    if not official(url) or url not in (HOME,SEARCH) and not safe_detail_url(url):
        raise ProvincialCoverageError("Teruel: intento de acceso fuera del dominio oficial")
    for attempt in range(3):
        try:
            r=(session.post(url,data=data,timeout=TIMEOUT,headers={"Referer":SEARCH})
               if data is not None else session.get(url,timeout=TIMEOUT))
            if r.status_code!=200 or not official(r.url):
                raise ProvincialCoverageError(f"Teruel: respuesta no oficial {r.status_code} {r.url}")
            if len(r.content)>2_000_000 or not r.content:
                raise ProvincialCoverageError("Teruel: HTML vacio o demasiado extenso")
            if not r.encoding:r.encoding="utf-8"
            return r.text
        except (requests.RequestException,OSError) as ex:
            if attempt==2:raise ProvincialCoverageError(f"Teruel: fallo de red en {url}: {ex}") from ex
    raise ProvincialCoverageError("Teruel: solicitud incompleta")


def official_session()->requests.Session:
    s=requests.Session()
    s.headers.update({
        "User-Agent":"Mozilla/5.0 (compatible; OpoAlert official archive audit/1.9)",
        "Accept-Language":"es",
    })
    return s


def parse_home(html:str)->tuple[date,int]:
    text=BeautifulSoup(html,"html.parser").get_text(" ",strip=True)
    m=HEADER_RE.search(text)
    if not m:
        raise ProvincialCoverageError("Teruel: portada sin fecha y numero BOP")
    month=MONTHS.get(fold(m.group(2)))
    if month is None:raise ProvincialCoverageError("Teruel: mes desconocido en portada")
    return date(int(m.group(3)),month,int(m.group(1))),int(m.group(4))


def post_form(soup:BeautifulSoup,trigger:str,day:date)->dict:
    form=soup.select_one("form")
    if form is None or form.get("id")!=FORM:
        raise ProvincialCoverageError("Teruel: formulario de busqueda no reconocido")
    result={x["name"]:x.get("value","") for x in form.select("input[name]")
            if x.get("type")=="hidden"}
    if "$$viewid" not in result or not result["$$viewid"]:
        raise ProvincialCoverageError("Teruel: token de pagina XPages ausente")
    result["$$xspsubmitid"]=trigger
    result.update({
        PREFIX+"Seccion1":"",
        PREFIX+"Emisor1":"",
        PREFIX+"SearchContenido1":"",
        PREFIX+"inputfechadesde":day.strftime("%d/%m/%Y"),
        PREFIX+"inputText2":day.strftime("%d/%m/%Y"),
    })
    return result


def parse_page(html:str,day:date,total:int|None=None)->tuple[int,list[dict],BeautifulSoup]:
    soup=BeautifulSoup(html,"html.parser")
    query=soup.find(id=PREFIX+"computedField1")
    expected=f"(FIELD ffecha_a >= {day:%d/%m/%Y}) AND (FIELD ffecha_a <= {day:%d/%m/%Y})"
    if query is None or " ".join(query.get_text(" ",strip=True).split())!=expected:
        raise ProvincialCoverageError(f"Teruel {day}: servidor no confirmo filtro de un dia")
    count=soup.find(id=PREFIX+"computedField2")
    label=count.get_text(" ",strip=True) if count else ""
    match=FOUND_RE.search(label)
    if match:
        found=int(match.group(1))
        if found>=100 or found<1:
            raise ProvincialCoverageError(f"Teruel {day}: 100-result cap o total invalido ({found})")
    elif "No hay anuncios" in label:
        found=0
    else:
        raise ProvincialCoverageError(f"Teruel {day}: recuento no confirmado {label[:120]}")
    if total is not None and total!=found:
        raise ProvincialCoverageError(f"Teruel {day}: cambia el total durante paginacion")
    titles=soup.select('span[id$=":vtitulo:_internalViewText"]')
    agencies=soup.select('span[id$=":vemisor:_internalViewText"]')
    stamps=soup.select('span[id$=":viewColumn4:_internalViewText"]')
    if not (len(titles)==len(agencies)==len(stamps)) or len(titles)>10:
        raise ProvincialCoverageError(f"Teruel {day}: filas desalineadas en buscador")
    rows=[]
    for title_cell,agency_cell,stamp_cell in zip(titles,agencies,stamps):
        a=title_cell.select_one("a.link_anuncio[href]")
        agency=agency_cell.select(".campo_seccion")
        stamp=stamp_cell.select_one(".campo_numbop_v")
        if not a or len(agency)!=2 or not stamp:
            raise ProvincialCoverageError(f"Teruel {day}: anuncio sin titulo, organismo o numero")
        match=ENTRY_RE.fullmatch(stamp.get_text(" ",strip=True))
        label=a.get_text(" ",strip=True)
        entity=agency[-1].get_text(" ",strip=True)
        url=NOTICE_PREFIX+a.get("href","").removeprefix("0/")
        if (not match or not label or not entity or not safe_detail_url(url)
            or match.group(2)!=day.strftime("%d")
            or MONTHS.get(fold(match.group(3)))!=day.month
            or int(match.group(4))!=day.year):
            raise ProvincialCoverageError(f"Teruel {day}: datos incoherentes {stamp.get_text(' ',strip=True)}")
        rows.append({"id":match.group(1),"title":label,"entity":entity,"url":url})
    if len({x["url"] for x in rows})!=len(rows):
        raise ProvincialCoverageError(f"Teruel {day}: documento original duplicado en pagina")
    if (found==0 and rows) or (found>0 and not rows):
        raise ProvincialCoverageError(f"Teruel {day}: ausencia o presencia incoherente de anuncios")
    return found,rows,soup


def next_page_trigger(soup:BeautifulSoup,next_number:int)->str:
    # Native numbered XPages pager controls; prefer page-specific link
    # to avoid losing results when the pager exposes several groups.
    for a in soup.select("a[id][title]"):
        if a.get("title","").strip().lower()==f"go to page {next_number}":
            return a["id"]
    # The XPages ajax handler is bound to the enclosing span, not its <a>.
    parent=soup.find(id=PREFIX+"viewPanel1:pager1__Next")
    a=parent.select_one("a[id]") if parent else None
    if a is not None and parent.get("id"):
        return parent["id"]
    raise ProvincialCoverageError(f"Teruel: no existe enlace a pagina {next_number}")


def parse_detail(html:str,record:dict,day:date)->int:
    soup=BeautifulSoup(html,"html.parser")
    text=" ".join(soup.get_text(" ",strip=True).split())
    m=DETAIL_RE.search(text)
    date_parts=[int(x) for x in m.group(2).split("/")] if m else []
    if len(date_parts)==3 and date_parts[2]<100:
        date_parts[2]+=2000
    if not m or m.group(1)!=record["id"] or date_parts!=[day.day,day.month,day.year]:
        raise ProvincialCoverageError(f"Teruel {day}: detalle no corresponde a {record['id']}: {text[:500]}")
    # Only the official notice pages contain the full wording and issuer.
    normalized=fold(" ".join(text.split()))
    title=fold(" ".join(record["title"].split())).rstrip(". ")
    entity=fold(" ".join(record["entity"].split()))
    if title not in normalized or entity not in normalized:
        raise ProvincialCoverageError(f"Teruel {day}: titulo/emisor no coinciden {record['id']}; titulo={record['title']!r}; entidad={record['entity']!r}; detalle={text[:850]!r}")
    number=int(m.group(3))
    if number<1 or number>366:
        raise ProvincialCoverageError(f"Teruel {day}: numero de BOP imposible {number}")
    return number


def scan(day:date,session_factory=official_session)->dict|None:
    session=session_factory()
    try:
        form_html=request(session,SEARCH)
        first_html=request(session,SEARCH,post_form(BeautifulSoup(form_html,"html.parser"),
                                                   PREFIX+"_id139",day))
        total,rows,soup=parse_page(first_html,day)
        if total==0:return None
        pages=ceil(total/10)
        if len(rows)!=min(10,total):
            raise ProvincialCoverageError(f"Teruel {day}: primera pagina incompleta")
        for n in range(2,pages+1):
            trigger=next_page_trigger(soup,n)
            html=request(session,SEARCH,post_form(soup,trigger,day))
            got,more,soup=parse_page(html,day,total)
            expected=min(10,total-(n-1)*10)
            if len(more)!=expected:
                raise ProvincialCoverageError(f"Teruel {day}: pagina {n} con {len(more)} de {expected}")
            rows.extend(more)
        if len(rows)!=total or len({x["url"] for x in rows})!=total:
            raise ProvincialCoverageError(f"Teruel {day}: faltan anuncios tras paginacion")
        sample=rows[0]
        number=parse_detail(request(session,sample["url"]),sample,day)
        notices=[]
        for item in rows:
            kind=classify(item["title"])
            if kind is None:continue
            found_number=number if item["id"]==sample["id"] else parse_detail(
                request(session,item["url"]),item,day)
            if found_number!=number:
                raise ProvincialCoverageError(f"Teruel {day}: anuncio de otra edicion")
            notices.append({
                "id":"TE-"+item["id"]+"-"+item["url"].rsplit("/",1)[-1],"province":PROVINCE,"title":item["title"],
                "entity":item["entity"],"date":day.strftime("%d/%m/%Y"),
                "bulletin":str(number),"type":kind,"url":item["url"],
            })
        return {"date":day,"number":number,"read":total,"pages":pages,"notices":notices}
    finally:
        session.close()


def audit(days:int=30,today:date|None=None,scanner=scan,session_factory=official_session)->dict:
    if days!=30:raise ProvincialCoverageError("Teruel: se exigen exactamente 30 dias")
    end=today or date.today()
    start=end-timedelta(days=29)
    s=session_factory()
    try:
        latest,latest_number=parse_home(request(s,HOME))
    finally:
        s.close()
    if latest>end or (end-latest).days>4:
        raise ProvincialCoverageError(f"Teruel: BOP portada desactualizado {latest}")
    issues=[]
    absent=[]
    errors=[]
    dates=[start+timedelta(days=i) for i in range(days)]
    # Dos conexiones independientes como maximo, con sesiones HTTP por fecha.
    def checked(day:date):
        try:
            return scanner(day),None
        except ProvincialCoverageError as ex:
            return None,str(ex)
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(checked,dates))
    for day,(result,error) in zip(dates,results):
        if error:
            errors.append(f"{day}: {error}")
            print(f"Teruel {day}: ERROR VALIDACION {error}",flush=True)
            continue
        if result is None:
            absent.append(day.isoformat())
            print(f"Teruel {day}: no hay anuncios oficiales",flush=True)
            continue
        if result["date"]!=day or result["read"]<len(result["notices"]) or result["pages"]<1:
            raise ProvincialCoverageError(f"Teruel {day}: datos de edicion incorrectos")
        if issues and not errors:
            old=issues[-1]
            if old["date"].year==day.year and result["number"]!=old["number"]+1:
                raise ProvincialCoverageError(f"Teruel: saltan los numeros {old['number']} a {result['number']}")
            if old["date"].year!=day.year and result["number"]!=1:
                raise ProvincialCoverageError("Teruel: reinicio anual no confirmado")
        issues.append(result)
        print(f"Teruel {day}: BOP {result['number']}, {result['read']} anuncios, "
              f"{result['pages']} paginas, {len(result['notices'])} candidatas",flush=True)
    if errors:
        raise ProvincialCoverageError(f"Teruel: {len(errors)} fechas rechazadas; "+" | ".join(errors))
    if (len(issues)<15 or issues[-1]["date"]!=latest
        or issues[-1]["number"]!=latest_number
        or (issues[0]["date"]-start).days>4):
        raise ProvincialCoverageError("Teruel: historial incompleto frente a portada oficial")
    all_notices=[n for issue in issues for n in issue["notices"]]
    if not all_notices or len({n["id"] for n in all_notices})!=len(all_notices):
        raise ProvincialCoverageError("Teruel: candidatas vacias o duplicadas")
    all_notices.sort(key=lambda n:(datetime.strptime(n["date"],"%d/%m/%Y"),n["id"]),reverse=True)
    count=sum(issue["read"] for issue in issues)
    pages=sum(issue["pages"] for issue in issues)
    return {
       "schemaVersion":1,"source":HOME,"province":PROVINCE,
       "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
       "coverage":{"complete":True,"status":"complete","bulletin":str(latest_number),
                   "pagesVisited":pages,"announcementsRead":count,"opportunities":len(all_notices)},
       "historyCoverage":{"complete":True,"rangeStart":start.isoformat(),"rangeEnd":end.isoformat(),
                   "issuesRead":len(issues),"pagesVisited":pages,
                   "announcementsRead":count,"opportunities":len(all_notices),
                   "bulletins":[str(x["number"]) for x in issues],
                   "publicationDates":[x["date"].isoformat() for x in issues],
                   "nonPublicationDates":absent},
       "notices":all_notices,
    }


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--days",type=int,default=30)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    feed=audit(args.days)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(feed,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"TERUEL OK {feed['historyCoverage']['issuesRead']} ediciones, "
          f"{feed['coverage']['announcementsRead']} anuncios, "
          f"{len(feed['notices'])} candidatas",flush=True)
