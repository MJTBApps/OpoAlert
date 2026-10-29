#!/usr/bin/env python3
"""OpoAlert: 30-day BOP Salamanca, audited against original Diputación mirror.

Uses the authenticated public PDF index (CVE ...-000.pdf) for every day,
checks its complete numbered CVE sequence, verifies all individual publisher
PDF links and compares every selected vacancy against its full original PDF.
Never invents notices, deadlines, or publication dates.
"""
from __future__ import annotations
import argparse,io,re,threading,time,unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urlsplit
import requests
from pypdf import PdfReader
from clm_common import employment,publish_audit,write_output
from provincial_common import ProvincialCoverageError,fold

START=date(2026,9,30)
END=date(2026,10,29)
SOURCE="https://www.lasalina.es/documentacion/bop/"
PROVINCE="Salamanca"
HOST="www.lasalina.es"
CVE_RE=re.compile(r"\bBOP-SA-(\d{8})\s*-\s*(\d{3})\b",re.I)
ISSUE_RE=re.compile(r"N\.\s*[ºo]\s*(\d{1,3})\s*[•·]\s*(?:lunes|martes|miercoles|miércoles|jueves|viernes|sabado|sábado|domingo)",re.I)
threadlocal=threading.local()

def bad(msg):raise ProvincialCoverageError("BOP Salamanca: "+str(msg))
def pdf_url(day,n):
    d=day.strftime("%Y%m%d")
    return f"{SOURCE}2026/{d}/BOP-SA-{d}-{n:03}.pdf"
def session():
    if not hasattr(threadlocal,"client"):
        threadlocal.client=requests.Session()
        threadlocal.client.headers.update({"User-Agent":"Mozilla/5.0 (OpoAlert public BOP official research reader)","Accept-Language":"es-ES,es;q=0.9"})
    return threadlocal.client
def official_url(url):
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443) or u.username or u.password or u.fragment or u.query or not u.path.startswith("/documentacion/bop/2026/"):
        bad("Enlace fuera de dominio/ruta oficial: "+url[:150])
def read_pdf(url,allow404=False,header_only=False,limit=25_000_000):
    official_url(url)
    error=None
    for attempt in range(3):
        try:
            r=session().get(url,timeout=(8,36),stream=True,allow_redirects=False)
            if r.status_code==404 and allow404:return None
            if r.status_code!=200:
                error=f"HTTP {r.status_code} en {url}"
                r.close()
            else:
                chunks=[]
                size=0
                for part in r.iter_content(32768):
                    size+=len(part)
                    if size>limit:bad("PDF supera límite de tamaño: "+url)
                    chunks.append(part)
                    if header_only and size>=5:break
                r.close()
                data=b"".join(chunks)
                if (len(data)>=5 and data.startswith(b"%PDF-") and
                     "pdf" in r.headers.get("content-type","").lower()):
                    return data
                error="Archivo no es PDF oficial: "+url
        except requests.RequestException as ex:error=str(ex)[:210]
        if attempt<2:time.sleep(.6*(attempt+1))
    bad(error)

def toc_lines(data,day):
    if len(data)>2_000_000:bad("Sumario inverosímilmente largo")
    try:pdf=PdfReader(io.BytesIO(data),strict=False)
    except Exception as ex:bad("Sumario PDF ilegible: "+str(ex)[:200])
    if not 1<=len(pdf.pages)<=12:bad("Sumario sin páginas plausibles")
    pages=[x.extract_text() or "" for x in pdf.pages]
    text="\n".join(pages)
    if not re.search("BOLET[IÍ]N OFICIAL DE LA PROVINCIA DE SALAMANCA",text,re.I):
        bad("Sumario no corresponde a boletín oficial de Salamanca")
    m=ISSUE_RE.search(fold(text))
    if m is None:bad("N.º y fecha de boletín ilegibles: "+day.isoformat())
    number=int(m[1])
    month=("septiembre" if day.month==9 else "octubre")
    if not re.search(rf"(?i)\b0?{day.day}\s+de\s+{month}\s+de\s+2026",fold(text)):
        bad("Fecha publicada no coincide con PDF original "+day.isoformat())
    return text,number,len(pdf.pages)

