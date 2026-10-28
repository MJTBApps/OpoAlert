#!/usr/bin/env python3
"""BOP Zaragoza: 30-day audit from the official Gobierno de Aragon open-data API.

The Diputacion BOPZ portal is intermittently inaccessible from GitHub Actions.
The Gobierno de Aragon publishes the *whole* provincial bulletin in its BOA
opendata interface (BASE=BZHT, SECC-C=zaragoza). Do not set SUBS-C=sexta:
that omits all other BOPZ subsections and could lose competitions.
For each day validate the official XML independently against the JSON export,
verify every result ordinal, issue number, date, body, publisher and original
official PDF. Refuse publication if any edition is truncated or inconsistent.
"""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta,timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit,parse_qs
import xml.etree.ElementTree as ET
import requests
from provincial_common import ProvincialCoverageError,classify,fold

SOURCE="https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI"
PROVINCE="Zaragoza"
PDF_RE=re.compile(r"https://www\.boa\.aragon\.es/cgi-bin/EBOA/BRSCGI\?CMD=VEROBJ&MLKOB=[0-9]{9,18}")
ID_RE=re.compile(r"[0-9]{9}")
ORDINAL_RE=re.compile(r"(\d{1,5}) de (\d{1,5})")
SECTION_RE=re.compile(r"(?i)bolet[ií]n oficial de la provincia de zaragoza")
MAX_RESULTS=10_000
BASE={
    "CMD":"VERLST","OUTPUTMODE":"JSON","BASE":"BZHT","DOCS":f"1-{MAX_RESULTS}",
    "SEC":"OPENDATABOAJSON","SORT":"-PUBL","SEPARADOR":"",
    "@PUBL-GE":"","@PUBL-LE":"","NUMB":"","RANG":"",
    "TITU-C":"","FDIS-C":"","TITU":"","ORGA-C":"","TEXT-C":"",
    "SECC-C":"zaragoza","SECC":"","SUBS-C":"",
}

def pdf_url(raw:str)->str:
    if not isinstance(raw,str):
        raise ProvincialCoverageError("Zaragoza: URL oficial ausente")
    match=PDF_RE.search(raw)
    if not match:
        raise ProvincialCoverageError(f"Zaragoza: enlace oficial irregular: {raw[:100]}")
    url=match.group()
    clean=raw.strip()
    if clean.startswith("<enlace>") and clean.endswith("</enlace>"):
        clean=clean.removeprefix("<enlace>").removesuffix("</enlace>").strip()
    else:
        clean=clean.strip("`´ ").strip()
    if not safe_pdf(url) or clean!=url:
        raise ProvincialCoverageError("Zaragoza: URL contiene datos no oficiales")
    return url

def safe_pdf(url:str)->bool:
    if not isinstance(url,str) or not PDF_RE.fullmatch(url):
        return False
    parts=urlsplit(url)
    return (parts.scheme=="https" and parts.hostname=="www.boa.aragon.es"
            and parts.port is None and parts.username is None
            and not parts.password and not parts.fragment
            and parts.path=="/cgi-bin/EBOA/BRSCGI"
            and set(parse_qs(parts.query))=={"CMD","MLKOB"}
            and parse_qs(parts.query)["CMD"]==["VEROBJ"])

def date_params(day:date,xml:bool=False)->dict:
    params=dict(BASE)
    params["@PUBL-GE"]=params["@PUBL-LE"]=day.strftime("%Y%m%d")
    if xml:
        params["OUTPUTMODE"]="XML"
        params["SEC"]="OPENDATABOAXML"
    return params

def official_session()->requests.Session:
    s=requests.Session()
    s.headers.update({
        "User-Agent":"Mozilla/5.0 (compatible; OpoAlert Zaragoza official bulletin audit/1.10)",
        "Accept":"application/json, application/xml, text/html;q=0.7",
        "Accept-Language":"es",
    })
    return s

def get(session:requests.Session,params:dict)->requests.Response:
    for attempt in range(3):
        try:
            response=session.get(SOURCE,params=params,timeout=(12,45))
            if response.status_code!=200 or urlsplit(response.url).hostname!="www.boa.aragon.es":
                raise ProvincialCoverageError(f"Zaragoza: respuesta HTTP {response.status_code}")
            if not response.content or len(response.content)>20_000_000:
                raise ProvincialCoverageError("Zaragoza: respuesta vacia o excesiva")
            if response.encoding is None:response.encoding="ISO-8859-1"
            return response
        except requests.RequestException as exc:
            if attempt==2:
                raise ProvincialCoverageError(f"Zaragoza: API oficial inaccesible: {exc}") from exc
    raise ProvincialCoverageError("Zaragoza: fallo desconocido")

