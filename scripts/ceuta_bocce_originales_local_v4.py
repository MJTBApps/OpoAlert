#!/usr/bin/env python3
"""OpoAlert: retrieve and audit 2026 CEUTA BOCCE from original public editor.

Focused follow-up to the v3 ZIP supplied from a Spanish personal computer.
Only first-party jDownloads PUBLIC pages and PDFs are accessed. No logins,
cookies, CAPTCHA workarounds, private files, or automatic uploads.
A PDF SHA does not prove full 30-day editorial coverage. The manifest is
explicitly PARTIAL, pending independent review of ordinary/extras sequences.
"""
from __future__ import annotations

import argparse,hashlib,io,json,re,ssl,time,unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urljoin,urlsplit,unquote
from urllib.request import build_opener,HTTPSHandler,HTTPRedirectHandler,Request
from zipfile import ZipFile,ZIP_DEFLATED
from pypdf import PdfReader

HOST="www.ceuta.es"
PERIOD_START=date(2026,9,30)
PERIOD_END=date(2026,10,29)
ID_URL="https://www.ceuta.es/ceuta/component/jdownloads/viewdownload/{category}/{id}?Itemid=534"
PUBLIC_SLUG=re.compile(r"BOCCE[_ -]?(Extra\s*\d{1,3}|\d{4})[_ -](\d{2}-\d{2}-2026)",re.I)
SENSITIVE=re.compile(r"token|session|password|auth|secret|api_key|csrf",re.I)
REQ_TIMEOUT=15
MAX_PDF_BYTES=28_000_000

def fold(s):
 t=unicodedata.normalize("NFD",str(s).lower())
 return re.sub(r"\s+"," ","".join(x for x in t if unicodedata.category(x)!="Mn")).strip()

def official(url):
 try:
  p=urlsplit(url)
  segments=unquote(p.path).split("/")
  return bool(p.scheme=="https" and p.hostname==HOST and p.username is None and
    p.password is None and p.port in (None,443) and p.path.startswith("/ceuta/component/jdownloads/") and
    not any(s in (".","..") for s in segments) and
    "/login" not in p.path.lower())
 except ValueError:return False

class RedirectPolicy(HTTPRedirectHandler):
 def redirect_request(self,req,fp,code,msg,headers,newurl):
  if not official(newurl):
   raise ValueError("Editor redirige fuera del dominio/archivo oficial")
  return super().redirect_request(req,fp,code,msg,headers,newurl)

def fetch(url,limit):
 if not official(url):raise ValueError("URL fuera de editor oficial")
 opener=build_opener(HTTPSHandler(context=ssl.create_default_context()),RedirectPolicy())
 req=Request(url,headers={
  "User-Agent":"Mozilla/5.0 (compatible; OpoAlert official public PDF integrity audit)",
  "Accept":"text/html,application/pdf;q=0.9,*/*;q=0.8",
  "Accept-Language":"es-ES,es;q=0.9"})
 with opener.open(req,timeout=REQ_TIMEOUT) as res:
  final=res.geturl()
  if not official(final):raise ValueError("Redireccion fuera de editor oficial")
  b=res.read(limit+1)
  if len(b)>limit:raise ValueError("Documento excede límite de lectura segura")
  return b,final,res.headers.get("Content-Type","")

class Links(HTMLParser):
 def __init__(self,base):
  super().__init__(convert_charrefs=True)
  self.base=base;self.links=[];self.text=[];self.anchor=None
  self.ignore=0
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag in ("script","style","noscript","iframe"):self.ignore+=1
  if self.ignore:return
  if tag=="a" and a.get("href"):
   u=urljoin(self.base,a["href"])
   self.anchor=[u,[]]
 def handle_endtag(self,tag):
  if tag in ("script","style","noscript","iframe"):
   self.ignore=max(0,self.ignore-1)
   return
  if tag=="a" and self.anchor:
   u,parts=self.anchor
   if official(u):self.links.append({"url":u,"label":" ".join(parts)[:160]})
   self.anchor=None
 def handle_data(self,data):
  if self.ignore:return
  d=" ".join(data.split())
  if d:
   self.text.append(d)
   if self.anchor:self.anchor[1].append(d)

