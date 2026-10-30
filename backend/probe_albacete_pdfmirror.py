#!/usr/bin/env python3
"""Check publisher-hosted Albacete BOP PDF mirror, without guessing coverage.

Official BOE references establish issue 114 (30 Sep), 116 (5 Oct) and
117 (7 Oct) 2026. This merely checks the Diputacion's older static URL pattern.
"""
from __future__ import annotations
import json
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from urllib.parse import urlsplit

HOST="www.dipualba.es"
PATH="https://www.dipualba.es/bop/ficheros"
TARGETS={
 "known_2025_control": f"{PATH}/2025/106/BOP%20106-25-P.PDF",
 "issue_114_2026": f"{PATH}/2026/114/BOP%20114-26-P.PDF",
 "issue_116_2026": f"{PATH}/2026/116/BOP%20116-26-P.PDF",
 "issue_117_2026": f"{PATH}/2026/117/BOP%20117-26-P.PDF",
 "issue_117_page_4": f"{PATH}/2026/117/BOP%20117-26-P-4.PDF",
}
def allowed(url):
 p=urlsplit(url)
 return p.scheme=="https" and p.hostname==HOST and p.username is None and p.password is None and p.port in (None,443)
def check(item):
 name,url=item
 obj={"name":name,"url":url,"audited30Days":False}
 try:
  req=Request(url,headers={"User-Agent":"Mozilla/5.0","Accept":"application/pdf"})
  with urlopen(req,timeout=12) as r:
   if not allowed(r.geturl()):
    obj["status"]="nonofficial_redirect"
   else:
    data=r.read(24)
    obj.update({"status":"official_pdf_header" if data.startswith(b"%PDF-") else "invalid_pdf_header",
                "http":r.status,"type":r.headers.get("Content-Type","")[:80],
                "sampleBytes":len(data)})
 except HTTPError as e:obj.update({"status":"http_error","http":e.code})
 except (URLError, OSError, TimeoutError) as e:obj.update({"status":"connection_error","error":type(e).__name__})
 return obj
def main():
 assert all(allowed(v) for v in TARGETS.values())
 for name,url in TARGETS.items():
  print("ALBACETE_STATIC",json.dumps(check((name,url)),ensure_ascii=False),flush=True)
 print("ONLY A PDF SIGNATURE PROBE; NOT A 30-DAY AUDIT",flush=True)
if __name__=="__main__":main()
