#!/usr/bin/env python3
"""Soria official BOP over 30 days, individual PDF verified for each candidate."""
from __future__ import annotations
import argparse,re,json,requests,threading
from pathlib import Path
from datetime import date,datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlsplit
from clm_common import employment,invalid

HOST="bop.dipsoria.es"
SOURCE="https://bop.dipsoria.es/index.php/mod.boloficial/relmenu.149"
_DETAIL=re.compile(r"^/index\.php/mod\.boloficial/mem\.detalle/id\.(\d+)/relcategoria\.(\d+)(?:/relmenu\.\d+)?$")
_DOC=re.compile(r"^/index\.php/mod\.documentos/mem\.descargar/fichero\.documentos_(\d{1,6})_([a-f0-9]{8})%232E%23pdf$",re.I)
_ISSUE=re.compile(r"^/index\.php/mod\.documentos/mem\.descargar/fichero\.documentos_BOPSoria_(\d{1,3})_([a-f0-9]{8})%232E%23pdf$",re.I)
_T=threading.local()
def client():
    if not hasattr(_T,"s"):
        s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es"});_T.s=s
    return _T.s

def fetch(url,pdf=False):
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443) or u.username or u.query or u.fragment:
        invalid("Soria: URL ajena al BOP")
    try:
        r=client().get(url,timeout=(11,26),stream=pdf,headers={"Range":"bytes=0-95"} if pdf else {})
        if r.status_code not in ((200,206) if pdf else (200,)):
            invalid("Soria: documento no disponible HTTP "+str(r.status_code))
        if pdf:
            sample=next(r.iter_content(100),b"")
            if not sample.startswith(b"%PDF-") or "pdf" not in r.headers.get("Content-Type","").lower():
                invalid("Soria: el fichero oficial no es un PDF")
            r.close();return ""
        if not r.content or len(r.content)>1_800_000:invalid("Soria: HTML de boletín vacío")
        return r.text
    except requests.RequestException as e:invalid("Soria: error de conexión con BOP: "+str(e)[:180])

def archive(html,start,end):
    h=BeautifulSoup(html,"html.parser")
    links=[]
    for a in h.select("h3 a[href]"):
        m=re.fullmatch(r"BOP\s+(\d{1,3})\s+.*?(\d{4})",a.get_text(" ",strip=True),re.I)
        parent=a.find_parent("li")
        dt=parent.select_one("p.fec") if parent else None
        if not m or dt is None:continue
        try:d=datetime.strptime(dt.get_text(" ",strip=True),"%d/%m/%Y").date()
        except ValueError:continue
        u=urljoin(SOURCE,a["href"]);parsed=urlsplit(u)
        if parsed.hostname!=HOST or not _DETAIL.fullmatch(parsed.path):invalid(f"Soria: enlace de detalle no oficial: {u}")
        if start<=d<=end:
            links.append((d,int(m[1]),u))
    links=sorted(set(links))
    if len(links)<10 or (links[0][0]-start).days>4 or (end-links[-1][0]).days>4:
        invalid(f"Soria: índice insuficiente: {len(links)} ediciones; primera {links[0][0] if links else None}; última {links[-1][0] if links else None}")
    if any(b[1]!=a[1]+1 for a,b in zip(links,links[1:])):
        invalid("Soria: falta número de boletín en archivo oficial")
    return links

