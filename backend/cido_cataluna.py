#!/usr/bin/env python3
"""Official CIDO open data -> four Catalonia province feeds (selection processes).

This is the Diputacio de Barcelona's CIDO catalogue, not a complete BOP.
All pages are verified before writing any file. Only current/open/pending
records updated during the past 30 calendar days are included.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

BASE="https://api.diba.cat/dadesobertes/cido/v1/oposicions"
PROVINCES={5:("Barcelona","barcelona"), 6:("Girona","girona"), 7:("Lleida","lleida"), 8:("Tarragona","tarragona_cido")}
URL_RE=re.compile(r"https://cido\.diba\.cat/oposicions/(\d+)\Z")
MAX_ITEMS=10_000
PAGE_LIMIT=500


class CidoCoverageError(ValueError):
    pass


def query(start: date, end: date, offset: int=0) -> str:
    if end < start or offset < 0 or offset % PAGE_LIMIT:
        raise CidoCoverageError("Intervalo/offset de CIDO incorrecto")
    # Full range limited to active CIDO process records in four provincial scopes.
    q=[
        ("filter[idAmbit]", "5,6,7,8"),
        ("filter[idEstat]", "1,2,3"),
        ("filter[maxDataPublicacioDocument][GE]",start.isoformat()),
        ("filter[maxDataPublicacioDocument][LE]",end.isoformat()),
        ("page[limit]", str(PAGE_LIMIT)),
        ("sort", "-maxDataPublicacioDocument"),
    ]
    if offset: q.append(("page[offset]",str(offset)))
    return BASE+"?"+urlencode(q)


def download(url: str) -> dict:
    parts=urlsplit(url)
    if parts.scheme!="https" or parts.hostname!="api.diba.cat" or parts.port is not None or parts.username or parts.password or parts.fragment or parts.path!="/dadesobertes/cido/v1/oposicions":
        raise CidoCoverageError("CIDO: URL de API ajena al organismo")
    error=None
    for retry in range(3):
        try:
            req=Request(url,headers={
                "Accept":"application/vnd.api+json",
                "User-Agent":"OpoAlert/1.4 (CIDO public data; https://github.com/MJTBApps/OpoAlert)",
            })
            with urlopen(req,timeout=35) as response:
                if response.status!=200 or urlsplit(response.url).hostname!="api.diba.cat":
                    raise CidoCoverageError("CIDO: respuesta HTTP/URL inesperada")
                body=response.read(3_500_001)
                if len(body)>3_500_000:
                    raise CidoCoverageError("CIDO: pagina de datos excesiva")
            time.sleep(0.15)
            obj=json.loads(body.decode("utf-8"))
            if not isinstance(obj,dict) or not isinstance(obj.get("data"),list):
                raise CidoCoverageError("CIDO: respuesta JSON API invalida")
            return obj
        except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
            error=exc
            if retry<2:time.sleep(1+retry)
    raise CidoCoverageError(f"CIDO: datos oficiales inaccesibles: {error}")


def normalize_record(row: dict, start: date, end: date) -> tuple[int,dict]:
    if not isinstance(row,dict) or row.get("type")!="oposicions" or not str(row.get("id","")).isdigit():
        raise CidoCoverageError("CIDO: registro no identificado")
    a=row.get("attributes",{})
    if not isinstance(a,dict):
        raise CidoCoverageError("CIDO: atributos ausentes")
    territory=a.get("idAmbit")
    if territory not in PROVINCES:
        raise CidoCoverageError(f"CIDO: ambito desconocido {territory}")
    ident=str(row["id"])
    url=a.get("urlCido","")
    match=URL_RE.fullmatch(url)
    if not match or match.group(1)!=ident:
        raise CidoCoverageError(f"CIDO: documento no oficial {ident}")
    iso=a.get("maxDataPublicacioDocument")
    if not iso or not isinstance(iso,str):
        raise CidoCoverageError(f"CIDO: fecha ausente {ident}")
    try: day=date.fromisoformat(iso)
    except ValueError as exc: raise CidoCoverageError(f"CIDO: fecha invalida {ident}") from exc
    if not start<=day<=end:
        raise CidoCoverageError(f"CIDO: fuera de periodo {ident} {day}")
    title=a.get("titol")
    agency=a.get("institucioDesenvolupat")
    if not isinstance(title,str) or not title.strip() or not isinstance(agency,str) or not agency.strip():
        raise CidoCoverageError(f"CIDO: proceso sin organismo/denominacion {ident}")
    state=a.get("idEstat")
    if state not in (1,2,3):
        raise CidoCoverageError(f"CIDO: proceso en estado no permitido {ident}:{state}")
    name,slug=PROVINCES[territory]
    return territory, {
        "id":"CIDO"+str(territory)+"-"+ident,
        "title":title.strip(), "entity":agency.strip(),
        "date":day.strftime("%d/%m/%Y"),
        "bulletin":"CIDO", "province":name,
        "type":"Bolsa de trabajo" if a.get("borsaTreball") is True else "Plaza / oposición",
        "url":url,
    }


def build_feeds(days: int=30, until: date | None=None, fetcher=download) -> dict:
    if days!=30:raise ValueError("La cobertura CIDO exige un periodo completo de 30 dias")
    end=until or date.today()
    start=end-timedelta(days=29)
    results={pid:[] for pid in PROVINCES}
    total=None
    seen=set()
    offset=0
    while True:
        url=query(start,end,offset)
        response=fetcher(url)
        raw=response.get("data")
        metadata=response.get("meta",{})
        links=response.get("links",{})
        if not isinstance(raw,list) or not isinstance(metadata,dict) or not isinstance(links,dict):
            raise CidoCoverageError("CIDO: pagina sin metadatos")
        current=metadata.get("totalResourceCount")
        if not isinstance(current,int) or current<0 or current>MAX_ITEMS:
            raise CidoCoverageError(f"CIDO: total fuera de rango: {current}")
        if total is None:total=current
        if total!=current or len(raw)!=min(PAGE_LIMIT,total-offset):
            raise CidoCoverageError("CIDO: paginas incompletas o total cambiante")
        for row in raw:
            area,notice=normalize_record(row,start,end)
            if notice["id"] in seen:
                raise CidoCoverageError("CIDO: documento duplicado entre paginas")
            seen.add(notice["id"])
            results[area].append(notice)
        offset+=len(raw)
        print(f"CIDO: {offset}/{total} procesos verificados",flush=True)
        if offset==total:
            if links.get("next"):
                raise CidoCoverageError("CIDO: paginacion continua fuera del total")
            break
        expected_next=query(start,end,offset)
        if not isinstance(links.get("next"),str):
            raise CidoCoverageError("CIDO: falta enlace pagina siguiente")
        # Server may reorder query params; decoded consistency checked by direct known URL.
        if urlsplit(links["next"]).hostname!="api.diba.cat":
            raise CidoCoverageError("CIDO: siguiente pagina externa")
        if offset>MAX_ITEMS:
            raise CidoCoverageError("CIDO: demasiadas paginas")
    if total!=len(seen):
        raise CidoCoverageError("CIDO: no se recibieron todos los procesos del filtro")
    now=datetime.now(timezone.utc).isoformat()
    feeds={}
    for pid,(name,slug) in PROVINCES.items():
        notices=results[pid]
        notices.sort(key=lambda x:(datetime.strptime(x["date"],"%d/%m/%Y"),x["id"]),reverse=True)
        pub=sorted({datetime.strptime(x["date"],"%d/%m/%Y").date() for x in notices})
        pubset=set(pub)
        all_days=[start+timedelta(days=i) for i in range(days)]
        feeds[slug]={
            "schemaVersion":2, "source":BASE,
            "province":name,"lastCheckedUTC":now,
            "scope":"CIDO: processos selectius municipals; no equivale a BOP provincial completo",
            "coverage":{"complete":True,"bulletin":"CIDO","announcementsRead":len(notices),
                        "opportunities":len(notices),"status":"api_filtered_full_pagination"},
            "historyCoverage":{"complete":True,"basis":"CIDO_API_LAST_DOCUMENT_30_DAYS",
                               "rangeStart":start.isoformat(),"rangeEnd":end.isoformat(),
                               "publicationDates":[x.isoformat() for x in pub],
                               "nonPublicationDates":[x.isoformat() for x in all_days if x not in pubset],
                               "bulletins":[],"issuesRead":0,"announcementsRead":len(notices),
                               "opportunities":len(notices)},
            "notices":notices,
        }
        print(f"CIDO {name}: {len(notices)} procesos con actualizaciones recientes",flush=True)
    return feeds


def main():
    arg=argparse.ArgumentParser()
    arg.add_argument("--days",type=int,default=30)
    arg.add_argument("--output",type=Path,required=True)
    options=arg.parse_args()
    feeds=build_feeds(options.days)
    options.output.mkdir(parents=True,exist_ok=True)
    for name,feed in feeds.items():
        (options.output/(name+".json")).write_text(
            json.dumps(feed,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


if __name__=="__main__":main()
