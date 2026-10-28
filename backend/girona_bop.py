#!/usr/bin/env python3
"""Girona BOP: scan every official issue within 30 calendar days.

Archive issue numbers must be consecutive, dates decreasing and all links
fully identified. No partial publication if a PDF link or issue is missing.
"""
from __future__ import annotations
import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from bs4 import BeautifulSoup

from provincial_common import ProvincialCoverageError, classify

BASE = "https://www.ddgi.cat/bop/"
ISSUE_PATH = "https://www.ddgi.cat/bop/mostra-bop/{}/{}/{}"
PROVINCE = "Girona (BOP)"
PDF_HOST = "ssl4.ddgi.cat"
ISSUE_HEADER = re.compile(r"Bop\s*n[úu]mero\s*:\s*(\d+)\s*/\s*(\d+)\s*-\s*(\d{2}/\d{2}/\d{4})", re.I)
PDF_PATH = re.compile(r"^/bopV1/pdf/(\d{4})/(\d{1,3})/(\d{12})\.pdf$")


def download(url: str) -> str:
    p=urlsplit(url)
    if p.scheme != "https" or p.hostname != "www.ddgi.cat" or not p.path.startswith("/bop/") or p.query or p.fragment or p.username or p.password:
        raise ProvincialCoverageError("Girona: URL no oficial")
    last=None
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={
                "User-Agent":"OpoAlert/1.6 (https://github.com/MJTBApps/OpoAlert)",
                "Accept":"text/html", "Accept-Language":"ca,es;q=0.8",
            }),timeout=24) as response:
                if response.status != 200 or urlsplit(response.url).hostname != "www.ddgi.cat":
                    raise ProvincialCoverageError("Girona: respuesta no verificable")
                raw=response.read(650_001)
                if len(raw)>650_000:raise ProvincialCoverageError("Girona: indice HTML excesivo")
                return raw.decode(response.headers.get_content_charset() or "utf-8","replace")
        except (HTTPError,URLError,OSError,TimeoutError) as exc:
            last=exc
            if attempt<2:
                import time;time.sleep(attempt+1)
    raise ProvincialCoverageError(f"Girona: no se pudo leer {url}: {last}")


def parse_issue(html: str, expected_number: int|None=None) -> dict:
    soup=BeautifulSoup(html,"html.parser")
    h1=soup.select_one("h1")
    header=h1.get_text(" ",strip=True) if h1 else ""
    found=ISSUE_HEADER.search(header)
    if not found:
        raise ProvincialCoverageError(f"Girona: cabecera del BOP ilegible: {header[:100]}")
    number=int(found.group(1))
    if found.group(2)!="0":
        raise ProvincialCoverageError("Girona: edicion adicional no documentada")
    day=datetime.strptime(found.group(3),"%d/%m/%Y").date()
    if expected_number is not None and number != expected_number:
        raise ProvincialCoverageError(f"Girona: BOP {number} recibido, esperado {expected_number}")
    rows=[]
    nodes=soup.select("li.edicte")
    if not nodes:
        raise ProvincialCoverageError(f"Girona BOP {number}: sin edictos")
    for li in nodes:
        a=li.select_one('a.linkAjuda[href]')
        if a is None:raise ProvincialCoverageError(f"Girona BOP {number}: edicto sin enlace")
        p=urlsplit(a.get("href",""))
        match=PDF_PATH.fullmatch(p.path)
        if (p.scheme!="https" or p.hostname != PDF_HOST or p.port not in (None,443)
                or p.query or p.fragment or p.username or not match):
            raise ProvincialCoverageError(f"Girona BOP {number}: PDF no oficial")
        fileyear,issue_in_path,filename=match.groups()
        if int(fileyear)!=day.year or int(issue_in_path)!=number:
            raise ProvincialCoverageError(f"Girona BOP {number}: PDF de otra edicion")
        name=a.select_one("span")
        agency=name.get_text(" ",strip=True) if name else ""
        full=a.get_text(" ",strip=True)
        match_prefix=re.match(r"^(\d{1,6})\s*-\s*", full)
        if not agency or not match_prefix:
            raise ProvincialCoverageError(f"Girona BOP {number}: edicto sin entidad/registro")
        edict=int(match_prefix.group(1))
        expected_file=f"{day.year}{number:03d}{edict:05d}"
        if filename!=expected_file:
            raise ProvincialCoverageError(f"Girona BOP {number}: PDF con registro distinto {filename=} {expected_file=} {full[:170]=}")
        rest=full[match_prefix.end():]
        if not rest.startswith(agency):
            raise ProvincialCoverageError(f"Girona BOP {number}: entidad no coincide")
        title=rest[len(agency):].lstrip(" -:\n\t")
        if not title or len(title)>2500:raise ProvincialCoverageError("Girona: edicto sin titulo")
        kind=classify(title)
        if kind is not None:
            rows.append({
                "id":f"GI-{day.year}-{number:03d}-{edict:05d}",
                "title":title,"entity":agency,"date":day.strftime("%d/%m/%Y"),
                "bulletin":str(number),"province":PROVINCE,"type":kind,
                "url":p.geturl(),
            })
    if len(rows)!=len({row["id"] for row in rows}):
        raise ProvincialCoverageError(f"Girona BOP {number}: registros duplicados")
    return {"number":number,"date":day,"read":len(nodes),"notices":rows}