def parse_json(raw:bytes,day:date)->tuple[int|None,list[dict]]:
    try:
        data=json.loads(raw.decode("ISO-8859-1"))
    except (ValueError,UnicodeError) as exc:
        raise ProvincialCoverageError(f"Zaragoza {day}: JSON oficial incorrecto: {exc}") from exc
    if not isinstance(data,list):
        raise ProvincialCoverageError(f"Zaragoza {day}: JSON no es una lista")
    if len(data)>=MAX_RESULTS:
        raise ProvincialCoverageError(f"Zaragoza {day}: limite de paginacion alcanzado")
    if not data:
        return None,[]
    totals=set()
    issue_numbers=set()
    identifiers=set()
    for position,item in enumerate(data,1):
        if not isinstance(item,dict):
            raise ProvincialCoverageError(f"Zaragoza {day}: anuncio no es objeto")
        m=ORDINAL_RE.fullmatch(str(item.get("NOrden","")))
        docn=item.get("DOCN","")
        issue=item.get("Numeroboletin","")
        agency=str(item.get("Emisor","")).strip()
        title=str(item.get("Titulo","")).strip()
        body=str(item.get("Texto","")).strip()
        if (m is None or int(m.group(1))!=position
            or not ID_RE.fullmatch(str(docn)) or docn in identifiers
            or item.get("FechaPublicacion")!=day.strftime("%Y%m%d")
            or not SECTION_RE.search(str(item.get("Seccion","")))
            or not item.get("Subseccion") or not agency or not title or not body
            or not str(issue).isdigit() or not 1<=int(issue)<=366
            or not safe_pdf(pdf_url(item.get("UrlPdf","")))):
            raise ProvincialCoverageError(f"Zaragoza {day}: fila oficial incoherente posicion {position}")
        totals.add(int(m.group(2)))
        issue_numbers.add(int(issue))
        identifiers.add(docn)
    if totals!={len(data)}:
        raise ProvincialCoverageError(f"Zaragoza {day}: pagina incompleta {totals} vs {len(data)}")
    if len(issue_numbers)!=1:
        raise ProvincialCoverageError(f"Zaragoza {day}: varios numeros BOP para una fecha")
    return issue_numbers.pop(),data

def parse_xml(raw:bytes,day:date)->dict[str,dict]:
    try:
        root=ET.fromstring(raw)
    except ET.ParseError as ex:
        raise ProvincialCoverageError(f"Zaragoza {day}: XML oficial invalido: {ex}") from ex
    if root.tag.lower()!="documento":
        raise ProvincialCoverageError(f"Zaragoza {day}: XML no contiene documento")
    records={}
    for reg in root.findall("registro"):
        ident=(reg.findtext("docn") or "").strip()
        published=(reg.findtext("fecha") or "").strip()
        sect=(reg.findtext("seccion") or "").strip()
        agency=(reg.findtext("emisor") or "").strip()
        pdf=(reg.findtext("url") or "").strip()
        if (not ID_RE.fullmatch(ident) or ident in records
            or published!=day.strftime("%Y%m%d")
            or not SECTION_RE.search(sect) or not agency
            or not safe_pdf(pdf_url(pdf))):
            raise ProvincialCoverageError(f"Zaragoza {day}: fila XML inconsistente {ident}")
        records[ident]={"date":published,"agency":agency,"pdf":pdf_url(pdf)}
    if len(records)>=MAX_RESULTS:
        raise ProvincialCoverageError(f"Zaragoza {day}: XML llega a limite pagina")
    return records

def compare_exports(day:date,number:int|None,rows:list[dict],xml:dict)->None:
    if set(xml)!={x["DOCN"] for x in rows}:
        raise ProvincialCoverageError(f"Zaragoza {day}: JSON y XML no contienen los mismos anuncios")
    for row in rows:
        item=xml[row["DOCN"]]
        if (fold(item["agency"])!=fold(row["Emisor"].strip())
            or item["pdf"]!=pdf_url(row["UrlPdf"])):
            raise ProvincialCoverageError(f"Zaragoza {day}: XML difiere en el anuncio {row['DOCN']}")
    if (number is None)!=(not rows):
        raise ProvincialCoverageError(f"Zaragoza {day}: numero de BOP y anuncios inconsistentes")

