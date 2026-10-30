#!/usr/bin/env python3
"""Asturias BOPA: strict first-party 30-day snapshot (30 Sep - 29 Oct 2026).

Evidence combines the 22 original BOPA issue indices captured from the
publisher's web pages on a user's Spanish connection, with fresh publisher
PDFs downloaded from a separate official host (www.asturias.es). Audits one
original per issue and every accepted candidate original. Includes the one
October 23 supplement and excludes its personnel-dismissal announcement.

NO user secrets, third-party mirrors, automatic public feed or PDF bypass.
The PDF host is the same Government of Asturias as the original summary host.
"""
from __future__ import annotations

import argparse,base64,gzip,hashlib,io,json,re,time,unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit
import requests
from pypdf import PdfReader
from clm_common import publish_audit,write_output
from provincial_common import ProvincialCoverageError

ENCODED=Path(__file__).parent/"snapshots"/"AS_index_20261029.json.gz.b64"
SOURCE="https://miprincipado.asturias.es/ast/bopa-sumario"
ORIGINAL_HOST="www.asturias.es"
PROVINCE="Asturias (BOPA)"
START=date(2026,9,30)
END=date(2026,10,29)
MANIFEST_HASH="91fbec5def3cd9316bb3b206da3e51b6f8a26de6bad358e2fd17d6daa6062f22"
COMPRESSED_HASH="ee66c02791bc3e59a4d0dc9f99ca68947e21a2767d51c7e28abf4299a10a6cd2"
SUPPLEMENT_DATE="2026-10-23"
SUPPLEMENT_NO="206S1"
SUPPLEMENT_CODE="2026-08829"
SUPPLEMENT_SHA="8956a3b3fd6d11f2ce5031afb295910abbb32d9aba0c326ab3bc93ce7a4f950e"
# Two ORIGINAL PDF header typos demonstrated by the publisher's 53-PDF survey.
# Never generalize to other editions or other original documents.
KNOWN_EDITORIAL_HEADER_ANOMALIES={
    ("2026-08061","2026-10-13",198,197):
      "1f85f35ef7d84ac0a011548effb98ec157492fa29462e3b204e4768bb298c8ea",
    ("2026-08160","2026-10-15",200,199):
      "1968d147cb6d32ad4d64758ac6d9b88f8ed73e04c859e79d6efc3db67821a4c0",
}
ROMAN_MONTH={9:"ix",10:"x"}

def fail(reason):
    raise ProvincialCoverageError("Asturias BOPA: "+str(reason))

def fold(s):
    d=unicodedata.normalize("NFD",str(s).casefold())
    return re.sub(r"\s+"," ","".join(x for x in d if unicodedata.category(x)!="Mn")).strip()

def load_manifest():
    raw64=ENCODED.read_text(encoding="ascii").strip()
    blob=base64.b64decode(raw64,validate=True)
    if hashlib.sha256(blob).hexdigest()!=COMPRESSED_HASH:
        fail("manifiesto comprimido ha cambiado")
    raw=gzip.decompress(blob)
    if hashlib.sha256(raw).hexdigest()!=MANIFEST_HASH:
        fail("manifiesto de editor original no coincide con la auditoría")
    value=json.loads(raw)
    if value.get("source")!=SOURCE or value.get("period")!=[START.isoformat(),END.isoformat()]:
        fail("fuente/intervalo de captura cambiado")
    if not re.fullmatch(r"[0-9a-f]{64}",value.get("inputSHA256","")):
        fail("sin procedencia verificable del ZIP institucional original")
    issues=value.get("issues")
    if not isinstance(issues,list) or len(issues)!=22:
        fail("faltan boletines originales en sumario")
    expected=[d for d in (START+timedelta(days=i) for i in range(30)) if d.weekday()<5]
    if len(expected)!=22 or [x.get("d") for x in issues]!=[d.isoformat() for d in expected]:
        fail("calendario oficial 30 días no coincide con 22 fechas")
    nonpub=[(START+timedelta(days=i)).isoformat() for i in range(30)
            if (START+timedelta(days=i)).weekday()>=5]
    if value.get("nonPublicationDates")!=nonpub:
        fail("fechas sin publicación incorrectas")
    indexed={}
    for i,issue in enumerate(issues):
        if issue.get("n")!=189+i:
            fail("números BOPA no consecutivos")
        day=issue["d"]
        ids=issue.get("ids","").split(",")
        if len(ids)<1 or len(ids)>200 or len(set(ids))!=len(ids):
            fail("índice oficial de disposiciones vacío o repetido")
        for suffix in ids:
            if not re.fullmatch(r"\d{5}",suffix):
                fail("código fuera del formato BOPA")
            code="2026-"+suffix
            if code in indexed:
                fail("documento original duplicado en varios boletines")
            indexed[code]={"d":day,"number":issue["n"]}
    if len(indexed)!=917:
        fail(f"índice de anuncios truncado: {len(indexed)} / 917")
    cands=value.get("candidates")
    if not isinstance(cands,list) or len(cands)!=32:
        fail("número de convocatorias seleccionadas no certificado")
    keys=set()
    for c in cands:
        code=c.get("id")
        if (code not in indexed or c.get("d")!=indexed[code]["d"] or
            c.get("n")!=indexed[code]["number"] or code in keys or
            c.get("kind") not in ("Bolsa de trabajo","Plaza / oposición") or
            not isinstance(c.get("title"),str) or not 20<len(c["title"])<=2500 or
            not 3<len(c.get("entity",""))<=400):
            fail("candidato fuera del calendario del editor")
        t=fold(c["title"])
        if any(x in t for x in ("nombramiento para la provision","resolucion por la que se resuelve",
                                 "modificacion de la convocatoria","rectificacion de las bases",
                                 "plazas a adjudicar","juez de paz","concurso de traslados")):
            fail("candidato puede ser actuación de un proceso ya resuelto")
        keys.add(code)
    return value,indexed

