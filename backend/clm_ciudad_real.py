#!/usr/bin/env python3
"""BOP Ciudad Real, TLS certificate chain repaired from official GlobalSign HTTPS."""
from __future__ import annotations
import argparse,re,certifi,requests,tempfile
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urljoin,urlsplit,parse_qs
from concurrent.futures import ThreadPoolExecutor
from bs4 import BeautifulSoup
from cryptography import x509
from cryptography.hazmat.primitives import serialization
from clm_common import invalid,get,pdf_header,record,publish_audit,write_output,numbering_ok

HOME="https://bop.dipucr.es"
SOURCE=HOME+"/"
HOST={"bop.dipucr.es"}
PDF_HOST={"se1.dipucr.es"}
CA_ISSUER="https://secure.globalsign.com/cacert/gsgccr6alphasslca2025.crt"
ISSUER="CN=GlobalSign GCC R6 AlphaSSL CA 2025,O=GlobalSign nv-sa,C=BE"
DAY=re.compile(r"^/bop/(\d{4})/(\d{2})/(\d{2})$")
NUM=re.compile(r"Bolet[ií]n\s+Oficial\s+de\s+la\s+Provincia\s+(\d{1,3})\s*·",re.I)
CA_BUNDLE=None

def trusted_bundle():
    global CA_BUNDLE
    if CA_BUNDLE:return CA_BUNDLE
    r=requests.get(CA_ISSUER,timeout=(8,25),verify=True)
    if r.status_code!=200 or len(r.content)>10000:invalid("GlobalSign: certificado no disponible")
    try:cert=x509.load_der_x509_certificate(r.content)
    except ValueError:cert=x509.load_pem_x509_certificate(r.content)
    if cert.subject.rfc4514_string()!=ISSUER:
        invalid("GlobalSign: certificado intermedio con emisor inesperado")
    from datetime import datetime,timezone
    if not (cert.not_valid_before_utc<datetime.now(timezone.utc)<cert.not_valid_after_utc):
        invalid("GlobalSign: certificado no vigente")
    ca_bytes=cert.public_bytes(serialization.Encoding.PEM)
    bundle=tempfile.NamedTemporaryFile("wb",prefix="opoalert-cr-ca-",suffix=".pem",delete=False)
    with bundle as h:
        h.write(Path(certifi.where()).read_bytes()+b"\n"+ca_bytes)
    CA_BUNDLE=bundle.name
    # A partir de aquí OpenSSL verifica la identidad y firma del servidor;
    # nunca se usa verify=False para indexar anuncios.
    return CA_BUNDLE

def cr_get(url):
    return get(url,HOST,verify=trusted_bundle())

def issue_url(d):
    return f"{HOME}/bop/{d:%Y/%m/%d}"

def archive(html,start,end):
    s=BeautifulSoup(html,"html.parser")
    dates=set()
    for a in s.select('a[href^="/bop/"]'):
        u=urlsplit(urljoin(HOME,a["href"]))
        m=DAY.fullmatch(u.path)
        if not m:continue
        d=date(*map(int,m.groups()))
        if start<=d<=end:dates.add(d)
    return sorted(dates)

def pdf_url(url):
    u=urlsplit(url)
    q=parse_qs(u.query)
    if (u.scheme!="https" or u.hostname not in PDF_HOST or u.port!=4443 or
        u.path!="/SIGEM_BuscadorDocsWeb/getDocument.do" or u.fragment or
        q.get("entidad")!=["005"] or not re.fullmatch(r"\d{1,9}",q.get("doc",[""])[0])):
        invalid("PDF SIGEM no procede de la Diputación de Ciudad Real")
    return url

def parse_issue(html,day):
    soup=BeautifulSoup(html,"html.parser")
    title=soup.title.get_text(" ",strip=True) if soup.title else ""
    match=NUM.search(title)
    if match is None:invalid("Ciudad Real: número BOP no identificado")
    number=int(match[1])
    if not 1<=number<=366:invalid("Ciudad Real: número BOP imposible")
    # El <h2> del portal puede indicar el último boletín global, aunque se
    # consulte una edición histórica. Validar la fecha del título del BOP.
    mdate=re.search(r"\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+(\d{4})",title,re.I)
    months=("enero","febrero","marzo","abril","mayo","junio","julio","agosto","septiembre","octubre","noviembre","diciembre")
    if not mdate:
        invalid("Ciudad Real: fecha del título oficial ausente")
    observed=date(int(mdate[3]),months.index(mdate[2].lower())+1,int(mdate[1]))
    if observed!=day:
        invalid(f"Ciudad Real: edición de {observed} solicitada para {day}")
    all_rows=[]
    agency=""
    for node in soup.select("#boletin h3.admons, #boletin p.clasificaciones, #boletin ul.anuncios"):
        if node.name in ("h3","p"):
            agency=node.get_text(" ",strip=True)
            continue
        for item in node.select("li[id]"):
            idstr=item.get("id","")
            if not idstr.isdigit():invalid("Ciudad Real: ID del anuncio inválido")
            num=int(idstr)
            a=next((x for x in item.select('a[href]') if x.get_text(" ",strip=True)),None)
            if a is None or not agency:invalid("Ciudad Real: anuncio sin título o organismo")
            title=" ".join(a.get_text(" ",strip=True).split())
            row=record("CR","Ciudad Real",f"CR-{day.year}-{num}",title,agency,day,number,pdf_url(a["href"]))
            if (item.select_one("span.nAnuncio") is None or
                not re.search(rf"\b{num}\b",item.select_one("span.nAnuncio").get_text(" ",strip=True))):
                invalid("Ciudad Real: no coincide identificador en texto de anuncio")
            all_rows.append(row)
    if not all_rows or len({x["id"] for x in all_rows})!=len(all_rows):
        invalid("Ciudad Real: edición sin anuncios o con duplicaciones")
    return {"day":day,"number":str(number),"read":len(all_rows),
      "notices":[row for row in all_rows if row["type"]],
      "sample":all_rows[0]["url"]}

def scan(day):
    item=parse_issue(cr_get(issue_url(day)).text,day)
    pdf_header(item["sample"],PDF_HOST)
    print("CIUDAD REAL",day,"boletín",item["number"],"anuncios",item["read"],
       "candidatas",len(item["notices"]),flush=True)
    return item

def audit(today=None):
    end=today or date.today()
    start=end-timedelta(days=29)
    dates=set()
    for d in {start,end}:
        dates.update(archive(cr_get(issue_url(d)).text,start,end))
    if len(dates)<15:invalid(f"Ciudad Real: calendario de 30 días insuficiente: {len(dates)}")
    with ThreadPoolExecutor(max_workers=3) as pool:
        items=list(pool.map(scan,sorted(dates)))
    if not numbering_ok([(x["day"],int(x["number"])) for x in items]):
        invalid(f"Ciudad Real: faltan números de BOP {[x['number'] for x in items]}")
    return publish_audit(SOURCE,"Ciudad Real",items,today=end)

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    write_output(args.output,audit())
