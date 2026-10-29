#!/usr/bin/env python3
"""Official Almeria/Jaen provincial BOP reader through the Diputaciones' Pandora archives.

Both publishers run an official Pandora archive that exposes a complete issue
index, original PDF and publisher-supplied OCR text at text.vm. No third-party
search aggregators and no computer generated OCR. The issue's summary IDs must
match the IDs in its full body. Fail closed on gaps, truncated lists or PDFs.

Almeria's old Domino index is removed; Jaen's main BOP is returning 500,
but the publishers' official digitized editions remain public and up to date.
"""
from __future__ import annotations
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date,datetime,timedelta,timezone
import json
from math import ceil
from pathlib import Path
import re
from urllib.parse import urlsplit,parse_qs,urljoin
import requests
from bs4 import BeautifulSoup
from provincial_common import ProvincialCoverageError,classify,fold

@dataclass(frozen=True)
class Gazette:
    name:str
    code:str
    host:str
    folder:str
    view:str
    archive_id:str
    count_root:int
    almeria:bool

ALMERIA=Gazette("Almería","AM","app.dipalme.org","/pandora/","boletines","0000010919",0,True)
JAEN=Gazette("Jaén","JA","bophistorico.dipujaen.es","/","boletin","0000395018",0,False)
GAZETTES={"almeria":ALMERIA,"jaen":JAEN}
DATE_RE=re.compile(r"\b(\d{1,2})/(\d{1,2})/(\d{4})\b")
PAGES_RE=re.compile(r"\((\d{1,4}) p[aá]ginas?\b",re.I)
COUNT_RE=re.compile(r"Resultados:\s*([\d.]+)",re.I)
NUMBER_RE=re.compile(r"\bN[uú]mero:\?\s*(\d{1,3})\b",re.I)
# Some OCR editions use "Número 191" without a colon.
NUMBER_RE=re.compile(r"\bN[uú]mero\s*:?\s*(\d{1,3})\b",re.I)
YEAR_CODE=re.compile(r"(?:20\d{2})")
MONTHS={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
        "julio":7,"agosto":8,"septiembre":9,"setiembre":9,"octubre":10,
        "noviembre":11,"diciembre":12}
AL_BODY=re.compile(r"(?m)^[ \t]*(\d{3,5})/(\d{2})\b")
JA_BODY=re.compile(r"(?m)^[ \t]*(\d{4})/(\d{3,5})\b")
AL_SUMMARY=re.compile(r"\b0*(\d{3,5})-([0-9]{2})\b")
JA_SUMMARY=re.compile(r"\bBOP-(\d{4})-(\d{3,5})\b",re.I)
JA_AGENCY=re.compile(
    r"^(?:AYUNTAMIENTO|DIPUTACI[ÓO]N|ENTIDAD LOCAL|CONSORCIO|MANCOMUNIDAD|"
    r"ORGANISMO AUT[ÓO]NOMO|JUNTA DE ANDALUC[ÍI]A|UNIVERSIDAD|"
    r"C[ÁA]MARA OFICIAL|COMARCA)\b",re.I)
AL_AGENCY=re.compile(
    r"(?:AYUNTAMIENTO|DIPUTACI[ÓO]N|MANCOMUNIDAD|CONSORCIO|"
    r"JUNTA DE ANDALUC[ÍI]A|ENTIDAD LOCAL|UNIVERSIDAD|"
    r"C[ÁA]MARA OFICIAL|COMUNIDAD DE REGANTES|TRIBUNAL|MINISTERIO)\b",re.I)

def archive_url(g:Gazette)->str:
    return f"https://{g.host}{g.folder}results.vm?q=parent:{g.archive_id}&view={g.view}"

def session()->requests.Session:
    s=requests.Session()
    s.headers.update({
        "User-Agent":"Mozilla/5.0 (compatible; OpoAlert verified provincial archive 1.12)",
        "Accept-Language":"es",
    })
    return s

def get(s:requests.Session,url:str,params:dict|None=None,stream:bool=False)->requests.Response:
    expected_host=urlsplit(url).hostname
    if expected_host not in (ALMERIA.host,JAEN.host) or urlsplit(url).scheme!="https":
        raise ProvincialCoverageError("Andalucía: fuente fuera de hemeroteca oficial")
    for i in range(3):
        try:
            r=s.get(url,params=params,stream=stream,timeout=(12,34),allow_redirects=True)
            if r.status_code!=200 or urlsplit(r.url).hostname!=expected_host:
                raise ProvincialCoverageError(f"Andalucía: portal oficial HTTP {r.status_code}")
            if not stream and (not r.content or len(r.content)>2_500_000):
                raise ProvincialCoverageError("Andalucía: archivo de texto no valido")
            return r
        except requests.RequestException as ex:
            if i==2:raise ProvincialCoverageError(f"Andalucía: error de conexión {ex}") from ex
    raise ProvincialCoverageError("Andalucía: error inesperado")

