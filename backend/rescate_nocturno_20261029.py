#!/usr/bin/env python3
"""OpoAlert night recovery: official publisher evidence, never an audited feed.

Collects a repeatable partial manifest of original Jaen index/PDF issues and
limited connectivity to the other blocked editorial endpoints. An incomplete
30-day sequence is NOT eligible for Android, alerts, feeds or publication.
"""
from __future__ import annotations

import argparse
import concurrent.futures
from datetime import date, datetime, timedelta, timezone
from io import BytesIO
import json
from pathlib import Path
import re
import time
from urllib.parse import parse_qs, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup

WINDOW_END = date(2026, 10, 29)
WINDOW_START = WINDOW_END - timedelta(days=29)
JAEN_BASE = "https://www.dipujaen.es/hemerotecadigital/"
JAEN_COLLECTION = "0000395018"
CHECKS = {
    "AB": ("https://bop.dipualba.es/",
           "https://www.dipualba.es/bop/"),
    "CU": ("https://www.dipucuenca.es/boletin-oficial-de-la-provincia",
           "https://sede.dipucuenca.es/"),
    "BU": ("https://bopbur.diputaciondeburgos.es/",
           "https://www.burgos.es/servicios/bop"),
    "VD": ("https://bop.sede.diputaciondevalladolid.es/calendario",),
    "AS": ("https://miprincipado.asturias.es/ast/bopa-sumario",
           "https://descargas.asturias.es/asturias/opendata/LegislacionyJusticia/BOPA2019-28/dataset-sum-bopa-2026.json"),
    "CB": ("https://boc.cantabria.es/boces/",),
    "NA": ("https://bon.navarra.es/es/inicio",
           "https://datosabiertos.navarra.es/es/api/3/action/package_search?q=boletin"),
    "CE": ("https://www.ceuta.es/ceuta/bocce",),
    "LD": ("https://ebop.diputaciolleida.cat/",),
}
HEADERS = {"User-Agent": "OpoAlert/1.30 (public official source research)",
           "Accept-Language": "es-ES,es;q=0.9"}
CAPTCHA = ("captcha", "turnstile", "verificacion de seguridad",
           "verificación de seguridad", "verificacion necesaria",
           "verificación necesaria")

def permitted(url, hosts):
    try:
        p = urlsplit(url)
        return (p.scheme == "https" and p.hostname in hosts and
                p.port in (None, 443) and p.username is None and
                p.password is None and not p.fragment)
    except ValueError:
        return False

def fetch(url, hosts, cap=220000, timeout=(6, 18)):
    if not permitted(url, hosts):
        raise ValueError("El host inicial no es una fuente oficial permitida")
    with requests.Session() as s:
        s.headers.update(HEADERS)
        with s.get(url, stream=True, timeout=timeout, allow_redirects=True) as response:
            if not permitted(response.url, hosts):
                raise ValueError("Redirección fuera del editor oficial")
            data = bytearray()
            for part in response.iter_content(16384):
                data.extend(part)
                if len(data) > cap:
                    break
            return {"http": response.status_code, "final": response.url,
                    "mime": response.headers.get("Content-Type", ""),
                    "bytesSampled": len(data), "truncated": len(data) > cap}, bytes(data)

def check(url, territory):
    tick=time.monotonic()
    hosts={urlsplit(u).hostname for u in CHECKS[territory]}
    try:
        meta,data=fetch(url,hosts,cap=36000,timeout=(5,11))
        html=BeautifulSoup(data,"html.parser")
        text=data[:10000].decode("utf-8","replace").lower()
        meta.update({"territory":territory,"url":url,
                     "isPdf":data.startswith(b"%PDF-"),
                     "securityChallenge":any(x in text for x in CAPTCHA),
                     "title":html.title.get_text(" ",strip=True)[:120] if html.title else "",
                     "hasDateOrYear":b"2026" in data,
                     "readableFirstPartyIndexVerified":False})
    except Exception as ex:
        meta={"territory":territory,"url":url,
              "error":type(ex).__name__+": "+str(ex)[:190],
              "readableFirstPartyIndexVerified":False}
    meta["elapsedSeconds"]=round(time.monotonic()-tick,1)
    return meta

