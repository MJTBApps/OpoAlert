#!/usr/bin/env python3
"""OpoAlert: fail-closed Madrid BOCM official 30-day archive reader.

Scans the complete issue catalogue, including multiple/extraordinary issues on
one date, and verifies the original PDF for all employment candidates.
"""
from __future__ import annotations
import argparse,json,re,time,xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urljoin,urlsplit
import requests
from bs4 import BeautifulSoup
from provincial_common import ProvincialCoverageError,classify

HOME="https://www.bocm.es"
CATALOG=HOME+"/listado-de-boletines"
PROVINCE="Madrid"
ISSUE_LINK=re.compile(r"^/boletin/bocm-(\d{8})-(\d{1,3})$",re.I)
NOTICE_ID=re.compile(r"^BOCM-(\d{8})-(\d{1,5})$")
PDF_PATTERN=re.compile(r"^/boletin/CM_Orden_BOCM/(\d{4})/(\d{2})/(\d{2})/BOCM-(\d{8})-(\d{1,5})\.PDF$",re.I)
ISSUE_PDF_PATTERN=re.compile(r"^/boletin/CM_Boletin_BOCM/(\d{4})/(\d{2})/(\d{2})/(\d{1,3})00\.PDF$",re.I)
ISSUE_XML_PATTERN=re.compile(r"^/boletin/CM_Boletin_BOCM/(\d{4})/(\d{2})/(\d{2})/BOCM-(\d{8})(\d{1,3})\.xml$",re.I)
def fail(why):raise ProvincialCoverageError("BOCM Madrid: "+why)

def request(url:str,pdf:bool=False)->requests.Response:
    parts=urlsplit(url)
    if (parts.scheme!="https" or parts.hostname!="www.bocm.es" or parts.port not in (None,443)
        or parts.username or parts.password or parts.fragment or parts.query
        or not (parts.path in ("/listado-de-boletines",)
          or re.fullmatch(r"/boletin-completo/BOCM-\d{8}/\d{1,3}",parts.path)
          or re.fullmatch(r"/boletin/CM_Boletin_BOCM/\d{4}/\d{2}/\d{2}/[a-zA-Z0-9-]+\.(?:xml|PDF)",parts.path)
          or re.fullmatch(r"/boletin/CM_Orden_BOCM/\d{4}/\d{2}/\d{2}/BOCM-\d{8}-\d{1,5}\.(?:PDF|json)",parts.path))):
        fail("URL no oficial o con parámetros")
    error=None
    for n in range(3):
        try:
            resp=requests.get(url,timeout=(10,33),stream=pdf,allow_redirects=True,
                headers={"User-Agent":"Mozilla/5.0 (compatible; OpoAlert Madrid verified index)",
                         "Accept-Language":"es"})
            if resp.status_code!=200 or urlsplit(resp.url).hostname!="www.bocm.es":
                status=resp.status_code
                resp.close()
                fail(f"HTTP {status} al leer {url}")
            if not pdf and (not resp.content or len(resp.content)>4_000_000):
                resp.close()
                fail("XML/HTML oficial vacío o demasiado largo")
            return resp
        except (requests.RequestException,ProvincialCoverageError) as ex:
            error=ex
            if n<2:time.sleep(0.8*(n+1))
    fail(f"no se pudo acceder a {url}: {error}")

def issue_html(day:date,number:int)->str:
    return f"{HOME}/boletin-completo/BOCM-{day:%Y%m%d}/{number}"

def issue_xml(day:date,number:int)->str:
    return f"{HOME}/boletin/CM_Boletin_BOCM/{day:%Y/%m/%d}/BOCM-{day:%Y%m%d}{number}.xml"

def issue_pdf(day:date,number:int)->str:
    return f"{HOME}/boletin/CM_Boletin_BOCM/{day:%Y/%m/%d}/{number}00.PDF"

def pdf_ok(url:str,day:date,number:int|None=None)->bool:
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname!="www.bocm.es" or u.query or u.fragment or u.username or u.port not in (None,443):
        return False
    if number is None:
        match=PDF_PATTERN.fullmatch(u.path)
    else:match=ISSUE_PDF_PATTERN.fullmatch(u.path)
    if not match:return False
    yy,mm,dd=map(int,match.groups()[:3])
    if date(yy,mm,dd)!=day:return False
    if number is None:
        encoded=match.group(4)
        return encoded==day.strftime("%Y%m%d")
    return int(match.group(4))==number

