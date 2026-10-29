#!/usr/bin/env python3
"""Check potential missing publicly served official Jaen issues by catalogue ID.

This only inspects neighboring public textual records, never private files.
Every recovered edition must have a matching publisher-issued PDF, number and
date; guessed IDs are not taken as evidence of complete coverage.
"""
from concurrent.futures import ThreadPoolExecutor
import requests,re
ROOT="https://bophistorico.dipujaen.es"
IDS=list(range(1747453,1747473))
def check(num):
 id_=f"{num:010d}"
 url=f"{ROOT}/text.vm?id={id_}&view=boletin"
 try:
  r=requests.get(url,timeout=(10,18),headers={"User-Agent":"Mozilla/5.0"})
  s=r.content.decode("utf-8","replace")
  m=re.search(r"(?im)^\s*N[uú]mero\s*:?\s*(\d{2,3})\s*$",s[:600])
  issue=m.group(1) if m else "-"
  date=re.search(r"(?i)\b\d{1,2} de octubre de 2026\b",s[:450])
  is_bop="ADMINISTRACIÓN LOCAL" in s[:2000] and "2026" in s[:500]
  print("CANDIDATE",id_,r.status_code,"SIZE",len(r.content),"BOP",issue,
        "DATE",date.group() if date else "-", "LIKELY",is_bop,"HEAD",repr(s[:110]),flush=True)
  if issue in ("198","199","201") and date:
    pdf=f"{ROOT}/high.raw?id={id_}&name=00000001.original.pdf&attachment={id_}.pdf"
    pr=requests.get(pdf,timeout=(10,22),stream=True)
    data=next(pr.iter_content(100),b"")
    print("POSSIBLE_MISSING",id_,issue,date.group(),pr.status_code,
          pr.headers.get("Content-Type"),repr(data[:15]),pdf,flush=True)
    pr.close()
 except Exception as exc:print("ERROR",id_,type(exc).__name__,str(exc)[:180],flush=True)
with ThreadPoolExecutor(max_workers=3) as p:list(p.map(check,IDS))
