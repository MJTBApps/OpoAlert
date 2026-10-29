#!/usr/bin/env python3
"""Málaga BOP: full 30-day official summaries, with verified links to original PDFs.
The publisher uses a Turnstile challenge to DOWNLOAD PDFs. We never bypass it.
"""
from __future__ import annotations
import argparse,json,re,requests,threading,time
from urllib.parse import urljoin,urlsplit,parse_qs
from datetime import datetime,date,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from clm_common import employment,publish_audit,invalid,write_output

SOURCE="https://www.bopmalaga.es/sumario.php"
HOME="https://www.bopmalaga.es/"
HOST="www.bopmalaga.es"
EDICT=re.compile(r"^(\d{8})-(\d{5})-(\d{4})-(\d{2})$")
PDF_EDICT=re.compile(r"^/verificacion\.php$")
_thread=threading.local()

def session():
    if not hasattr(_thread,"client"):
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es","Cache-Control":"no-cache",
          "Referer":SOURCE})
        _thread.client=s
    return _thread.client

def request(url):
    q=urlsplit(url)
    if q.scheme!="https" or q.hostname!=HOST or q.port not in (None,443) or q.fragment or q.username:
        invalid("Málaga: enlace fuera de portal oficial")
    error=None
    for attempt in range(3):
        try:
            r=session().get(url,timeout=(10,25))
            if (r.status_code==200 and urlsplit(r.url).hostname==HOST
                and r.content and len(r.content)<=4_000_000
                and b"Verificacion necesaria" not in r.content[:2500]
                and b"Verificaci\xc3\xb3n de seguridad" not in r.content[:2500]
                and b"<title>Verificacion necesaria</title>" not in r.content[:2500]):
                return r
            error=f"HTTP {r.status_code}, {len(r.content)} bytes, respuesta de seguridad o vacia"
        except requests.RequestException as ex:error=str(ex)[:150]
        if attempt<2:time.sleep(1.6*(attempt+1))
    invalid("Málaga: archivo no disponible sin verificación interactiva: "+url+" ("+str(error)+")")

def day_url(day):
    return SOURCE+"?fecha="+day.strftime("%d-%m-%Y")

def calendar(html,start,end):
    h=BeautifulSoup(html,"html.parser")
    days={}
    for a in h.select("#table_calendario a[href]"):
        t=a.select_one("time[datetime]")
        m=re.search(r"^BOP\s+(\d{1,3}):",a.get("title",""),re.I)
        if not t or not m:continue
        try:day=date.fromisoformat(t["datetime"])
        except ValueError:invalid("Málaga: fecha del calendario incorrecta")
        link=urlsplit(urljoin(SOURCE,a.get("href","")))
        if link.hostname!=HOST or link.path!="/sumario.php" or parse_qs(link.query).get("fecha")!=[day.strftime("%d-%m-%Y")]:
            invalid("Málaga: fecha del enlace del calendario distinta")
        if start<=day<=end:
            k=int(m[1])
            if day in days and days[day]!=k:invalid("Málaga: fechas con doble numeración")
            days[day]=k
    if not days:invalid("Málaga: calendario oficial vacío")
    return days

def pdf_from_edicto(html,day,serial,year,revision):
    h=BeautifulSoup(html,"html.parser")
    expected=f"{day:%Y%m%d}-{serial:05d}-{year}-{revision}"
    body=h.get_text(" ",strip=True)
    if not re.search(rf"Edicto\s+{serial}/{year}\b",body,re.I):
        invalid("Málaga: ficha no coincide con número de edicto")
    matches=[]
    for a in h.select("a[href]"):
        u=urlsplit(urljoin(HOME,a["href"]))
        p=parse_qs(u.query)
        if u.scheme=="https" and u.hostname==HOST and u.path=="/verificacion.php" and p.get("archivo")==[expected+".pdf"]:
            matches.append(urljoin(HOME,a["href"]))
    if not matches:invalid(f"Málaga: ficha sin enlace al PDF original {expected}")
    # verificacion.php: requiere desafío web interactivo de la propia Diputación.
    # No se simula la verificación automática ni se presupone descarga del PDF.
    return matches[0]

