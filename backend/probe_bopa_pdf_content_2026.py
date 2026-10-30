#!/usr/bin/env python3
"""Independent original-PDF sample for BOPA; no feed activated."""
import base64,gzip,hashlib,json,requests,re,io
from pathlib import Path
from pypdf import PdfReader
DATA=Path("backend/snapshots/AS_index_20261029.json.gz.b64")
expected="91fbec5def3cd9316bb3b206da3e51b6f8a26de6bad358e2fd17d6daa6062f22"
encoded=DATA.read_text(encoding="ascii").strip()
raw=gzip.decompress(base64.b64decode(encoded,validate=True))
print("MANIFEST_SHA256",hashlib.sha256(raw).hexdigest(),"expected",expected,flush=True)
if hashlib.sha256(raw).hexdigest()!=expected:raise ValueError("Index manifest corrupt: do not proceed")
data=json.loads(raw)
print("MANIFEST_COUNTS",len(data["issues"]),sum(len(i["ids"].split(",")) for i in data["issues"]),len(data["candidates"]),flush=True)
bydate={i["d"]:i for i in data["issues"]}
targets=[("candidate",data["candidates"][0]["d"],data["candidates"][0]["id"]),
 ("candidate",data["candidates"][-1]["d"],data["candidates"][-1]["id"])]
for i in (0,8,11,19,21):
 issue=data["issues"][i];targets.append(("sample",issue["d"],"2026-"+issue["ids"].split(",")[0]))
for name,d,code in targets:
 url="https://www.asturias.es/bopa/"+d.replace("-","/")+"/"+code+".pdf"
 try:
  with requests.get(url,stream=True,timeout=(7,30),headers={"User-Agent":"Mozilla/5.0 (OpoAlert official BOPA audit)"}) as r:
   b=bytearray()
   for chunk in r.iter_content(32768):
    b.extend(chunk)
    if len(b)>11_000_000:break
   if r.status_code!=200 or not b.startswith(b"%PDF-") or len(b)>11_000_000:
    raise ValueError(f"Original failed HTTP {r.status_code}, bytes {len(b)}")
   reader=PdfReader(io.BytesIO(b),strict=False)
   text=(reader.pages[0].extract_text() or "")[:2400]
   print("BOPA_PDF_TEXT",json.dumps({"target":name,"day":d,"code":code,
      "pdfBytes":len(b),"pages":len(reader.pages),"sha256":hashlib.sha256(b).hexdigest(),
      "containsCode":code in text,"head":text[:1200]},ensure_ascii=True),flush=True)
 except Exception as e:print("BOPA_PDF_ERROR",json.dumps({"day":d,"code":code,"error":type(e).__name__+":"+str(e)[:230]}),flush=True)
