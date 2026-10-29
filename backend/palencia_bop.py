#!/usr/bin/env python3
"""Palencia BOP 30-day audit. Notices from original signed full-issue PDF TOC.

The provincial site supplies complete original PDF issues. Individual PDFs are
not offered there; OpoAlert links to the signed original issue, not a made-up PDF.
"""
from __future__ import annotations
import argparse,json,re,requests,threading
import fitz
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin,urlsplit
from bs4 import BeautifulSoup
from clm_common import employment,invalid

SOURCE="https://www.diputaciondepalencia.es/servicios/boletin-oficial-provincia"
HOST="www.diputaciondepalencia.es"
PDF_RE=re.compile(r"^/system/files/bop/(\d{4})/(\d{8})-bop-(\d{1,3})-(Ordinario|Extraordinario)\.pdf$",re.I)
_TLS=threading.local()
def session():
    if not hasattr(_TLS,"s"):
        x=requests.Session();x.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es"});_TLS.s=x
    return _TLS.s
def get(url,pdf=False):
    p=urlsplit(url)
    if p.scheme!="https" or p.hostname!=HOST or p.port not in (None,443) or p.username or p.fragment:
        invalid("Palencia: URL ajena al BOP")
    try:
        r=session().get(url,timeout=(12,35),stream=False)
        if r.status_code!=200 or urlsplit(r.url).hostname!=HOST or not r.content:
            invalid(f"Palencia: HTTP {r.status_code} para {url}")
        if pdf:
            if not r.content.startswith(b"%PDF-") or "pdf" not in r.headers.get("Content-Type","").lower() or len(r.content)>22_000_000:
                invalid("Palencia: documento original no es PDF")
            return r.content
        if len(r.content)>3_000_000:invalid("Palencia: índice HTML inesperadamente grande")
        return r.text
    except requests.RequestException as e:invalid("Palencia: error de conexión "+str(e)[:155])

def index_pages(start,end):
    rows={}
    # There are 10 entries per page; a full month crosses page 1.
    for page in range(3):
        url=SOURCE+(f"?page={page}" if page else "")
        s=BeautifulSoup(get(url),"html.parser")
        anchors=[a for a in s.select('a[href*="/system/files/bop/"]') if PDF_RE.fullmatch(urlsplit(urljoin(SOURCE,a["href"])).path)]
        if page<2 and len(anchors)<8:invalid("Palencia: paginación oficial incompleta")
        for a in anchors:
            full=urljoin(SOURCE,a["href"])
            p=PDF_RE.fullmatch(urlsplit(full).path)
            d=datetime.strptime(p[2],"%Y%m%d").date()
            if p[1]!=str(d.year):invalid("Palencia: año del PDF incoherente")
            if start<=d<=end:
                key=(d,int(p[3]),p[4].lower())
                if key in rows and rows[key]!=full:invalid("Palencia: dos PDF para una edición")
                rows[key]=full
    ordered=sorted(rows.items())
    if len(ordered)<12 or (ordered[0][0][0]-start).days>3 or (end-ordered[-1][0][0]).days>3:
        invalid("Palencia: faltan ediciones del último mes")
    ords=[n for (day,n,kind),url in ordered if kind=="ordinario"]
    if any(b!=a+1 for a,b in zip(ords,ords[1:])):
        invalid("Palencia: numeración ordinaria con saltos")
    return ordered

