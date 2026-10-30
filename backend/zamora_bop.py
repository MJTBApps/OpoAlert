#!/usr/bin/env python3
"""30-day BOP Zamora official HTML and signed notice PDFs; fail closed."""
from __future__ import annotations
import argparse,json,re,requests,threading
from pathlib import Path
from datetime import date,datetime,timedelta,timezone
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from clm_common import employment,invalid,numbering_ok

HOST="www.diputaciondezamora.es"
SOURCE="https://www.diputaciondezamora.es/opencms/servicios/BOP/busqueda-en-el-bop/"
INDEX_RE=re.compile(r"^/opencms/servicios/BOP/indice-bop/([0-9a-f-]{36})/$")
DOC_RE=re.compile(r"^/opencms/export/sites/dipu-zamora/servicios/BOP/\.Archivos/documentos/BOP/anuncios/(\d{4})/(\d{1,3})(?:-extraordinario)?/(\d{9})\.pdf$",re.I)
ISSUE_RE=re.compile(r"^/opencms/export/sites/dipu-zamora/servicios/BOP/\.Archivos/documentos/BOP/(\d{4})/(\d{8})-(\d{1,3})(?:-extraordinario)?\.pdf$",re.I)
TLS=threading.local()
def client():
    if not hasattr(TLS,"s"):
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es"})
        TLS.s=s
    return TLS.s
def get(url,pdf=False):
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname!=HOST or u.username or u.fragment or u.port not in (None,443):
        invalid("Zamora: enlace fuera del portal oficial")
    try:
        r=client().get(url,timeout=(10,28),headers={"Range":"bytes=0-96"} if pdf else {},stream=pdf)
        if r.status_code not in ((200,206) if pdf else (200,)):
            invalid(f"Zamora: HTTP {r.status_code} para {url}")
        if pdf:
            h=next(r.iter_content(128),b"")
            if not h.startswith(b"%PDF-") or "pdf" not in r.headers.get("Content-Type","").lower():
                invalid("Zamora: respuesta no contiene PDF auténtico")
            r.close()
            return ""
        if not r.content or len(r.content)>2_000_000:invalid("Zamora: página vacía o excesiva")
        return r.text
    except requests.RequestException as e:invalid("Zamora: no responde el portal: "+str(e)[:175])
def listing(html,start,end):
    h=BeautifulSoup(html,"html.parser")
    cards=h.select("div.search-result")
    if len(cards)!=15:invalid("Zamora: el índice oficial de 15 boletines está incompleto")
    rows=[]
    for card in cards:
        heading=card.select_one("h4.search-result-heading")
        a=heading.find("a",href=True) if heading else None
        tag=heading.select_one(".search-badge") if heading else None
        if not a or not tag:invalid("Zamora: fila sin fecha o enlace")
        m=re.fullmatch(r"BOP\s+(\d{1,3})",a.get_text(" ",strip=True),re.I)
        dm=re.fullmatch(r"(ORDINARIO|EXTRAORDINARIO)\s*-\s*(\d{2}/\d{2}/\d{4})",tag.get_text(" ",strip=True),re.I)
        url=urljoin(SOURCE,a["href"]);u=urlsplit(url)
        if not m or not dm or u.hostname!=HOST or not INDEX_RE.fullmatch(u.path):
            invalid("Zamora: enlace o número de edición fuera del BOP")
        d=datetime.strptime(dm[2],"%d/%m/%Y").date()
        if start<=d<=end:
            rows.append((d,int(m[1]),url.split("?")[0]))
    if not rows:invalid("Zamora: índices de BOP fuera del mes")
    return rows