def pdf_url(day,code):
    if not re.fullmatch(r"2026-\d{5}",code) or not START<=date.fromisoformat(day)<=END:
        fail("código/fecha de PDF incorrectos")
    return f"https://{ORIGINAL_HOST}/bopa/{day.replace('-','/')}/{code}.pdf"

def read_pdf(url,max_size=18_000_000):
    p=urlsplit(url)
    if (p.scheme!="https" or p.hostname!=ORIGINAL_HOST or p.port not in (None,443)
        or p.username or p.password or p.query or p.fragment or not p.path.startswith("/bopa/2026/")):
        fail("URL no controlada por el editor autonómico")
    last=None
    for attempt in range(3):
        try:
            with requests.get(url,stream=True,allow_redirects=False,timeout=(9,35),
                 headers={"User-Agent":"Mozilla/5.0 (compatible; OpoAlert BOPA original 2026 verification)"}) as r:
                if r.status_code!=200 or r.url!=url or not r.headers.get("Content-Type","").lower().startswith("application/pdf"):
                    fail(f"editor no devolvió PDF válido: HTTP {r.status_code} para {url}")
                data=bytearray()
                for ch in r.iter_content(32768):
                    data.extend(ch)
                    if len(data)>max_size:
                        fail("PDF excede límite sin garantía de integridad")
                if not data.startswith(b"%PDF-") or len(data)<3500:
                    fail("documento sin firma PDF original")
            raw=bytes(data)
            reader=PdfReader(io.BytesIO(raw),strict=False)
            if not 1<=len(reader.pages)<=400:
                fail("PDF sin páginas o de tamaño inesperado")
            first=(reader.pages[0].extract_text() or "")[:6500]
            if len(first)<160:
                fail("no se puede extraer el encabezado del PDF original")
            return raw,len(reader.pages),first
        except requests.RequestException as ex:
            last=ex
            if attempt<2:time.sleep(1.4*(attempt+1))
    fail(f"documento no accesible tras reintentos: {str(last)[:110]}")

def verify_original(task):
    """One original from each issue; additionally every candidate's original."""
    day,n,code,title,kind,entity=task
    url=pdf_url(day,code)
    data,pages,first=read_pdf(url)
    top=fold(first[:900])
    roman=ROMAN_MONTH[date.fromisoformat(day).month]
    d=date.fromisoformat(day)
    header=re.search(fr"num[.]\s*(\d{{2,4}})\s+de\s+{d.day}-{roman}-{d.year}\b",top)
    code_ok=bool(re.search(r"\bcod[.]\s*"+re.escape(code)+r"\b",top))
    if header is None or not code_ok:
        fail(f"fecha y CVE del PDF original no corresponden al sumario oficial: {code}; dia={day}, roman={roman}, cabecera={bool(header)}, codigo={code_ok}, texto={top[:200]!r}")
    actual_number=int(header[1])
    number_matches=actual_number==int(n)
    # Exactly two publisher-origin typographical anomalies have been independently
    # verified; require exact document ID, date, expected/actual issue AND SHA256.
    original_sha=hashlib.sha256(data).hexdigest()
    anomaly_key=(code,day,int(n),actual_number)
    documented_anomaly=(KNOWN_EDITORIAL_HEADER_ANOMALIES.get(anomaly_key)==original_sha)
    if not number_matches and not documented_anomaly:
        fail(f"numero de cabecera no coincide con sumario BOPA: {code}, esperado {n}, PDF {actual_number}")
    ratio=None
    if title:
        words=[w for w in re.findall(r"[a-z0-9]{4,}",fold(title)) if w not in
               ("anuncio","resolucion","edito","edicto","octubre","septiembre","asturias","principado")]
        words=words[:34]
        pdf_words=set(re.findall(r"[a-z0-9]{4,}",fold(first)))
        ratio=sum(w in pdf_words for w in words)/max(1,len(words))
        if len(words)<4 or ratio<0.61:
            fail(f"texto/título de convocatoria no coincide con original {code}: coincidencia {ratio:.2f}")
    return {"id":code,"day":day,"bulletin":str(n),
        "url":url,"sha256":hashlib.sha256(data).hexdigest(),
        "bytes":len(data),"pages":pages,
        "publisherDateAndCVEVerified":True,"publisherIssueNumberMatched":number_matches,
        "pdfHeaderIssueNumber":actual_number,"documentedEditorialNumberAnomaly":documented_anomaly,
        "originalTitleMatched":bool(title),
        "titleTokenMatch":round(ratio,3) if ratio is not None else None}

