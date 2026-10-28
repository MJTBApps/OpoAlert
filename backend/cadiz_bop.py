#!/usr/bin/env python3
"""Strict 30-day BOP Cadiz reader using official edition indexes and PDF files."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta,timezone
import json
from pathlib import Path
import re
from urllib.parse import urljoin,urlsplit,parse_qs
import requests
from bs4 import BeautifulSoup
from provincial_common import ProvincialCoverageError,classify

HOME="https://www.bopcadiz.es/"
PROVINCE="Cádiz"
ISSUE_RE=re.compile(r"/boletin/Boletin-numero-(\d{1,4})-del-ano-(\d{4})/?")
TITLE_RE=re.compile(r"Bolet[ií]n n[uú]mero\s+(\d{1,4}) del a[nñ]o\s+(\d{4})",re.I)
SUM_RE=re.compile(r"^SU-(\d{1,4})_(\d{2})-(\d{2})-(\d{2})\.pdf$",re.I)
PDF_RE=re.compile(r"^BOP(\d{1,4})_(\d{2})-(\d{2})-(\d{2})\.pdf$",re.I)
ID_RE=re.compile(r"^\s*(\d{1,3})\.(\d{3})\s*\.\s*-\s*")
PAGE_RE=re.compile(r"page=(\d{1,5})")
DATE_STAMP_RE=re.compile(r"\b(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)\s+([A-Za-z]{3})\s+(\d{1,2})\s+\d{2}:\d{2}:\d{2}\s+(?:CET|CEST)\s+(\d{4})")
SPANISH_DATE_RE=re.compile(r"\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})\b",re.I)
SPANISH_MONTHS={name:i for i,name in enumerate(("enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre"),1)}
PATH_PREFIX="/export/sites/default/.boletines_pdf/"
OFFICIAL_HOST="www.bopcadiz.es"
HTTP_TIMEOUT=(10,26)

def official_session()->requests.Session:
    s=requests.Session()
    s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert Cadiz official archive audit/1.11)",
                      "Accept-Language":"es"})
    return s

def validate_doc(url:str)->bool:
    try:
        p=urlsplit(url)
        m=PAGE_RE.fullmatch(p.fragment)
        return (p.scheme=="https" and p.hostname==OFFICIAL_HOST and p.port is None
            and p.username is None and p.password is None and not p.query
            and p.path.startswith(PATH_PREFIX) and PDF_RE.fullmatch(p.path.rsplit("/",1)[-1]) is not None
            and m is not None and int(m.group(1))<=1500)
    except (TypeError,ValueError):return False

def validate_full_pdf(url:str)->bool:
    p=urlsplit(url)
    return (p.scheme=="https" and p.hostname==OFFICIAL_HOST and p.port is None
        and p.username is None and p.password is None and not p.query and not p.fragment
        and p.path.startswith("/.boletines_pdf/")
        and PDF_RE.fullmatch(p.path.rsplit("/",1)[-1]) is not None)

def get(session:requests.Session,url:str)->requests.Response:
    if not url.startswith(HOME) or urlsplit(url).hostname!=OFFICIAL_HOST:
        raise ProvincialCoverageError("Cadiz: fuente HTTP no oficial")
    for attempt in range(3):
        try:
            r=session.get(url,timeout=HTTP_TIMEOUT)
            if r.status_code!=200 or r.url!=url or not r.content or len(r.content)>2_000_000:
                raise ProvincialCoverageError(f"Cadiz: error HTTP/index oficial {r.status_code}")
            if "html" not in r.headers.get("Content-Type","").lower():
                raise ProvincialCoverageError("Cadiz: no se recibio HTML oficial")
            return r
        except requests.RequestException as ex:
            if attempt==2:raise ProvincialCoverageError(f"Cadiz: boletin inaccesible {url}: {ex}") from ex
    raise ProvincialCoverageError("Cadiz: consulta oficial no disponible")

def check_pdf(session:requests.Session,url:str)->None:
    if not validate_full_pdf(url):
        raise ProvincialCoverageError("Cadiz: URL PDF ajena a sede oficial")
    try:
        r=session.get(url,headers={"Range":"bytes=0-160"},stream=True,timeout=HTTP_TIMEOUT)
        try:
            if (r.status_code not in (200,206) or r.url!=url
                or "pdf" not in r.headers.get("Content-Type","").lower()
                or not next(r.iter_content(chunk_size=160),b"").startswith(b"%PDF-")):
                raise ProvincialCoverageError(f"Cadiz: PDF original no disponible {url}")
        finally:r.close()
    except requests.RequestException as ex:
        raise ProvincialCoverageError(f"Cadiz: fallo PDF original {url}: {ex}") from ex

def available_issues(html:str)->tuple[int,dict[int,str]]:
    soup=BeautifulSoup(html,"html.parser")
    heading=soup.find("h2",string=TITLE_RE)
    if not heading:
        raise ProvincialCoverageError("Cadiz: pagina inicial sin boletin vigente")
    m=TITLE_RE.fullmatch(heading.get_text(" ",strip=True))
    if m is None:raise ProvincialCoverageError("Cadiz: boletin de portada invalido")
    year=int(m.group(2))
    if year!=date.today().year:
        raise ProvincialCoverageError("Cadiz: portada no corresponde al ejercicio vigente")
    active=int(m.group(1))
    found={}
    for a in soup.select("a[href]"):
        href=a.get("href","")
        hit=ISSUE_RE.fullmatch(href)
        if hit and int(hit.group(2))==year:
            number=int(hit.group(1))
            found[number]=urljoin(HOME,href)
    if not found or active not in found or max(found)!=active:
        raise ProvincialCoverageError("Cadiz: calendario de boletines incompleto en portada")
    indices=list(range(min(found),active+1))
    if set(indices)!=set(found):
        raise ProvincialCoverageError("Cadiz: hay saltos en el calendario de boletines")
    return active,found

def parse_issue(html:str,year:int,number:int)->dict:
    soup=BeautifulSoup(html,"html.parser")
    heading=soup.find("h2",string=TITLE_RE)
    if not heading:
        raise ProvincialCoverageError(f"Cadiz BOP {number}: falta titulo de edicion")
    match=TITLE_RE.fullmatch(heading.get_text(" ",strip=True))
    if match is None or (int(match.group(1)),int(match.group(2)))!=(number,year):
        raise ProvincialCoverageError(f"Cadiz BOP {number}: numero/año no verificados")
    # Full edition PDF and independent issue date encoded by the Diputacion.
    issue_pdf=[]
    sum_pdf=[]
    for a in soup.select("a[href]"):
        raw=a.get("href","")
        url=urljoin(HOME,raw)
        label=a.get_text(" ",strip=True)
        if label=="Boletín PDF" and validate_full_pdf(url):
            issue_pdf.append(url)
        elif label=="Sumario PDF":
            sum_pdf.append(url)
    if len(issue_pdf)!=1 or len(sum_pdf)!=1:
        raise ProvincialCoverageError(f"Cadiz BOP {number}: PDFs del indice/boletin no identificados")
    pdf=issue_pdf[0]
    pm=PDF_RE.fullmatch(urlsplit(pdf).path.rsplit("/",1)[-1])
    sm=SUM_RE.fullmatch(urlsplit(sum_pdf[0]).path.rsplit("/",1)[-1])
    if not pm or not sm or (pm.group(1),pm.group(2),pm.group(3),pm.group(4))!=(
        sm.group(1),sm.group(2),sm.group(3),sm.group(4)):
        raise ProvincialCoverageError(f"Cadiz BOP {number}: indice y boletin no corresponden")
    if int(pm.group(1))!=number:
        raise ProvincialCoverageError(f"Cadiz BOP {number}: nombre PDF de otra edicion")
    day=date(2000+int(pm.group(4)),int(pm.group(3)),int(pm.group(2)))
    if day.year!=year:
        raise ProvincialCoverageError(f"Cadiz BOP {number}: año fecha incorrecto")
    stamp=soup.select_one("p.fecha")
    published=stamp.get_text(" ",strip=True) if stamp else ""
    english=DATE_STAMP_RE.search(published)
    spanish=SPANISH_DATE_RE.search(published)
    if english:
        try:official_day=datetime.strptime(f"{english.group(1)} {english.group(2)} {english.group(3)}","%b %d %Y").date()
        except ValueError as ex:raise ProvincialCoverageError("Cadiz: fecha HTML invalida") from ex
    elif spanish:
        official_day=date(int(spanish.group(3)),SPANISH_MONTHS[spanish.group(2).lower()],int(spanish.group(1)))
    else:
        raise ProvincialCoverageError(f"Cadiz BOP {number}: cabecera sin fecha oficial {published[:130]!r}")
    if official_day!=day:
        raise ProvincialCoverageError(f"Cadiz BOP {number}: fecha HTML difiere del PDF oficial")
    # Only read the article body between edition h2 and calendar h2.
    records=[]
    category=None
    finished=False
    for el in heading.find_all_next(["h2","h3","p"]):
        if el.name=="h2":
            finished=True
            if "Calendario de boletines" not in el.get_text(" ",strip=True):
                raise ProvincialCoverageError(f"Cadiz BOP {number}: contenido no reconocido")
            break
        if el.name=="h3":
            category=el.get_text(" ",strip=True)
            continue
        a=el.select_one('a[href*="/export/sites/default/.boletines_pdf/"]')
        if a is None:continue
        if not category:
            raise ProvincialCoverageError(f"Cadiz BOP {number}: anuncio sin seccion")
        full=a.get_text(" ",strip=True)
        code=ID_RE.match(full)
        agency_cell=a.select_one("strong")
        agency=agency_cell.get_text(" ",strip=True) if agency_cell else ""
        # Keep the primary sender separately, while preserving the complete
        # official bulletin summary as title for reliable candidate screening.
        agency=ID_RE.sub("",agency).strip(" .-\t")
        original=urljoin(HOME,a.get("href",""))
        if not code or not agency or not validate_doc(original):
            raise ProvincialCoverageError(f"Cadiz BOP {number}: anuncio sin ID, organismo o PDF")
        if urlsplit(original).path!=urlsplit(pdf).path.replace("/.boletines_pdf/","/export/sites/default/.boletines_pdf/",1):
            raise ProvincialCoverageError(f"Cadiz BOP {number}: enlace a PDF de otro boletin")
        ident=f"CA-{year}-{code.group(1)}{code.group(2)}".replace("CA-"+str(year)+"-0","CA-"+str(year)+"-0")
        if not re.fullmatch(r"CA-\d{4}-\d{4,7}",ident):
            raise ProvincialCoverageError(f"Cadiz BOP {number}: referencia irregular {ident}")
        title=full[code.end():].strip(" .-\t")
        if not title or agency.casefold() not in title.casefold():
            # Some sources trim the first emitter from the header.
            title=full
        records.append({
            "id":ident,"title":title,"entity":agency,
            "url":original,"section":category,
        })
    if not finished or not records:
        raise ProvincialCoverageError(f"Cadiz BOP {number}: falta indice oficial de anuncios")
    if len({x["id"] for x in records})!=len(records):
        raise ProvincialCoverageError(f"Cadiz BOP {number}: anuncio duplicado")
    candidates=[]
    for rec in records:
        kind=classify(rec["title"])
        if kind is None:continue
        candidates.append({
           "id":rec["id"],"province":PROVINCE,"title":rec["title"],
           "entity":rec["entity"],"date":day.strftime("%d/%m/%Y"),
           "bulletin":str(number),"type":kind,"url":rec["url"],
        })
    return {"number":number,"date":day,"count":len(records),"candidates":candidates,
            "sections":list(dict.fromkeys(x["section"] for x in records)),
            "pdf":pdf}

def scan_issue(number:int,year:int,session_factory=official_session)->dict:
    session=session_factory()
    try:
        url=f"{HOME}boletin/Boletin-numero-{number}-del-ano-{year}/"
        data=parse_issue(get(session,url).text,year,number)
        check_pdf(session,data["pdf"])
        return data
    finally:session.close()

def audit(days:int=30,today:date|None=None,scanner=scan_issue,session_factory=official_session)->dict:
    if days!=30:raise ProvincialCoverageError("Cadiz: se exige historial de 30 dias")
    end=today or date.today()
    start=end-timedelta(days=29)
    s=session_factory()
    try:latest,all_issues=available_issues(get(s,HOME).text)
    finally:s.close()
    year=end.year
    # Annual index is ordered by BOP number, every issue must be traversed.
    # Include 35 previous issues to prove the 30-day boundary rather than
    # guessing whether holidays or weekends published.
    to_check=sorted([n for n in all_issues if n>=latest-35])
    if not to_check or len(to_check)<20:
        raise ProvincialCoverageError("Cadiz: calendario insuficiente para 30 dias")
    def checked(number):
        try:return scanner(number,year),None
        except (ProvincialCoverageError,requests.RequestException,ValueError) as ex:
            return None,str(ex)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(checked,to_check))
    errors=[]
    all_rows=[]
    for number,(issue,error) in zip(to_check,results):
        if error:
            errors.append(f"{number}: {error}")
            print(f"Cadiz BOP {number}: ERROR {error}",flush=True)
            continue
        if issue is None or issue["number"]!=number or issue["count"]<len(issue["candidates"]):
            raise ProvincialCoverageError(f"Cadiz: BOP {number} incoherente")
        all_rows.append(issue)
        print(f"Cadiz BOP {number} {issue['date']}: {issue['count']} anuncios, "
              f"{len(issue['candidates'])} candidatas",flush=True)
    if errors:
        raise ProvincialCoverageError("Cadiz: BOPs sin verificar: "+" | ".join(errors))
    if not all_rows or all_rows[-1]["number"]!=latest:
        raise ProvincialCoverageError("Cadiz: no coincide con ultima edicion")
    if not any(x["date"]<start for x in all_rows):
        raise ProvincialCoverageError("Cadiz: no se ha probado el limite anterior de 30 dias")
    chosen=[x for x in all_rows if start<=x["date"]<=end]
    if len(chosen)<15 or chosen[-1]["number"]!=latest:
        raise ProvincialCoverageError("Cadiz: faltan boletines en los ultimos 30 dias")
    if any(a["date"]>=b["date"] for a,b in zip(chosen,chosen[1:])):
        raise ProvincialCoverageError("Cadiz: boletines en fecha incorrecta o duplicada")
    if any(b["number"]!=a["number"]+1 for a,b in zip(chosen,chosen[1:])):
        raise ProvincialCoverageError("Cadiz: numeracion BOP incompleta")
    nums={x["number"] for x in chosen}
    if nums!={n for n in all_issues if min(nums)<=n<=latest}:
        raise ProvincialCoverageError("Cadiz: no coinciden boletines con calendario")
    found=[n for x in chosen for n in x["candidates"]]
    if not found or len({n["id"] for n in found})!=len(found):
        raise ProvincialCoverageError("Cadiz: convocatorias vacias o repetidas")
    found.sort(key=lambda r:(datetime.strptime(r["date"],"%d/%m/%Y"),r["id"]),reverse=True)
    total=sum(x["count"] for x in chosen)
    pubdays={x["date"].isoformat() for x in chosen}
    absent=[(start+timedelta(days=i)).isoformat() for i in range(30)
            if (start+timedelta(days=i)).isoformat() not in pubdays]
    return {"schemaVersion":1,"source":HOME,"province":PROVINCE,
      "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
      "coverage":{"complete":True,"status":"complete",
        "bulletin":str(latest),"announcementsRead":total,
        "opportunities":len(found),"pagesVisited":len(chosen)},
      "historyCoverage":{"complete":True,"rangeStart":start.isoformat(),
         "rangeEnd":end.isoformat(),"issuesRead":len(chosen),
         "announcementsRead":total,"opportunities":len(found),
         "pagesVisited":len(chosen),
         "bulletins":[str(x["number"]) for x in chosen],
         "publicationDates":[x["date"].isoformat() for x in chosen],
         "nonPublicationDates":absent,
         "sectionsRead":sorted({s for x in chosen for s in x["sections"]})},
      "notices":found}

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--days",type=int,default=30)
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    feed=audit(args.days)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(feed,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"CADIZ OK {feed['historyCoverage']['issuesRead']} boletines "
          f"{feed['coverage']['announcementsRead']} anuncios "
          f"{len(feed['notices'])} candidatas",flush=True)