def check_pdf(url:str,day:date,number:int|None=None):
    if not pdf_ok(url,day,number):fail("PDF fuera del dominio, fecha o número oficial")
    resp=request(url,pdf=True)
    try:
        first=next(resp.iter_content(chunk_size=64),b"")
        if (not first.startswith(b"%PDF-")
            or "pdf" not in resp.headers.get("Content-Type","").lower()):
            fail("el documento enlazado no es un PDF original")
    finally:resp.close()

def archive(html:str,start:date,end:date)->list[tuple[date,int]]:
    soup=BeautifulSoup(html,"html.parser")
    found={}
    for a in soup.select('a[href]'):
        href=urlsplit(a.get("href","")).path
        m=ISSUE_LINK.fullmatch(href)
        if m is None:continue
        try:d=datetime.strptime(m.group(1),"%Y%m%d").date()
        except ValueError:fail("fecha imposible en catálogo")
        number=int(m.group(2))
        if not (1<=number<=366):fail("numeración BOCM inválida")
        label=a.get_text(" ",strip=True)
        if not re.search(rf"\bN[º°o]\s*{number}\b",label,re.I) or f"BOCM-{d:%Y%m%d}" not in label:
            fail(f"índice oficial sin número o fecha: {href}")
        if start<=d<=end:
            key=(d,number)
            found[key]=found.get(key,0)+1
    data=sorted(found)
    if len(data)<20 or any(v>2 for v in found.values()):
        fail("catálogo no cubre 30 días o tiene duplicaciones")
    if (end-data[-1][0]).days>4 or (data[0][0]-start).days>4:
        fail("faltan boletines al inicio o fin de los 30 días")
    numbers=[n for _,n in data]
    if any(b!=a+1 for a,b in zip(numbers,numbers[1:])):
        fail("faltan números de BOCM en el calendario oficial")
    return data

def exact_doc_id(raw:str,day:date)->int:
    m=NOTICE_ID.fullmatch(raw.strip())
    if not m or m.group(1)!=day.strftime("%Y%m%d"):fail("identificador de anuncio no coincide con fecha")
    num=int(m.group(2))
    if not (1<=num<=99999):fail("número de anuncio imposible")
    return num

def classify_bocm(title:str)->str|None:
    """BOCM town notices use generic headings ('Ofertas de empleo. Proceso selectivo')."""
    from provincial_common import fold
    t=" ".join(fold(title).split())
    if any(x in t for x in ("se resuelve la convocatoria", "se resuelve el concurso",
        "resolucion definitiva", "nombramiento", "lista definitiva",
        "lista provisional", "admitid", "excluid", "tribunal calificador",
        "correccion de errores", "cese y nombramiento")):
        return None
    regular=classify(title)
    if regular:return regular
    if "ofertas de empleo" in t or "oferta de empleo" in t:
        if any(x in t for x in ("bolsa", "bolsas")):return "Bolsa de trabajo"
        if any(x in t for x in ("proceso selectivo", "convocatoria", "bases", "plazas","oposiciones")):
            return "Plaza / oposición"
    return None

def nearest_entity(node,parent_map:dict)->str:
    current=node
    while current in parent_map:
        current=parent_map[current]
        if current.tag=="organismo":
            attrs=current.attrib
            for k in ("nombre","denominacion","descripcion","titulo"):
                if (attrs.get(k) or "").strip():return attrs[k].strip()
            for k in ("nombre","descripcion","titulo"):
                value=current.findtext(k)
                if value and value.strip():return value.strip()
        if current.tag=="seccion" and current.attrib.get("nombre"):
            fallback=current.attrib["nombre"].strip()
    return fallback if "fallback" in locals() else ""