def audit():
    manifest,indexed=load_manifest()
    byday={i["d"]:i for i in manifest["issues"]}
    candidates=manifest["candidates"]
    # Download each candidate and at least one PDF for every official issue.
    todo={}
    for issue in manifest["issues"]:
        code="2026-"+issue["ids"].split(",")[0]
        todo[code]=(issue["d"],issue["n"],code,None,None,None)
    for cand in candidates:
        # Recheck the title even when first issue PDF is also selected.
        todo[cand["id"]]=(cand["d"],cand["n"],cand["id"],cand["title"],cand["kind"],cand["entity"])
    print("ASTURIAS_REVISANDO",len(todo),"PDF originales, 22 sumarios, 32 candidatas y suplemento",flush=True)
    with ThreadPoolExecutor(max_workers=5) as pool:
        validated=list(pool.map(verify_original,todo.values()))
    bycode={x["id"]:x for x in validated}
    for issue in manifest["issues"]:
        code="2026-"+issue["ids"].split(",")[0]
        if code not in bycode or not bycode[code]["publisherDateAndCVEVerified"]:
            fail("sin original del día "+issue["d"])
        print("ASTURIAS_EDICION",issue["n"],issue["d"],len(issue["ids"].split(",")),code,flush=True)
    for cand in candidates:
        row=bycode.get(cand["id"])
        if not row or not row["originalTitleMatched"]:
            fail("falta original de convocatoria "+cand["id"])
        print("ASTURIAS_ORIGINAL",cand["id"],"titulo",row["titleTokenMatch"],flush=True)
    extra_url=f"https://{ORIGINAL_HOST}/bopa/2026/10/23/20261023Su1.pdf"
    supplement,pages,first=read_pdf(extra_url)
    if (len(supplement)!=122840 or pages!=1 or hashlib.sha256(supplement).hexdigest()!=SUPPLEMENT_SHA
        or not re.search(r"suplemento al num[.]\s*206 de 23-x-2026",fold(first[:500]))
        or SUPPLEMENT_CODE not in first
        or "cese" not in fold(first[:1200])):
        fail("suplemento 206S1 no verificado íntegramente: bloquear fuente")
    issues=[]
    for e in manifest["issues"]:
        d=date.fromisoformat(e["d"]);n=str(e["n"])
        notices=[]
        for cand in candidates:
            if cand["d"]!=e["d"]:continue
            notices.append({"id":"AS-"+cand["id"],"province":PROVINCE,
              "title":cand["title"],"entity":cand["entity"],
              "date":d.strftime("%d/%m/%Y"),"bulletin":n,
              "type":cand["kind"],"url":pdf_url(e["d"],cand["id"])})
        issues.append({"day":d,"number":n,"read":len(e["ids"].split(",")),"notices":notices})
    issues.append({"day":date(2026,10,23),"number":SUPPLEMENT_NO,"read":1,"notices":[]})
    feed=publish_audit(SOURCE,PROVINCE,issues,today=END,min_issues=23)
    h=feed["historyCoverage"]
    h["originalArchiveSHA256"]=manifest["inputSHA256"]
    h["indexManifestSHA256"]=MANIFEST_HASH
    h["indexEvidence"]=manifest["issues"]
    h["sourceMainIssues"]=22
    h["supplementIssues"]=1
    h["supplementEvidence"]={"date":SUPPLEMENT_DATE,"number":SUPPLEMENT_NO,
      "originalCode":SUPPLEMENT_CODE,"url":extra_url,"sha256":SUPPLEMENT_SHA,
      "pages":pages,"title":"Decreto 79/2026, cese de Director General de Agenda 2030",
      "classifiedAsEmployment":False}
    h["verifiedOriginalSamples"]=sorted(validated,key=lambda x:(x["day"],x["id"]))
    h["pdfHeaderEditorialDiscrepancies"]=[{"day":x["day"],"code":x["id"],
        "sumarioNumber":x["bulletin"],"originalPdfHeaderNumber":x["pdfHeaderIssueNumber"],
        "sha256":x["sha256"]} for x in validated if x["documentedEditorialNumberAnomaly"]]
    h["verifiedIssueRepresentatives"]=22
    h["verifiedCandidateOriginals"]=32
    h["indexedOriginalUrlsVerifiedFromPublisherIndex"]=917
    h["originalPdfHost"]=ORIGINAL_HOST
    h["frozenSnapshotAsOf"]=END.isoformat()
    if len(feed["notices"])!=32 or feed["coverage"]["announcementsRead"]!=918:
        fail("sumarios, suplemento o candidatas sin auditoría íntegra")
    write_output("out/AS.json",feed)
    return feed

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output",type=Path,required=True)
    args=p.parse_args()
    output=audit()
    if args.output!=Path("out/AS.json"):
        write_output(args.output,output)
