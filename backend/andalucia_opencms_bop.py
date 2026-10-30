#!/usr/bin/env python3
"""Official Granada and Sevilla BOP readers. Fail closed on incomplete 30-day archives."""
from __future__ import annotations
import argparse,json,re,time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date,datetime,timedelta,timezone
from math import ceil
from pathlib import Path
from urllib.parse import urljoin,urlsplit
import requests
from bs4 import BeautifulSoup
from provincial_common import ProvincialCoverageError,classify,fold

@dataclass(frozen=True)
class Source:
    slug:str
    province:str
    code:str
    host:str
    ref_prefix:str

GRANADA=Source("granada","Granada","GR","bop.dipgra.es","BOP-GRA")
SEVILLA=Source("sevilla","Sevilla","SV","bopsevilla.dipusevilla.es","BOP-SE")
SOURCES={x.slug:x for x in (GRANADA,SEVILLA)}
HEADER_RE=re.compile(r"BOP\s+n[úu]m\.\s*(\d{1,3})\s+del\s+(\d{2}/\d{2}/\d{4})",re.I)
COUNT_RE=re.compile(r"Resultados\s+del\s+(\d+)\s+al\s+(\d+)\s+de\s+(\d+)",re.I)

def home(s:Source)->str:
    return f"https://{s.host}/publica/consulta-de-bops/"

def daily_url(s:Source,d:date)->str:
    return f"https://{s.host}/publica/consulta-de-bops/buscador/BOP-{d:%d-%m-%Y}/"

def official_url(s:Source,url:str,prefix:str)->bool:
    p=urlsplit(url)
    return bool(p.scheme=="https" and p.hostname==s.host and p.port in (None,443)
      and not p.username and not p.password and not p.fragment and not p.query
      and p.path.startswith(prefix))

def pdf_url_ok(s:Source,url:str,edition:bool=False)->bool:
    prefix="/export/sites/bop/.galleries/Documentos-BOPs-en-PDF/" if edition else (
      "/export/sites/bop/.galleries/Documentos-Anuncios-en-PDF/")
    return official_url(s,url,prefix) and urlsplit(url).path.lower().endswith(".pdf")

def get(s:Source,url:str,missing_ok:bool=False,pdf:bool=False)->requests.Response|None:
    p=urlsplit(url)
    if not official_url(s,url,p.path) and not (
        p.scheme=="https" and p.hostname==s.host and
        re.fullmatch(r"/publica/consulta-de-bops/buscador/BOP-\d{2}-\d{2}-\d{4}/",p.path) and
        re.fullmatch(r"page=[1-9]\d*",p.query) and not p.fragment and not p.username):
        raise ProvincialCoverageError(f"{s.province}: URL no autorizada")
    if pdf and not (pdf_url_ok(s,url) or pdf_url_ok(s,url,True)):
        raise ProvincialCoverageError(f"{s.province}: PDF fuera de la diputacion")
    last=None
    for attempt in range(2):
        try:
            r=requests.get(url,timeout=(10,32),stream=pdf,allow_redirects=True,
                headers={"User-Agent":"Mozilla/5.0 (compatible; OpoAlert verified gazette)",
                         "Accept-Language":"es"})
            if r.status_code==404 and missing_ok:
                r.close()
                return None
            if r.status_code!=200 or urlsplit(r.url).hostname!=s.host:
                status=r.status_code
                r.close()
                raise ProvincialCoverageError(f"{s.province}: HTTP {status}, no se publica")
            if pdf:
                return r
            if not r.content or len(r.content)>1_600_000:
                raise ProvincialCoverageError(f"{s.province}: HTML vacio/excesivo")
            return r
        except (requests.RequestException,ProvincialCoverageError) as err:
            last=err
            if attempt==0:time.sleep(0.5)
    raise ProvincialCoverageError(f"{s.province}: no se pudo leer {url}: {last}")

def check_pdf(s:Source,url:str,edition:bool=False)->None:
    if not pdf_url_ok(s,url,edition):raise ProvincialCoverageError(f"{s.province}: PDF no oficial")
    r=get(s,url,pdf=True)
    try:
        head=next(r.iter_content(chunk_size=48),b"")
        if "pdf" not in r.headers.get("Content-Type","").lower() or not head.startswith(b"%PDF-"):
            raise ProvincialCoverageError(f"{s.province}: archivo PDF original no comprobado")
    finally:r.close()