def issue(html,day,number):
    h=BeautifulSoup(html,"html.parser")
    title=h.select_one("h1.intro-headline")
    m=re.search(r"(ORDINARIO|EXTRAORDINARIO)\s*:\s*BOP\s+(\d{1,3})",title.get_text(" ",strip=True),re.I) if title else None
    if not m or int(m[2])!=number:invalid(f"Zamora {day}: número BOP incorrecto")
    dates=h.select(".info.date")
    names={1:"enero",2:"febrero",3:"marzo",4:"abril",5:"mayo",6:"junio",7:"julio",8:"agosto",9:"septiembre",10:"octubre",11:"noviembre",12:"diciembre"}
    expected=f"{day.day} de {names[day.month]} de {day.year}"
    if not any(expected in x.get_text(" ",strip=True).lower() for x in dates):
        invalid(f"Zamora: fecha de edición incorrecta {day}")
    link=h.find("a",string=re.compile(r"Descargar BOP completo",re.I))
    url=urljoin(SOURCE,link["href"]) if link else ""
    u=urlsplit(url);p=ISSUE_RE.fullmatch(u.path)
    if not p or u.hostname!=HOST or int(p[1])!=day.year or p[2]!=day.strftime("%Y%m%d") or int(p[3])!=number:
        invalid(f"Zamora {day} BOP {number}: PDF completo incorrecto: {url}")
    blocks=h.select("#anuncio")
    if not blocks:invalid("Zamora: la edición carece de anuncios")
    rows=[];seen=set()
    for block in blocks:
        a=block.find("a",string=re.compile(r"Descargar Anuncio",re.I))
        text=block.get_text(" ",strip=True)
        ref=re.search(r"N[ºo°]\s*de\s*referencia:\s*(\d{9})\b",text,re.I)
        extract=block.select_one("div.body.default div.text")
        title=" ".join(extract.get_text(" ",strip=True).split()) if extract else ""
        organism=re.search(r"Organismo:\s*(.*?)\s+Extracto:",text,re.I)
        agency=organism[1].strip() if organism else ""
        pdf=urljoin(SOURCE,a["href"]) if a else ""
        v=urlsplit(pdf);pm=DOC_RE.fullmatch(v.path)
        if (not ref or not title or not agency or not pm or v.hostname!=HOST
            or int(pm[1])!=day.year or int(pm[2])!=number or pm[3]!=ref[1] or ref[1] in seen):
            invalid(f"Zamora: anuncio o PDF mal identificado {day}: {text[:260]}, URL={pdf}")
        seen.add(ref[1])
        kind=employment(title)
        if kind:
            rows.append({"id":"ZM-"+ref[1],"province":"Zamora","title":title,"entity":agency,
                "date":day.strftime("%d/%m/%Y"),"bulletin":str(number),"type":kind,"url":pdf})
    return {"day":day,"number":str(number),"read":len(seen),"notices":rows,"pdf":url}

def scan(t):
    day,num,url=t
    x=issue(get(url),day,num)
    get(x["pdf"],pdf=True)
    for n in x["notices"]:get(n["url"],pdf=True)
    print("ZAMORA",day,"BOP",num,"anuncios",x["read"],"candidatas",len(x["notices"]),flush=True)
    return x
def audit(today=None):
    end=today or date.today();start=end-timedelta(days=29)
    # Zamora publishes primarily Mondays, Wednesdays and Fridays.
    # The first 15 result entries cover the complete recent 30-day window.
    current=listing(get(SOURCE),start,end)
    if len(current)<12:invalid("Zamora: faltan días de publicación de las últimas cuatro semanas")
    if (end-current[0][0]).days>4 or (current[-1][0]-start).days>4:
        invalid("Zamora: no se cubren los límites del periodo")
    # La lista va de la más reciente a la más antigua.
    if (any(day1<day2 for (day1,_,_),(day2,_,_) in zip(current,current[1:]))
        or not numbering_ok([(d,n) for d,n,_ in reversed(current)])):
        invalid("Zamora: faltan números BOP en la lista")
    with ThreadPoolExecutor(max_workers=4) as pool:
        data=list(pool.map(scan,current))
    data.sort(key=lambda z:z["day"])
    allrows=[n for x in data for n in x["notices"]]
    if not allrows or len({n["id"] for n in allrows})!=len(allrows):invalid("Zamora: duplicados o sin candidatas")
    total=sum(x["read"] for x in data)
    now=datetime.now(timezone.utc).isoformat()
    days=[x["day"].isoformat() for x in data]
    n=[x["number"] for x in data]
    return {"schemaVersion":1,"source":SOURCE,"province":"Zamora","lastCheckedUTC":now,
        "coverage":{"complete":True,"status":"complete","bulletin":n[-1],"pagesVisited":len(data),
            "announcementsRead":total,"opportunities":len(allrows)},
        "historyCoverage":{"complete":True,"rangeStart":start.isoformat(),"rangeEnd":end.isoformat(),
            "issuesRead":len(data),"bulletins":n,"publicationDates":days,
            "nonPublicationDates":[(start+timedelta(days=i)).isoformat() for i in range(30)
                if (start+timedelta(days=i)).isoformat() not in days],
            "editionPDFs":[x["pdf"] for x in data],"announcementsRead":total,"opportunities":len(allrows)},
        "notices":sorted(allrows,key=lambda x:(datetime.strptime(x["date"],"%d/%m/%Y"),x["id"]),reverse=True)}

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path)
    a=p.parse_args();v=audit();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"ZAMORA AUDITADO: {v['historyCoverage']['issuesRead']} boletines, "
          f"{v['coverage']['announcementsRead']} anuncios y {len(v['notices'])} candidatas",flush=True)
