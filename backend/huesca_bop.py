#!/usr/bin/env python3
"""BOP Huesca: audit official daily HTML pages with complete pagination.

The official JSON export is malformed (verified 2026-10-28). This reader uses
the official HTML and follows each candidate to the official PDF. 404 dates
are accepted as non-publication ONLY when the surrounding BOP issue numbers
are consecutive. Never publishes a partial 30-day audit.
"""
from __future__ import annotations
from datetime import date,datetime,timedelta,timezone
from math import ceil
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from urllib.parse import urlsplit,urljoin
from bs4 import BeautifulSoup
import argparse,json,re,time

from provincial_common import ProvincialCoverageError,classify,fold

HOME="https://bop.dphuesca.es/publica/consulta-de-bops/"
INDEX="https://bop.dphuesca.es/publica/consulta-de-bops/buscador/BOP-{}/"
PDF_PATH="/export/sites/bop/.galleries/Documentos-Anuncios-en-PDF/"
DETAIL_PREFIX="/publica/buscador-anuncios/anuncio/"
PROVINCE="Huesca"
HEADER_RE=re.compile(r"BOP\s*n[úu]m\.\s*(\d+)\s+del\s+(\d{2}/\d{2}/\d{4})",re.I)
COUNT_RE=re.compile(r"Resultados\s+del\s+(\d+)\s+al\s+(\d+)\s+de\s+(\d+)",re.I)
ID_RE=re.compile(r"BOPH-(\d{4})-(\d{3})(\d{3})")
DAILY_SLUG=re.compile(r"/publica/consulta-de-bops/buscador/BOP-(\d{2})-(\d{2})-(\d{4})/")


def safe_url(url:str,prefix:str) -> bool:
    p=urlsplit(url)
    return (p.scheme=="https" and p.hostname=="bop.dphuesca.es"
            and p.port in (None,443) and p.username is None and p.password is None
            and p.path.startswith(prefix) and not p.fragment and not p.query)


def fetch(url:str,allow_missing:bool=False) -> str|None:
    # Query allowed only when it is a trusted pagination parameter.
    p=urlsplit(url)
    if not (safe_url(url,p.path) or
            (p.scheme=="https" and p.hostname=="bop.dphuesca.es"
             and p.path.startswith("/publica/consulta-de-bops/buscador/BOP-")
             and re.fullmatch(r"page=[1-9]\d{0,2}",p.query)
             and not p.username and not p.fragment)):
        raise ProvincialCoverageError("Huesca: URL ajena al portal oficial")
    last=None
    for attempt in range(3):
        try:
            req=Request(url,headers={
                "User-Agent":"Mozilla/5.0 (compatible; OpoAlert public source validation/1.8)",
                "Accept":"text/html","Accept-Language":"es",
            })
            with urlopen(req,timeout=22) as resp:
                final=urlsplit(resp.url)
                if resp.status!=200 or final.hostname!="bop.dphuesca.es":
                    raise ProvincialCoverageError("Huesca: respuesta o redireccion no oficial")
                raw=resp.read(700_001)
                if len(raw)>700_000:raise ProvincialCoverageError("Huesca: HTML demasiado grande")
                return raw.decode(resp.headers.get_content_charset() or "utf-8","replace")
        except HTTPError as ex:
            if ex.code==404 and allow_missing:return None
            last=ex
        except (URLError,OSError,TimeoutError) as ex:
            last=ex
        if attempt<2:time.sleep(attempt+1)
    raise ProvincialCoverageError(f"Huesca: error leyendo {url}: {last}")


def latest_issue_date(html:str)->date:
    soup=BeautifulSoup(html,"html.parser")
    found=[]
    for a in soup.select("a[href]"):
        m=DAILY_SLUG.search(urlsplit(a.get("href","")).path)
        if m:
            found.append(date(int(m.group(3)),int(m.group(2)),int(m.group(1))))
    if not found:raise ProvincialCoverageError("Huesca: pagina principal sin enlace al ultimo BOP")
    return max(found)