def verify_pdf(session:requests.Session,url:str)->None:
    if not safe_pdf(url):raise ProvincialCoverageError("Zaragoza: PDF no oficial")
    try:
        r=session.get(url,headers={"Range":"bytes=0-64"},stream=True,timeout=(10,28))
        try:
            p=urlsplit(r.url)
            if (r.status_code not in (200,206) or p.hostname!="www.boa.aragon.es"
                or "pdf" not in r.headers.get("Content-Type","").lower()
                or not next(r.iter_content(chunk_size=64),b"").startswith(b"%PDF-")):
                raise ProvincialCoverageError(f"Zaragoza: documento oficial no es PDF {url}")
        finally:r.close()
    except requests.RequestException as exc:
        raise ProvincialCoverageError(f"Zaragoza: PDF oficial inaccesible {exc}") from exc

def classify_candidate(row:dict)->str|None:
    title=str(row["Titulo"]).strip()
    result=classify(title)
    if result:return result
    # The official BOPZ index often truncates titles to an ellipsis. Read the
    # opening of the original full text, never infer a deadline from its body.
    body=" ".join(str(row["Texto"]).split())
    return classify(body[:700])

def public_title(row:dict)->str:
    title=" ".join(str(row["Titulo"]).split())
    if title.endswith("..."):
        full=" ".join(str(row["Texto"]).split())
        if len(full)>len(title) and fold(title[:-3].strip()) in fold(full[:240]):
            return full[:210].rsplit(" ",1)[0]+"…" if len(full)>210 else full
    return title

def fetch_day(day:date,session_factory=official_session)->dict|None:
    session=session_factory()
    try:
        response=get(session,date_params(day))
        number,rows=parse_json(response.content,day)
        xml=get(session,date_params(day,xml=True))
        other=parse_xml(xml.content,day)
        compare_exports(day,number,rows,other)
        if not rows:return None
        # PDF integrity: verify representative document for the edition and
        # every candidate. URL points to original provincial text in BOA.
        verify_pdf(session,pdf_url(rows[0]["UrlPdf"]))
        notices=[]
        for row in rows:
            kind=classify_candidate(row)
            if kind is None:continue
            url=pdf_url(row["UrlPdf"])
            if row is not rows[0]:verify_pdf(session,url)
            notices.append({
                "id":"ZA-"+row["DOCN"],
                "province":PROVINCE,
                "title":public_title(row),
                "entity":str(row["Emisor"]).strip(),
                "date":day.strftime("%d/%m/%Y"),
                "bulletin":str(number),
                "type":kind,
                "url":url,
            })
        return {"date":day,"number":number,"read":len(rows),"pages":2,
                "notices":notices,"sections":dict(Counter(x["Subseccion"] for x in rows))}
    finally:session.close()

