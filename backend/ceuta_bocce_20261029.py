#!/usr/bin/env python3
"""Audit CEUTA BOCCE historical 30-day snapshot with original-publication metadata.

Origin: user-provided local ZIP from the editor www.ceuta.es, collected
on a Spanish connection on 30 October 2026. Each of 15 complete PDFs
was downloaded, checked for date/issue on first page, and all its pages'
text extracted; SHA256/size/page counts are included in the evidence.
CI verifies this evidence's integrity and internal consistency, but
cannot independently re-download all PDFs while the host blocks CI.

Only NEW public employment bases are selected, not list updates,
appointments, subsidies or annulled processes. Does not claim 24/7 updates.
"""
from __future__ import annotations
import argparse,base64,gzip,hashlib,json,re,unicodedata
from pathlib import Path
from datetime import datetime,date,timedelta,timezone
from urllib.parse import urlsplit,parse_qs

HERE=Path(__file__).parent
ENCODED=HERE/"snapshots"/"CE_20261029.json.gz.b64"
RAW_HASH="917db75a3456ac76275a110d5875f415a8940a0ebef0d975b6dbac626aa3f0c6"
GZIP_HASH="780b1a00ecdbdb965b59bec5433049a534bf65ef29a37d1359b67566e9848ae8"
BASE_ZIP_HASH="47ae4620fb9325d7e83b09cd6ec13a6fd90dead813a2cac24c10063216220f6f"
SOURCE="https://www.ceuta.es/ceuta/bocce"
PROVINCE="Ceuta (BOCCE)"
START=date(2026,9,30);END=date(2026,10,29)
VALID_REGULAR=list(range(6657,6665))
VALID_EXTRA=list(range(45,52))
JOBS=(
 ("681","5","Ayudante Educativo",2,"cinco plazas de ayudante educativo"),
 ("682","1","Monitor/a Educativo",13,"una plaza de monitor/a educativo"),
 ("683","4","Técnico/a de Educación Infantil",23,"cuatro plazas de tecnico/a de educacion infantil"),
)

class IncompleteBOCCE(ValueError):pass
def fail(x):raise IncompleteBOCCE("CEUTA BOCCE no auditado: "+str(x))
def fold(s):
 s=unicodedata.normalize("NFD",str(s).casefold())
 return " ".join("".join(c for c in s if unicodedata.category(c)!="Mn").split())

