#!/usr/bin/env python3
"""Verified DOCM source, including ordinary and extraordinary editions."""
from __future__ import annotations
import argparse,re
from pathlib import Path
from datetime import date,timedelta,datetime
from urllib.parse import parse_qs,urlsplit,urljoin
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from clm_common import invalid,get,pdf_header,record,publish_audit,write_output

HOME="https://docm.jccm.es"
SOURCE=HOME+"/docm/"
HOST={"docm.jccm.es"}
DOC_PDF=re.compile(r"/docm/descargarArchivo\.do\?ruta=(\d{4})/(\d{2})/(\d{2})(?:-ext-\d+)?/pdf/(\d{4})_(\d{1,8})\.pdf&tipo=rutaDocm$")
NID=re.compile(r"\[\s*NID\s+(\d{4})/(\d{1,8})\s*\]")
EDITION=re.compile(r"\bN[uú]m\.\s*(\d{1,4})\b",re.I)
DATE_RE=re.compile(r"^\d{8}(?:-ext-\d+)?$")

def bulletin_link(key):
    tail=f"&numDogv={key.rsplit('-',1)[-1]}" if "-ext-" in key else ""
    return HOME+"/docm/cambiarBoletin.do?fecha="+key+tail

def calendar(html,start,end):
    s=BeautifulSoup(html,"html.parser")
    result={}
    for a in s.select('a[href*="cambiarBoletin.do?fecha="]'):
        u=urlsplit(urljoin(SOURCE,a.get("href","")))
        if u.hostname not in HOST:continue
        q=parse_qs(u.query)
        key=q.get("fecha",[""])[0]
        if not DATE_RE.fullmatch(key):continue
        try:d=datetime.strptime(key[:8],"%Y%m%d").date()
        except ValueError:invalid("fecha de calendario imposible")
        if start<=d<=end:
            extra=("-ext-" in key)
            if not (a.get_text(" ",strip=True).lower() in ("ord.","ext.")):invalid("boletín sin marca ordinario/extraordinario")
            if extra!=(a.get_text(" ",strip=True).lower()=="ext."):
                invalid("marca extraordinaria incongruente")
            result[key]=d
    return result

def validate_pdf(url,day,nid):
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname not in HOST or u.port not in (None,443) or u.fragment or u.username:
        invalid("PDF del DOCM fuera del host oficial")
    m=DOC_PDF.fullmatch(u.path+"?"+u.query)
    if not m or date(int(m[1]),int(m[2]),int(m[3]))!=day or m[4]!=str(day.year) or int(m[5])!=nid:
        invalid(f"PDF del DOCM distinto de fecha/NID: {url} esperado {day.isoformat()} NID={nid}")
    return url

def parse_issue(html,key,day):
    s=BeautifulSoup(html,"html.parser")
    body=s.get_text(" ",strip=True)
    m=EDITION.search(body)
    if m is None or not re.search(r"\baño\s+[IVXLCDM]+\b",body,re.I):
        invalid(f"DOCM {key}: falta número y año de la edición")
    num=m[1]+("E" if "-ext-" in key else "")
    official_dates=re.search(r"\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})",body,re.I)
    months=("enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre")
    if official_dates:
        observed=date(int(official_dates[3]),months.index(official_dates[2].lower())+1,int(official_dates[1]))
        if observed!=day:invalid(f"DOCM {key}: HTML corresponde al día {observed}")
    else:invalid(f"DOCM {key}: fecha no comprobable")
    rows=[]
    agency=""
    for el in s.select("h4.tituloOrganismo, p.sumario"):
        if el.name=="h4":
            agency=el.get_text(" ",strip=True)
            continue
        title=" ".join(el.get_text(" ",strip=True).split())
        mm=NID.search(title)
        if mm is None:
            invalid(f"DOCM {key}: NID ausente en disposición")
        year,nid=int(mm[1]),int(mm[2])
        if year!=day.year or not agency:invalid("NID o emisor inesperado")
        a=el.select_one('a[href*="descargarArchivo.do"]')
        if a is None:invalid("DOCM disposición sin PDF")
        pdf=validate_pdf(urljoin(SOURCE,a.get("href","")),day,nid)
        nid_str=f"CM-{year}-{nid}"
        rows.append(record("CM","Castilla-La Mancha (DOCM)",nid_str,title,agency,day,num,pdf))
    if not rows or len({x["id"] for x in rows})!=len(rows):
        invalid(f"DOCM {key}: sin disposiciones o identificadores repetidos")
    return {"day":day,"number":num,"read":len(rows),"notices":[n for n in rows if n["type"]],"pdfs":[n["url"] for n in rows]}

def scan(info):
    key,day=info
    html=get(bulletin_link(key),HOST,retries=5).text
    result=parse_issue(html,key,day)
    check=result["notices"] or result["pdfs"]
    if check:pdf_header(check[0]["url"] if isinstance(check[0],dict) else check[0],HOST)
    print("DOCM",key,"número",result["number"],"anuncios",result["read"],
          "candidatas",len(result["notices"]),flush=True)
    return result

def audit(today=None):
    end=today or date.today()
    start=end-timedelta(days=29)
    idx={}
    for day in {start,end}:
        h=get(bulletin_link(day.strftime("%Y%m%d")),HOST,retries=5).text
        idx.update(calendar(h,start,end))
    # El portal a veces conserva el calendario del mes actual al consultar
    # el mes anterior. Verificar explícitamente la primera edición del intervalo.
    firstkey=start.strftime("%Y%m%d")
    if start.weekday()<5 and firstkey not in idx:
        firstpage=get(bulletin_link(firstkey),HOST,retries=5).text
        parse_issue(firstpage,firstkey,start)
        idx[firstkey]=start
    if len(idx)<19:invalid(f"DOCM: calendario insuficiente ({len(idx)} ediciones)")
    print("DOCM CALENDARIO",sorted(idx),flush=True)
    # Los extraordinarios tienen un sumario separado y pueden sufrir
    # limitación temporal de acceso; comprobarlos al principio de la lectura.
    ordered=sorted(idx.items(),key=lambda pair:(0 if "-ext-" in pair[0] else 1,pair[1],pair[0]))
    with ThreadPoolExecutor(max_workers=1) as p:
        items=list(p.map(scan,ordered))
    return publish_audit(SOURCE,"Castilla-La Mancha (DOCM)",items,today=end)

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--output",type=Path,required=True)
    args=a.parse_args()
    write_output(args.output,audit())