def audit(days:int=30,today:date|None=None,scanner=fetch_day)->dict:
    if days!=30:
        raise ProvincialCoverageError("Zaragoza: no se permite historico menor de 30 dias")
    end=today or date.today()
    start=end-timedelta(days=29)
    dates=[start+timedelta(days=i) for i in range(30)]
    errors=[]
    def checked(day:date):
        try:return scanner(day),None
        except (ProvincialCoverageError,requests.RequestException,ValueError) as ex:
            return None,str(ex)
    with ThreadPoolExecutor(max_workers=4) as p:
        responses=list(p.map(checked,dates))
    issues=[]
    missing=[]
    for day,(data,error) in zip(dates,responses):
        if error:
            errors.append(f"{day.isoformat()}: {error}")
            print("ZARAGOZA ERROR",errors[-1],flush=True)
            continue
        if data is None:
            missing.append(day.isoformat())
            print("Zaragoza",day,"sin edicion BOPZ",flush=True)
            continue
        if data["date"]!=day or data["read"]<len(data["notices"]) or data["read"]<1:
            raise ProvincialCoverageError(f"Zaragoza: auditoria incoherente para {day}")
        issues.append(data)
        print(f"Zaragoza {day}: BOP {data['number']}, {data['read']} anuncios, "
              f"{len(data['sections'])} secciones, {len(data['notices'])} candidatas",flush=True)
    if errors:
        raise ProvincialCoverageError(f"Zaragoza: {len(errors)} fechas no auditadas: "+" | ".join(errors))
    if len(issues)<20 or (end-issues[-1]["date"]).days>4:
        raise ProvincialCoverageError("Zaragoza: faltan ediciones o no se ha consultado la mas reciente")
    if issues[0]["date"]>start+timedelta(days=3):
        raise ProvincialCoverageError("Zaragoza: faltan boletines al inicio del historico")
    for old,current in zip(issues,issues[1:]):
        if old["date"].year==current["date"].year:
            if old["number"]+1!=current["number"]:
                raise ProvincialCoverageError(f"Zaragoza: salto entre BOP {old['number']} y {current['number']}")
        elif current["number"]!=1:
            raise ProvincialCoverageError("Zaragoza: nueva anualidad sin reinicio BOP")
    notices=[n for x in issues for n in x["notices"]]
    if not notices or len({n["id"] for n in notices})!=len(notices):
        raise ProvincialCoverageError("Zaragoza: candidatas vacias o identificadores duplicados")
    notices.sort(key=lambda x:(datetime.strptime(x["date"],"%d/%m/%Y"),x["id"]),reverse=True)
    total=sum(x["read"] for x in issues)
    pages=sum(x["pages"] for x in issues)
    all_sections=Counter()
    for x in issues:all_sections.update(x["sections"])
    return {
       "schemaVersion":1,"source":SOURCE,"province":PROVINCE,
       "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
       "coverage":{"complete":True,"status":"complete",
                   "bulletin":str(issues[-1]["number"]),"pagesVisited":pages,
                   "announcementsRead":total,"opportunities":len(notices)},
       "historyCoverage":{"complete":True,"rangeStart":start.isoformat(),
           "rangeEnd":end.isoformat(),"issuesRead":len(issues),
           "pagesVisited":pages,"announcementsRead":total,
           "opportunities":len(notices),
           "bulletins":[str(x["number"]) for x in issues],
           "publicationDates":[x["date"].isoformat() for x in issues],
           "nonPublicationDates":missing,
           "sectionsRead":dict(all_sections)},
       "notices":notices,
    }


def query_range(start:date,end:date,xml:bool=False)->dict:
    params=dict(BASE)
    params["@PUBL-GE"]=start.strftime("%Y%m%d")
    params["@PUBL-LE"]=end.strftime("%Y%m%d")
    if xml:
        params["OUTPUTMODE"]="XML"
        params["SEC"]="OPENDATABOAXML"
    return params

def parse_range_json(raw:bytes,start:date,end:date)->list[dict]:
    # Some official notices contain a literal backslash before a letter/digit
    # (for example a reference to a power line), which violates JSON escaping.
    # Escape ONLY malformed backslashes, then independently compare every
    # document ID, date, agency and PDF with the official XML export.
    try:
        source=raw.decode("ISO-8859-1")
    except UnicodeError as ex:
        raise ProvincialCoverageError("Zaragoza: codificacion no valida") from ex
    fixed=source
    try:
        data=json.loads(source)
    except json.JSONDecodeError as ex:
        if "Invalid \\escape" not in str(ex):
            raise ProvincialCoverageError(f"Zaragoza: JSON corrupto no reparable: {ex}") from ex
        fixed=re.sub(r"\\(?![\"\\/bfnrtu])",r"\\\\",source)
        if fixed==source or len(fixed)-len(source)>30:
            raise ProvincialCoverageError("Zaragoza: demasiadas alteraciones en JSON oficial")
        try:data=json.loads(fixed)
        except (ValueError,UnicodeError) as err:
            raise ProvincialCoverageError("Zaragoza: JSON oficial no corregible") from err
        print(f"Zaragoza: normalizados {len(fixed)-len(source)} caracteres de escape invalidos en JSON; contraste XML obligatorio",flush=True)
    if not isinstance(data,list) or not 20<=len(data)<MAX_RESULTS:
        raise ProvincialCoverageError(f"Zaragoza: volumen insuficiente o paginacion truncada: {len(data) if isinstance(data,list) else '?'}")
    ids=set()
    seen_pdfs=set()
    totals=set()
    for position,item in enumerate(data,1):
        if not isinstance(item,dict):
            raise ProvincialCoverageError("Zaragoza: entrada JSON irregular")
        m=ORDINAL_RE.fullmatch(str(item.get("NOrden","")))
        docn=item.get("DOCN","")
        date_raw=item.get("FechaPublicacion","")
        number=str(item.get("Numeroboletin",""))
        agency=item.get("Emisor","")
        title=item.get("Titulo","")
        full_text=item.get("Texto","")
        try:d=datetime.strptime(date_raw,"%Y%m%d").date()
        except (ValueError,TypeError) as ex:
            raise ProvincialCoverageError("Zaragoza: fecha de publicacion incorrecta") from ex
        if (m is None or int(m.group(1))!=position
            or not ID_RE.fullmatch(str(docn)) or docn in ids
            or not start<=d<=end or not number.isdigit() or not 1<=int(number)<=366
            or not SECTION_RE.search(str(item.get("Seccion","")))
            or not isinstance(item.get("Subseccion"),str) or not item["Subseccion"].strip()
            or not isinstance(agency,str) or not agency.strip()
            or not isinstance(title,str) or not title.strip()
            or not isinstance(full_text,str) or not full_text.strip()):
            raise ProvincialCoverageError(f"Zaragoza: fecha, contenido o indice incongruente, fila {position}")
        pdf=pdf_url(item.get("UrlPdf",""))
        issue_pdf=pdf_url(item.get("UrlBCOM",""))
        if pdf in seen_pdfs:
            raise ProvincialCoverageError(f"Zaragoza: PDF duplicado para anuncio {docn}")
        seen_pdfs.add(pdf)
        ids.add(docn)
        totals.add(int(m.group(2)))
    if totals!={len(data)}:
        raise ProvincialCoverageError(f"Zaragoza: API informa {totals}, pero llegaron {len(data)} anuncios")
    return data