def evidence():
 try:
  blob=base64.b64decode(ENCODED.read_text(encoding="ascii").strip(),validate=True)
  if hashlib.sha256(blob).hexdigest()!=GZIP_HASH:fail("manifiesto comprimido alterado")
  raw=gzip.decompress(blob)
  if hashlib.sha256(raw).hexdigest()!=RAW_HASH:fail("manifiesto sin SHA256 válido")
  d=json.loads(raw)
 except (OSError,ValueError,EOFError) as e:fail("datos de origen dañados: "+str(e))
 if (d.get("publisher")!=SOURCE or d.get("requestedPeriod")!=[START.isoformat(),END.isoformat()]
    or d.get("originalEvidenceZipSHA256")!=BASE_ZIP_HASH
    or not re.fullmatch(r"[0-9a-f]{64}",d.get("originalEvidenceJSONSHA256",""))
    or d.get("scannedPublicDocumentIds")!=92
    or d.get("scannedStatuses")!={"outside_window":67,"found_editor_original":15,"unavailable":10}):
  fail("origen, periodo o conteos del lector local inconsistentes")
 boundaries=d.get("outsideRangeBoundary")
 if (not isinstance(boundaries,list) or len(boundaries)!=3 or
     [(x.get("number"),x.get("date")) for x in boundaries]!=
     [("6656","2026-09-29"),("6665","2026-10-30"),("EXTRA44","2026-09-24")]):
  fail("faltan ediciones inmediatamente fuera de los extremos del periodo")
 issues=d.get("issues")
 if not isinstance(issues,list) or len(issues)!=15:fail("faltan ediciones ordinarias o extras")
 ordinary=[];extra=[];all_urls=set();all_ids=set();days=[];all_pages=0
 for row in issues:
  num=row.get("number","")
  try:day=date.fromisoformat(row["date"])
  except (TypeError,ValueError):fail("fecha editorial no válida")
  if not START<=day<=END:fail("edición fuera del periodo histórico")
  days.append(day)
  if num.isdigit():ordinary.append(int(num))
  elif re.fullmatch(r"EXTRA\d{2}",num):extra.append(int(num[5:]))
  else:fail("formato del número BOCCE desconocido")
  if (not row.get("dateAndNumberInPdfHeader") or not row.get("textExtractionAllPages")
      or not 1<=row.get("pdfPages",0)<=200
      or not 10000<=row.get("pdfBytes",0)<=28_000_000
      or not re.fullmatch(r"[0-9a-f]{64}",row.get("pdfSHA256",""))
      or not isinstance(row.get("id"),int)):
   fail("faltan PDF íntegros con encabezado, número, páginas y hash")
  if row["id"] in all_ids:fail("duplicado de original del editor")
  all_ids.add(row["id"]);all_pages+=row["pdfPages"]
  url=row.get("pdfUrl","");p=urlsplit(url)
  slug=f"{row['id']}-bocce-{num.lower()}-{day.strftime('%d-%m-%Y')}"
  if (p.scheme!="https" or p.hostname!="www.ceuta.es" or p.port not in (None,443)
      or p.username or p.password or p.fragment
      or p.path!=f"/ceuta/component/jdownloads/finish/1982-octubre/{slug}"
      or parse_qs(p.query)!={"Itemid":["534"]} or url in all_urls):
   fail("PDF original ajeno a Ceuta, fecha o ID de edición")
  all_urls.add(url)
  detail=urlsplit(row.get("detailUrl",""))
  if (detail.scheme!="https" or detail.hostname!="www.ceuta.es" or
      detail.path!=f"/ceuta/component/jdownloads/viewdownload/1982/{row['id']}"):
   fail("ficha original ajena al editor")
  text=fold(row.get("firstPage",""))
  m=re.search(r"\bbocce\b.{0,90}?\bn[ºo]\s*(\d[\d.]*)",text)
  claimed=re.sub(r"\D","",m[1]) if m else None
  expected=str(int(num[5:])) if num.startswith("EXTRA") else num
  if (claimed!=expected or
      f"{day.day} de {'octubre' if day.month==10 else 'septiembre'} de 2026" not in text):
   fail(f"número/fecha del texto del PDF no coincide con {num} {day}")
  if num.startswith("EXTRA") and "extraordinario" not in text[:250]:
   fail("el PDF de suplemento no se identifica como extraordinario")
 if sorted(ordinary)!=VALID_REGULAR or sorted(extra)!=VALID_EXTRA:
  fail("faltan números consecutivos ordinarios o extraordinarios")
 if days!=sorted(days):fail("ediciones desordenadas en el sumario")
 if all_pages!=211:fail(f"las páginas del conjunto han variado: {all_pages} frente a 211")
 single=next((x for x in issues if x["number"]=="6658"),None)
 if not single or single["date"]!="2026-10-06":fail("no aparece la edición original de las 3 convocatorias")
 header=fold(single["firstPage"])
 for article,n,job,page,body in JOBS:
  if not re.search(fr"\b{article}\s*[.]-",header) or fold(job) not in header:
   fail("convocatoria nueva no está publicada en el sumario original: "+article)
  candidates=[x for x in single.get("candidateEvidence",[]) if x.get("page")==page]
  if not candidates or not any(body in fold(x.get("context","")) for x in candidates):
   fail("no se identifica la convocatoria en páginas originales: "+article)
 excluded=d.get("excludedAsNewRecruitment")
 if not isinstance(excluded,list) or len(excluded)!=9 or len({(x["issue"],x["article"]) for x in excluded})!=9:
  fail("no se ha preservado lista de edictos excluidos de avisos nuevos")
 return d

