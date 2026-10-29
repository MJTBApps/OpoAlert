#!/usr/bin/env python3
"""Verified Boletín Oficial de Córdoba, reading every official daily index and PDF."""
from __future__ import annotations
import argparse,json,re,time
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit,urljoin
import requests
from bs4 import BeautifulSoup
from provincial_common import ProvincialCoverageError,classify

HOME="https://bop.dipucordoba.es/"
HOST="bop.dipucordoba.es"
PROVINCE="Córdoba"
HEADER_RE=re.compile(r"BOLET[IÍ]N\s+n[uú]mero\s+(\d{1,3})",re.I)
PDF_RE=re.compile(r"^/visor-pdf/(\d{2})-(\d{2})-(\d{4})/BOP-([AS])-(\d{4})-(\d{1,7})\.pdf$")
TITLE_RE=re.compile(r"Boletín Oficial de la Provincia de Córdoba del día (\d{2}-\d{2}-\d{4})")

def day_url(day:date)->str:
    return f"{HOME}dia/{day:%d-%m-%Y}"

def pdf_valid(url:str,day:date,kind:str="A")->tuple[bool,str]:
    p=urlsplit(url)
    m=PDF_RE.fullmatch(p.path)
    if not (m and p.scheme=="https" and p.hostname==HOST and p.port in (None,443)
        and not p.username and not p.password and not p.query and not p.fragment
        and m.group(4)==kind and int(m.group(5))==day.year
        and (int(m.group(3)),int(m.group(2)),int(m.group(1)))==(day.year,day.month,day.day)):
        return False,""
    return True,m.group(6)

def request(url:str,pdf:bool=False)->requests.Response:
    p=urlsplit(url)
    if not (p.scheme=="https" and p.hostname==HOST and p.port in (None,443)
        and p.username is None and p.password is None and not p.query and not p.fragment
        and (re.fullmatch(r"/dia/\d{2}-\d{2}-\d{4}",p.path) or
             re.fullmatch(r"/visor-pdf/\d{2}-\d{2}-\d{4}/BOP-[AS]-\d{4}-\d{1,7}\.pdf",p.path))):
        raise ProvincialCoverageError("Córdoba: enlace ajeno al BOP oficial")
    error=None
    for i in range(2):
        try:
            r=requests.get(url,stream=pdf,timeout=(10,35),allow_redirects=True,
                headers={"User-Agent":"Mozilla/5.0 (compatible; OpoAlert verified BOP)"})
            if r.status_code!=200 or urlsplit(r.url).hostname!=HOST:
                status=r.status_code;r.close()
                raise ProvincialCoverageError(f"Córdoba: portal oficial HTTP {status}")
            if not pdf and (not r.content or len(r.content)>1_500_000):
                raise ProvincialCoverageError("Córdoba: HTML de boletín vacío o excesivo")
            return r
        except (requests.RequestException,ProvincialCoverageError) as exc:
            error=exc
            if i==0:time.sleep(0.5)
    raise ProvincialCoverageError(f"Córdoba: no se pudo leer {url}: {error}")

def check_pdf(url:str,day:date,kind:str="A")->None:
    if not pdf_valid(url,day,kind)[0]:
        raise ProvincialCoverageError("Córdoba: PDF no pertenece a esa fecha/edicion")
    response=request(url,pdf=True)
    try:
        first=next(response.iter_content(chunk_size=60),b"")
        if "pdf" not in response.headers.get("Content-Type","").lower() or not first.startswith(b"%PDF-"):
            raise ProvincialCoverageError("Córdoba: el documento original no es PDF")
    finally:response.close()

def parse_issue(html:str,day:date)->dict|None:
    soup=BeautifulSoup(html,"html.parser")
    title=soup.title.get_text(" ",strip=True) if soup.title else ""
    t=TITLE_RE.search(title)
    if t is None or t.group(1)!=day.strftime("%d-%m-%Y"):
        raise ProvincialCoverageError(f"Córdoba {day}: no coincide fecha publicada en el portal")
    header=next((x for x in soup.select("h2") if HEADER_RE.fullmatch(x.get_text(" ",strip=True))),None)
    # The official Next.js portal serves an empty page for non-publication days.
    if header is None:
        if soup.select("li.announcement") or soup.select('a[href*="/visor-pdf/"]'):
            raise ProvincialCoverageError(f"Córdoba {day}: numero BOP ausente en pagina con anuncios")
        return None
    m=HEADER_RE.fullmatch(header.get_text(" ",strip=True))
    if m is None:raise ProvincialCoverageError("Córdoba: número de BOP ilegible")
    number=int(m.group(1))
    if number<1 or number>366:raise ProvincialCoverageError("Córdoba: número imposible")
    summary=[urljoin(HOME,a["href"]) for a in soup.select('a[href*="/visor-pdf/"]')
             if pdf_valid(urljoin(HOME,a["href"]),day,"S")[0]]
    if len(set(summary))!=1 or not summary[0].endswith(f"/BOP-S-{day.year}-{number}.pdf"):
        raise ProvincialCoverageError(f"Córdoba {day}: no existe sumario oficial de este numero")
    rows=[]
    for li in soup.select("li.announcement"):
        a=li.select_one('a.pdf[href*="/visor-pdf/"]')
        first=li.find("p")
        parent=li.find_parent("li",class_="emisor")
        emitter=parent.find("h2",recursive=False) if parent else None
        if a is None or first is None or emitter is None:
            raise ProvincialCoverageError(f"Córdoba {day}: faltan título, emisor o PDF")
        name=first.get_text(" ",strip=True)
        agency=emitter.get_text(" ",strip=True)
        link=urljoin(HOME,a["href"])
        valid,number_id=pdf_valid(link,day)
        if (not valid or not name or not agency or len(name)>2500 or len(agency)>250
            or not a.get_text(" ",strip=True).endswith(f"BOP-A-{day.year}-{number_id}")):
            raise ProvincialCoverageError(f"Córdoba {day}: anuncio no comprobado PDF={link} emisor={agency[:100]!r} titulo={name[:130]!r} enlace={a.get_text(' ',strip=True)!r} identificador={number_id!r}")
        rows.append({"id":f"CO-{day.year}-{int(number_id)}",
          "province":PROVINCE,"title":name,"entity":agency,
          "date":day.strftime("%d/%m/%Y"),"bulletin":str(number),
          "type":classify(name),"url":link})
    if len(rows)<1 or len({x["id"] for x in rows})!=len(rows):
        raise ProvincialCoverageError(f"Córdoba {day}: índice de anuncios vacío o duplicado")
    return {"date":day,"number":number,"read":len(rows),"rows":rows,"summary":summary[0]}

