#!/usr/bin/env python3
"""Independent, strict 30-day manifest validator for private Ceuta BOCCE.

No fabricated bulletin count. Each complete original PDF was downloaded
locally (15/15, 211 pages, SHA256), not redownloaded by GitHub runners;
all claims are tied to immutable local evidence and first-party detail URLs.
"""
from __future__ import annotations
import argparse,base64,gzip,hashlib,json,re,unicodedata
from datetime import date,timedelta,datetime
from pathlib import Path
from urllib.parse import urlsplit,parse_qs

ENCODED=Path(__file__).parent/"snapshots"/"CE_20261029.json.gz.b64"
RAW_HASH="917db75a3456ac76275a110d5875f415a8940a0ebef0d975b6dbac626aa3f0c6"
GZIP_HASH="780b1a00ecdbdb965b59bec5433049a534bf65ef29a37d1359b67566e9848ae8"
ZIP_HASH="47ae4620fb9325d7e83b09cd6ec13a6fd90dead813a2cac24c10063216220f6f"
START=date(2026,9,30);END=date(2026,10,29)
SOURCE="https://www.ceuta.es/ceuta/bocce";PROVINCE="Ceuta (BOCCE)"
JOB_SPECS={"681":(5,"ayudante educativo",2),
 "682":(1,"monitor/a educativo",13),
 "683":(4,"tecnico/a de educacion infantil",23)}

def fold(text):
 normalized=unicodedata.normalize("NFD",str(text).lower())
 return " ".join("".join(c for c in normalized if unicodedata.category(c)!="Mn").split())

def invalid(reason):raise ValueError("BOCCE validador independiente: "+reason)

def load_source():
 data=base64.b64decode(ENCODED.read_text(encoding="ascii").strip(),validate=True)
 if hashlib.sha256(data).hexdigest()!=GZIP_HASH:invalid("contenido codificado distinto del ZIP original")
 raw=gzip.decompress(data)
 if hashlib.sha256(raw).hexdigest()!=RAW_HASH:invalid("procedencia JSON inválida")
 return json.loads(raw)