def parse_page(s:Source,html:str,day:date,first_expected:int=1)->dict:
    doc=BeautifulSoup(html,"html.parser")
    h=doc.select_one("h1") if s.slug=="leon" else doc.select_one("h2")
    match=HEADER_RE.fullmatch(h.get_text(" ",strip=True)) if h else None
    if match is None or match.group(2)!=day.strftime("%d/%m/%Y"):
        raise ProvincialCoverageError(f"{s.province} {day}: cabecera de boletin incorrecta")
    number=int(match.group(1))
    count=COUNT_RE.search(doc.get_text(" ",strip=True))
    if count is None:raise ProvincialCoverageError(f"{s.province} {day}: falta contador de anuncios")
    first,last,total=map(int,count.groups())
    if not (1<=total<=1300 and 1<=number<=366 and first==first_expected and first<=last<=total):
        raise ProvincialCoverageError(f"{s.province} {day}: contador de pagina imposible")
    cards=doc.select("li.elementoListado")
    if len(cards)!=last-first+1:
        raise ProvincialCoverageError(f"{s.province} {day}: faltan anuncios en pagina")
    rows=[]
    seen=set()
    for card in cards:
        a=card.select_one("a.enlace_elemento[href]")
        title=card.select_one("h3.titulo_elemento")
        agency=card.select_one(".campo_1")
        field=card.select_one(".campo_3")
        dayfield=card.select_one(".fecha_elemento")
        if any(x is None for x in (a,title,agency,field,dayfield)):
            raise ProvincialCoverageError(f"{s.province} {day}: anuncio sin identificacion")
        ident=field.get_text(" ",strip=True)
        expected=re.fullmatch(re.escape(s.ref_prefix)+r"-(\d{4})-(\d{3})(\d{3})",ident)
        detail=urljoin(home(s),a.get("href",""))
        name=title.get_text(" ",strip=True)
        entity=agency.get_text(" ",strip=True)
        if (expected is None or int(expected.group(1))!=day.year
            or int(expected.group(2))!=number or int(expected.group(3))==0
            or dayfield.get_text(" ",strip=True)!=day.strftime("%d/%m/%Y")
            or ident in seen or not name or not entity
            or len(name)>600 or len(entity)>300
            or not official_url(s,detail,"/publica/buscador-anuncios/anuncio/")
            or not urlsplit(detail).path.endswith("/")):
            raise ProvincialCoverageError(f"{s.province} {day}: anuncio no verificable {ident}")
        seen.add(ident)
        rows.append({"id":ident,"title":name,"entity":entity,"detail":detail})
    editions=[urljoin(home(s),a["href"]) for a in doc.select('a[href]') if
       "/Documentos-BOPs-en-PDF/" in a["href"]]
    editions=[u for u in editions if pdf_url_ok(s,u,edition=True)]
    if len(set(editions))!=1:
        raise ProvincialCoverageError(f"{s.province} {day}: PDF del numero completo no encontrado")
    return {"date":day,"number":number,"total":total,"first":first,"last":last,
            "rows":rows,"editionPdf":editions[0]}

def detail_pdf(s:Source,html:str,day:date,index_title:str)->tuple[str,str]:
    doc=BeautifulSoup(html,"html.parser")
    h=doc.select_one("h1.titulo_detalle")
    if h is None:raise ProvincialCoverageError(f"{s.province}: ficha sin titulo original")
    full=h.get_text(" ",strip=True)
    displayed=fold(index_title.rstrip(". ").replace("…","").rstrip(". "))
    if not full or len(full)>1500 or not fold(full).startswith(displayed[:min(len(displayed),50)]):
        raise ProvincialCoverageError(f"{s.province}: titulo no coincide con ficha")
    if ("Fecha de publicación "+day.strftime("%d/%m/%Y")) not in doc.get_text(" ",strip=True):
        raise ProvincialCoverageError(f"{s.province}: anuncio de otra fecha")
    pdfs=[urljoin(home(s),a["href"]) for a in doc.select("a[href]") if
         pdf_url_ok(s,urljoin(home(s),a["href"]))]
    if len(set(pdfs))!=1:
        raise ProvincialCoverageError(f"{s.province}: anuncio sin un PDF oficial unico")
    return full,pdfs[0]