def parser(html,base):
 p=Links(base)
 p.feed(html.decode("utf-8","replace"))
 return p

def load_v3(path):
 with ZipFile(path) as z:
  names=z.namelist()
  if names!=["evidencias_pendientes_v3.json","LEER.txt"] and "evidencias_pendientes_v3.json" not in names:
   raise ValueError("ZIP v3 no verificado")
  if z.getinfo("evidencias_pendientes_v3.json").file_size>2_000_000:
   raise ValueError("Entrada v3 inesperadamente grande")
  d=json.loads(z.read("evidencias_pendientes_v3.json"))
 if d.get("tool")!="OpoAlert-Recolector-Pendientes-Oficiales-v3":
  raise ValueError("Evidencias no proceden del recolector oficial v3")
 prior=[r for r in d.get("results",[]) if r.get("code")=="CE"]
 first=[]
 for row in prior:
  for l in (row.get("page") or {}).get("links",[]):
   u=l.get("url","");name=l.get("text","")
   if not official(u) or "/viewdownload/" not in urlsplit(u).path:continue
   m=PUBLIC_SLUG.search(name)
   if m:first.append({"name":name,"viewUrl":u})
 ids=[int(m[1]) for x in first if (m:=re.search(r"/viewdownload/[^/]+/(\d{5})(?:-|$)",urlsplit(x["viewUrl"]).path))]
 if not ids:raise ValueError("No hay documentos públicos CE con ID anclado en el ZIP v3")
 return sorted(ids),first,hashlib.sha256(path.read_bytes()).hexdigest()

def read_detail(category,identifier):
 u=ID_URL.format(category=category,id=identifier)
 try:
  body,final,mime=fetch(u,850000)
  if "html" not in mime.lower() and not body.lstrip().lower().startswith(b"<!doctype"):
   return {"id":identifier,"category":category,"status":"not_html","mime":mime[:80]}
  p=parser(body,final)
  txt=" ".join(p.text)
  # Read the DOWNLOAD DETAILS section only, not the five global sidebar links.
  ix=fold(txt).find("detalles de descarga")
  if ix<0:ix=fold(txt).find("detalls de descarrega")
  if ix<0:return {"id":identifier,"category":category,"status":"not_download_detail"}
  details=txt[ix:ix+700]
  m=PUBLIC_SLUG.search(details)
  if not m:return {"id":identifier,"category":category,"status":"not_bocce_detail"}
  num=(re.sub(r"\s+","",m[1]).upper())
  day=datetime.strptime(m[2],"%d-%m-%Y").date()
  if not PERIOD_START<=day<=PERIOD_END:
   return {"id":identifier,"category":category,"status":"outside_window","number":num,"date":day.isoformat()}
  links=[a["url"] for a in p.links if "/jdownloads/finish/" in urlsplit(a["url"]).path and str(identifier) in a["url"]]
  if not links:return {"id":identifier,"category":category,"status":"no_original_pdf_link","number":num,"date":day.isoformat()}
  u=links[0]
  return {"id":identifier,"category":category,"status":"found_editor_original","number":num,
          "date":day.isoformat(),"detailUrl":final,"pdfUrl":u,"publisherHeading":details[:170]}
 except (HTTPError,URLError,ValueError,OSError,TimeoutError) as e:
  return {"id":identifier,"category":category,"status":"unavailable","error":type(e).__name__}
 except Exception as e:
  return {"id":identifier,"category":category,"status":"unparseable","error":type(e).__name__}

EMPLOYMENT=("plazas","plaza de","plaza del","bolsa de","bolsa temporal","convocatoria de","convocatorias",
  "personal funcionario","personal laboral","proceso selectivo","procesos selectivos",
  "seleccion de personal","oposicion","concurso-oposicion","bases especificas")