def audit(days:int=30, today:date|None=None, fetch=download) -> dict:
    if days!=30:raise ValueError("Se auditan 30 dias naturales")
    end=today or date.today()
    start=end-timedelta(days=29)
    current=parse_issue(fetch(BASE))
    latest=current["date"]
    if latest>end or (end-latest).days>4:
        raise ProvincialCoverageError(f"Girona: ultimo boletin muy antiguo o futuro: {latest}")
    if current["number"]<3:
        raise ProvincialCoverageError("Girona: cruce de año pendiente de comprobacion")
    numbers=[]
    previous=None
    for steps in range(35):
        if steps>0:
            number=current["number"]-steps
            if number<1:
                raise ProvincialCoverageError("Girona: cruce de año sin verificar")
            url=ISSUE_PATH.format(latest.isoformat(),latest.year,number)
            issue=parse_issue(fetch(url), number)
        else:
            issue=current
        issue_day=issue["date"]
        if previous and issue_day>=previous:
            raise ProvincialCoverageError(f"Girona: fechas de ediciones no decrecientes {issue_day}")
        previous=issue_day
        if issue_day<start:
            break
        if issue_day>end:raise ProvincialCoverageError("Girona: edicion posterior a hoy")
        numbers.append(issue)
        print(f"Girona {issue_day}: BOP {issue['number']} · {issue['read']} edictos · "
              f"{len(issue['notices'])} candidatas",flush=True)
    else:
        raise ProvincialCoverageError("Girona: no se ha encontrado edicion anterior al comienzo")
    if len(numbers)<8:
        raise ProvincialCoverageError("Girona: menos de 8 ediciones, posible auditoria incompleta")
    numbers.reverse()
    pub_dates=[row["date"].isoformat() for row in numbers]
    pub=set(pub_dates)
    all_days=[start+timedelta(days=n) for n in range(days)]
    notices=[n for row in numbers for n in row["notices"]]
    if len({r["id"] for r in notices})!=len(notices):
        raise ProvincialCoverageError("Girona: ID duplicado entre BOP")
    notices.sort(key=lambda x:(datetime.strptime(x["date"],"%d/%m/%Y"),x["id"]),reverse=True)
    read=sum(row["read"] for row in numbers)
    return {
        "schemaVersion":1,
        "source":BASE,"province":PROVINCE,
        "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
        "coverage":{
            "complete":True,"bulletin":str(numbers[-1]["number"]),
            "pagesVisited":len(numbers),"announcementsRead":read,
            "opportunities":len(notices),"status":"complete",
        },
        "historyCoverage":{
            "complete":True,"rangeStart":start.isoformat(),"rangeEnd":end.isoformat(),
            "issuesRead":len(numbers),"pagesVisited":len(numbers),
            "announcementsRead":read,"opportunities":len(notices),
            "bulletins":[str(x["number"]) for x in numbers],
            "publicationDates":pub_dates,
            "nonPublicationDates":[x.isoformat() for x in all_days if x.isoformat() not in pub],
        },
        "notices":notices,
    }


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--days",type=int,default=30)
    args=parser.parse_args()
    result=audit(args.days)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"GIRONA OK {result['historyCoverage']['issuesRead']} ediciones, "
          f"{result['coverage']['announcementsRead']} edictos, "
          f"{len(result['notices'])} candidatas",flush=True)