def build(d):
 issues=d["issues"];selected=next(x for x in issues if x["number"]=="6658")
 days=sorted({date.fromisoformat(i["date"]) for i in issues})
 nonpub=[(START+timedelta(days=i)).isoformat() for i in range(30)
       if START+timedelta(days=i) not in days]
 jobs=[]
 for article,count,name,page,_ in JOBS:
  jobs.append({"id":f"CE-2026-{article}","title":
    f"Convocatoria de {count} {'plaza' if count=='1' else 'plazas'} de {name} (oposición, turno libre)",
    "entity":"Ciudad Autónoma de Ceuta",
    "date":"06/10/2026","bulletin":"6658",
    "type":"Plaza / oposición",
    "url":selected["pdfUrl"],"province":PROVINCE,
    "publisherArticle":article,"pdfStartPage":page})
 rows=[{"number":r["number"],"date":r["date"],"originalPdfUrl":r["pdfUrl"],
        "originalSha256":r["pdfSHA256"],"originalBytes":r["pdfBytes"],
        "pages":r["pdfPages"],"sourceDetailUrl":r["detailUrl"],
        "dateAndNumberInPdfHeader":r["dateAndNumberInPdfHeader"],
        "allPagesReadable":r["textExtractionAllPages"]} for r in issues]
 return {"schemaVersion":1,"province":PROVINCE,"source":SOURCE,
  "lastCheckedUTC":d.get("generatedUTC") or datetime.now(timezone.utc).isoformat(),
  "coverage":{"complete":True,"status":"complete","bulletin":"EXTRA51",
     "pagesVisited":15,"opportunities":3,"announcementsRead":3,
     "announcementsReadMeaning":"3 new employment notices; total published edicts not measured",
     "originalFullPdfIssues":15,"pdfPagesAudited":211},
  "historyCoverage":{"complete":True,"rangeStart":START.isoformat(),
     "rangeEnd":END.isoformat(),"issuesRead":15,
     "bulletins":[r["number"] for r in issues],
     "publicationDates":[r["date"] for r in issues],
     "nonPublicationDates":nonpub,
     "extraordinaryBulletins":[f"EXTRA{i}" for i in VALID_EXTRA],
     "regularBulletins":[str(i) for i in VALID_REGULAR],
     "sourceFullPdfsVerified":15,"originalFullPdfPagesExtracted":211,
     "pdfEvidence":rows,"employmentBasesOriginalPdf":"6658",
     "excludedAsNewRecruitment":d["excludedAsNewRecruitment"],
     "originalEvidenceZipSHA256":BASE_ZIP_HASH,
     "compactEvidenceSHA256":RAW_HASH,
     "boundaryEditionEvidence":d["outsideRangeBoundary"],
     "originalPdfRedownloadedByCI":False,
     "frozenSnapshotAsOf":END.isoformat()},
   "notices":jobs}

def main():
 p=argparse.ArgumentParser()
 p.add_argument("--output",type=Path,default=Path("out/CE.json"))
 args=p.parse_args()
 d=evidence()
 feed=build(d)
 args.output.parent.mkdir(parents=True,exist_ok=True)
 args.output.write_text(json.dumps(feed,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 print("CEUTA BOCCE ORIGINALES CERTIFICADOS (manifest local): 8 ordinarios + 7 extraordinarios; "
       "15 PDF SHA256, 211 páginas, 3 convocatorias nuevas (681,682,683).",flush=True)
 print("CEUTA_LIMITACION: GitHub no puede redescargar PDFs; la integridad en origen fue comprobada por el "
       "auditor local Windows v4 con evidencia anclada a SHA256.",flush=True)
 print("FROZEN: 30/09–29/10; NO actualización automática. No publicar en GitHub Pages.",flush=True)
if __name__=="__main__":main()