def parse_index(html:str,expected_day:date,page:int=1)->tuple[int,int,list[dict]]:
    soup=BeautifulSoup(html,"html.parser")
    header=soup.select_one("h2")
    label=header.get_text(" ",strip=True) if header else ""
    m=HEADER_RE.search(label)
    if not m or m.group(2)!=expected_day.strftime("%d/%m/%Y"):
        raise ProvincialCoverageError(f"Huesca {expected_day}: cabecera de edicion incorrecta {label[:100]}")
    number=int(m.group(1))
    text=soup.get_text(" ",strip=True)
    count=COUNT_RE.search(text)
    if not count:raise ProvincialCoverageError(f"Huesca {expected_day}: falta total de anuncios")
    first,last,total=map(int,count.groups())
    expected_first=(page-1)*20+1
    expected_last=min(total,page*20)
    if not 1<=total<=1000 or (first,last)!=(expected_first,expected_last):
        raise ProvincialCoverageError(f"Huesca {expected_day}: paginacion {first}..{last}/{total} anomala")
    cards=soup.select("li.elementoListado")
    if len(cards)!=last-first+1:
        raise ProvincialCoverageError(f"Huesca {expected_day}: fichas {len(cards)} != {last-first+1}")
    rows=[]
    for li in cards:
        a=li.select_one("a.enlace_elemento[href]")
        h=li.select_one("h3.titulo_elemento")
        agency=li.select_one(".campo_1")
        date_div=li.select_one(".fecha_elemento")
        registry=li.select_one(".campo_3")
        if any(x is None for x in (a,h,agency,date_div,registry)):
            raise ProvincialCoverageError(f"Huesca {expected_day}: anuncio sin campos oficiales")
        title=h.get_text(" ",strip=True)
        entity=agency.get_text(" ",strip=True)
        dated=date_div.get_text(" ",strip=True)
        reg=registry.get_text(" ",strip=True)
        ident=ID_RE.fullmatch(reg)
        detail=urljoin(HOME,a.get("href",""))
        if (not ident or int(ident.group(1))!=expected_day.year
                or int(ident.group(2))!=number or int(ident.group(3))==0
                or dated!=expected_day.strftime("%d/%m/%Y")
                or not title or not entity
                or not safe_url(detail,DETAIL_PREFIX)
                or not detail.endswith("/")):
            raise ProvincialCoverageError(f"Huesca {expected_day}: datos o enlace no validos {reg}")
        rows.append({"id":reg,"title":title,"entity":entity,"detail":detail})
    if len(rows)!=len({item["id"] for item in rows}):
        raise ProvincialCoverageError(f"Huesca {expected_day}: registros duplicados")
    return number,total,rows


def parse_pdf(html:str,day:date,title:str)->str:
    soup=BeautifulSoup(html,"html.parser")
    h=soup.select_one("h1.titulo_detalle")
    displayed=h.get_text(" ",strip=True) if h else ""
    text=soup.get_text(" ",strip=True)
    if fold(displayed).rstrip(". ")!=fold(title).rstrip(". ") or (
        "Fecha de publicación "+day.strftime("%d/%m/%Y") not in text):
        raise ProvincialCoverageError("Huesca: ficha individual no coincide con anuncio")
    links=[urljoin(HOME,a.get("href","")) for a in soup.select("a[href]")]
    pdfs=[u for u in links if safe_url(u,PDF_PATH) and u.lower().endswith(".pdf")]
    if len(set(pdfs))!=1:raise ProvincialCoverageError("Huesca: enlace original PDF ausente o ambiguo")
    return pdfs[0]


