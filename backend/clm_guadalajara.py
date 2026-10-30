#!/usr/bin/env python3
"""BOP Guadalajara: official daily calendar, full per-issue notices and PDFs."""
from __future__ import annotations
import argparse,re
from datetime import date,datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from clm_common import invalid,get,pdf_header,record,publish_audit,write_output,employment,numbering_ok
from provincial_common import fold

HOME="https://boletin.dguadalajara.es"
SOURCE=HOME+"/boletin/"
HOST={"boletin.dguadalajara.es"}
DAY_PATH=re.compile(r"^/boletin/index\.php/buscar-k2-menu/date/(\d{4})/(\d{1,2})/(\d{1,2})$")
ISSUE_PATH=re.compile(r"^/boletin/index\.php/9-general/\d{1,8}-[^/?#]+$")
ARTICLE_PATH=re.compile(r"^/boletin/index\.php/2-anuncios/\d{1,8}-.+$")
PDF_PATH=re.compile(r"^/boletin/pdf/pdf(\d{4})_(\d{1,8})\.pdf$")
NUMBER=re.compile(r"\bn[uú]m\.\s*(\d{1,4})\b",re.I)
DATE=re.compile(r"\b(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóú]+)\s+de\s+(\d{4})",re.I)
MONTHS=["enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"]

def day_url(day):
    return f"{SOURCE}index.php/buscar-k2-menu/date/{day.year}/{day.month:02d}/{day.day:02d}?catid=9"

def calendar(html,start,end):
    s=BeautifulSoup(html,"html.parser")
    found=set()
    for a in s.select('td.calendarDateLinked a[href],td.calendarTodayLinked a[href]'):
        u=urlsplit(urljoin(SOURCE,a["href"]))
        m=DAY_PATH.fullmatch(u.path)
        if not m:continue
        d=date(*map(int,m.groups()))
        if start<=d<=end:found.add(d)
    return sorted(found)

def parse_day(html,day):
    s=BeautifulSoup(html,"html.parser")
    links=[]
    for h in s.select("h2.genericItemTitle a[href]"):
        u=urljoin(SOURCE,h["href"])
        if urlsplit(u).hostname in HOST and ISSUE_PATH.fullmatch(urlsplit(u).path):
            if u not in links:links.append(u)
    if not links:invalid(f"Guadalajara: calendario marca {day} pero no hay boletín")
    if len(links)>3:invalid("Guadalajara: demasiadas ediciones para un día")
    return links

def parse_date_number(title,day):
    m=NUMBER.search(title)
    dat=DATE.search(title)
    if not m or not dat:invalid("Guadalajara: título de boletín sin fecha o número")
    month=fold(dat[2])
    if month not in MONTHS:invalid("Guadalajara: mes desconocido")
    published=date(int(dat[3]),MONTHS.index(month)+1,int(dat[1]))
    if published!=day:invalid(f"Guadalajara: boletín de otra fecha {published} esperado {day}")
    number=int(m[1])
    if not 1<=number<=366:invalid("Guadalajara: número imposible")
    return number

def pdf_link_from_article(html,day,nid,title):
    soup=BeautifulSoup(html,"html.parser")
    published_title=soup.select_one("h2.itemTitle")
    if not published_title or fold(" ".join(published_title.get_text(" ",strip=True).split()))!=fold(" ".join(title.split())):
        invalid(f"Guadalajara {day}: ficha no coincide con sumario {nid}")
    urls=[]
    for a in soup.select('a[href*="/boletin/pdf/"]'):
        u=urljoin(SOURCE,a["href"])
        p=urlsplit(u)
        m=PDF_PATH.fullmatch(p.path)
        if (p.hostname in HOST and p.scheme=="https" and m is not None
            and int(m[1])==day.year and int(m[2])==nid):
            if u not in urls:urls.append(u)
    if len(urls)!=1:invalid(f"Guadalajara: {nid} sin PDF único oficial")
    return urls[0]

def scan_issue(pair):
    url,day=pair
    doc=get(url,HOST).text
    soup=BeautifulSoup(doc,"html.parser")
    title=(soup.select_one("h2.itemTitle") or soup.title)
    if title is None:invalid("Guadalajara: cabecera BOP ausente")
    number=parse_date_number(title.get_text(" ",strip=True),day)
    rows=[]
    for item in soup.select("div.itemFullText div.itemSumario"):
        title_a=item.select_one("h3.catItemTitle a[href]")
        agency=item.select_one("p.pTituloCorto")
        code=item.select_one("p.codigo_anuncio")
        if not (title_a and agency and code):invalid("Guadalajara: sumario incompleto")
        num=code.get_text(" ",strip=True)
        if not num.isdigit():invalid("Guadalajara: código de anuncio inválido")
        itemurl=urljoin(SOURCE,title_a["href"])
        if not (urlsplit(itemurl).hostname in HOST and ARTICLE_PATH.fullmatch(urlsplit(itemurl).path)):
            invalid("Guadalajara: URL de ficha fuera de portal")
        agency_text=agency.get_text(" ",strip=True)
        notice_title=title_a.get_text(" ",strip=True)
        kind=employment(notice_title)
        if not kind:
            continue
        individual=get(itemurl,HOST).text
        pdf=pdf_link_from_article(individual,day,int(num),notice_title)
        row=record("GJ","Guadalajara",f"GJ-{day.year}-{int(num)}",
          notice_title,agency_text,day,number,pdf)
        if row["type"]:rows.append(row)
    # Count even non-employment notices; the entire sumario is traversed.
    all_items=soup.select("div.itemFullText div.itemSumario")
    if not all_items or len({x.select_one("p.codigo_anuncio").get_text(" ",strip=True) for x in all_items})!=len(all_items):
        invalid("Guadalajara: edición incompleta o repetida")
    if rows:pdf_header(rows[0]["url"],HOST)
    print("GUADALAJARA",day,"boletín",number,"anuncios",len(all_items),"candidatas",len(rows),flush=True)
    return {"day":day,"number":number,"read":len(all_items),"notices":rows}

def audit(today=None):
    end=today or date.today()
    start=end-timedelta(days=29)
    dates=set()
    for day in {start,end}:
        html=get(day_url(day),HOST).text
        dates.update(calendar(html,start,end))
    if len(dates)<15:invalid(f"Guadalajara: calendario con solo {len(dates)} días")
    jobs=[]
    with ThreadPoolExecutor(max_workers=3) as pool:
        day_results=list(pool.map(lambda d:(d,parse_day(get(day_url(d),HOST).text,d)),sorted(dates)))
        for d,items in day_results:
            jobs.extend((url,d) for url in items)
        issues=list(pool.map(scan_issue,jobs))
    if not numbering_ok([(x["day"],int(x["number"])) for x in issues]):
        invalid(f"Guadalajara: BOP omitido {[x['number'] for x in issues]}")
    return publish_audit(SOURCE,"Guadalajara",issues,today=end)

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    write_output(args.output,audit())