def scan(s:Source,day:date)->dict|None:
    base=daily_url(s,day)
    r=get(s,base,missing_ok=True)
    if r is None:return None
    first=parse_page(s,r.text,day)
    total=first["total"]
    rows=list(first["rows"])
    size=first["last"]
    if size<1:raise ProvincialCoverageError(f"{s.province}: primera pagina vacia")
    for page in range(2,ceil(total/size)+1):
        other=parse_page(s,get(s,base+f"?page={page}").text,day,(page-1)*size+1)
        if other["number"]!=first["number"] or other["total"]!=total or other["editionPdf"]!=first["editionPdf"]:
            raise ProvincialCoverageError(f"{s.province}: paginacion de otro boletin")
        rows.extend(other["rows"])
    if len(rows)!=total or len({x["id"] for x in rows})!=total:
        raise ProvincialCoverageError(f"{s.province} {day}: sumario incompleto")
    check_pdf(s,first["editionPdf"],edition=True)
    notices=[]
    for row in rows:
        # Classification reads published title only; never guesses positions or application deadlines.
        if classify(row["title"]) is None:continue
        response=get(s,row["detail"])
        full,url=detail_pdf(s,response.text,day,row["title"])
        kind=classify(full)
        if kind is None:continue
        check_pdf(s,url)
        notices.append({"id":s.code+"-"+row["id"][len(s.ref_prefix)+1:],
             "province":s.province,"title":full,"entity":row["entity"],
             "date":day.strftime("%d/%m/%Y"),"bulletin":str(first["number"]),
             "type":kind,"url":url})
    return {"date":day,"number":first["number"],"read":total,
            "pages":ceil(total/size),"notices":notices,"pdf":first["editionPdf"]}

def audit(s:Source,days:int=30,today:date|None=None,reader=scan)->dict:
    if days!=30:raise ProvincialCoverageError("Solo se permite auditoria de 30 dias")
    end=today or date.today()
    start=end-timedelta(days=29)
    dates=[start+timedelta(days=n) for n in range(30)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        editions=list(pool.map(lambda d: reader(s,d),dates))
    issues=[]
    absent=[]
    for day,data in zip(dates,editions):
        if data is None:
            absent.append(day.isoformat());continue
        if (data["date"]!=day or data["read"]<len(data["notices"])
            or data["pages"]<1 or not pdf_url_ok(s,data["pdf"],True)):
            raise ProvincialCoverageError(f"{s.province} {day}: datos inconsistentes")
        # En enero la numeración vuelve a empezar en 1.
        if issues and data["number"]!=issues[-1]["number"]+1 and not (
            data["date"].year!=issues[-1]["date"].year and data["number"]==1):
            raise ProvincialCoverageError(f"{s.province}: salto de numero entre BOP "
               f"{issues[-1]['number']} y {data['number']}")
        if issues and (day-issues[-1]["date"]).days>5:
            raise ProvincialCoverageError(f"{s.province}: intervalo no publicado no comprobado")
        issues.append(data)
        print(s.province,day,"BOP",data["number"],"anuncios",data["read"],
              "candidatas",len(data["notices"]),flush=True)
    if (len(issues)<15 or (issues[0]["date"]-start).days>4
        or (end-issues[-1]["date"]).days>4):
        raise ProvincialCoverageError(f"{s.province}: cobertura mensual insuficiente")
    notices=[n for x in issues for n in x["notices"]]
    if not notices or len({x["id"] for x in notices})!=len(notices):
        raise ProvincialCoverageError(f"{s.province}: sin candidatas o identificadores repetidos")
    notices.sort(key=lambda x:(datetime.strptime(x["date"],"%d/%m/%Y"),x["id"]),reverse=True)
    count=sum(x["read"] for x in issues)
    pages=sum(x["pages"] for x in issues)
    return {"schemaVersion":1,"source":home(s),"province":s.province,
      "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
      "coverage":{"complete":True,"status":"complete","bulletin":str(issues[-1]["number"]),
          "pagesVisited":pages,"announcementsRead":count,"opportunities":len(notices)},
      "historyCoverage":{"complete":True,"rangeStart":start.isoformat(),
          "rangeEnd":end.isoformat(),"issuesRead":len(issues),
          "pagesVisited":pages,"announcementsRead":count,"opportunities":len(notices),
          "bulletins":[str(x["number"]) for x in issues],
          "publicationDates":[x["date"].isoformat() for x in issues],
          "nonPublicationDates":absent,
          "editionPDFs":[x["pdf"] for x in issues]},
      "notices":notices}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--province",required=True,choices=list(SOURCES))
    p.add_argument("--days",type=int,default=30)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    result=audit(SOURCES[args.province],args.days)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"{result['province'].upper()} AUDITADO: {result['historyCoverage']['issuesRead']} "
      f"boletines, {result['coverage']['announcementsRead']} anuncios, "
      f"{len(result['notices'])} candidatas",flush=True)