def pdf_url(g:Gazette,raw:str)->tuple[str,str]:
    """Normalize and whitelist official high.raw PDF links from index HTML."""
    u=urljoin(f"https://{g.host}{g.folder}",raw)
    p=urlsplit(u)
    qs=parse_qs(p.query)
    keys=set(qs)
    if (p.scheme!="https" or p.hostname!=g.host or p.port not in (None,443)
        or p.username is not None or p.password is not None or p.fragment
        or p.path!=g.folder+"high.raw"
        or not {"id","name"}<=keys or not keys<={"id","name","attachment"}
        or len(qs["id"])!=1 or not re.fullmatch(r"\d{8,10}",qs["id"][0])
        or qs.get("name")!=["00000001.original.pdf"]
        or not qs.get("attachment",["file.pdf"])[0].lower().endswith(".pdf")):
        raise ProvincialCoverageError(f"{g.name}: PDF fuera de hemeroteca oficial: {u[:150]}")
    return u,qs["id"][0]

def text_url(g:Gazette,id_:str)->str:
    if not re.fullmatch(r"\d{8,10}",id_):
        raise ProvincialCoverageError(f"{g.name}: id de edición incorrecto")
    return f"https://{g.host}{g.folder}text.vm?id={id_}&view={g.view}"

def issue_entry(g:Gazette,card)->dict:
    title=card.get_text(" ",strip=True)
    matches=set(DATE_RE.findall(title))
    pm=PAGES_RE.search(title)
    a=card.find("a",href=re.compile(r"^high\.raw\?"))
    if len(matches)!=1 or not pm or a is None:
        raise ProvincialCoverageError(f"{g.name}: ficha de edición sin fecha/páginas/PDF")
    day=date(*reversed([int(n) for n in next(iter(matches))]))
    pages=int(pm.group(1))
    if not 1<=pages<=600:raise ProvincialCoverageError(f"{g.name}: tamaño BOP inverosimil")
    url,id_=pdf_url(g,a["href"])
    # Pandora stable internal document ID equals the index card identifier.
    if card.get("id")!=f"frame-{id_}":
        raise ProvincialCoverageError(f"{g.name}: identificador de edición incorrecto")
    return {"date":day,"pdf":url,"id":id_,"pages":pages}

def index_page(g:Gazette,html:str,expected_total:int|None=None)->tuple[int,list[dict]]:
    soup=BeautifulSoup(html,"html.parser")
    label=soup.select_one("form#wide-sheet")
    if label is None or fold(g.name) not in fold(soup.title.get_text(" ",strip=True) if soup.title else ""):
        raise ProvincialCoverageError(f"{g.name}: índice HTML no corresponde a hemeroteca oficial")
    match=COUNT_RE.search(soup.get_text(" ",strip=True))
    if not match:raise ProvincialCoverageError(f"{g.name}: total de ediciones no encontrado")
    total=int(match.group(1).replace(".",""))
    if not 1000<total<100_000 or (expected_total is not None and total!=expected_total):
        raise ProvincialCoverageError(f"{g.name}: total de ediciones cambiante o imposible")
    cards=soup.select("div.list-frame")
    if not 1<=len(cards)<=15:
        raise ProvincialCoverageError(f"{g.name}: paginación del índice incompleta")
    entries=[issue_entry(g,card) for card in cards]
    if len({x["id"] for x in entries})!=len(entries) or entries!=sorted(entries,key=lambda x:x["date"]):
        raise ProvincialCoverageError(f"{g.name}: fechas o identificadores duplicados")
    return total,entries

