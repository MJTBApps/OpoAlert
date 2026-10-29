#!/usr/bin/env python3
"""DOGC Catalonia: audited 30-day official issues via the publisher's own API.

Reads the official DOGC calendar and all summaries, including annex A/B if any.
For each potential public-employment notice, obtains the official full text from
documentDOGC and validates the publisher's authenticity/integrity response.
Never replaces official source with aggregators or treats HTTP 200 as coverage.
The independent validation and Android compilation are separate gating steps.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from threading import local
import re
import ssl
import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup
from clm_common import employment, publish_audit, write_output
from provincial_common import ProvincialCoverageError, fold

SOURCE = "https://portaldogc.gencat.cat/eadop-rest/api/dogc/summaryDOGC"
BASE = "https://portaldogc.gencat.cat/eadop-rest/api/"
DOCUMENT_URL = "https://dogc.gencat.cat/ca/document-del-dogc/"
HOST = "portaldogc.gencat.cat"
PROVINCE = "Cataluña (DOGC)"
END = date(2026, 10, 29)
START = END - timedelta(days=29)
_thread = local()
DOC_RE = re.compile(r"\d{6,9}")
NUMBER_RE = re.compile(r"\d{4,5}[A-Z]?")
CVE_RE = re.compile(r"CVE-DOGC-[A-Z]-[A-Z0-9-]+-2026")
EXCLUDED = (
    "adjudicacio", "adjudicacion", "nomenament", "nombramiento", "cese",
    "cessament", "cesses", "trasllat", "traslado", "llista provisional",
    "llista definitiva", "admesos", "exclosos", "admitidos", "excluidos",
    "resultat", "resultado", "tribunal", "correccio d", "correccion de",
    "subvencio", "subvencion", "beca", "licitacio", "licitacion",
)
POSITIVE = ("convocatoria", "bases reguladores del proces selectiu", "bases del proces selectiu",
            "concurs oposicio", "oposicions", "proces selectiu", "borsa de treball",
            "borses de treball", "seleccio de personal", "places de personal",
            "oferta publica d'ocupacio", "oferta publica d'ocupacio", "funcionari de carrera")

def fail(msg):
    raise ProvincialCoverageError("DOGC: " + str(msg))

class OfficialTLSAdapter(HTTPAdapter):
    """Require trusted CA but permit the original publisher's legacy TLS1.2."""
    def init_poolmanager(self,*args,**kwargs):
        context = ssl.create_default_context()
        context.maximum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers("DEFAULT:@SECLEVEL=1")
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args,**kwargs)

def session():
    if not hasattr(_thread, "session"):
        s = requests.Session()
        s.mount("https://"+HOST, OfficialTLSAdapter())
        s.headers.update({
            "User-Agent": "Mozilla/5.0 (compatible; OpoAlert official DOGC source audit)",
            "Accept": "application/json,text/javascript,*/*;q=0.01",
            "Accept-Language": "ca,es;q=0.9",
            "Referer": "https://dogc.gencat.cat/ca/",
        })
        _thread.session = s
    return _thread.session

def request_json(endpoint, payload):
    if endpoint not in ("dogc/calendarDOGC", "dogc/summaryDOGC",
                        "dogc/documentDOGC", "suplement/summarySuplement"):
        fail("endpoint externo al API editorial")
    url = BASE+endpoint
    try:
        r = session().post(url, data=payload, timeout=(10,40), allow_redirects=False)
        if r.status_code != 200 or r.url != url or len(r.content)>3_000_000:
            fail(f"respuesta oficial invalida {endpoint}: HTTP {r.status_code}")
        obj = r.json()
        if not isinstance(obj,dict) or obj.get("errorCode"):
            fail(f"API DOGC devolvio error: {str(obj)[:200]}")
        return obj
    except (requests.RequestException, ValueError) as ex:
        fail(f"API DOGC inaccesible: {endpoint}: {str(ex)[:160]}")

def norm(s):
    return re.sub(r"\s+"," ",fold(str(s or ""))).strip()