def pdf_detail(row):
 u=row["pdfUrl"]
 out={**row,"verifiedOriginal":False}
 try:
  b,final,mime=fetch(u,MAX_PDF_BYTES)
  if not b.startswith(b"%PDF-") or not re.search(r"pdf|octet-stream",mime,re.I):
   raise ValueError("No se recibió PDF completo")
  reader=PdfReader(io.BytesIO(b),strict=False)
  if not 1<=len(reader.pages)<=950:raise ValueError("PDF sin páginas o excesivas")
  first=(reader.pages[0].extract_text() or "")[:3000]
  head=fold(first[:1200])
  when=date.fromisoformat(row["date"])
  # PDF must identify date exactly, not just be downloaded from matching slug.
  day_ok=(str(when.day) in head[:260] and str(when.year) in head[:400]
      and ("octubre" in head[:500] or "septiembre" in head[:500]))
  numero=row["number"]
  # Editor often prints BOCCE 6.664 (dot separator) rather than 6664.
  expected_digits=re.sub(r"\D","",numero)
  numbers=[re.sub(r"\D","",m[0]) for m in re.finditer(r"(?<!\d)\d[\d.]*",head[:700])]
  num_ok=bool(expected_digits and expected_digits in numbers)
  if not day_ok or not num_ok:
   raise ValueError("La portada del PDF no coincide con fecha o numeración del editor")
  employment=[]
  failed_pages=[]
  for i,page in enumerate(reader.pages):
   try:
    content=page.extract_text() or ""
    f=fold(content)
    if not f.strip():
     failed_pages.append({"page":i+1,"error":"pdf_page_without_extractable_text"})
    found=[kw for kw in EMPLOYMENT if kw in f]
    if found:
     for kw in found[:3]:
      at=f.index(kw)
      employment.append({"page":i+1,"keyword":kw,"context":f[max(0,at-230):at+650]})
   except Exception as e:
    failed_pages.append({"page":i+1,"error":type(e).__name__})
  if failed_pages:raise ValueError("Páginas sin texto verificable: "+str(failed_pages[:3]))
  out.update({"verifiedOriginal":True,"pdfSHA256":hashlib.sha256(b).hexdigest(),
    "pdfBytes":len(b),"pdfPages":len(reader.pages),"dateAndNumberInPdfHeader":True,
    "firstPage":first[:1300],"employmentHits":employment[:240],"candidatePages":len({x["page"] for x in employment}),
    "textExtractionAllPages":True})
 except Exception as e:
  out["validationError"]=type(e).__name__+": "+str(e)[:180]
 return out

def save(path,manifest):
 path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_name(path.stem+".tmp.zip")
 with ZipFile(temp,"w",ZIP_DEFLATED,compresslevel=7) as z:
  z.writestr("ceuta_bocce_originales_v4.json",json.dumps(manifest,indent=2,ensure_ascii=False))
  z.writestr("LEER.txt","Prueba parcial del archivo oficial BOCCE 2026. NO certifica 30 dias ni publica feeds.\n"
             "Originales identificados por URL, fecha, paginas y SHA256; sin cookies ni datos privados.\n")
 temp.replace(path)