def parse_range_xml(raw:bytes,start:date,end:date)->dict[str,dict]:
    try:root=ET.fromstring(raw)
    except ET.ParseError as ex:
        raise ProvincialCoverageError(f"Zaragoza: XML oficial no integro: {ex}") from ex
    if root.tag.lower()!="documento":
        raise ProvincialCoverageError("Zaragoza: XML no es formato de datos abiertos")
    out={}
    for reg in root.findall("registro"):
        docn=(reg.findtext("docn") or "").strip()
        date_raw=(reg.findtext("fecha") or "").strip()
        agency=(reg.findtext("emisor") or "").strip()
        sec=(reg.findtext("seccion") or "").strip()
        title=(reg.findtext("titulo") or "").strip()
        try:d=datetime.strptime(date_raw,"%Y%m%d").date()
        except (ValueError,TypeError) as ex:
            raise ProvincialCoverageError("Zaragoza: fecha XML incorrecta") from ex
        if (not ID_RE.fullmatch(docn) or docn in out
            or not start<=d<=end or not SECTION_RE.search(sec)
            or not agency or not title):
            raise ProvincialCoverageError("Zaragoza: XML no corresponde al BOPZ esperado")
        out[docn]={"date":date_raw,"agency":agency,
                    "title":title,"pdf":pdf_url(reg.findtext("url") or "")}
    if not 20<=len(out)<MAX_RESULTS:
        raise ProvincialCoverageError("Zaragoza: XML vacio o truncado")
    return out