def valid_pdf_ref(url):
    p = urlsplit(str(url or ""))
    q = parse_qs(p.query,keep_blank_values=True)
    if (p.scheme!="https" or p.hostname!=HOST or p.port not in (None,443)
        or p.username is not None or p.password is not None or p.fragment
        or p.path!="/utilsEADOP/AppJava/PdfProviderServlet"
        or set(q) != {"documentId","type","language"}
        or q["type"] != ["01"] or q["language"] != ["ca_ES"]
        or len(q["documentId"])!=1 or DOC_RE.fullmatch(q["documentId"][0]) is None):
        fail("enlace a documento individual no corresponde al editor")
    return q["documentId"][0]

def classify_conservative(title):
    s = norm(title)
    if any(ex in s for ex in EXCLUDED):
        return None
    kind = employment(title)
    if kind and any(ex in s for ex in ("resolucio d'adjudicacio","resolucio de nomenament")):
        return None
    if kind:
        return kind
    if not any(x in s for x in POSITIVE):
        return None
    if ("borsa de treball" in s or "borses de treball" in s):
        return "Bolsa de trabajo"
    if (any(x in s for x in ("convocatoria", "bases", "proces selectiu", "oposicions",
                              "concurs oposicio", "oferta publica d'ocupacio"))
        and any(x in s for x in ("places", "placa", "personal", "funcionar", "treball",
                                  "ocupacio", "llocs", "seleccio"))):
        return "Plaza / oposición"
    return None

def calendars():
    records={}
    for month in (9,10):
        d=request_json("dogc/calendarDOGC",
            {"month":str(month),"year":"2026","language":"ca"})
        rows=d.get("calendar")
        if not isinstance(rows,list) or len(rows)!=(30 if month==9 else 31):
            fail("calendario mensual oficial truncado")
        for entry in rows:
            if not isinstance(entry,dict) or not isinstance(entry.get("hasDOGC"),bool):
                fail("estructura de calendario inesperada")
            try:day=datetime.strptime(entry["date"],"%d/%m/%Y").date()
            except Exception:fail("calendario con fecha no valida")
            if day.year!=2026 or day.month!=month or day in records:
                fail("fecha repetida o fuera del calendario")
            numbers=re.findall(r"(?:numDOGC=)(\d{4,5})",str(entry.get("linkDOGC",""))) if entry["hasDOGC"] else []
            if (entry["hasDOGC"] and len(numbers)!=1) or (not entry["hasDOGC"] and numbers):
                fail("calendario sin identificador de diario")
            records[day]=(numbers[0] if entry["hasDOGC"] else None)
    selected=[(START+timedelta(days=i),records[START+timedelta(days=i)]) for i in range(30)]
    dates=[day for day,n in selected if n is not None]
    nums=[int(n) for _,n in selected if n is not None]
    if (not dates or dates[0]!=START or dates[-1]!=END or len(dates)!=23
        or nums!=list(range(9761,9784))):
        fail("calendario DOGC 30 dias incompleto o numeros no consecutivos")
    return selected

def flatten(node):
    """Read every original summary document even when grouped into subheaders."""
    out=[]
    def visit(x):
        if isinstance(x,list):
            for v in x:visit(v)
        elif isinstance(x,dict):
            if "linkDownloadDocumentPDF" in x or ("title" in x and "documentId" in x):
                title=" ".join(str(x.get("title") or "").split())
                if not title:
                    fail("disposicion original sin titulo")
                did=valid_pdf_ref(x.get("linkDownloadDocumentPDF"))
                out.append((did,title))
                return
            for k,v in x.items():
                if isinstance(v,(list,dict)):visit(v)
    visit(node)
    if not out or len(out)>350 or len({x[0] for x in out})!=len(out):
        fail("indice de documentos vacio, repetido o demasiado grande")
    return out

