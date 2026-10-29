#!/usr/bin/env python3
"""Strict connectivity inventory of the 12 outstanding OpoAlert territories.

Diagnostics only: HTTP 200 is not evidence of a complete 30-day official
bulletin; it also does not imply that a linked document is official.
"""
from __future__ import annotations
import concurrent.futures
import json
import socket
import time
from pathlib import Path
from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup

TARGETS = {
 "JA": [
  "https://bop.dipujaen.es/",
  "https://bop.dipujaen.es/bopdigital/",
  "https://bophistorico.dipujaen.es/advanced.vm?s=1&view=boletin",
 ],
 "MA": [
  "https://www.bopmalaga.es/sumario.php?fecha=29-10-2026",
  "https://www.bopmalaga.es/sumario.php?fecha=30-09-2026",
  "https://www.bopmalaga.es/",
 ],
 "AB": [
  "https://bop.dipualba.es/",
  "https://www.dipualba.es/",
  "https://sede.dipualba.es/",
 ],
 "CU": [
  "https://www.dipucuenca.es/boletin-oficial-de-la-provincia",
  "https://www.dipucuenca.es/documents/",
  "https://www.dipucuenca.es/",
 ],
 "BU": [
  "https://bopbur.diputaciondeburgos.es/bopbur-2026-202",
  "https://bopbur.diputaciondeburgos.es/",
  "https://www.burgos.es/servicios/bop",
 ],
 "SA": [
  "https://sede.diputaciondesalamanca.gob.es/BOP/",
  "https://www.lasalina.es/bop",
  "https://www.lasalina.es/",
 ],
 "SG": [
  "https://www.dipsegovia.es/bop",
  "https://www.dipsegovia.es/bop?month=9&year=2026",
  "https://sede.dipsegovia.es/",
 ],
 "VD": [
  "https://bop.sede.diputaciondevalladolid.es/calendario",
  "https://bop.sede.diputaciondevalladolid.es/ultimobop",
  "https://www.diputaciondevalladolid.es/",
 ],
 "AS": [
  "https://miprincipado.asturias.es/bopa/ultimos-boletines",
  "https://www.asturias.es/bopa/",
  "https://sede.asturias.es/bopa/",
 ],
 "CB": [
  "https://boc.cantabria.es/boces/",
  "https://boc.gobcantabria.es/boces/",
  "https://www.cantabria.es/web/boc",
 ],
 "NA": [
  "https://bon.navarra.es/es/inicio",
  "https://www.navarra.es/es/",
  "https://www.lexnavarra.navarra.es/buscador.asp",
 ],
 "CE": [
  "https://www.ceuta.es/ceuta/bocce",
  "https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1965-2026?Itemid=534",
  "https://sede.ceuta.es/",
 ],
}

def request_one(code,url):
    hostname=urlparse(url).hostname
    item={"zone":code,"url":url,"host":hostname}
    try:
        item["dns"] = sorted({x[4][0] for x in socket.getaddrinfo(hostname,443, type=socket.SOCK_STREAM)})[:5]
    except Exception as e: item["dns_error"]=str(e)[:110]
    try:
        start=time.monotonic()
        with requests.Session() as s:
            s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert/1.27 source healthcheck)","Accept-Language":"es-ES,es;q=0.9"})
            response=s.get(url,timeout=(6,13),allow_redirects=True,stream=True)
            data=b""
            for block in response.iter_content(chunk_size=8192):
                data+=block
                if len(data)>70_000: break
            item.update({"http":response.status_code, "final":response.url, "contentType":response.headers.get("Content-Type",""),
                         "sampleBytes":len(data),"elapsed":round(time.monotonic()-start,1)})
            if data.startswith(b"%PDF-"):
                item["pdfHeader"]=True
            else:
                doc=BeautifulSoup(data,"html.parser")
                item["title"]=doc.title.get_text(" ",strip=True)[:140] if doc.title else ""
                item["text"]=doc.get_text(" ",strip=True)[:280]
    except Exception as e: item["error"]=type(e).__name__+": "+str(e)[:200]
    return item

def main():
    pairs=[(key,url) for key,urls in TARGETS.items() for url in urls]
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as ex:
        rows=list(ex.map(lambda x:request_one(*x),pairs))
    summary={}
    for code in TARGETS:
        results=[r for r in rows if r["zone"]==code]
        live=[r["url"] for r in results if r.get("http")==200 and r.get("sampleBytes",0)>1000]
        summary[code]={"responding":len(live),"urls":live,"errors":[r.get("error","") for r in results if r.get("error")]}
    for row in rows: print("SOURCE_PROBE",json.dumps(row,ensure_ascii=False),flush=True)
    print("SOURCE_SUMMARY",json.dumps(summary,ensure_ascii=False),flush=True)
    p=Path("out");p.mkdir(exist_ok=True)
    (p/"cierre_12_probe.json").write_text(json.dumps({"summary":summary,"results":rows},ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
if __name__=="__main__":main()