def parse_jaen_card(card,index_url):
    title=" ".join(card.get_text(" ",strip=True).split())
    match=re.search(r"Boletín Oficial de la Provincia de Jaén\.\s*(\d{1,2}/\d{1,2}/2026)\.",title,re.I)
    if not match:
        return None
    day=datetime.strptime(match[1],"%d/%m/%Y").date()
    if not WINDOW_START <= day <= WINDOW_END:
        return None
    a=card.find("a",href=re.compile(r"high[.]raw"))
    if a is None:
        return None
    url=urljoin(JAEN_BASE,a.get("href",""))
    p=urlsplit(url)
    q=parse_qs(p.query)
    identifier=q.get("id",[""])[0]
    if (not permitted(url,{"www.dipujaen.es"}) or
        p.path!="/hemerotecadigital/high.raw" or
        not re.fullmatch(r"\d{10}",identifier)):
        return None
    pages=re.search(r"\((\d+)\s+páginas",title,re.I)
    return {"date":day.isoformat(),"catalogueId":identifier,
            "publisherOriginalUrl":url,"sourceIndexUrl":index_url,
            "pagesListed":int(pages[1]) if pages else None,
            "pdfFullyDownloaded":False,"dateInOriginalVerified":False}

def check_jaen_pdf(entry):
    result={"date":entry["date"],"catalogueId":entry["catalogueId"]}
    try:
        meta,raw=fetch(entry["publisherOriginalUrl"],{"www.dipujaen.es"},
                        cap=15_000_000,timeout=(8,35))
        valid=(meta["http"]==200 and not meta["truncated"] and
               raw.startswith(b"%PDF-") and len(raw)>800)
        page_count=None
        excerpt=""
        if valid:
            from pypdf import PdfReader
            reader=PdfReader(BytesIO(raw),strict=False)
            page_count=len(reader.pages)
            excerpt=(reader.pages[0].extract_text() or "")[:1800]
            valid=(page_count>0 and
                   (entry["pagesListed"] is None or page_count==entry["pagesListed"]))
        # The index date is not enough to claim matching first-party PDF.
        d=datetime.fromisoformat(entry["date"]).date()
        date_variants=(f"{d.day}/{d.month}/{d.year}",
                       f"{d.day:02d}/{d.month:02d}/{d.year}",
                       f"{d.day} de " + ["","enero","febrero","marzo","abril","mayo",
                             "junio","julio","agosto","septiembre","octubre",
                             "noviembre","diciembre"][d.month] + f" de {d.year}")
        matching_date=any(x.casefold() in excerpt.casefold() for x in date_variants)
        result.update({"http":meta["http"],"pdfValidated":bool(valid),
          "firstPageMatchesDate":bool(valid and matching_date),
          "pagesParsed":page_count,"bytes":len(raw),
          "firstPageSample":excerpt[:230]})
    except Exception as ex:
        result["error"]=type(ex).__name__+": "+str(ex)[:180]
    return result