def official_original(task):
    did,title,day,issue,kind=task
    data=request_json("dogc/documentDOGC",{"documentId":did,"language":"ca"})
    meta=data.get("documentData")
    verification=data.get("authenticityIntegrity")
    if not isinstance(meta,dict) or not isinstance(verification,dict):
        fail(f"documento {did}: metadatos/autenticidad ausentes")
    if (str(meta.get("numDOGC"))!=issue
        or meta.get("dateDOGC")!=day.strftime("%d/%m/%Y")
        or not str(meta.get("issuingAuthority") or "").strip()
        or not CVE_RE.fullmatch(str(meta.get("CVE") or ""))
        or meta.get("tipusDiari") not in ("DOGC",None)):
        fail(f"documento {did}: fecha/numero/CVE/editor no coinciden")
    autentic=norm(verification.get("result"))
    if not (("satisfact" in autentic) and ("autentic" in autentic) and ("integr" in autentic)):
        fail(f"documento {did}: autenticidad original no verificada")
    original_title=" ".join(str(data.get("titleDocument") or "").split())
    if not original_title or not (norm(title)[:45] in norm(original_title)
                                  or norm(original_title)[:45] in norm(title)):
        fail(f"documento {did}: titulo no coincide con sumario")
    text=BeautifulSoup(str(data.get("textDocument") or ""),"html.parser").get_text(" ",strip=True)
    if len(text)<110:
        fail(f"documento {did}: texto oficial original no recuperado")
    url=DOCUMENT_URL+"?documentId="+did
    return ({
      "id":f"DC-2026-{did}","province":PROVINCE,"title":title,
      "entity":" ".join(str(meta["issuingAuthority"]).split()),"date":day.strftime("%d/%m/%Y"),
      "bulletin":issue,"type":kind,"url":url
    }, {"id":did,"cve":meta["CVE"],"issue":issue,"date":day.isoformat(),
        "textChars":len(text),"authenticityVerified":True})

def collect_main(number,day):
    response=request_json("dogc/summaryDOGC",{"numDOGC":number,"language":"ca"})
    summaries=response.get("sumaris")
    if not isinstance(summaries,list) or not 1<=len(summaries)<=8:
        fail(f"numero {number}: ausencia de sumarios principales/anexos")
    ids=[]
    issued=[]
    tasks=[]
    supplement=None
    for i,entry in enumerate(summaries):
        if not isinstance(entry,dict):fail("sumario no estructurado")
        issue=str(entry.get("numDOGC") or "")
        if NUMBER_RE.fullmatch(issue) is None or not issue.startswith(number):
            fail("sumario/numero discrepantes")
        if i==0 and issue!=number:
            fail("el primer sumario no es la edicion principal")
        if entry.get("dateDOGC")!=day.strftime("%d/%m/%Y"):
            fail(f"edicion {issue}: fecha distinta al calendario")
        pdf=str(entry.get("linkDownloadDOGCPDF") or "")
        if not (pdf.startswith("https://"+HOST+"/utilsEADOP/AppJava/PdfProviderServlet?")
            and f"dogcId={issue}" in pdf):
            fail(f"edicion {issue}: no hay enlace de documento editorial")
        articles=flatten(entry.get("section"))
        if any(did in ids for did,_ in articles):
            fail("anuncio repetido entre edicion y anexo")
        ids.extend(did for did,_ in articles)
        for did,title in articles:
            kind=classify_conservative(title)
            if kind:
                tasks.append((did,title,day,issue,kind))
        issued.append({"day":day,"number":issue,"read":len(articles),"notices":[]})
        sup=entry.get("numSuplement")
        if i==0 and sup is not None:
            if not re.fullmatch(number+r"SN",str(sup)):
                fail("identificador de suplemento no corresponde al diario")
            supplement=str(sup)
        if i>0 and sup is not None:
            fail("anexo con suplemento inesperado")
    return issued,tasks,{"date":day.isoformat(),"main":number,
                          "editions":[x["number"] for x in issued],
                          "counts":[x["read"] for x in issued],
                          "originalIds":ids,"supplement":supplement}

