#!/usr/bin/env python3
"""Print *official* BOP Salamanca TOC text around CVEs to derive reader."""
import requests,io,re
from pypdf import PdfReader
for day in ("20261007","20261012","20261016","20261028","20261029"):
 url=f"https://www.lasalina.es/documentacion/bop/2026/{day}/BOP-SA-{day}-000.pdf"
 try:
  r=requests.get(url,timeout=(8,20))
  print("SA_TOC",day,r.status_code,len(r.content),flush=True)
  if r.status_code!=200 or not r.content.startswith(b"%PDF-"):continue
  doc=PdfReader(io.BytesIO(r.content),strict=False)
  for j,page in enumerate(doc.pages[:6]):
   t=(page.extract_text() or "")
   lines=t.splitlines()
   print("SA_TOC_PAGE",day,j,"lines",len(lines),flush=True)
   for n,line in enumerate(lines):
    if n>230: break
    print(f"SA_TOC_LINE {day} {j}:{n:03} {line[:360]}",flush=True)
 except Exception as e:print("SA_TOC_ERR",day,type(e).__name__,str(e)[:160],flush=True)
