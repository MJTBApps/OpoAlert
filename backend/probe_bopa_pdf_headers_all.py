#!/usr/bin/env python3
"""BOPA: check editorial PDF header numbering for all 53 original controls.
Diagnostic only: each original must be genuine PDF, dated and CVE-matched.
Never creates an APK or a supposedly complete province feed.
"""
import concurrent.futures,json,re,time,hashlib
from pathlib import Path
from asturias_bopa_20261029 import load_manifest,pdf_url,read_pdf,fold
MAN,INDEX=load_manifest()
tasks={}
for i in MAN["issues"]:
 code="2026-"+i["ids"].split(",")[0]
 tasks[code]=(i["d"],i["n"],code,None)
for c in MAN["candidates"]:
 tasks[c["id"]]=(c["d"],c["n"],c["id"],c["title"])
def check(t):
 d,num,code,title=t
 try:
  raw,pages,txt=read_pdf(pdf_url(d,code))
  top=fold(txt[:950])
  x=re.search(r"\bnum[.]\s*(\d{2,4})\s+de\s+(\d{1,2})-(ix|x)-2026",top)
  code_ok=bool(re.search(r"\bcod[.]\s*"+re.escape(code)+r"\b",top))
  first=txt.splitlines()[:6]
  diff=int(x[1])-num if x else None
  return {"date":d,"expected":num,"code":code,"isCandidate":bool(title),
   "headerNum":int(x[1]) if x else None,"headerDay":int(x[2]) if x else None,
   "headerMonth":x[3] if x else None,"difference":diff,"codeOK":code_ok,
   "pages":pages,"sha256":hashlib.sha256(raw).hexdigest(),
   "headerSample":" ".join(first)[:260]}
 except Exception as e:return {"date":d,"expected":num,"code":code,"error":str(e)[:230]}
print("BOPA_HEADER_SURVEY_START",len(tasks),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
 result=list(pool.map(check,tasks.values()))
bad=[]
for x in result:
 if x.get("difference")!=0 or not x.get("codeOK"):
  bad.append(x)
  print("BOPA_HEADER_DISCREPANCY",json.dumps(x,ensure_ascii=True),flush=True)
summary={"checked":len(result),"publisherPDFs":sum("sha256" in x for x in result),
 "normal":sum(x.get("difference")==0 and x.get("codeOK") for x in result),
 "discrepancies":bad,"all":result}
Path("out").mkdir(exist_ok=True)
Path("out/BOPA_header_survey.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False))
print("BOPA_HEADER_SURVEY_RESULT",json.dumps({k:summary[k] for k in ("checked","publisherPDFs","normal")},ensure_ascii=True),"discrepancies",len(bad),flush=True)