def parse_xml(raw:bytes,day:date,number:int)->dict:
    if not raw.lstrip().startswith(b"<sumario>"):fail("XML no es un sumario BOCM")
    try:root=ET.fromstring(raw)
    except ET.ParseError as ex:fail(f"XML mal formado: {ex}")
    if root.tag!="sumario":fail("raíz XML desconocida")
    meta=root.find("metadatos")
    diario=root.find("diario")
    if meta is None or diario is None:fail("metadatos diarios ausentes")
    official_date=meta.findtext("fecha_publicacion")
    official_number=meta.findtext("numero")
    if (meta.findtext("publicacion")!="BOCM" or official_date!=day.strftime("%Y/%m/%d")
        or official_number!=str(number) or diario.attrib.get("numero")!=str(number)):
        fail(f"XML devuelve otro boletín, solicitado {number}, recibido {official_number}")
    expected=issue_xml(day,number)
    if meta.findtext("url_xml_sumario")!=expected:
        fail("XML oficial corresponde a otro número: enlace de metadatos")
    actual_pdf=meta.findtext("url_pdf_diario") or ""
    if actual_pdf!=issue_pdf(day,number):fail("PDF de edición incoherente con fecha y número")
    parent_map={ch:p for p in root.iter() for ch in p}
    rows=[]
    for notice in root.findall(".//disposicion"):
        key=(notice.findtext("identificador") or "").strip()
        n=exact_doc_id(key,day)
        title=" ".join((notice.findtext("titulo") or "").split())
        agency=nearest_entity(notice,parent_map)
        if (not agency or agency.startswith("III. ADMINISTRACIÓN LOCAL")) and title.startswith("–"):
            match=re.match(r"^–\s*([^\.]{3,125})\.",title)
            if match:agency=match.group(1).strip()
        pdf=(notice.findtext("url_pdf") or "").strip()
        if (not pdf_ok(pdf,day) or
            pdf.rsplit("/",1)[-1]!=f"{key}.PDF" or
            not title or len(title)>2800 or not agency or len(agency)>400):
            fail(f"anuncio incompleto en número {number}: {key}, emisor={agency!r}")
        rows.append({"id":"MD-"+day.strftime("%Y%m%d")+"-"+str(n),"province":PROVINCE,
            "title":title,"entity":agency,"date":day.strftime("%d/%m/%Y"),
            "bulletin":str(number),"type":classify_bocm(title),"url":pdf})
    if len(rows)<1 or len({r["id"] for r in rows})!=len(rows):
        fail(f"XML vacío o anuncios duplicados en BOCM {number}")
    return {"date":day,"number":number,"read":len(rows),"rows":rows,
      "editionPdf":actual_pdf,"method":"xml"}

def parse_fallback_html(html:str,day:date,number:int,fetch_json=request)->dict:
    # The publisher occasionally serves the previous issue's XML for an
    # extraordinary issue. The HTML contains the correct issue and item links.
    soup=BeautifulSoup(html,"html.parser")
    text=soup.get_text(" ",strip=True)
    if not re.search(rf"\bBOCM\s+N[º°o]\s*{number}\b",text,re.I):
        fail(f"el HTML de respaldo no confirma boletín {number}")
    links=[]
    for a in soup.select('a[href]'):
        url=urljoin(HOME,a["href"])
        if pdf_ok(url,day) and url not in links:links.append(url)
    if not (1<=len(links)<=180):fail("HTML de respaldo vacío o no verificable")
    rows=[]
    for pdf in links:
        name=pdf.rsplit("/",1)[-1]
        raw=name[:-4]
        n=exact_doc_id(raw,day)
        json_url=pdf[:-4]+".json"
        payload=fetch_json(json_url).json()
        if payload.get("legislationIdentifier")!=raw or not (payload.get("name") or "").strip():
            fail(f"ficha JSON-LD de {raw} inconsistente")
        title=" ".join(payload["name"].split())
        # In a fallback, the official section heading is a grounded grouping,
        # never guessed as a specific legal entity.
        parent=payload.get("isPartOf") or {}
        if not isinstance(parent,dict) or parent.get("name")!=f"BOCM - Nº {number}":
            fail(f"ficha {raw} no pertenece al extraordinario {number}")
        if payload.get("datePublished")!=day.strftime("%Y/%m/%d"):
            fail(f"ficha {raw} de otra fecha")
        authority=payload.get("legislationResponsible") or {}
        agency=(authority.get("name") or "").strip() if isinstance(authority,dict) else ""
        if not agency:fail(f"autoridad oficial no identificada en ficha {raw}")
        if len(title)>2800 or len(agency)>400:fail("registro de respaldo demasiado largo")
        rows.append({"id":f"MD-{day:%Y%m%d}-{n}","province":PROVINCE,
            "title":title,"entity":agency,"date":day.strftime("%d/%m/%Y"),
            "bulletin":str(number),"type":classify_bocm(title),"url":pdf})
    if len(set(r["id"] for r in rows))!=len(rows):fail("HTML duplicó avisos")
    return {"date":day,"number":number,"read":len(rows),"rows":rows,
      "editionPdf":issue_pdf(day,number),"method":"html"}

