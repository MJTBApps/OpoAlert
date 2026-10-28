#!/usr/bin/env python3
"""Barcelona BOPB: validated 30-day official issue and original PDF reader.

The BOPB publishes working days (excluding Catalonia/Barcelona public
holidays). Any missing expected bulletin, page, notice or PDF aborts the
publication. The classification is a title-only candidate selection.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from math import ceil
from pathlib import Path
import re
import time
from urllib.parse import urljoin, urlsplit
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from bs4 import BeautifulSoup

from provincial_common import ProvincialCoverageError, classify

BASE="https://bop.diba.cat/anteriors/"
PROVINCE="Barcelona (BOP)"
PAGE_SIZE=20
MAX_ITEMS=800
PDF_PREFIX="/anunci/descarrega-pdf/"
DETAIL_RE=re.compile(r"^/anunci/(\d+)/[a-z0-9-]+$")
TOTAL_RE=re.compile(r"(?:S['’]han trobat|Se han encontrado)\s+([\d.,]+)\s+resultats?",re.I)
RANGE_RE=re.compile(r"(?:mostrant|mostrando)\s+(?:del\s+)?(\d+)\s+(?:al)\s+(\d+)",re.I)
DATE_RE=re.compile(r"Data de publicaci[oó]\s*:\s*(\d{2}/\d{2}/\d{4})",re.I)
REG_RE=re.compile(r"Registre\s*:\s*(\d{12})",re.I)
DETAIL_REG_RE=re.compile(r"N[uú]mero de Registre\s*:\s*(\d{12})",re.I)

# Official 2026 Catalonia/Barcelona holiday calendar, including local days:
# https://guia.barcelona.cat/.../festes-estatals-i-autonomiques-a-catalunya-i-locals-a-barcelona-al-2025_99400735671.html
# Restrict to verified year; never infer unknown 2027 public holidays.
HOLIDAYS_2026={
 date(2026,1,1),date(2026,1,6),date(2026,4,3),date(2026,4,6),
 date(2026,5,1),date(2026,5,25),date(2026,6,24),date(2026,8,15),
 date(2026,9,11),date(2026,9,24),date(2026,10,12),date(2026,12,8),
 date(2026,12,25),date(2026,12,26),
}


def publishes(day: date) -> bool:
    if day.year!=2026:raise ProvincialCoverageError("BOPB: calendario festivo no verificado para este año")
    return day.weekday()<5 and day not in HOLIDAYS_2026


def official(url:str,path:str="/") -> bool:
    p=urlsplit(url)
    return (p.scheme=="https" and p.hostname=="bop.diba.cat"
            and p.port in (None,443) and not p.username and not p.password
            and not p.query and not p.fragment and p.path.startswith(path))


def download(url:str) -> str:
    if not official(url):raise ProvincialCoverageError("Barcelona: URL ajena al BOP")
    last=None
    for attempt in range(3):
        try:
            with urlopen(Request(url,headers={
                "User-Agent":"OpoAlert/1.6 (https://github.com/MJTBApps/OpoAlert)",
                "Accept-Language":"ca,es;q=0.8","Accept":"text/html",
            }),timeout=26) as response:
                if response.status!=200 or not official(response.url):
                    raise ProvincialCoverageError(f"Barcelona: HTTP o redireccion inesperada {url}")
                data=response.read(650_001)
                if len(data)>650_000:raise ProvincialCoverageError("Barcelona: indice HTML excesivo")
                time.sleep(0.06)
                return data.decode(response.headers.get_content_charset() or "utf-8","replace")
        except (HTTPError,URLError,OSError,TimeoutError) as exc:
            last=exc
            if attempt<2:time.sleep(attempt+1)
    raise ProvincialCoverageError(f"Barcelona: pagina no disponible: {url} ({last})")


def parse_index(html:str,day:date,page:int=1)->tuple[int,list[dict]]:
    soup=BeautifulSoup(html,"html.parser")
    title=soup.title.get_text(" ",strip=True) if soup.title else ""
    if day.strftime("%d/%m/%Y") not in title or "Barcelona" not in title:
        raise ProvincialCoverageError(f"Barcelona {day}: la edicion mostrada no coincide")
    text=soup.get_text(" ",strip=True)
    match=TOTAL_RE.search(text)
    if not match:raise ProvincialCoverageError(f"Barcelona {day}: no hay total oficial verificable")
    total=int(match.group(1).replace(".","").replace(",",""))
    if not 1<=total<=MAX_ITEMS:
        raise ProvincialCoverageError(f"Barcelona {day}: numero de anuncios anomalo {total}")
    cards=soup.select("div.card.bg-white")
    if len(cards)!=min(PAGE_SIZE,total-(page-1)*PAGE_SIZE):
        raise ProvincialCoverageError(f"Barcelona {day} pagina {page}: fichas incompletas")
    displayed=RANGE_RE.search(text)
    start=(page-1)*PAGE_SIZE+1
    end=min(page*PAGE_SIZE,total)
    if not displayed or (int(displayed.group(1)),int(displayed.group(2)))!=(start,end):
        raise ProvincialCoverageError(f"Barcelona {day}: paginacion no coincidente")
    rows=[]
    for card in cards:
        anchor=card.select_one('h3.card-title a[href*="/anunci/"]')
        paragraph=card.select_one("div.card-body > p")
        if anchor is None or paragraph is None:
            raise ProvincialCoverageError(f"Barcelona {day}: falta anuncio oficial en ficha")
        detail=urljoin("https://bop.diba.cat/",anchor.get("href",""))
        if not official(detail,"/anunci/") or not DETAIL_RE.fullmatch(urlsplit(detail).path):
            raise ProvincialCoverageError(f"Barcelona {day}: enlace de ficha no oficial")
        raw=card.get_text(" ",strip=True)
        reg=REG_RE.search(raw)
        posted=DATE_RE.search(raw)
        if not reg or not posted or posted.group(1)!=day.strftime("%d/%m/%Y"):
            raise ProvincialCoverageError(f"Barcelona {day}: ficha sin registro o fecha comprobable")
        entity=anchor.get_text(" ",strip=True)
        adtitle=paragraph.get_text(" ",strip=True)
        if not entity or not adtitle:
            raise ProvincialCoverageError("Barcelona: falta titulo/organismo")
        rows.append({"reg":reg.group(1),"entity":entity,"title":adtitle,"detail":detail})
    if len({row["reg"] for row in rows})!=len(rows):
        raise ProvincialCoverageError(f"Barcelona {day}: registros repetidos en pagina")
    return total,rows


def official_pdf(html:str, detail_id:str, reg:str, day:date)->str:
    soup=BeautifulSoup(html,"html.parser")
    text=soup.get_text(" ",strip=True)
    posted=DATE_RE.search(text)
    number=DETAIL_REG_RE.search(text)
    if not posted or posted.group(1)!=day.strftime("%d/%m/%Y") or not number or number.group(1)!=reg:
        raise ProvincialCoverageError(f"Barcelona {reg}: ficha y sumario discrepan")
    url="https://bop.diba.cat"+PDF_PREFIX+detail_id
    links=[urljoin("https://bop.diba.cat",a.get("href","")) for a in soup.select('a[href*="/anunci/descarrega-pdf/"]')]
    if not official(url,PDF_PREFIX) or url not in links:
        raise ProvincialCoverageError(f"Barcelona {reg}: no se encuentra el PDF original")
    return url


def scan(day:date,fetch=download)->dict:
    source=BASE+day.isoformat()
    total,rows=parse_index(fetch(source),day)
    pages=ceil(total/PAGE_SIZE)
    for page in range(2,pages+1):
        n,new=parse_index(fetch(source+"/"+str(page)),day,page)
        if n!=total:raise ProvincialCoverageError(f"Barcelona {day}: total cambia entre paginas")
        rows.extend(new)
    if len(rows)!=total or len({x["reg"] for x in rows})!=total:
        raise ProvincialCoverageError(f"Barcelona {day}: faltan edictos en el sumario")
    notices=[]
    for row in rows:
        kind=classify(row["title"])
        if kind is None:continue
        ident=DETAIL_RE.fullmatch(urlsplit(row["detail"]).path)
        pdf=official_pdf(fetch(row["detail"]),ident.group(1),row["reg"],day)
        notices.append({
            "id":"BA-"+row["reg"],"title":row["title"],"entity":row["entity"],
            "date":day.strftime("%d/%m/%Y"),"bulletin":day.strftime("%d/%m/%Y"),
            "province":PROVINCE,"type":kind,"url":pdf,
        })
    return {"date":day,"total":total,"pages":pages,"notices":notices}


def audit(days:int=30,today:date|None=None,reader=scan)->dict:
    if days!=30:raise ValueError("BOPB: la auditoria exige 30 dias")
    end=today or date.today()
    start=end-timedelta(days=29)
    results=[]
    for offset in range(days):
        day=start+timedelta(days=offset)
        if publishes(day):
            issue=reader(day)
            if issue["date"]!=day or issue["total"]<len(issue["notices"]) or issue["pages"]<1:
                raise ProvincialCoverageError(f"Barcelona {day}: edicion incompleta")
            results.append(issue)
            print(f"Barcelona {day}: {issue['total']} edictos, {issue['pages']} paginas, {len(issue['notices'])} candidatas",flush=True)
        else:
            print(f"Barcelona {day}: dia sin publicacion segun calendario oficial",flush=True)
    if len(results)<8:raise ProvincialCoverageError("Barcelona: muy pocas ediciones auditadas")
    notices=[n for x in results for n in x["notices"]]
    if len(notices)!=len({x["id"] for x in notices}):
        raise ProvincialCoverageError("Barcelona: registros duplicados en 30 dias")
    notices.sort(key=lambda x:(datetime.strptime(x["date"],"%d/%m/%Y"),x["id"]),reverse=True)
    read=sum(x["total"] for x in results)
    pages=sum(x["pages"] for x in results)
    published=[x["date"].isoformat() for x in results]
    pubset=set(published)
    return {
        "schemaVersion":1,"source":BASE,"province":PROVINCE,
        "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
        "coverage":{
            "complete":True,"bulletin":published[-1],"pagesVisited":pages,
            "announcementsRead":read,"opportunities":len(notices),"status":"complete",
        },
        "historyCoverage":{
            "complete":True,"rangeStart":start.isoformat(),"rangeEnd":end.isoformat(),
            "issuesRead":len(published),"pagesVisited":pages,
            "announcementsRead":read,"opportunities":len(notices),
            "bulletins":published,"publicationDates":published,
            "nonPublicationDates":[(start+timedelta(days=i)).isoformat() for i in range(days)
                                   if (start+timedelta(days=i)).isoformat() not in pubset],
        },
        "notices":notices,
    }


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    p.add_argument("--days",type=int,default=30)
    options=p.parse_args()
    output=audit(options.days)
    options.output.parent.mkdir(parents=True,exist_ok=True)
    options.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"BARCELONA OK: {output['historyCoverage']['issuesRead']} ediciones, "
          f"{output['coverage']['announcementsRead']} edictos y {len(output['notices'])} candidatas",flush=True)
