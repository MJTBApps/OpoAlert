#!/usr/bin/env python3
"""Audit official BOPA supplement from captured 23 October 2026 summary.
Never assume a main-edition-only audit covers supplements."""
import requests,io,hashlib,json,re
from pypdf import PdfReader
URL="https://www.asturias.es/bopa/2026/10/23/20261023Su1.pdf"
r=requests.get(URL,timeout=(8,45),headers={"User-Agent":"Mozilla/5.0 (compatible; OpoAlert BOPA supplement audit)"})
print("SUPPLEMENT_HTTP",r.status_code,"host",r.url,"mime",r.headers.get("Content-Type"),"bytes",len(r.content),flush=True)
if r.status_code!=200 or not r.content.startswith(b"%PDF-") or len(r.content)>55_000_000:
 raise SystemExit("El suplemento no es un PDF original accesible: FAIL_CLOSED")
pdf=PdfReader(io.BytesIO(r.content),strict=False)
first=(pdf.pages[0].extract_text() or "")[:6500]
last=(pdf.pages[-1].extract_text() or "")[:1800]
print("SUPPLEMENT_ORIGINAL",json.dumps({"url":r.url,"sha256":hashlib.sha256(r.content).hexdigest(),
 "pages":len(pdf.pages),"first":first,"last":last,"hasEmploymentWords":bool(re.search(r"convocatori|bolsa|plaza|empleo",first+" "+last,re.I))},ensure_ascii=True)[:18000],flush=True)
