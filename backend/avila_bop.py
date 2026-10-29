#!/usr/bin/env python3
"""Ávila official BOP: 30-day chronological issue and per-notice PDF audit."""
from __future__ import annotations
import argparse,re,requests,threading
import fitz
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlsplit
from datetime import date,datetime,timedelta
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from clm_common import employment,publish_audit,invalid,write_output

HOST="www.diputacionavila.es"
SOURCE="https://www.diputacionavila.es/boletin-oficial/2026/"
_THREAD=threading.local()
def client():
    if not hasattr(_THREAD,"http"):
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es"})
        _THREAD.http=s
    return _THREAD.http

def load(url,pdf=False):
    v=urlsplit(url)
    if v.scheme!="https" or v.hostname!=HOST or v.port not in (None,443) or v.username or v.fragment:
        invalid("Ávila: URL fuera de la Diputación")
    try:
        r=client().get(url,timeout=(11,25),headers={"Range":"bytes=0-80"} if pdf else {},stream=pdf)
        if r.status_code not in ((200,206) if pdf else (200,)):
            invalid("Ávila: HTTP "+str(r.status_code)+" "+url)
        if pdf:
            head=next(r.iter_content(100),b"")
            if not head.startswith(b"%PDF-") or "pdf" not in r.headers.get("Content-Type","").lower():
                invalid("Ávila: documento no es un PDF oficial")
            r.close()
            return ""
        if not r.content or len(r.content)>2_000_000:invalid("Ávila: sumario vacío")
        return r.text
    except requests.RequestException as ex:invalid("Ávila: conexión oficial fallida "+str(ex)[:170])

def issues(html,start,end):
    s=BeautifulSoup(html,"html.parser")
    found=set()
    for a in s.select("a[href]"):
        u=urlsplit(urljoin(SOURCE,a["href"]))
        match=re.fullmatch(r"/boletin-oficial/2026/(\d{2})-(\d{2})-(2026)\.html",u.path)
        if not match or u.hostname!=HOST:continue
        day=date(int(match[3]),int(match[2]),int(match[1]))
        if start<=day<=end:found.add(day)
    ordered=sorted(found)
    if len(ordered)<18 or (ordered[0]-start).days>4 or (end-ordered[-1]).days>4:
        invalid("Ávila: índice insuficiente para 30 días")
    return ordered

def parse(html,day):
    soup=BeautifulSoup(html,"html.parser")
    h=soup.find("h3")
    if not h or day.strftime("%d/%m/%Y") not in h.get_text(" ",strip=True):
        invalid(f"Ávila: sumario no corresponde al {day}")
    body=soup.get_text(" ",strip=True)
    m=re.search(r"B\.?\s*O\.?\s*P\.?\s*(\d{1,3})\s*/\s*(\d{2})",body,re.I)
    if not m or int(m[2])!=day.year%100:invalid("Ávila: número del BOP ausente")
    number=m[1]
    print("AVILA_NUM",day,number,"TEXT",body[body.find("B.O.P.")-80:body.find("B.O.P.")+65],flush=True)
    notices=[];all_ids=set()
    lists=soup.select("div.listado")
    if not lists:invalid("Ávila: faltan bloques de anuncios")
    for block in lists:
        org=block.find("span")
        agency=org.get_text(" ",strip=True) if org else ""
        if not agency:invalid("Ávila: anuncio sin organismo")
        for item in block.select("li"):
            a=item.find("a",href=True)
            if not a:invalid("Ávila: anuncio sin PDF")
            u=urlsplit(urljoin(SOURCE,a["href"]))
            title=" ".join(a.get_text(" ",strip=True).split())
            idtxt=item.get_text(" ",strip=True)
            nm=re.search(r"n[ºo°]\s*(\d{1,7})\s*/\s*(\d{2})",idtxt,re.I)
            if not nm or int(nm[2])!=day.year%100:invalid("Ávila: anuncio sin número propio")
            if re.fullmatch(r"/bops/2026/\d{2}-\d{2}-2026\.pdf",u.path,re.I):
                continue  # PDF del boletín completo, no es anuncio individual
            if (u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443)
                or not re.fullmatch(r"/bops/2026/\d{2}-\d{2}-2026/[^/]+\.pdf",u.path,re.I)
                or f"/{day:%d-%m-%Y}/" not in u.path):
                invalid(f"Ávila: PDF de otro boletín día {day} URL {u.geturl()}")
            id=f"AV-{day.year}-{int(nm[1])}"
            if id in all_ids:invalid("Ávila: anuncio duplicado")
            all_ids.add(id)
            kind=employment(title)
            if kind:
                notices.append({"id":id,"province":"Ávila","title":title,"entity":agency,
                  "date":day.strftime("%d/%m/%Y"),"bulletin":number,
                  "type":kind,"url":urljoin(SOURCE,a["href"])})
    if not all_ids:invalid("Ávila: sin anuncios")
    return {"day":day,"number":number,"read":len(all_ids),"notices":notices}

def scan(day):
    u=f"https://www.diputacionavila.es/boletin-oficial/2026/{day:%d-%m-%Y}.html"
    x=parse(load(u),day)
    # El portal de la Diputación contiene una errata comprobada: el 06/10
    # indica B.O.P. 103/26 pero el PDF original lleva N.º 193.
    if day==date(2026,10,6) and x["number"]=="103":
        original=f"https://www.diputacionavila.es/bops/2026/{day:%d-%m-%Y}.pdf"
        rr=client().get(original,timeout=(12,30))
        if rr.status_code!=200 or not rr.content.startswith(b"%PDF-"):
            invalid("Ávila 06/10: imposible confirmar número en PDF oficial")
        doc=fitz.open(stream=rr.content,filetype="pdf")
        head=doc[0].get_text()[:200]
        if not re.match(r"6 de octubre de 2026\s+N\.\s*[º°o]?\s*193\b",head,re.I):
            invalid(f"Ávila 06/10: PDF no respalda corrección: {head[:100]!r}")
        x["number"]="193"
        print("AVILA ERRATA OFICIAL: HTML 103/26; PDF firmado número 193, verificado",flush=True)
    for notice in x["notices"]:load(notice["url"],pdf=True)
    print("AVILA",day,"BOP",x["number"],"anuncios",x["read"],"candidatas",len(x["notices"]),flush=True)
    return x

def audit(today=None):
    end=today or date.today();start=end-timedelta(days=29)
    days=issues(load(SOURCE),start,end)
    with ThreadPoolExecutor(max_workers=5) as pool:
        rows=list(pool.map(scan,days))
    numbers=[int(x["number"]) for x in rows]
    if any(b!=a+1 for a,b in zip(numbers,numbers[1:])):
        invalid("Ávila: faltan ediciones ordinarias o extraordinarias")
    return publish_audit(SOURCE,"Ávila",rows,today=end)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path)
    args=p.parse_args();write_output(args.output,audit())
