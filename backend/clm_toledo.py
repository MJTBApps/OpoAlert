#!/usr/bin/env python3
"""BOP Toledo reader: official year calendar, daily summaries, original PDFs."""
from __future__ import annotations
import argparse,re
from datetime import date,datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import parse_qs,urlsplit,urljoin,quote
from bs4 import BeautifulSoup
from clm_common import invalid,get,pdf_header,record,publish_audit,write_output,numbering_ok

HOME="https://bop.diputoledo.es"
SOURCE=HOME+"/webEbop/"
HOST={"bop.diputoledo.es"}
DATE_KEY=re.compile(r"^\d{2}/\d{2}/\d{4}$")
DOCGET=re.compile(r"^/webEbop/DocGet$")

def issue_url(day):
    value=day.strftime("%d/%m/%Y")
    return SOURCE+"ebopResumen.jsp?publication_date="+value+"&publication_date_to="+value

def dates_from_calendar(html,start,end):
    s=BeautifulSoup(html,"html.parser")
    found=set()
    for a in s.select('a[href*="ebopResumen.jsp?publication_date="]'):
        u=urlsplit(urljoin(SOURCE,a["href"]))
        q=parse_qs(u.query)
        date_text=q.get("publication_date",[""])[0]
        to_text=q.get("publication_date_to",[""])[0]
        if not DATE_KEY.fullmatch(date_text) or date_text!=to_text:invalid("fecha/intervalo del calendario incongruente")
        day=datetime.strptime(date_text,"%d/%m/%Y").date()
        if start<=day<=end:found.add(day)
    return sorted(found)

def official_document(href,year,number):
    url=urljoin(SOURCE,href)
    u=urlsplit(url)
    if not (u.scheme=="https" and u.hostname in HOST and u.path=="/webEbop/DocGet"
        and u.port in (None,443) and not u.username and not u.fragment):
        invalid("URL DocGet no oficial")
    q=parse_qs(u.query,keep_blank_values=True)
    if q.get("insert_year")!=[str(year)] or q.get("insert_number")!=[str(number)]:
        invalid("PDF no coincide con el anuncio")
    code=q.get("id",[""])[0]
    if not re.fullmatch(r"\d+;0",code):invalid("ID original de anuncio inválido")
    return url

def parse_issue(html,day):
    s=BeautifulSoup(html,"html.parser")
    body=s.get_text(" ",strip=True)
    if "No hay anuncios publicados" in body:
        return None
    a=s.select_one('a[href*="DocGet?bop="]')
    if a is None:invalid("Toledo: no existe PDF del boletín")
    u=urlsplit(urljoin(SOURCE,a["href"]))
    q=parse_qs(u.query)
    if (u.hostname not in HOST or u.path!="/webEbop/DocGet" or
        q.get("insert_year",[""])[0] not in (str(day.year-1),str(day.year),str(day.year+1)) or
        q.get("publication_date")!=[day.strftime("%d%m%Y")] or
        q.get("anexo")!=["0"]):
        invalid("Toledo: PDF de edición de otro día")
    number=q.get("bop",[""])[0]
    if not number.isdigit() or not 1<=int(number)<=366:invalid("Toledo: número BOP ausente")
    items=[]
    agency=""
    for node in s.select("#searchResult h3.publisherBlock, #searchResult div.announce"):
        if node.name=="h3":
            agency=node.get_text(" ",strip=True).replace("Anunciante :","").strip()
            continue
        link=node.select_one('a[href*="DocGet?id="]')
        if link is None:invalid("Toledo: anuncio sin PDF")
        doc_url=urlsplit(urljoin(SOURCE,link["href"]))
        query=parse_qs(doc_url.query)
        inserted=query.get("insert_number",[""])[0]
        if not inserted.isdigit():invalid("Toledo: identificador de inserción ausente")
        # Alrededor de año nuevo hay inserciones registradas el año anterior
        # o, a final de diciembre, ya con el año siguiente.
        year=query.get("insert_year",[""])[0]
        if year not in (str(day.year-1),str(day.year),str(day.year+1)):invalid("Toledo: año de inserción inesperado")
        title_item=next((x for x in node.select("li") if "Resumen/Asunto" in x.get_text(" ",strip=True)),None)
        if title_item is None:invalid("Toledo: resumen original ausente")
        title=title_item.get_text(" ",strip=True).replace("Resumen/Asunto :","").strip()
        if not agency:
            invalid("Toledo: ayuntamiento/organismo no identificado")
        pdf=official_document(link["href"],int(year),int(inserted))
        items.append(record("TO","Toledo",f"TO-{year}-{int(inserted)}",title,agency,day,number,pdf))
    if not items or len({x["id"] for x in items})!=len(items):
        invalid("Toledo: sin anuncios o duplicados")
    return {"day":day,"number":number,"read":len(items),
       "notices":[v for v in items if v["type"]],"pdf":urljoin(SOURCE,a["href"])}

def scan(day):
    parsed=parse_issue(get(issue_url(day),HOST).text,day)
    if parsed is None:
        if day==date.today():
            print("TOLEDO: el calendario señala hoy, pero aún no está publicada la edición; sin inventar anuncios",flush=True)
            return None
        invalid(f"Toledo: {day} figura en calendario pero no tiene anuncios")
    pdf_header(parsed["pdf"],HOST)
    print("TOLEDO",day,"boletín",parsed["number"],"anuncios",parsed["read"],
          "candidatas",len(parsed["notices"]),flush=True)
    return parsed

def audit(today=None):
    end=today or date.today()
    start=end-timedelta(days=29)
    # El calendario oficial es anual: pedir cada año de la ventana.
    dates=sorted({d for year in {start.year,end.year}
                  for d in dates_from_calendar(get(SOURCE+f"ebopCalendar.jsp?calendar_year={year}",HOST).text,start,end)})
    if len(dates)<15:invalid(f"Toledo: calendario no cubre 30 días: {len(dates)} ediciones")
    with ThreadPoolExecutor(max_workers=3) as pool:
        data=[issue for issue in pool.map(scan,dates) if issue is not None]
    if not numbering_ok([(x["day"],int(x["number"])) for x in data]):
        invalid(f"Toledo: salto en numeración oficial {[x['number'] for x in data]}")
    return publish_audit(SOURCE,"Toledo",data,today=end)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    a=ap.parse_args()
    write_output(a.output,audit())