def main():
 a=argparse.ArgumentParser()
 a.add_argument("--self-test",action="store_true")
 a.add_argument("--input",type=Path)
 a.add_argument("--output",type=Path)
 a.add_argument("--max-ids",type=int,default=92)
 a.add_argument("--max-pdfs",type=int,default=30)
 args=a.parse_args()
 if args.self_test:
  assert official("https://www.ceuta.es/ceuta/component/jdownloads/viewdownload/1982/23304?Itemid=534")
  assert not official("https://www.ceuta.es/ceuta/component/jdownloads/../../../etc/passwd")
  assert not official("http://www.ceuta.es/ceuta/component/jdownloads/viewdownload/1982/23304")
  assert not official("https://evil.example.com/ceuta/component/jdownloads/viewdownload/1982/23304")
  assert PUBLIC_SLUG.search("Detalles de Descarga BOCCE_Extra51_28-10-2026 Datos").groups()==("Extra51","28-10-2026")
  assert PUBLIC_SLUG.search("Detalles de Descarga BOCCE_6664_27-10-2026 Datos").groups()==("6664","27-10-2026")
  head=fold("BOCCE Nº6.664 martes, 27 de octubre de 2026")
  assert "6664" in [re.sub(r"\D","",m[0]) for m in re.finditer(r"(?<!\d)\d[\d.]*",head)]
  with __import__("tempfile").TemporaryDirectory() as d:
   p=Path(d)/"tmp.zip";save(p,{"audit30DaysComplete":False,"sources":[]})
   with ZipFile(p) as z:assert not json.loads(z.read("ceuta_bocce_originales_v4.json"))["audit30DaysComplete"]
  print("OK: URLs editoriales, fecha, número y ZIP parcial; no network, no cookies",flush=True)
  return
 folder=Path.home()/"Documents"/"OpoAlert"
 v3s=sorted(folder.glob("OpoAlert_pendientes_oficiales_v3_*.zip"),key=lambda p:p.stat().st_mtime,reverse=True)
 input_file=args.input or (v3s[0] if v3s else None)
 if input_file is None:raise SystemExit("Falta ZIP v3 en Documentos/OpoAlert")
 ids,seeds,input_hash=load_v3(input_file)
 max_id=max(ids)
 target=args.output or folder/("OpoAlert_Ceuta_BOCCE_originales_v4_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".zip")
 result={"tool":"OpoAlert-Ceuta-BOCCE-Originales-v4","baseEvidenceSHA256":input_hash,
  "generatedUTC":datetime.now(timezone.utc).isoformat(),
  "window":[PERIOD_START.isoformat(),PERIOD_END.isoformat()],
  "audit30DaysComplete":False,"newFeedAuthorized":False,
  "publisher":"www.ceuta.es","knownIds":ids,
  "scannedIds":[],"originals":[],"suspectedNumberGaps":[]}
 save(target,result)
 count=max(3,min(140,args.max_ids))
 # Walk a *bounded* sequence of the publisher's public document IDs and only
 # accept issues that the publisher itself labels BOCCE with an original PDF.
 # NOTE: unrelated/old IDs are discarded; unknown gaps remain pending.
 for offset in range(count):
  identifier=max_id-offset
  if identifier<=0:break
  first=read_detail("1982",identifier)
  if first["status"] not in ("found_editor_original","outside_window"):
   other=read_detail("1980",identifier)
   if other["status"] in ("found_editor_original","outside_window"):
    first=other
  result["scannedIds"].append(first)
  if first["status"]=="found_editor_original" and first["pdfUrl"] not in {x.get("pdfUrl") for x in result["originals"]}:
   if len(result["originals"])<min(50,args.max_pdfs):
    pdf=pdf_detail(first)
    result["originals"].append(pdf)
    print("CEUTA_PDF",pdf["number"],pdf["date"],"PAGS",pdf.get("pdfPages",0),
      "VALIDADO",pdf["verifiedOriginal"],"EMPLEO_PAGS",pdf.get("candidatePages",0),
      "ERROR",pdf.get("validationError","-"),flush=True)
   else:result["originals"].append({**first,"verifiedOriginal":False,"validationError":"max_pdfs budget reached"})
  if offset%8==0:
   save(target,result)
   print("CEUTA_AVANCE",offset+1,"/",count,"originales",len(result["originals"]),
    "validados",sum(x.get("verifiedOriginal") for x in result["originals"]),flush=True)
  time.sleep(0.28)
 ordinary=sorted({int(x["number"]) for x in result["originals"] if x.get("verifiedOriginal") and x["number"].isdigit()})
 if ordinary:
  result["suspectedNumberGaps"]=list(sorted(set(range(min(ordinary),max(ordinary)+1))-set(ordinary)))
 result["summary"]={"publicIdsScanned":len(result["scannedIds"]),
  "officialPdfCount":len(result["originals"]),
  "originalsValidated":sum(x.get("verifiedOriginal") for x in result["originals"]),
  "ordinaryNumbersFound":ordinary,
  "extraordinaryFound":sorted({x["number"] for x in result["originals"] if "EXTRA" in x["number"]}),
  "potentialGaps":result["suspectedNumberGaps"],
  "audit30DaysComplete":False}
 save(target,result)
 print("CEUTA_RESULT",json.dumps(result["summary"],ensure_ascii=True),flush=True)
 print("ZIP_GENERADO",str(target),flush=True)
 print("NO_APK: pendiente revisión independiente de inicio de periodo, extras, huecos y títulos",flush=True)

if __name__=="__main__":main()