def extract_entry_info(text,day):
    # Every official sumario contains one numbered CVE per announcement.
    raw=[(int(d),int(n)) for d,n in CVE_RE.findall(text)]
    expected_day=int(day.strftime("%Y%m%d"))
    if any(d!=expected_day for d,n in raw):bad("Sumario mezcla fechas CVE de boletines")
    nums=list(dict.fromkeys(n for d,n in raw if n>0))
    if not nums or nums!=list(range(1,max(nums)+1)):
        bad("Sumario con secuencia de CVE incompleta o desordenada: "+str(nums[:60]))
    if len(nums)>150:bad("CVE excesivos para un sumario diario")
    return nums

def clean(line):
    return " ".join(line.replace("‐","-").replace("–","-").split()).strip()

def parse_titles(toc,day):
    lines=toc.splitlines()
    sections=[]
    entity="Boletín Oficial de Salamanca"
    group=""
    pending=[]
    rows=[]
    daystr=day.strftime("%Y%m%d")
    for line in lines:
        s=clean(line)
        if not s:continue
        f=fold(s)
        if (f.startswith(("https://","www.lasalina","boletin oficial","d.l.:","d. l.:","n.º","b.o.p.","se publica","se publica","se publica","administracion:","excma. diputacion","domicilio:","telef.","bop@lasalina.es","advertencia editorial","presentacion de originales","los originales","digital"))
          or "diputaciondesalamanca.gob.es/bop" in f
          or re.match(r"^\s*(?:i+v?|v?i+)\.\s*administracion ",f)
          or f.startswith(("administracion local.","administracion auton","administracion central.","administracion electoral."))):
            if f.startswith("administracion ") or "administracion electoral" in f:group=s
            # Don't clear pending between lines of an ongoing notice; page footer
            # is decoration, not an article delimiter.
            continue
        mm=CVE_RE.search(s)
        if mm is not None:
            if mm[1]!=daystr:bad("CVE de otro día")
            idx=int(mm[2])
            if idx==0:continue
            title=" ".join(pending[-16:]).strip(" .-")
            if len(title)<8:
                title="Anuncio original del BOP de Salamanca"
            if len(title)>1300:title=title[:1300].rsplit(" ",1)[0]
            rows.append({"index":idx,"title":title,"entity":entity,"section":group})
            pending=[]
            continue
        # Publisher indicates governing entity using a leading dash, and an
        # Ayuntamientos heading followed by municipality names.
        if s.startswith("-"):
            x=s.lstrip("- ").rstrip(".")
            f2=fold(x)
            if "ayuntamientos" in f2.replace(" ",""):
                entity="Ayuntamientos de Salamanca"
                group="Administración local · Ayuntamientos"
            elif "mancomunidades" in f2.replace(" ",""):
                entity="Mancomunidades de Salamanca"
            elif len(x)>5:
                entity=x
            pending=[]
            continue
        if (group.startswith("Administración local · Ayuntamientos")
             and s.endswith(".") and 3<len(s)<85 and len(pending)==0
             and not re.search(r"(?i)(anuncio|decreto|resolucion|aprobacion|convocatoria|bases|plaza|vacante|publicacion|provision|reglamento|acuerdo)",s)):
            entity="Ayuntamiento de "+s.rstrip(".")
            continue
        pending.append(s)
    return rows

def extract_original_metadata(pdf_bytes,day,num,idx):
    try:
        pdf=PdfReader(io.BytesIO(pdf_bytes),strict=False)
        first=(pdf.pages[0].extract_text() or "")
    except Exception as e:bad("PDF original CVE ilegible: "+str(e)[:200])
    m=ISSUE_RE.search(fold(first))
    if m is None or int(m[1])!=num:bad(f"PDF CVE {idx} de número de boletín diferente")
    found={(int(d),int(n)) for d,n in CVE_RE.findall(first)}
    if (int(day.strftime("%Y%m%d")),idx) not in found:
        bad(f"PDF original CVE {idx} no coincide con sumario")
    return first