def parse_issue(html,day,number,load_detail=None):
    h=BeautifulSoup(html,"html.parser")
    mark=h.select_one("h2 time[datetime]")
    if mark is None or mark["datetime"]!=day.isoformat():
        invalid(f"Málaga: se recibió sumario de otro día en lugar de {day}")
    pdfs=h.select('#lista_pdf a[href*="verificacion.php?archivo="]')
    original=[]
    for a in pdfs:
        u=urlsplit(urljoin(HOME,a["href"]))
        file=parse_qs(u.query).get("archivo",[""])[0]
        m=re.fullmatch(r"(\d{2})(\d{2})(\d{2})(\d{1,3})(?:a\d{2})?\.pdf",file,re.I)
        if (u.scheme!="https" or u.hostname!=HOST or u.path!="/verificacion.php"
          or m is None or file[:6]!=day.strftime("%d%m%y") or int(m[4])!=number):
            invalid(f"Málaga: PDF de edición no coincide con día o BOP {day}")
        original.append(urljoin(HOME,a["href"]))
    if not original:invalid("Málaga: enlace PDF de edición ausente")
    all_rows=[];candidates=[]
    for section in h.select("section"):
        head=section.find("h3",recursive=False)
        if head is None:continue
        group=head.get_text(" ",strip=True).upper()
        for article in section.find_all("article",recursive=False):
            link=article.select_one('a[href*="edicto.php?edicto="]')
            b=article.find("b")
            if link is None or b is None:invalid("Málaga: anuncio sin municipio o enlace de edicto")
            town=b.get_text(" ",strip=True)
            content=article.get_text(" ",strip=True)
            title=content.split(". ",1)[-1]
            title=re.sub(r"\s*\[\s*Edicto\s+\d+/\d{4}\s*\]\s*$","",title).strip()
            if not town or not title:invalid("Málaga: organismo/título vacío")
            u=urlsplit(urljoin(HOME,link["href"]))
            code=parse_qs(u.query).get("edicto",[""])[0]
            m=EDICT.fullmatch(code)
            if (u.scheme!="https" or u.hostname!=HOST or u.path!="/edicto.php"
                or m is None or m[1]!=day.strftime("%Y%m%d") or int(m[3])!=day.year):
                invalid("Málaga: enlace de edicto de otra fecha")
            ident=f"MA-{day:%Y%m%d}-{m[2]}"
            if group=="AYUNTAMIENTO":agency="AYUNTAMIENTO · "+town
            elif group=="DIPUTACIÓN":agency="DIPUTACIÓN · "+town
            else:agency=group+" · "+town
            all_rows.append(ident)
            kind=employment(title)
            if kind is None:continue
            url=urljoin(HOME,link["href"])
            detail=load_detail(url) if load_detail else request(url).text
            official=pdf_from_edicto(detail,day,int(m[2]),int(m[3]),m[4])
            candidates.append({"id":ident,"province":"Málaga","title":title,"entity":agency,
              "date":day.strftime("%d/%m/%Y"),"bulletin":str(number),"type":kind,"url":official})
    if not all_rows or len(all_rows)!=len(set(all_rows)):
        invalid("Málaga: sumario vacío o edictos duplicados")
    return {"day":day,"number":str(number),"read":len(all_rows),"notices":candidates,
      "editions":original}

def scan(pair):
    day,number=pair
    issue=parse_issue(request(day_url(day)).text,day,number)
    print("MALAGA",day,"BOP",number,"anuncios",issue["read"],
          "candidatas",len(issue["notices"]),flush=True)
    return issue

def audit(today=None):
    end=today or date.today()
    start=end-timedelta(days=29)
    found={}
    # Both months are needed when 30-day range crosses the boundary.
    for d in {start,end}:
        page=request(day_url(d)).text
        c=calendar(page,start,end)
        for day,num in c.items():
            if day in found and found[day]!=num:invalid("Málaga: calendarios contradictorios")
            found[day]=num
    items=sorted(found.items())
    if (len(items)<18 or (end-items[-1][0]).days>4 or
        (items[0][0]-start).days>4):
        invalid("Málaga: no cubre 30 días")
    for (d,n),(d2,n2) in zip(items,items[1:]):
        if n2!=n+1:invalid(f"Málaga: salto entre BOP {n} y {n2}")
    # One session per worker, official server limits parallel traffic.
    with ThreadPoolExecutor(max_workers=1) as pool:
        issued=list(pool.map(scan,items))
    data=publish_audit(SOURCE,"Málaga",issued,today=end)
    data["historyCoverage"]["editionsPDFLinks"]=[url for row in issued for url in row["editions"]]
    data["historyCoverage"]["pdfAccess"]="Los PDF originales requieren verificación Turnstile interactiva, no eludida por el lector."
    return data

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    write_output(args.output,audit())