def parse(html,day,num):
    h=BeautifulSoup(html,"html.parser")
    headings=h.select("h1,h2,h3")
    if not any(re.search(rf"\bBOP\s+{num}\b",x.get_text(" ",strip=True),re.I) for x in headings):
        invalid(f"Soria: número del BOP distinto de {num}")
    if day.strftime("%d/%m/%Y") not in h.get_text(" ",strip=True):
        invalid("Soria: fecha del BOP distinta")
    edition=[]
    for a in h.select('a[href*="mem.descargar"]'):
        u=urljoin(SOURCE,a["href"]).replace("http://bop.dipsoria.es/","https://bop.dipsoria.es/",1)
        p=urlsplit(u)
        if p.hostname==HOST and (m:=_ISSUE.fullmatch(p.path)) and int(m[1])==num:
            edition.append(u)
    if len(set(edition))!=1:invalid("Soria: el BOP completo carece de PDF original")
    ul=h.select_one("ul.lst")
    if ul is None:invalid("Soria: índice de anuncios ausente")
    result=[];seen=set()
    current_entity="Boletín Oficial de la Provincia de Soria"
    total=0
    for li in ul.find_all("li",recursive=False):
        a=li.select_one('a[href*="mem.descargar"]')
        if a is None:continue
        url=urljoin(SOURCE,a["href"]).replace("http://bop.dipsoria.es/","https://bop.dipsoria.es/",1)
        u=urlsplit(url);m=_DOC.fullmatch(u.path)
        if u.hostname!=HOST or not m:invalid("Soria: anuncio sin PDF individual válido")
        marker=m[1]
        if marker in seen:invalid("Soria: anuncio duplicado")
        seen.add(marker);total+=1
        value=" ".join(li.get_text(" ",strip=True).split())
        text=re.sub(r"\s*Descargar\s+\d+\s+\d+\s*KB\s*$","",value,flags=re.I).strip(" -")
        if re.search(r"DIPUTACI[OÓ]N PROVINCIAL DE SORIA",text,re.I):
            current_entity="Diputación Provincial de Soria"
        elif mm:=re.search(r"AYUNTAMIENTOS\s+-\s+([A-ZÁÉÍÓÚÑ ]{3,60})\s+-",text):
            current_entity="Ayuntamiento de "+mm[1].strip().title()
        else:
            mm=re.match(r"^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ ]{3,55})\s+-",text)
            if mm and mm[1].strip() not in ("SUMARIO","ADMINISTRACIÓN LOCAL"):
                current_entity="Ayuntamiento de "+mm[1].strip().title()
        kind=employment(text)
        if kind is not None:
            result.append({"id":f"SR-{day.year}-{int(marker)}","province":"Soria",
               "title":text,"entity":current_entity,"date":day.strftime("%d/%m/%Y"),
               "bulletin":str(num),"type":kind,"url":url})
    if total==0:invalid("Soria: índice sin anuncios")
    return {"day":day,"number":str(num),"read":total,"notices":result,"pdf":edition[0]}

def one(row):
    day,num,url=row
    x=parse(fetch(url),day,num)
    fetch(x["pdf"],pdf=True)
    for notice in x["notices"]:fetch(notice["url"],pdf=True)
    print("SORIA",day,"BOP",num,"anuncios",x["read"],"candidatas",len(x["notices"]),flush=True)
    return x

def audit(today=None):
    end=today or date.today();start=end-timedelta(days=29)
    cases=archive(fetch(SOURCE),start,end)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows=list(pool.map(one,cases))
    notices=[n for x in rows for n in x["notices"]]
    if not notices or len({n["id"] for n in notices})!=len(notices):
        invalid("Soria: sin candidatos o referencias duplicadas")
    dates=[x["day"].isoformat() for x in rows];nums=[x["number"] for x in rows]
    count=sum(x["read"] for x in rows)
    return {"schemaVersion":1,"province":"Soria","source":SOURCE,
      "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
      "coverage":{"complete":True,"status":"complete","bulletin":nums[-1],
        "pagesVisited":len(rows),"announcementsRead":count,"opportunities":len(notices)},
      "historyCoverage":{"complete":True,"rangeStart":start.isoformat(),"rangeEnd":end.isoformat(),
        "issuesRead":len(rows),"bulletins":nums,"publicationDates":dates,
        "nonPublicationDates":[(start+timedelta(days=i)).isoformat() for i in range(30)
            if (start+timedelta(days=i)).isoformat() not in dates],
        "editionPDFs":[x["pdf"] for x in rows],"announcementsRead":count,"opportunities":len(notices)},
      "notices":sorted(notices,key=lambda n:(datetime.strptime(n["date"],"%d/%m/%Y"),n["id"]),reverse=True)}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();x=audit();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"SORIA AUDITADO: {x['historyCoverage']['issuesRead']} boletines, "
      f"{x['coverage']['announcementsRead']} anuncios y {len(x['notices'])} candidatas",flush=True)