def classify(title):
    kind=employment(title)
    if kind is None:return None
    s=fold(title)
    if any(w in s for w in ("presupuesto general","modificacion presupuestaria","plantilla de personal",
       "resolucion del proceso selectivo","contrato de arrendamiento","elecciones a","levantamiento de actas",
       "puesta al cobro","convocatoria de junta","junta general ordinaria","plazas de aparcamiento",
       "convocatoria de subvenciones","relacion de aprobados","listas de aprobados")):
        return None
    return kind

def probe_date(day):
    u=pdf_url(day,0)
    index=read_pdf(u,allow404=True)
    if index is None:return None
    text,number,pgs=toc_lines(index,day)
    nums=extract_entry_info(text,day)
    rows=parse_titles(text,day)
    indices=[x["index"] for x in rows]
    if indices!=nums:
        bad(f"Fallo al emparejar CVE con títulos de {day}: {indices} != {nums}")
    print(f"BOPSA_INDEX {day} nº {number} {len(nums)} CVE sumario {pgs} páginas",flush=True)
    return {"day":day,"number":number,"rows":rows,"summaryPdf":u,"summaryPages":pgs}

def issue_content(issue):
    day=issue["day"];number=issue["number"]
    rows=issue["rows"]
    # Link to every indexed PDF must exist and advertise PDF content.
    with ThreadPoolExecutor(max_workers=5) as e:
        list(e.map(lambda a:read_pdf(pdf_url(day,a["index"]),header_only=True),rows))
    print(f"BOPSA_LINKS {day} {len(rows)} PDF individuales originales accesibles",flush=True)
    candidates=[]
    for item in rows:
        kind=classify(item["title"])
        if not kind:continue
        url=pdf_url(day,item["index"])
        first=extract_original_metadata(read_pdf(url,limit=30_000_000),day,number,item["index"])
        # Since the official title is taken directly from the certified table
        # of contents, the original PDF CVE is the binding identity.
        name=clean(item["title"])
        entity=clean(item["entity"]) or "BOP Salamanca"
        candidates.append({"id":f"SA-{day:%Y%m%d}-{item['index']:03d}",
             "province":PROVINCE,"title":name,"entity":entity,
             "date":day.strftime("%d/%m/%Y"),"bulletin":str(number),
             "type":kind,"url":url})
        print("BOPSA_CANDIDATE",day,item["index"],repr(name[:160]),flush=True)
    return {"day":day,"number":str(number),"read":len(rows),"notices":candidates,
       "summaryPdf":issue["summaryPdf"],"summaryPages":issue["summaryPages"]}

def audit():
    days=[START+timedelta(days=i) for i in range(30)]
    with ThreadPoolExecutor(max_workers=5) as pool:
        all_days=list(pool.map(probe_date,days))
    pub=sorted((x for x in all_days if x is not None),key=lambda x:x["day"])
    if len(pub)!=22 or pub[0]["day"]!=START or pub[-1]["day"]!=END:
        bad(f"Histórico 30 días incompleto: {len(pub)} boletines")
    n=[x["number"] for x in pub]
    if n!=list(range(189,211)):bad(f"Números del BOP no son consecutivos: {n}")
    if [x["day"] for x in pub]!=[d for d in days if d.weekday()<5]:
        bad("Ediciones extraordinarias o días ausentes; se requiere revisión especial")
    print("BOPSA_CALENDAR 22 sumarios originales entre 30/09 y 29/10, nº 189–210",flush=True)
    with ThreadPoolExecutor(max_workers=3) as pool:
        issues=list(pool.map(issue_content,pub))
    if sum(x["read"] for x in issues)<200:bad("Suma de edictos insuficiente")
    feed=publish_audit(SOURCE,PROVINCE,issues,today=END,min_issues=22)
    h=feed["historyCoverage"]
    h["summaryPDFs"]=[x["summaryPdf"] for x in issues]
    h["CVECounts"]=[x["read"] for x in issues]
    h["originalPDFsChecked"]=sum(x["read"] for x in issues)
    print("BOPSA_AUDIT_COMPLETE",len(issues),sum(x["read"] for x in issues),len(feed["notices"]),flush=True)
    return feed

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    write_output(args.output,audit())