def fetch_index(g:Gazette,start:date,end:date,s:requests.Session)->tuple[list[dict],int,int]:
    # This archive's original order is chronological with 15 cards per page.
    # Start from last page, then walk backward until 30-day start is covered.
    base=archive_url(g)
    total,first=index_page(g,get(s,base).text)
    offset=((total-1)//15)*15
    visited=0
    all_entries=[]
    while visited<12:
        _,items=index_page(g,get(s,base,{"s":offset}).text,total)
        expected=min(15,total-offset)
        if len(items)!=expected:
            raise ProvincialCoverageError(f"{g.name}: índice truncado en página {offset}")
        if all_entries and items[-1]["date"]>=all_entries[0]["date"]:
            raise ProvincialCoverageError(f"{g.name}: salto o duplicación en índice de ediciones")
        all_entries=items+all_entries
        visited+=1
        if all_entries[0]["date"]<=start:break
        if offset==0:raise ProvincialCoverageError(f"{g.name}: no alcanza fecha inicial de auditoria")
        offset=max(0,offset-15)
    else:raise ProvincialCoverageError(f"{g.name}: demasiadas páginas sin alcanzar inicio")
    if not all_entries or all_entries[-1]["date"]>end or (end-all_entries[-1]["date"]).days>4:
        raise ProvincialCoverageError(f"{g.name}: última edición ausente/desactualizada")
    if all_entries[0]["date"]>start:
        raise ProvincialCoverageError(f"{g.name}: inicio histórico no encontrado")
    selected=[x for x in all_entries if start<=x["date"]<=end]
    if len(selected)<15 or len({x["date"] for x in selected})!=len(selected):
        raise ProvincialCoverageError(f"{g.name}: faltan ediciones o fechas repetidas")
    return selected,total,visited

def parse_date_header(g:Gazette,txt:str,day:date)->int:
    lines=[x.strip() for x in txt.splitlines()[:12] if x.strip()]
    header=" ".join(lines)
    m=NUMBER_RE.search(header)
    datere=re.search(r"(\d{1,2}) de ([A-Za-záéíóúñÁÉÍÓÚÑ]+) de (\d{4})",header,re.I)
    month=MONTHS.get(fold(datere.group(2))) if datere else None
    if (m is None or datere is None or month is None
        or date(int(datere.group(3)),month,int(datere.group(1)))!=day):
        raise ProvincialCoverageError(f"{g.name}: cabecera OCR no corresponde a {day}")
    number=int(m.group(1))
    if not 1<=number<=366:
        raise ProvincialCoverageError(f"{g.name}: numero de BOP imposible")
    if g.almeria and not re.search(r"Bolet[ií]n Oficial de la Provincia de "+g.name,txt[:3000],re.I):
        # Jaen's first page can have a compact header; confirmation on issue archive remains.
        raise ProvincialCoverageError(f"{g.name}: nombre de boletin oficial ausente")
    return number

def split_ocr(g:Gazette,text:str,day:date)->tuple[list[dict],int]:
    """Match original publication IDs in official sumario and full body, 1:1."""
    if len(text)<200 or len(text)>2_500_000:
        raise ProvincialCoverageError(f"{g.name} {day}: OCR vacío o demasiado grande")
    line_regex=AL_BODY if g.almeria else JA_BODY
    matches=list(line_regex.finditer(text))
    correct=[]
    year_suffix=day.year%100
    for m in matches:
        year=int(m.group(2)) if g.almeria else int(m.group(1))
        code=int(m.group(1)) if g.almeria else int(m.group(2))
        if year == (year_suffix if g.almeria else day.year):
            correct.append((m,code))
    if not correct:
        raise ProvincialCoverageError(f"{g.name} {day}: OCR sin edictos del anio")
    first=correct[0][0].start()
    summary=text[:first]
    smatches=AL_SUMMARY.findall(summary) if g.almeria else JA_SUMMARY.findall(summary)
    expected=[int(code) for code,year in smatches if int(year)==year_suffix] if g.almeria else [
        int(code) for year,code in smatches if int(year)==day.year]
    if not expected or len(set(expected))!=len(expected):
        raise ProvincialCoverageError(f"{g.name} {day}: sumario OCR no legible o códigos duplicados")
    # Other lines in the document may refer to unrelated resolutions like
    # 2026/747; only codes printed in the original issue summary count.
    correct=[(m,code) for m,code in correct if code in set(expected)]
    seen=[code for _,code in correct]
    if set(expected)!=set(seen) or len(seen)!=len(set(seen)):
        missing=set(expected)-set(seen)
        extra=set(seen)-set(expected)
        raise ProvincialCoverageError(f"{g.name} {day}: sumario/cuerpo OCR no coincide, faltan {sorted(missing)[:9]}, extra {sorted(extra)[:9]}")
    notices=[]
    # Preserve all original edict numbers and match the preceding official issuer.
    for i,(match,code) in enumerate(correct):
        end=correct[i+1][0].start() if i+1<len(correct) else len(text)
        fragment=text[match.end():end]
        before=text[max(0,match.start()-850):match.start()]
        agency,title=identify(g,fragment,before,match.group(0))
        kind=classify(title)
        if kind is None:continue
        if not agency:
            raise ProvincialCoverageError(f"{g.name} {day}: emisor de convocatoria ausente {code}")
        notices.append({"code":code,"title":title,"agency":agency,"type":kind})
    return notices,len(expected)

def identify(g:Gazette,fragment:str,before:str,raw_code:str)->tuple[str,str]:
    lines=[x.strip() for x in fragment.splitlines() if x.strip()]
    if not lines:raise ProvincialCoverageError(f"{g.name}: anuncio sin texto")
    if g.almeria:
        # The body begins with issuer, often followed by the ministry/office,
        # then "ANUNCIO" / "EDICTO" and the complete first paragraph.
        issuer=next((x for x in lines[:5] if AL_AGENCY.search(x)),None)
        agency=""
        if issuer is not None:
            m=AL_AGENCY.search(issuer)
            agency=issuer[m.start():][:140]
        # Determine title only from the opening, never claim inferred deadlines.
        norm=" ".join(lines[:13])
        heading=re.search(r"\b(?:A\s*N\s*U\s*N\s*C\s*I\s*O|E\s*D\s*I\s*C\s*T\s*O|B\s*A\s*S\s*E\s*S)\b",norm,re.I)
        title=norm[heading.end():].strip() if heading else norm
        title=re.sub(r"\s+"," ",title)
        # Stop before applicant lists, formal signature, or legal argument.
        title=title[:380]
        if len(title)>225:title=title[:225].rsplit(" ",1)[0]+"…"
        if not title:return agency,""
        return agency,title
    # Jaen prints the official summary title next to "2026/xxxx", and the
    # immediately preceding uppercase lines give the issuer.
    heading=[]
    for x in lines[:7]:
        if re.fullmatch(r"(?:Anuncio|Edicto|Resoluci[oó]n|Bando)",x,re.I):
            break
        if len(heading)>=3:break
        heading.append(x)
    title=" ".join(heading).strip()
    if len(title)>250:title=title[:247].rsplit(" ",1)[0]+"…"
    agencies=[x.strip() for x in before.splitlines() if JA_AGENCY.match(x.strip())]
    return (agencies[-1][:160] if agencies else ""),title

def checked_pdf(g:Gazette,url:str,s:requests.Session)->None:
    if g.almeria:
        official_pdf=is_almeria_edict(url)
        if not official_pdf:
            pdf_url(g,url)
    else:
        pdf_url(g,url)
    r=get(s,url,stream=True)
    try:
        head=next(r.iter_content(chunk_size=64),b"")
        if ("pdf" not in r.headers.get("Content-Type","").lower()
            or not head.startswith(b"%PDF-")):
            raise ProvincialCoverageError(f"{g.name}: el enlace oficial no contiene PDF")
    finally:r.close()

def is_almeria_edict(url:str)->bool:
    p=urlsplit(url)
    return bool(p.scheme=="https" and p.hostname==ALMERIA.host and p.port in (None,443)
        and p.username is None and not p.fragment and not p.query
        and re.fullmatch(r"/bop/services/manager/edicto/20\d{2}/\d{1,6}/anuncio\.pdf",p.path))

def candidate_url(g:Gazette,day:date,code:int,edition_pdf:str,s:requests.Session)->str:
    if g.almeria:
        u=f"https://{g.host}/bop/services/manager/edicto/{day.year}/{code}/anuncio.pdf"
        try:
            checked_pdf(g,u,s)
            return u
        except ProvincialCoverageError:
            # Archive PDF is also the legally original edition, accessible in full.
            return edition_pdf
    return edition_pdf

def scan_issue(g:Gazette,issue:dict,session_factory=session)->dict:
    s=session_factory()
    try:
        day=issue["date"]
        ocr_url=text_url(g,issue["id"])
        txt=get(s,ocr_url).content.decode("utf-8")
        number=parse_date_header(g,txt,day)
        notices,read=split_ocr(g,txt,day)
        checked_pdf(g,issue["pdf"],s)
        out=[]
        for x in notices:
            link=candidate_url(g,day,x["code"],issue["pdf"],s)
            out.append({
                "id":f"{g.code}-{day.year}-{x['code']:05d}",
                "province":g.name,"title":x["title"],"entity":x["agency"],
                "date":day.strftime("%d/%m/%Y"),"bulletin":str(number),
                "type":x["type"],"url":link,
            })
        return {"date":day,"number":number,"read":read,"pages":issue["pages"],
                "notices":out,"pdf":issue["pdf"],"id":issue["id"]}
    finally:s.close()

def audit(g:Gazette,days:int=30,today:date|None=None,
          indexer=fetch_index,scanner=scan_issue)->dict:
    if days!=30:raise ProvincialCoverageError(f"{g.name}: se requieren 30 dias naturales")
    end=today or date.today()
    start=end-timedelta(days=29)
    s=session()
    try: issues,total,index_pages=indexer(g,start,end,s)
    finally:s.close()
    dates=[x["date"] for x in issues]
    if dates!=sorted(set(dates)) or (end-dates[-1]).days>4 or dates[0]>start+timedelta(days=4):
        raise ProvincialCoverageError(f"{g.name}: indice de ediciones con huecos")
    errors=[]
    def checked(issue:dict):
        try:return scanner(g,issue),None
        except (ProvincialCoverageError,requests.RequestException,ValueError,UnicodeError) as ex:
            return None,str(ex)
    with ThreadPoolExecutor(max_workers=3) as pool:
        responses=list(pool.map(checked,issues))
    results=[]
    for issue,(res,error) in zip(issues,responses):
        if error:
            errors.append(f"{issue['date']}: {error}")
            print(f"{g.name} ERROR {errors[-1]}",flush=True)
            continue
        if res["date"]!=issue["date"] or res["pages"]!=issue["pages"]:
            raise ProvincialCoverageError(f"{g.name}: fecha/numero páginas cambiantes")
        results.append(res)
        print(f"{g.name} {res['date']}: BOP {res['number']} · "
              f"{res['pages']} páginas · {res['read']} edictos · "
              f"{len(res['notices'])} candidatas",flush=True)
    if errors:
        raise ProvincialCoverageError(f"{g.name}: {len(errors)} boletines incompletos: "+" | ".join(errors))
    if len(results)<15 or len(results)!=len(issues):
        raise ProvincialCoverageError(f"{g.name}: faltan boletines")
    for old,nxt in zip(results,results[1:]):
        if old["date"].year==nxt["date"].year:
            if nxt["number"]!=old["number"]+1:
                raise ProvincialCoverageError(f"{g.name}: salto en BOP {old['number']} -> {nxt['number']}")
        elif nxt["number"]!=1:
            raise ProvincialCoverageError(f"{g.name}: numeración no reiniciada en enero")
        if (nxt["date"]-old["date"]).days>5:
            raise ProvincialCoverageError(f"{g.name}: más de 5 días sin BOP entre ediciones")
    notices=[x for item in results for x in item["notices"]]
    if not notices or len(set(x["id"] for x in notices))!=len(notices):
        raise ProvincialCoverageError(f"{g.name}: no hay candidatas, o se repiten")
    notices.sort(key=lambda x:(datetime.strptime(x["date"],"%d/%m/%Y"),x["id"]),reverse=True)
    missing=sorted({(start+timedelta(days=i)).isoformat() for i in range(30)}-{d.isoformat() for d in dates})
    pages=sum(x["pages"] for x in results)
    count=sum(x["read"] for x in results)
    source=archive_url(g)
    return {
       "schemaVersion":1,"source":source,"province":g.name,
       "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
       "coverage":{"complete":True,"status":"complete","bulletin":str(results[-1]["number"]),
                   "pagesVisited":pages,"announcementsRead":count,
                   "opportunities":len(notices)},
       "historyCoverage":{"complete":True,"rangeStart":start.isoformat(),
                   "rangeEnd":end.isoformat(),"issuesRead":len(results),
                   "pagesVisited":pages,"announcementsRead":count,
                   "opportunities":len(notices),
                   "bulletins":[str(x["number"]) for x in results],
                   "publicationDates":[x["date"].isoformat() for x in results],
                   "nonPublicationDates":missing,
                   "originalPdfPagesRead":pages,
                   "archiveIndexPagesRead":index_pages,
                   "archiveTotalIssues":total,
                   "editionPDFs":[x["pdf"] for x in results]},
       "notices":notices,
    }

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--province",choices=list(GAZETTES),required=True)
    p.add_argument("--days",type=int,default=30)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    result=audit(GAZETTES[args.province],args.days)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"{result['province'].upper()} AUDITADO: {result['historyCoverage']['issuesRead']} ediciones, "
          f"{result['coverage']['announcementsRead']} anuncios, "
          f"{len(result['notices'])} candidatas",flush=True)