def audit_batch(days:int=30,today:date|None=None,
                session_factory=official_session,pdf_check=verify_pdf)->dict:
    if days!=30:
        raise ProvincialCoverageError("Zaragoza: se exige historial exacto de 30 dias")
    end=today or date.today()
    start=end-timedelta(days=29)
    s=session_factory()
    try:
        raw_json=get(s,query_range(start,end)).content
        raw_xml=get(s,query_range(start,end,True)).content
        rows=parse_range_json(raw_json,start,end)
        xml=parse_range_xml(raw_xml,start,end)
        if set(xml)!={item["DOCN"] for item in rows}:
            raise ProvincialCoverageError("Zaragoza: los dos formatos oficiales no coinciden en identificadores")
        for item in rows:
            match=xml[item["DOCN"]]
            if (match["date"]!=item["FechaPublicacion"]
                or fold(" ".join(match["agency"].split()))!=fold(" ".join(item["Emisor"].split()))
                or match["pdf"]!=pdf_url(item["UrlPdf"])):
                raise ProvincialCoverageError(f"Zaragoza: datos contradictorios para anuncio {item['DOCN']}")
        per_issue={}
        for row in rows:
            rawday=row["FechaPublicacion"]
            no=int(row["Numeroboletin"])
            key=(rawday,no)
            if key not in per_issue:
                per_issue[key]=[]
            per_issue[key].append(row)
        keys=sorted(per_issue)
        issue_numbers=[n for _,n in keys]
        if (not 20<=len(keys)<=30
            or len(issue_numbers)!=len(set(issue_numbers))
            or keys[0][0]>(start+timedelta(days=4)).strftime("%Y%m%d")
            or keys[-1][0]<(end-timedelta(days=4)).strftime("%Y%m%d")):
            raise ProvincialCoverageError("Zaragoza: faltan boletines en el periodo consultado")
        for a,b in zip(keys,keys[1:]):
            if a[0][:4]==b[0][:4]:
                if b[1]!=a[1]+1:
                    raise ProvincialCoverageError(f"Zaragoza: falta numero BOP entre {a[1]} y {b[1]}")
            elif b[1]!=1:
                raise ProvincialCoverageError("Zaragoza: cambio anual incompleto")
        # Ensure all announcements within each edition share the same original
        # signed full-boletin PDF; individual links are checked separately.
        pdfs=set()
        seen=[]
        notices=[]
        sections=Counter()
        for date_raw,number in keys:
            group=per_issue[(date_raw,number)]
            day=datetime.strptime(date_raw,"%Y%m%d").date()
            whole_issue={pdf_url(x["UrlBCOM"]) for x in group}
            if len(whole_issue)!=1:
                raise ProvincialCoverageError(f"Zaragoza: varias ediciones originales en BOP {number}")
            first=pdf_url(group[0]["UrlPdf"])
            pdfs.add(first)
            for item in group:
                sections[item["Subseccion"]]+=1
                kind=classify_candidate(item)
                if kind is None:continue
                link=pdf_url(item["UrlPdf"])
                pdfs.add(link)
                notices.append({
                    "id":"ZA-"+item["DOCN"],"province":PROVINCE,
                    "title":public_title(item),"entity":item["Emisor"].strip(),
                    "date":day.strftime("%d/%m/%Y"),"bulletin":str(number),
                    "type":kind,"url":link,
                })
            seen.append({"day":day,"number":number,"read":len(group)})
            print(f"Zaragoza {day}: BOP {number}, {len(group)} anuncios (secciones verificadas en XML)",flush=True)
        if len(sections)<2:
            raise ProvincialCoverageError("Zaragoza: solo una seccion del boletin fue consultada")
        if not notices or len({x["id"] for x in notices})!=len(notices):
            raise ProvincialCoverageError("Zaragoza: ninguna candidata o IDs repetidos")
        # Limit network concurrency; no unverified PDF link can enter the feed.
        # Each request checks real application/pdf and PDF magic bytes.
        print(f"Zaragoza: verificando {len(pdfs)} PDF originales",flush=True)
        for i,url in enumerate(sorted(pdfs),1):
            pdf_check(s,url)
            if i%20==0:
                print(f"Zaragoza PDF verificados: {i}/{len(pdfs)}",flush=True)
        notices.sort(key=lambda n:(datetime.strptime(n["date"],"%d/%m/%Y"),n["id"]),reverse=True)
        published_days=sorted({x["day"].isoformat() for x in seen})
        absent=sorted({(start+timedelta(days=i)).isoformat() for i in range(30)}-set(published_days))
        # El calendario no se presume: la secuencia completa de numeros oficiales
        # demuestra que no falta ningun BOP entre las ediciones consultadas.
        num_issues=len(seen)
        result={
            "schemaVersion":1,"source":SOURCE,"province":PROVINCE,
            "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
            "coverage":{"complete":True,"status":"complete","bulletin":str(seen[-1]["number"]),
                "pagesVisited":2,"announcementsRead":len(rows),"opportunities":len(notices)},
            "historyCoverage":{
                "complete":True,"rangeStart":start.isoformat(),"rangeEnd":end.isoformat(),
                "issuesRead":num_issues,"pagesVisited":2,"announcementsRead":len(rows),
                "opportunities":len(notices),
                "bulletins":[str(x["number"]) for x in seen],
                "publicationDates":published_days,
                "issuePublicationDates":[x["day"].isoformat() for x in seen],
                "nonPublicationDates":absent,
                "sectionsRead":dict(sections),
                "documentsVerified":len(pdfs)},
            "notices":notices,
        }
        print(f"ZARAGOZA OK: {num_issues} boletines, {len(rows)} anuncios, {len(notices)} candidatas",flush=True)
        return result
    finally:
        s.close()

if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--days",type=int,default=30)
    parser.add_argument("--output",required=True,type=Path)
    args=parser.parse_args()
    feed=audit_batch(args.days)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(feed,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"ZARAGOZA VALIDADO: {feed['historyCoverage']['issuesRead']} ediciones, "
          f"{feed['coverage']['announcementsRead']} anuncios, "
          f"{len(feed['notices'])} candidatas",flush=True)