def scan(pair:tuple[date,int])->dict:
    day,number=pair
    xml_url=issue_xml(day,number)
    raw=request(xml_url).content
    try:
        parsed=parse_xml(raw,day,number)
    except ProvincialCoverageError as exc:
        if ("XML devuelve otro boletín" not in str(exc) and
            "XML oficial corresponde a otro número" not in str(exc)):
            raise
        parsed=parse_fallback_html(request(issue_html(day,number)).text,day,number)
        print("BOCM",day,number,"XML incorrecto, comparado HTML oficial",flush=True)
    check_pdf(parsed["editionPdf"],day,number)
    candidates=[]
    for row in parsed["rows"]:
        if row["type"] is None:continue
        check_pdf(row["url"],day)
        candidates.append({k:v for k,v in row.items() if k!="type"} | {"type":row["type"]})
    return {"date":day,"number":number,"read":parsed["read"],"pages":1,
       "method":parsed["method"],"notices":candidates,"pdf":parsed["editionPdf"]}

def audit(days:int=30,today:date|None=None,reader=scan,archive_html:str|None=None)->dict:
    if days!=30:fail("exigida auditoría de 30 días")
    end=today or date.today()
    start=end-timedelta(days=29)
    archive_data=archive(archive_html if archive_html is not None else request(CATALOG).text,start,end)
    with ThreadPoolExecutor(max_workers=3) as pool:
        rows=list(pool.map(reader,archive_data))
    for (day,number),item in zip(archive_data,rows):
        if (item["date"]!=day or item["number"]!=number or item["read"]<len(item["notices"])
            or item["read"]<1 or not pdf_ok(item["pdf"],day,number)
            or item["method"] not in ("xml","html")):
            fail(f"auditoría desordenada o incompleta BOCM {day}/{number}")
        print("Madrid BOCM",day,"nº",number,"anuncios",item["read"],
              "candidatas",len(item["notices"]),"método",item["method"],flush=True)
    notices=[n for item in rows for n in item["notices"]]
    if not notices or len({n["id"] for n in notices})!=len(notices):
        fail("sin candidatas o con identificadores duplicados")
    notices.sort(key=lambda n:(datetime.strptime(n["date"],"%d/%m/%Y"),int(n["id"].rsplit("-",1)[1])),reverse=True)
    dates=sorted({d for d,n in archive_data})
    absent=[(start+timedelta(days=i)).isoformat() for i in range(days)
            if start+timedelta(days=i) not in dates]
    total=sum(row["read"] for row in rows)
    result={"schemaVersion":1,"source":CATALOG,"province":PROVINCE,
      "lastCheckedUTC":datetime.now(timezone.utc).isoformat(),
      "coverage":{"complete":True,"status":"complete","bulletin":str(rows[-1]["number"]),
        "pagesVisited":len(rows),"announcementsRead":total,"opportunities":len(notices)},
      "historyCoverage":{"complete":True,"rangeStart":start.isoformat(),
        "rangeEnd":end.isoformat(),"issuesRead":len(rows),"pagesVisited":len(rows),
        "announcementsRead":total,"opportunities":len(notices),
        "bulletins":[str(r["number"]) for r in rows],
        "publicationDates":[r["date"].isoformat() for r in rows],
        "nonPublicationDates":absent,
        "editionPDFs":[r["pdf"] for r in rows],
        "parseMethods":[r["method"] for r in rows]},
      "notices":notices}
    return result

if __name__=="__main__":
    a=argparse.ArgumentParser()
    a.add_argument("--days",type=int,default=30)
    a.add_argument("--output",required=True,type=Path)
    args=a.parse_args()
    result=audit(args.days)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"MADRID AUDITADO: {result['historyCoverage']['issuesRead']} boletines, "
          f"{result['coverage']['announcementsRead']} anuncios y {len(result['notices'])} candidatas",flush=True)