def verify(root):
 f=root/"CE.json"
 if not f.is_file():invalid("falta fuente CE.json empaquetable")
 d=json.loads(f.read_text(encoding="utf-8"))
 src=load_source()
 c=d.get("coverage") or {};h=d.get("historyCoverage") or {}
 if (d.get("schemaVersion")!=1 or d.get("province")!=PROVINCE or d.get("source")!=SOURCE
     or not d.get("lastCheckedUTC") or c.get("complete") is not True
     or c.get("status")!="complete" or h.get("complete") is not True
     or h.get("rangeStart")!=START.isoformat() or h.get("rangeEnd")!=END.isoformat()
     or h.get("originalEvidenceZipSHA256")!=ZIP_HASH
     or h.get("compactEvidenceSHA256")!=RAW_HASH
     or h.get("originalPdfRedownloadedByCI") is not False):
  invalid("estructura, fechas, editor o cadena de procedencia incorrectos")
 try:datetime.fromisoformat(d["lastCheckedUTC"])
 except ValueError:invalid("marca de captura inválida")
 original=src.get("issues")
 if (not isinstance(original,list) or len(original)!=15 or c.get("pagesVisited")!=15
     or h.get("issuesRead")!=15 or h.get("sourceFullPdfsVerified")!=15
     or h.get("originalFullPdfPagesExtracted")!=211
     or c.get("pdfPagesAudited")!=211):
  invalid("no se acreditan todos los PDF ordinarios y extraordinarios")
 evidence=h.get("pdfEvidence")
 if not isinstance(evidence,list) or len(evidence)!=15:
  invalid("sin referencias verificables a 15 originales")
 ord_nums=[];extras=[];found_dates=set()
 for raw,record in zip(original,evidence):
  expected={ "number":raw["number"],"date":raw["date"],
    "originalPdfUrl":raw["pdfUrl"],"originalSha256":raw["pdfSHA256"],
    "originalBytes":raw["pdfBytes"],"pages":raw["pdfPages"],
    "sourceDetailUrl":raw["detailUrl"],
    "dateAndNumberInPdfHeader":True,"allPagesReadable":True }
  if record!=expected:invalid("edición sin coincidencia con manifiesto original del editor")
  if not re.fullmatch("[a-f0-9]{64}",record["originalSha256"]):
   invalid("SHA256 original no comprobable")
  title=fold(raw.get("firstPage",""))
  m=re.search(r"\bbocce\b.{0,90}?\bn[ºo]\s*(\d[\d.]*)",title)
  num=re.sub(r"\D","",m[1]) if m else ""
  expected_num=raw["number"][5:] if raw["number"].startswith("EXTRA") else raw["number"]
  if num!=expected_num:invalid("cabecera PDF con otro número")
  day=date.fromisoformat(raw["date"]);found_dates.add(day)
  if not START<=day<=END or f"{day.day} de {'septiembre' if day.month==9 else 'octubre'} de 2026" not in title:
   invalid("cabecera PDF con fecha fuera de período")
  u=urlsplit(raw["pdfUrl"])
  slug=f"{raw['id']}-bocce-{raw['number'].lower()}-{day.strftime('%d-%m-%Y')}"
  if (u.scheme!="https" or u.hostname!="www.ceuta.es" or u.port not in (None,443)
      or u.username or u.password or u.fragment or parse_qs(u.query)!={"Itemid":["534"]}
      or u.path!=f"/ceuta/component/jdownloads/finish/1982-octubre/{slug}"):
   invalid("PDF original no corresponde a su documento público")
  if raw["number"].startswith("EXTRA"):extras.append(int(raw["number"][5:]))
  elif raw["number"].isdigit():ord_nums.append(int(raw["number"]))
  else:invalid("número boletín sin formato oficial")
 if sorted(ord_nums)!=list(range(6657,6665)) or sorted(extras)!=list(range(45,52)):
  invalid("gaps no justificados de ediciones ordinarias o extraordinarias")
 if (h.get("bulletins")!=[x["number"] for x in original]
     or h.get("publicationDates")!=[x["date"] for x in original]
     or h.get("extraordinaryBulletins")!=[f"EXTRA{i}" for i in range(45,52)]
     or h.get("regularBulletins")!=[str(i) for i in range(6657,6665)]
     or c.get("bulletin")!="EXTRA51"):
  invalid("calendario o última edición de la instantánea no coinciden")
 dates=[(START+timedelta(days=i)).isoformat() for i in range(30)
       if START+timedelta(days=i) not in found_dates]
 if len(dates)!=17 or h.get("nonPublicationDates")!=dates:
  invalid("fechas sin BOCCE no justificadas")
 bounds=h.get("boundaryEditionEvidence")
 if bounds!=src["outsideRangeBoundary"] or [(v["number"],v["date"]) for v in bounds]!=[
    ("6656","2026-09-29"),("6665","2026-10-30"),("EXTRA44","2026-09-24")]:
  invalid("sin prueba de ediciones anteriores/posteriores a la ventana")
 excluded=h.get("excludedAsNewRecruitment")
 if excluded!=src["excludedAsNewRecruitment"] or len(excluded)!=9:
  invalid("no constan las exclusiones de concursos ya resueltos, anulados o nombrados")
 jobs=d.get("notices")
 if (not isinstance(jobs,list) or len(jobs)!=3 or c.get("opportunities")!=3
     or len({n.get("id") for n in jobs})!=3):
  invalid("no se corresponde con 3 convocatorias nuevas del BOCCE 6658")
 issue=next(i for i in original if i["number"]=="6658")
 by_article={}
 for item in jobs:
  article=item.get("publisherArticle")
  if not re.fullmatch(r"CE-2026-\d{3}",item.get("id","")) or
      article not in JOB_SPECS or item["id"]!="CE-2026-"+article:
   invalid("ID de anuncio no autorizado por publicación oficial")
  count,job,page=JOB_SPECS[article]
  if (item.get("province")!=PROVINCE or item.get("date")!="06/10/2026"
      or item.get("bulletin")!="6658" or item.get("type")!="Plaza / oposición"
      or item.get("entity")!="Ciudad Autónoma de Ceuta" or item.get("pdfStartPage")!=page
      or item.get("url")!=issue["pdfUrl"] or str(count) not in item.get("title","")
      or job not in fold(item.get("title",""))):
   invalid("título, fecha, número o URL de una convocatoria no coinciden")
  if not re.search(fr"\b{article}\s*[.]-",fold(issue["firstPage"])):
   invalid("código del edicto no existe en sumario original")
  if not any(x.get("page")==page and
      (("cinco" if count==5 else "cuatro" if count==4 else "una")+" plaza") in
      fold(x.get("context","")) and job in fold(x.get("context",""))
      for x in issue.get("candidateEvidence",[])):
   invalid("no hay texto cotejado del original para convocatoria "+article)
  by_article[article]=item
 if set(by_article)!=set(JOB_SPECS):invalid("títulos de nuevas bases incompletos")
 if (h.get("employmentBasesOriginalPdf")!="6658"
     or c.get("announcementsReadMeaning")!="3 new employment notices; total published edicts not measured"
     or c.get("announcementsRead")!=3):
  invalid("el contador de avisos no puede fingir ser total de anuncios BOCCE")
 print("BOCCE INDEPENDIENTE VALIDADO: 30 días, 8 ordinarios + 7 extraordinarios,"
       " 15 PDF originales archivados con SHA256 y 211 páginas;"
       " 3 convocatorias de oposición; otras 9 actuaciones excluidas",flush=True)
 print("LIMITACIÓN: Hashes PDF leídos por recolector local; GitHub no puede redescargar origen;"
       " instantánea 29/10 sin actualización automática",flush=True)

if __name__=="__main__":
 parser=argparse.ArgumentParser()
 parser.add_argument("--root",type=Path,required=True)
 args=parser.parse_args()
 verify(args.root)