def jaen_partial(max_pdfs):
    result={"territory":"JA","publisher":JAEN_BASE,
            "windowStart":WINDOW_START.isoformat(),"windowEnd":WINDOW_END.isoformat(),
            "status":"partial","complete30Days":False,
            "knownMissingNumbers":[198,199,201],"indexedIssues":[],"pdfChecks":[]}
    try:
        first_url=JAEN_BASE+"results.vm?q=parent:"+JAEN_COLLECTION+"&view=boletin&s=41775"
        meta,data=fetch(first_url,{"www.dipujaen.es"},timeout=(8,25))
        if meta["http"]!=200:
            raise ValueError("Hemeroteca no accesible: "+str(meta["http"]))
        soup=BeautifulSoup(data,"html.parser")
        count=re.search(r"Resultados:\s*([\d.]+)",soup.get_text(" ",strip=True))
        if not count:
            raise ValueError("Hemeroteca sin total de registros")
        total=int(count[1].replace(".",""))
        if not 41000<=total<=200000:
            raise ValueError("Número total fuera de límites esperados")
        last=((total-1)//15)*15
        offsets=list(range(max(last-60,0),last+1,15))
        by_day={}
        for off in offsets:
            url=JAEN_BASE+f"results.vm?q=parent:{JAEN_COLLECTION}&view=boletin&s={off}"
            if off==41775 and last==41775:
                h=data
            else:
                time.sleep(0.8)
                m,h=fetch(url,{"www.dipujaen.es"},timeout=(8,25))
                if m["http"]!=200:
                    raise ValueError("Índice de página no disponible: "+str(off))
            for card in BeautifulSoup(h,"html.parser").select("div.list-frame"):
                record=parse_jaen_card(card,url)
                if record is not None:
                    existing=by_day.get(record["date"])
                    if existing is not None and existing["catalogueId"]!=record["catalogueId"]:
                        raise ValueError("Dos originales incompatibles en la misma fecha")
                    by_day[record["date"]]=record
        result["indexedIssues"]=sorted(by_day.values(),key=lambda x:x["date"])
        result["indexCount"]=total
        result["indexedDates"]=len(by_day)
        for record in result["indexedIssues"][:max_pdfs]:
            time.sleep(1)
            pdf=check_jaen_pdf(record)
            result["pdfChecks"].append(pdf)
            if pdf.get("pdfValidated"):
                record["pdfFullyDownloaded"]=True
                record["dateInOriginalVerified"]=bool(pdf.get("firstPageMatchesDate"))
        print("JAEN_PARTIAL",json.dumps({"dates":len(result["indexedIssues"]),
            "pdfsDownloaded":sum(x.get("pdfValidated",False) for x in result["pdfChecks"]),
            "originalDatesMatched":sum(x.get("firstPageMatchesDate",False) for x in result["pdfChecks"]),
            "knownGaps":result["knownMissingNumbers"]},ensure_ascii=True),flush=True)
    except Exception as ex:
        result["error"]=type(ex).__name__+": "+str(ex)[:200]
        print("JAEN_PARTIAL_ERROR",result["error"],flush=True)
    return result

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,default=Path("out/rescate-nocturno.json"))
    parser.add_argument("--max-jaen-pdfs",type=int,default=4)
    parser.add_argument("--self-test",action="store_true")
    args=parser.parse_args()
    if args.self_test:
        assert permitted(JAEN_BASE+"results.vm",{"www.dipujaen.es"})
        assert not permitted("https://bophistorico.dipujaen.es/anything",{"www.dipujaen.es"})
        assert not permitted("http://www.dipujaen.es/",{"www.dipujaen.es"})
        assert parse_jaen_card(BeautifulSoup("<div class='list-frame'>"
          "<p>Ejemplar Boletín Oficial de la Provincia de Jaén. 14/10/2026. (51 páginas.)</p>"
          "<a href='high.raw?id=0001747453&name=x'>Ver</a></div>","html.parser").div,
          "https://www.dipujaen.es/hemerotecadigital/results.vm")["catalogueId"]=="0001747453"
        print("OK: controles de origen y parser, sin convertir parcial en cobertura",flush=True)
        return
    tasks=[(url,code) for code,urls in CHECKS.items() for url in urls]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        probes=list(pool.map(lambda p:check(*p),tasks))
    ja=jaen_partial(max(0,min(args.max_jaen_pdfs,12)))
    summary={code:{"probed":sum(x["territory"]==code for x in probes),
                   "http200":sum(x["territory"]==code and x.get("http")==200 for x in probes),
                   "verified30Days":False} for code in CHECKS}
    output={"timestampUTC":datetime.now(timezone.utc).isoformat(),
       "windowStart":WINDOW_START.isoformat(),"windowEnd":WINDOW_END.isoformat(),
       "purpose":"publisher-origin partial recovery diagnostics",
       "verified30Days":False,"officialPublisherOnly":True,
       "Jaen":ja,"health":summary,"probes":probes}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(output,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("HEALTH_ONLY",json.dumps(summary,ensure_ascii=True),flush=True)
    print("NOT_A_VALIDATED_FEED: no coverage, APK changes, or 30-day claim",flush=True)

if __name__=="__main__":
    main()
