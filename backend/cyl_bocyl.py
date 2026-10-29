#!/usr/bin/env python3
"""BOCYL: 30 days, all official tables of contents, notice titles, official PDFs."""
from __future__ import annotations
import argparse,re,requests,threading
from bs4 import BeautifulSoup
from urllib.parse import urlsplit,urljoin,parse_qs
from datetime import date,datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from clm_common import employment,publish_audit,invalid,write_output

HOST="bocyl.jcyl.es"
SOURCE="https://bocyl.jcyl.es/"
PDF_RE=re.compile(r"^/boletines/(\d{4})/(\d{2})/(\d{2})/pdf/BOCYL-D-(\d{8})-(\d{1,3})-(\d{1,4})\.pdf$",re.I)
_THREAD=threading.local()
def client():
    if not hasattr(_THREAD,"http"):
        c=requests.Session()
        c.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es"})
        _THREAD.http=c
    return _THREAD.http

def get(url,pdf=False):
    v=urlsplit(url)
    if v.scheme!="https" or v.hostname!=HOST or v.port not in (None,443) or v.fragment or v.username:
        invalid("BOCYL: sitio externo inesperado")
    if pdf and not PDF_RE.fullmatch(v.path):invalid("BOCYL: PDF ajeno a boletín")
    try:
        r=client().get(url,timeout=(11,28),stream=pdf,
            headers={"Range":"bytes=0-80"} if pdf else {},allow_redirects=True)
        if r.status_code not in ((200,206) if pdf else (200,)):
            invalid("BOCYL: HTTP "+str(r.status_code)+" en "+url)
        if pdf:
            prefix=next(r.iter_content(100),b"")
            if not prefix.startswith(b"%PDF-") or "pdf" not in r.headers.get("Content-Type","").lower():
                invalid("BOCYL: documento no es PDF oficial")
            r.close()
            return ""
        if not r.content or len(r.content)>2_000_000:invalid("BOCYL: HTML vacío")
        return r.text
    except requests.RequestException as e:invalid("BOCYL: acceso fallido "+str(e)[:170])

def days_in_calendar(html,start,end):
    h=BeautifulSoup(html,"html.parser")
    found=set()
    for a in h.select("a[href]"):
        u=urlsplit(urljoin(SOURCE,a["href"]))
        if u.hostname!=HOST or u.path!="/boletin.do":continue
        v=parse_qs(u.query).get("fechaBoletin",[])
        if len(v)!=1:continue
        try:d=datetime.strptime(v[0],"%d/%m/%Y").date()
        except ValueError:continue
        if start<=d<=end:found.add(d)
    return found

def parse_day(html,day):
    h=BeautifulSoup(html,"html.parser")
    header=h.find("h2",string=re.compile(r"Sumario\s+BOCYL",re.I))
    if header is None:
        header=next((x for x in h.select("h2") if "Sumario BOCYL" in x.get_text(" ",strip=True)),None)
    m=re.search(r"Sumario\s+BOCYL\s+n[º°.]*\s*(\d{1,3})\s*/\s*(\d{4})",
        header.get_text(" ",strip=True),re.I) if header else None
    if not m or int(m[2])!=day.year:invalid(f"BOCYL {day}: cabecera oficial ausente")
    number=int(m[1])
    tables=h.select("ul.descargaBoletin")
    if not tables:invalid(f"BOCYL {day}: no hay anuncios")
    seen=set();rows=[]
    for ul in tables:
        para=ul.find_previous_sibling("p")
        org=ul.find_previous("h5")
        title=" ".join(para.get_text(" ",strip=True).split()) if para else ""
        agency=" ".join(org.get_text(" ",strip=True).split()) if org else ""
        doclinks=[]
        for a in ul.select("a[href]"):
            u=urlsplit(urljoin(SOURCE,a["href"]))
            p=PDF_RE.fullmatch(u.path)
            if p and u.hostname==HOST and u.scheme=="https":
                yy,mm,dd=map(int,p.groups()[:3])
                if (date(yy,mm,dd)!=day or p[4]!=day.strftime("%d%m%Y")
                    or int(p[5])!=number):invalid("BOCYL: enlace PDF de otro día")
                doclinks.append((urljoin(SOURCE,a["href"]),int(p[6])))
        if len({z[0] for z in doclinks})!=1 or not title or not agency:
            invalid(f"BOCYL {day}: título/organismo/PDF no verificados")
        url,seq=doclinks[0]
        ident=f"CY-{day:%Y%m%d}-{seq}"
        if ident in seen:invalid("BOCYL: edicto duplicado")
        seen.add(ident)
        kind=employment(title)
        if kind:
            rows.append({"id":ident,"province":"Castilla y León (BOCYL)",
              "title":title,"entity":agency,"date":day.strftime("%d/%m/%Y"),
              "bulletin":str(number),"type":kind,"url":url})
    return {"day":day,"number":str(number),"read":len(seen),"notices":rows}

def scan(day):
    u=SOURCE+"boletin.do?fechaBoletin="+day.strftime("%d/%m/%Y")
    result=parse_day(get(u),day)
    for n in result["notices"]:get(n["url"],pdf=True)
    print("BOCYL",day,"número",result["number"],"anuncios",result["read"],
      "candidatas",len(result["notices"]),flush=True)
    return result

def audit(today=None):
    end=today or date.today();start=end-timedelta(days=29)
    entries=set()
    for year,month in {(start.year,start.month),(end.year,end.month)}:
        u=SOURCE+f"portada.do?m={month-1}&an={year}"
        entries |=days_in_calendar(get(u),start,end)
    ordered=sorted(entries)
    if len(ordered)<18 or (ordered[0]-start).days>3 or (end-ordered[-1]).days>3:
        invalid("BOCYL: faltan días o número de boletines")
    with ThreadPoolExecutor(max_workers=4) as pool:
        issues=list(pool.map(scan,ordered))
    nums=[int(x["number"]) for x in issues]
    if any(b!=a+1 for a,b in zip(nums,nums[1:])):
        invalid("BOCYL: salto de ediciones o extraordinarios no incluidos")
    return publish_audit(SOURCE,"Castilla y León (BOCYL)",issues,today=end)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path)
    args=p.parse_args();write_output(args.output,audit())