def collect_supplement(meta):
    supplement=meta.get("supplement")
    if not supplement:
        return None
    date_value=date.fromisoformat(meta["date"])
    response=request_json("suplement/summarySuplement",
            {"numSuplement":supplement,"language":"ca"})
    body=response.get("suplementData")
    if not isinstance(body,dict) or body.get("numSuplement")!=supplement:
        fail("suplemento de notificaciones ausente o cambiado")
    s=norm(body.get("dateSuplement"))
    m=re.search(r"\b(\d{1,2})\s+d['e]\s*(setembre|octubre)\s+de\s+2026\b",s)
    if not m or int(m[1])!=date_value.day or (9 if m[2]=="setembre" else 10)!=date_value.month:
        fail("fecha del suplemento no corresponde al DOGC oficial")
    linked=response.get("dogcRelacionats")
    if (not isinstance(linked,list) or
        set(str(row.get("dogc")) for row in linked)!=set(meta["editions"])):
        fail("el suplemento no coincide con las ediciones y anexos del DOGC")
    pdf=str(response.get("linkDownloadSuplementPDF") or "")
    if not pdf.startswith("https://"+HOST+"/utilsEADOP/AppJava/PdfProviderServlet?") or "dogcId="+supplement not in pdf:
        fail("referencia al suplemento PDF original no acreditada")
    documents=flatten(body.get("section"))
    notices=[]
    for did,title in documents:
        kind=classify_conservative(title)
        if kind is not None:
            # Supplemental notification pages may still contain a genuinely new
            # employment notice: never silently discard one.
            notices.append((did,title,date_value,supplement,kind))
    return {"day":date_value,"number":supplement,"read":len(documents),"notices":[]}, notices, documents

def audit():
    days=calendars()
    with ThreadPoolExecutor(max_workers=5) as pool:
        groups=list(pool.map(lambda item:collect_main(item[1],item[0]),[
            item for item in days if item[1] is not None]))
    all_editions=[edition for editions,_,_ in groups for edition in editions]
    tasks=[task for _,items,_ in groups for task in items]
    summaries=[summary for _,_,summary in groups]
    with ThreadPoolExecutor(max_workers=5) as pool:
        supplementary=list(pool.map(collect_supplement,summaries))
    extra_sections=0
    for entry,meta in zip(supplementary,summaries):
        if entry is None:
            continue
        issue,extra_candidates,all_documents=entry
        all_editions.append(issue)
        tasks.extend(extra_candidates)
        extra_sections+=1
        meta["supplementCount"]=len(all_documents)
        meta["supplementIds"]=[did for did,_ in all_documents]
    if len({task[0] for task in tasks})!=len(tasks):
        fail("documento candidato repetido en varios boletines")
    originals=[]
    with ThreadPoolExecutor(max_workers=5) as pool:
        validated=list(pool.map(official_original,tasks))
    by_issue={x["number"]:x for x in all_editions}
    for notice,meta in validated:
        by_issue[notice["bulletin"]]["notices"].append(notice)
        originals.append(meta)
    for i in summaries:
        print("DOGC",i["date"],"/".join(i["editions"]),
              "anuncios",sum(i["counts"]),
              "candidatas",sum(len(by_issue[k]["notices"]) for k in i["editions"]),flush=True)
    feed=publish_audit(SOURCE,PROVINCE,all_editions,today=END,min_issues=23)
    h=feed["historyCoverage"]
    h["calendarEvidence"]=[{"date":d.isoformat(),"mainBulletin":n} for d,n in days]
    h["sumariosVerificados"]=summaries
    h["candidateOriginalEvidence"]=originals
    h["originalCandidateDocumentsVerified"]=len(originals)
    h["mainIssues"]=23
    h["annexIssues"]=len(all_editions)-23-extra_sections
    h["supplementsAudited"]=extra_sections
    if extra_sections!=sum(bool(i["supplement"]) for i in summaries):
        fail("sumarios de suplementos del editor incompletos")
    write_output(Path("out/DC.json"),feed)
    return feed

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    value=audit()
    # Only written once a complete validated, internally consistent feed exists.
    if args.output!=Path("out/DC.json"):write_output(args.output,value)