def scan(day:date,reader=fetch)->dict|None:
    url=INDEX.format(day.strftime("%d-%m-%Y"))
    first_html=reader(url,allow_missing=True)
    if first_html is None:return None
    number,total,rows=parse_index(first_html,day)
    pages=ceil(total/20)
    for n in range(2,pages+1):
        html=reader(url+f"?page={n}")
        other_count,other_total,other=parse_index(html,day,n)
        if number!=other_count or total!=other_total:
            raise ProvincialCoverageError(f"Huesca {day}: edicion distinta en pagina {n}")
        rows.extend(other)
    if len(rows)!=total or len({x["id"] for x in rows})!=total:
        raise ProvincialCoverageError(f"Huesca {day}: total de anuncios incompleto")
    notices=[]
    for item in rows:
        kind=classify(item["title"])
        if kind is None:continue
        pdf=parse_pdf(reader(item["detail"]),day,item["title"])
        notices.append({
            "id":"HU-"+item["id"].removeprefix("BOPH-"),
            "province":PROVINCE,"title":item["title"],
            "entity":item["entity"],"date":day.strftime("%d/%m/%Y"),
            "bulletin":str(number),"type":kind,"url":pdf,
        })
    return {"date":day,"number":number,"read":total,"pages":pages,"notices":notices}


def audit(days:int=30,today:date|None=None,reader=scan,fetch_home=fetch)->dict:
    if days!=30:raise ProvincialCoverageError("Huesca: cobertura debe ser exactamente 30 dias")
    end=today or date.today()
    start=end-timedelta(days=days-1)
    last=latest_issue_date(fetch_home(HOME))
    if last>end or (end-last).days>4:
        raise ProvincialCoverageError(f"Huesca: el ultimo numero en portada es {last}")
    issues=[]
    absent=[]
    for n in range(days):
        day=start+timedelta(days=n)
        edition=reader(day)
        if edition is None:
            absent.append(day.isoformat())
            print("Huesca",day,"sin BOP",flush=True)
            continue
        if edition["date"]!=day or edition["pages"]<1 or edition["read"]<len(edition["notices"]):
            raise ProvincialCoverageError(f"Huesca {day}: edicion no verificable")
        if issues:
            old=issues[-1]
            if day.year==old["date"].year and edition["number"]!=old["number"]+1:
                raise ProvincialCoverageError(
                    f"Huesca: salto de numeracion BOP {old['number']} -> {edition['number']}")
            if day.year!=old["date"].year and edition["number"]!=1:
                raise ProvincialCoverageError("Huesca: reinicio anual de numeracion incorrecto")
        issues.append(edition)
        print(f"Huesca {day}: BOP {edition['number']}, {edition['read']} anuncios, "
              f"{edition['pages']} paginas, {len(edition['notices'])} candidatas",flush=True)
    if len(issues)<15 or issues[-1]["date"]!=last or (issues[0]["date"]-start).days>4:
        raise ProvincialCoverageError("Huesca: ediciones insuficientes, no se publica parcial")
    notices=[x for issue in issues for x in issue["notices"]]
    if len(notices)!=len({x["id"] for x in notices}):
        raise ProvincialCoverageError("Huesca: ID repetido entre ediciones")
    notices.sort(key=lambda x:(datetime.strptime(x["date"],"%d/%m/%Y"),x["id"]),reverse=True)
    read=sum(x["read"] for x in issues)
    pages=sum(x["pages"] for x in issues)
    history_dates=[x["date"].isoformat() for x in issues]
    return {
        "schemaVersion":1,"source":HOME,"province":PROVINCE,
        "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
        "coverage":{"complete":True,"status":"complete","bulletin":str(issues[-1]["number"]),
                    "pagesVisited":pages,"announcementsRead":read,"opportunities":len(notices)},
        "historyCoverage":{"complete":True,"rangeStart":start.isoformat(),"rangeEnd":end.isoformat(),
                           "issuesRead":len(issues),"pagesVisited":pages,"announcementsRead":read,
                           "opportunities":len(notices),"bulletins":[str(x["number"]) for x in issues],
                           "publicationDates":history_dates,"nonPublicationDates":absent},
        "notices":notices,
    }


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--days",type=int,default=30)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    result=audit(args.days)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"HUESCA OK {result['historyCoverage']['issuesRead']} ediciones, "
          f"{result['coverage']['announcementsRead']} anuncios, "
          f"{len(result['notices'])} candidatas",flush=True)