def render_streamed(day:date)->str:
    """Next.js streams some orphaned <li> elements; use a real rendered DOM."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(headless=True,args=["--no-sandbox"])
        try:
            page=browser.new_page(locale="es-ES")
            page.goto(day_url(day),wait_until="domcontentloaded",timeout=45000)
            page.wait_for_timeout(1800)
            return page.content()
        finally:
            browser.close()

def scan(day:date)->dict|None:
    html=request(day_url(day)).text
    try:
        parsed=parse_issue(html,day)
    except ProvincialCoverageError as ex:
        if ("faltan título, emisor o PDF" not in str(ex)
            and "numero BOP ausente" not in str(ex)):
            raise
        parsed=parse_issue(render_streamed(day),day)
    if parsed is None and day.weekday()<5:
        parsed=parse_issue(render_streamed(day),day)
    if parsed is None:return None
    check_pdf(parsed["summary"],day,"S")
    notices=[]
    for row in parsed["rows"]:
        if row["type"] is None:continue
        check_pdf(row["url"],day)
        notices.append(row)
    return {"date":day,"number":parsed["number"],"read":parsed["read"],
       "pages":1,"notices":notices,"pdf":parsed["summary"]}

def audit(days:int=30,today:date|None=None,reader=scan)->dict:
    if days!=30:raise ProvincialCoverageError("Córdoba: auditoría obligatoria de 30 días")
    end=today or date.today()
    start=end-timedelta(days=29)
    dates=[start+timedelta(days=i) for i in range(30)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        entries=list(pool.map(reader,dates))
    issues=[];missing=[]
    for day,row in zip(dates,entries):
        if row is None:
            missing.append(day.isoformat());continue
        if (row["date"]!=day or row["read"]<len(row["notices"])
           or row["pages"]!=1 or not pdf_valid(row["pdf"],day,"S")[0]):
            raise ProvincialCoverageError(f"Córdoba {day}: resultados incoherentes")
        if issues and row["number"]!=issues[-1]["number"]+1:
            raise ProvincialCoverageError(f"Córdoba: falta número entre BOP "
               f"{issues[-1]['number']} y {row['number']}")
        if issues and (day-issues[-1]["date"]).days>5:
            raise ProvincialCoverageError("Córdoba: faltan fechas de publicación")
        issues.append(row)
        print("Cordoba",day,"BOP",row["number"],"anuncios",row["read"],
           "candidatas",len(row["notices"]),flush=True)
    if (len(issues)<15 or (issues[0]["date"]-start).days>4
        or (end-issues[-1]["date"]).days>4):
        raise ProvincialCoverageError("Córdoba: ediciones insuficientes")
    notices=[x for row in issues for x in row["notices"]]
    if not notices or len({x["id"] for x in notices})!=len(notices):
        raise ProvincialCoverageError("Córdoba: no hay candidatas o anuncios duplicados")
    notices.sort(key=lambda n:(datetime.strptime(n["date"],"%d/%m/%Y"),n["id"]),reverse=True)
    read=sum(i["read"] for i in issues)
    pages=len(issues)
    return {"schemaVersion":1,"source":HOME,"province":PROVINCE,
      "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
      "coverage":{"complete":True,"status":"complete","bulletin":str(issues[-1]["number"]),
         "pagesVisited":pages,"announcementsRead":read,"opportunities":len(notices)},
      "historyCoverage":{"complete":True,"rangeStart":start.isoformat(),
         "rangeEnd":end.isoformat(),"issuesRead":len(issues),"pagesVisited":pages,
         "announcementsRead":read,"opportunities":len(notices),
         "bulletins":[str(i["number"]) for i in issues],
         "publicationDates":[i["date"].isoformat() for i in issues],
         "nonPublicationDates":missing,"editionPDFs":[i["pdf"] for i in issues]},
      "notices":notices}

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--days",type=int,default=30)
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    out=audit(args.days)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(f"CORDOBA AUDITADA: {out['historyCoverage']['issuesRead']} ediciones, "
      f"{out['coverage']['announcementsRead']} anuncios, {len(out['notices'])} candidatas",flush=True)