def toc_from_pdf(pdf,day,number,kind="ordinario"):
    first=pdf[0].get_text()
    number_ok=bool(re.search(rf"\bN[úu]m\.\s*{number}\b",first,re.I)
       or (kind=="extraordinario" and re.search(rf"Boletín\s+Extraordinario\s+N[º°o]\s*{number}\b",first,re.I)))
    if (day.year!=2026 or not number_ok
        or day.strftime("%Y") not in first or "Sumario" not in first):
        invalid(f"Palencia {day}: el PDF no corresponde a su fecha y número BOP {number}, portada={first[:550]!r}")
    results=[];cur_area="Boletín Oficial de la Provincia de Palencia"
    pending=[]
    for k in range(min(4,len(pdf))):
        raw=pdf[k].get_text()
        if "Sumario" not in raw:break
        for rawline in raw.splitlines():
            line=" ".join(rawline.split())
            if not line:continue
            if ("Firmado electrónicamente" in line or "Código de Verificación" in line
                or "Se publica los lunes" in line or "BOP de Palencia" in line):
                pending.clear();continue
            m=re.search(r"(.+?)\.{6,}\s*(\d{1,3})\s*$",line)
            if m:
                title=" ".join((pending[-3:]+[m[1]]))
                title=" ".join(title.split()).strip(" .")
                pending.clear()
                page_num=int(m[2])
                if page_num<1 or page_num>len(pdf):
                    invalid(f"Palencia {day} BOP {number}: página {page_num}, PDF páginas {len(pdf)}, título {title[:160]}")
                if not title:invalid("Palencia: anuncio sin título")
                kind=employment(title)
                results.append((title,cur_area,page_num,kind))
                continue
            if line.isupper() and len(line)<110 and not re.search(r"^[0-9]+",line):
                if any(z in line for z in ("DIPUTACIÓN","AYUNTAMIENTO","JUNTA","ADMINISTRACIÓN","CONSEJERÍA","ENTIDADES LOCALES")):
                    cur_area=line
                pending.clear()
                continue
            if line.endswith(":") and len(line)<130:
                if "Servicio" in line or "JUNTA" in line or "AYUNTAMIENTOS" in line:
                    cur_area=line.strip(":")
                pending.clear()
                continue
            if line.endswith(".") and len(line)<70 and not line.startswith("Lista "):
                if len(line.split())<=8 and not any(z in line.lower() for z in ("convocatoria","proceso","bases","bolsa")):
                    if line[0].isupper():cur_area=line.rstrip(".")
                    pending.clear();continue
            if ("Miércoles," in line or "Viernes," in line or "Lunes," in line or "Sumario"==line):
                pending.clear();continue
            pending.append(line)
            if len(pending)>4:pending=pending[-4:]
    if (kind=="extraordinario" and not results and
        re.search(r"relaci[oó]n de secciones",first,re.I) and
        re.search(r"mesas y locales electorales",first,re.I) and
        re.search(r"oficina del censo electoral",first,re.I)):
        # El extraordinario 3 publica únicamente la relación censal.
        # Se cuenta su anuncio pero no se presenta como empleo público.
        results=[("Relación de Secciones, Mesas y Locales Electorales",
            "Oficina del Censo Electoral",min(2,len(pdf)),None)]
    if len(results)<(1 if kind=="extraordinario" else 2):invalid("Palencia: no se puede recuperar sumario original de anuncios")
    return results

def scan(item):
    (day,num,kind),url=item
    content=get(url,pdf=True)
    try:pdf=fitz.open(stream=content,filetype="pdf")
    except Exception:invalid("Palencia: PDF original corrupto")
    with pdf:
        data=toc_from_pdf(pdf,day,num,kind)
        notices=[]
        for index,(title,agency,page,role) in enumerate(data,1):
            if role is None:continue
            notices.append({"id":f"PL-{day:%Y%m%d}-{index:03d}","province":"Palencia",
                "title":title,"entity":agency,"date":day.strftime("%d/%m/%Y"),
                "bulletin":str(num),"type":role,"url":url+"#page="+str(page)})
    print("PALENCIA",day,kind,"BOP",num,"sumario",len(data),
        "candidatas",len(notices),flush=True)
    return {"day":day,"number":str(num),"kind":kind,"read":len(data),
        "notices":notices,"pdf":url}

def audit(today=None):
    end=today or date.today();start=end-timedelta(days=29)
    cases=index_pages(start,end)
    with ThreadPoolExecutor(max_workers=4) as pool:issues=list(pool.map(scan,cases))
    nums=[str(x["number"]) for x in issues];ds=[x["day"].isoformat() for x in issues]
    total=sum(x["read"] for x in issues)
    notices=[n for x in issues for n in x["notices"]]
    if not notices or len({n["id"] for n in notices})!=len(notices):invalid("Palencia: falta identificación de convocatorias")
    return {"schemaVersion":1,"province":"Palencia","source":SOURCE,
        "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
        "coverage":{"complete":True,"status":"complete","bulletin":nums[-1],"pagesVisited":len(issues),
            "announcementsRead":total,"opportunities":len(notices)},
        "historyCoverage":{"complete":True,"rangeStart":start.isoformat(),"rangeEnd":end.isoformat(),
            "issuesRead":len(issues),"bulletins":nums,"publicationDates":ds,
            "editionTypes":[x["kind"] for x in issues],
            "nonPublicationDates":[(start+timedelta(days=i)).isoformat() for i in range(30)
                if (start+timedelta(days=i)).isoformat() not in ds],
            "editionPDFs":[x["pdf"] for x in issues],
            "announcementsRead":total,"opportunities":len(notices),
            "pdfScope":"El PDF completo firmado es el único documento publicado por edición; el enlace identifica también la página del anuncio."},
        "notices":sorted(notices,key=lambda n:(datetime.strptime(n["date"],"%d/%m/%Y"),n["id"]),reverse=True)}
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path);a=p.parse_args()
    x=audit();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"PALENCIA AUDITADO: {x['historyCoverage']['issuesRead']} ediciones, "
      f"{x['coverage']['announcementsRead']} anuncios y {len(x['notices'])} candidatas",flush=True)
