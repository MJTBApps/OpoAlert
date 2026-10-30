#!/usr/bin/env python3
"""Diagnostic for BOPA candidate official PDF issue-header variants. No feed."""
from asturias_bopa_20261029 import load_manifest,read_pdf,pdf_url,fold,ROMAN_MONTH
from datetime import date
import re,json
m,_=load_manifest()
ids={"2026-08061","2026-07742","2026-08847"}
for c in m["candidates"]:
 if c["id"] not in ids:continue
 d=date.fromisoformat(c["d"]);n=c["n"]
 raw,pages,first=read_pdf(pdf_url(c["d"],c["id"]))
 top=fold(first[:900])
 month=ROMAN_MONTH[d.month]
 pat=fr"num[.]\s*{n}\s+de\s+{d.day}-{month}-{d.year}\b"
 issue_ok=bool(re.search(pat,top))
 code_ok=bool(re.search(r"\bcod[.]\s*"+re.escape(c["id"])+r"\b",top))
 words=[w for w in re.findall("[a-z0-9]{4,}",fold(c["title"])) if w not in
   ("anuncio","resolucion","edito","edicto","octubre","septiembre","asturias","principado")][:34]
 pwords=set(re.findall("[a-z0-9]{4,}",fold(first)))
 ratio=sum(w in pwords for w in words)/max(1,len(words))
 print("ASTURIAS_DIAG",json.dumps({"id":c["id"],"date":c["d"],"number":n,"pages":pages,
  "issueCheck":issue_ok,"codeCheck":code_ok,"titleRatio":ratio,
  "issuePattern":pat,"headerFirst":top[:600],
  "originalTitle":c["title"][:250]},ensure_ascii=True),flush=True)


# Verify whether the 13 October "num. 197" is a single-PDF editorial typo
# or an issue-wide mismatch. These are original links from the publisher.
for code in ("2026-08237","2026-08032","2026-08042"):
 raw,pages,head=read_pdf(pdf_url("2026-10-13",code))
 print("ASTURIAS_OCT13_CONTROL",json.dumps({
  "code":code,"pages":pages,"sha256":__import__("hashlib").sha256(raw).hexdigest(),
  "header":fold(head[:350]),"hasCode":code in head
 },ensure_ascii=True),flush=True)
