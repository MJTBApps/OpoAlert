#!/usr/bin/env python3
"""OpoAlert local source verification v2 (BON Navarra, BOPA Asturias, BOP Jaén).

Read-only standalone program. Reuses locally captured official evidence,
verifies original articles and detects incorrect default pages. It never
declares public coverage: only an independent 30-day validator can do so.
No cookies, logins, CAPTCHA bypasses, browser profiles or auto-uploads.
"""
from __future__ import annotations
import argparse
from datetime import date,datetime,timedelta,timezone
import hashlib,json,re,sys,time,unicodedata
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
from urllib.request import Request,urlopen
from zipfile import ZipFile,ZIP_DEFLATED
from recolector_bop_local import get_page,safe_url

MONTHS={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,
        "julio":7,"agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
BON_INDEX="https://bon.navarra.es/es/indice-boletines"
JAEN_BASE="https://bop.dipujaen.es/bop/"
ASTUR_BASE="https://miprincipado.asturias.es/ast/bopa-sumario"
EXCLUDE=("subvencion","ayudas","beca","premio","recurso de alzada",
 "recursos de alzada","correccion de errores","corrige el error","rectificacion",
 "nombramiento","toma de posesion","lista provisional","lista definitiva",
 "listas provisionales","listas definitivas","admitid","excluid",
 "resultados","resultat","propuesta de nombramiento","suspension de",
 "aplazamiento de","desistimiento","se declara desierta",
 "se declara desierto","modificacion de las bases","modificacion de la convocatoria",
 "nombramiento de personal","nombramiento de funcionario","aspirantes aprobados",
 "resolucion por la que se resuelve","tribunal calificador","vocales del tribunal",
 "concurso de traslado","concurso de traslados","revocacion","oposicion de herederos",
 "concurso de acreedores","autorizacion de","concurso de proyecto")
def fold(s):
 t=unicodedata.normalize("NFD",str(s).casefold())
 return re.sub(r"\s+"," ","".join(x for x in t if unicodedata.category(x)!="Mn")).strip()
def classify(t):
 v=fold(t)
 if any(x in v for x in EXCLUDE):return None
 if "bolsa" in v and any(x in v for x in ("trabajo","empleo","personal","temporal")):
  return "Bolsa de trabajo"
 if ("lista de aspirantes" in v or "relacion de aspirantes" in v or "listas de aspirantes" in v):
  if any(x in v for x in ("constitucion","pruebas selectivas","contratacion temporal","cobertura de necesidades")):
   return "Bolsa de trabajo"
 if (("plaza" in v or "puesto de trabajo" in v or "personal investigador" in v or "proceso selectivo" in v)
     and any(x in v for x in ("oposicion","concurso","pruebas selectivas","proceso selectivo",
                               "convocatoria para la provision","se convoca"))):
  return "Plaza / oposición"
 if "oferta publica de empleo" in v and "para " in v:return "Plaza / oposición"
 return None
def parse_es_date(s):
 m=re.search(r"\b(\d{1,2})\s+de\s+(septiembre|octubre)\s+de\s+(2026)\b",s,re.I)
 if not m:raise ValueError("fecha oficial no hallada")
 return date(int(m[3]),MONTHS[m[2].lower()],int(m[1]))
def load_evidence(path):
 with ZipFile(path) as z:
  names=z.namelist()
  if "evidencias_oficiales.json" not in names:raise ValueError("ZIP original sin evidencias")
  if z.getinfo("evidencias_oficiales.json").file_size>12_000_000:raise ValueError("Evidencias demasiado grandes")
  data=json.loads(z.read("evidencias_oficiales.json"))
 if data.get("tool")!="OpoAlert-Recolector-Oficial" or not isinstance(data.get("results"),list):
  raise ValueError("El ZIP no corresponde al recolector oficial")
 return data
def issue_links(row,n):
 links=row.get("page",{}).get("links",[])
 ids=[]
 for entry in links:
  u=entry.get("url","")
  match=re.fullmatch(r"https://bon[.]navarra[.]es/es/anuncio/-/texto/2026/"+str(n)+r"/(\d{1,5})",u)
  if match:ids.append((int(match[1]),entry["text"],u))
 ids.sort(key=lambda x:x[0])
 if not ids or [x[0] for x in ids]!=list(range(len(ids))):
  raise ValueError(f"BON {n}: sumario no íntegro o índices de anuncios repetidos")
 return ids
def validate_bon_issue(row,n,day):
 if row.get("status")!="public_page_captured" or row.get("http")!=200:
  raise ValueError(f"BON {n}: ejemplar original no capturado")
 actual=row.get("page",{}).get("publicText","")
 m=re.search(r"\bBOLET[IÍ]N\s+N[ºO]\s+(\d{1,4})\s*[-–]\s*(\d{1,2}\s+de\s+\w+\s+de\s+2026)",actual,re.I)
 if not m or int(m[1])!=n or parse_es_date(m[2])!=day:
  raise ValueError(f"BON {n}: fecha o número no corresponden al índice")
 return issue_links(row,n)
def discover_bon(index,end):
 if index.get("status")!="public_page_captured":
  raise ValueError("BON: índice de ejemplares no capturado")
 entries={}
 for item in index["page"].get("links",[]):
  m=re.fullmatch(r"https://bon[.]navarra[.]es/es/boletin/-/sumario/2026/(\d{1,4})",
                 item.get("url",""))
  if not m:continue
  try:day=parse_es_date(item.get("text",""))
  except ValueError:continue
  if not end-timedelta(days=29)<=day<=end:continue
  n=int(m[1])
  if n in entries and entries[n][0]!=day:
   raise ValueError("BON: índice contradictorio")
  entries[n]=(day,item["url"],"extraordinario" in fold(item["text"]))
 nums=sorted(entries)
 if len(nums)<18 or nums!=list(range(nums[0],nums[-1]+1)):
  raise ValueError("BON: faltan números o el calendario editorial es incompleto")
 return entries
def save_bon_checkpoint(path, output, failures):
 # Atomic local-only ZIP; survives interruption without fake coverage claims.
 path.parent.mkdir(parents=True,exist_ok=True)
 temp=path.with_name(path.stem+".tmp.zip")
 payload={"source":"BON Navarra","complete30Days":False,
          "editor":"bon.navarra.es","issues":output,
          "failures":failures,"generatedUTC":datetime.now(timezone.utc).isoformat()}
 with ZipFile(temp,"w",ZIP_DEFLATED,compresslevel=6) as z:
  z.writestr("bon_navarra_avance.json",json.dumps(payload,ensure_ascii=False,indent=2))
  z.writestr("LEER.txt","Evidencias locales parciales: no equivalen a cobertura completa de Navarra.\n")
 temp.replace(path)

def run_bon(rows,end,limit,checkpoint=None,max_fallos=3):
 byname={x.get("name"):x for x in rows if x.get("code")=="NA"}
 index=byname.get("NA-entry-2")
 if index is None:raise ValueError("BON: falta índice principal")
 entries=discover_bon(index,end)
 output={"publisher":"bon.navarra.es","dateTo":end.isoformat(),
         "officialIssueCalendar":[{"number":n,"date":v[0].isoformat(),"extra":v[2]} for n,v in sorted(entries.items())],
         "issues":[],"originalCandidates":[],"incomplete":True}
 failures=[]
 for n,(day,url,extra) in sorted(entries.items()):
  row=byname.get("BON-"+str(n))
  if not row or row.get("officialUrl")!=url:
   row=get_page(url,"NA",f"BON-{n}")
  try:
   announced=validate_bon_issue(row,n,day)
   selected=[{"id":idx,"title":title,"url":url,"kind":classify(title)} for idx,title,url in announced
            if classify(title) is not None]
   output["issues"].append({"number":n,"date":day.isoformat(),"extraordinary":extra,
       "indexUrl":url,"documentsInSumario":len(announced),
       "candidates":len(selected),"numberDateValidated":True,"allLinksContiguous":True})
   for entry in selected:
    output["originalCandidates"].append({"bulletin":n,"date":day.isoformat(),**entry,
         "originalVerified":False})
  except Exception as ex:
   failures.append({"issue":n,"error":str(ex)[:220]})
 print("BON_SNAPSHOT",len(output["issues"]),"ediciones",
       sum(x["documentsInSumario"] for x in output["issues"]),"anuncios de índice",
       len(output["originalCandidates"]),"candidatos",flush=True)
 output["originalsAttempted"]=0
 output["originalsVerified"]=0
 if checkpoint:
  save_bon_checkpoint(checkpoint,output,failures)
  print("BON_GUARDADO_PARCIAL",str(checkpoint),flush=True)
 consecutive_fails=0
 for position,item in enumerate(output["originalCandidates"]):
  if position>=limit:
   failures.append({"error":f"Límite prudente {limit}; restantes sin verificar"})
   break
  print("BON_COMPROBANDO",position+1,"/",len(output["originalCandidates"]),
        "boletín",item["bulletin"],"anuncio",item["id"],flush=True)
  started=time.monotonic()
  result=get_page(item["url"],"NA",f"BON-ORIGINAL-{item['bulletin']}-{item['id']}")
  text=result.get("page",{}).get("publicText","")
  source=fold(item["title"])
  body=fold(text)
  # Never claim original text because an unrelated shell HTML returned 200.
  verified=(result.get("http")==200 and result.get("status")=="public_page_captured"
    and len(text)>450 and source[:min(28,len(source))] in body)
  item.update({"originalVerified":bool(verified),"http":result.get("http"),
               "status":result.get("status"),
               "originalTextExcerpt":text[:40000] if verified else text[:900],
               "originalPageHeadings":result.get("page",{}).get("headings",[])[:25]})
  output["originalsAttempted"]=position+1
  output["originalsVerified"]=sum(x.get("originalVerified") for x in output["originalCandidates"])
  connection_failed=result.get("status") in ("connection_error","http_error","human_verification","unverified_redirect")
  consecutive_fails=consecutive_fails+1 if connection_failed else 0
  print("BON_ORIGINALES",position+1,"/",len(output["originalCandidates"]),
       "verificados",output["originalsVerified"],
       "último",("OK" if verified else str(result.get("status","error"))),
       "duración",round(time.monotonic()-started,1),"s",flush=True)
  if checkpoint:
   save_bon_checkpoint(checkpoint,output,failures)
  if consecutive_fails>=max_fallos:
   failures.append({"error":"Se detiene la descarga por "+str(max_fallos)+" fallos consecutivos del editor oficial",
                    "lastBulletin":item["bulletin"],"lastArticle":item["id"],
                    "originalsAttempted":position+1})
   if checkpoint:save_bon_checkpoint(checkpoint,output,failures)
   print("BON_DETENIDO: origen no responde de forma fiable; avance parcial guardado, NO se declara cobertura",flush=True)
   break
  time.sleep(0.35)
 output["issuesMissing"]=failures
 output["originalsVerified"]=sum(x.get("originalVerified") for x in output["originalCandidates"])
 output["indexCompleteForWindow"]=(not failures and len(output["issues"])==len(entries))
 output["allCandidatesOriginalsVerified"]=(not failures and
         output["originalsVerified"]==len(output["originalCandidates"]))
 print("BON_RESULT",json.dumps({"issues":len(output["issues"]),"candidateOriginals":len(output["originalCandidates"]),
      "verified":output["originalsVerified"],"gaps":failures[:5]},ensure_ascii=True),flush=True)
 return output
def run_asturias(rows,end):
 from urllib.parse import parse_qs
 found=[];false_pages=[]
 for row in rows:
  m=re.fullmatch(r"BOPA-(\d{4}-\d{2}-\d{2})",row.get("name",""))
  if not m:continue
  requested=date.fromisoformat(m[1])
  if not end-timedelta(days=29)<=requested<=end:continue
  headers=[h["text"] for h in row.get("page",{}).get("headings",[]) if h.get("level")=="h1"]
  match=re.search(r"Bolet[ií]n\s+N[ºO]\s*(\d+)\s+del\s+\w+\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+2026",headers[0],re.I) if headers else None
  if not match:
   false_pages.append({"requested":requested.isoformat(),"reason":"no original issue heading"})
   continue
  actual=date(2026,MONTHS.get(fold(match[3]),0),int(match[2]))
  if actual!=requested:
   false_pages.append({"requested":requested.isoformat(),"served":actual.isoformat(),"reason":"default issue not original date"})
   continue
  pdfs=[]
  for a in row.get("page",{}).get("links",[]):
   u=a.get("url","")
   if re.fullmatch(r"https://miprincipado[.]asturias[.]es/bopa/2026/\d{2}/\d{2}/2026-\d{5}[.]pdf",u):
    pdfs.append(u)
  if not pdfs:raise ValueError("BOPA: boletín auténtico sin enlaces a disposiciones")
  found.append({"date":requested.isoformat(),"number":int(match[1]),"originalPdfLinks":sorted(set(pdfs)),
                "count":len(set(pdfs))})
 nums=[x["number"] for x in sorted(found,key=lambda a:a["date"])]
 complete=bool(nums) and nums==list(range(nums[0],nums[-1]+1))
 print("BOPA_RESULT",len(found),"ediciones",sum(x["count"] for x in found),
        "PDF enlazados; páginas sustituidas",len(false_pages),flush=True)
 return {"publisher":"miprincipado.asturias.es","issues":found,
      "unexpectedDefaultPages":false_pages,"consecutiveRealIssues":complete,
      "incomplete":True}
def parse_jaen_digital(row,expected_date,url):
 """Require official issue headline AND date-bound full PDF and summary URL."""
 if row.get("status")!="public_page_captured" or row.get("http")!=200:
  raise ValueError("La edición no está publicada o no se capturó")
 if row.get("finalOfficialUrl")!=url:
  raise ValueError("La página redirige a un día distinto")
 content=row.get("page",{})
 txt=content.get("publicText","")
 # Publisher can render 'Nº', 'N�', or 'N°' depending on HTML encoding.
 pat=(r"Bolet[ií]n\s+N[\sº°o\ufffd]*:?\s*(?P<num>\d{2,4})\s+"
      r"(?:Lunes|Martes|Mi[eé]rcoles|Jueves|Viernes|S[aá]bado|Domingo)\s*,\s*"
      r"(?P<day>\d{1,2})\s+de\s+(?P<month>septiembre|octubre)\s+de\s+2026")
 match=re.search(pat,txt,re.I)
 if not match:raise ValueError("No aparece la cabecera con número y fecha del BOP")
 if parse_es_date(match["day"]+" de "+match["month"]+" de 2026")!=expected_date:
  raise ValueError("La fecha de la edición no coincide con la solicitada")
 number=int(match["num"])
 original_pdf=None
 sumario_pdf=None
 edicts=[]
 for a in content.get("links",[]):
  u=a.get("url","")
  p=urlsplit(u)
  if p.scheme!="https" or p.hostname!="bop.dipujaen.es" or p.path!="/descargarws.dip":continue
  q=parse_qs(p.query)
  if (q.get("fechaBoletin")!=[expected_date.isoformat()] or
      q.get("ejercicioBop")!=["2026"] or
      q.get("boletinSuplemento")!=["0"]):continue
  kind=q.get("tipo",[""])[0]
  if kind in ("bopCompleto","bopSumario"):
   if q.get("numeroBoletin")!=[str(number)]:
    raise ValueError("PDF del sumario/edición con número distinto")
   if kind=="bopCompleto":original_pdf=u
   else:sumario_pdf=u
  elif kind=="bop":
   edi=q.get("numeroEdicto",[""])[0]
   if not re.fullmatch(r"\d{1,7}",edi) or q.get("anioExpedienteEdicto")!=["2026"]:
    raise ValueError("Anuncio con identificador original no verificable")
   edicts.append({"id":f"JA-2026-{edi}","url":u,
        "listedText":a.get("text","")[:160]})
 if not original_pdf or not sumario_pdf:
  raise ValueError("Edición sin enlaces originales completos y sumario")
 if len(edicts)<1 or len({e["id"] for e in edicts})!=len(edicts):
  raise ValueError("La lista de edictos está vacía o repetida")
 return {"date":expected_date.isoformat(),"number":number,"sourcePage":url,
       "officialCompletePdf":original_pdf,"officialSummaryPdf":sumario_pdf,
       "edictCount":len(edicts),"edicts":edicts,
       "indexText":txt,"issueAndOriginalLinksVerified":True,
       "originalPdfContentsVerified":False}

def run_jaen(rows,end,check_days):
 output={"publisher":"bop.dipujaen.es","issues":[],"noIssueOrMismatch":[],
         "incomplete":True,"publisherOriginalsLinkedOnly":True}
 cached={x.get("officialUrl"):x for x in rows if x.get("code")=="JA"}
 start=end-timedelta(days=29)
 for d in (start+timedelta(days=i) for i in range(30)):
  url=JAEN_BASE+d.strftime("%d-%m-%Y")
  row=cached.get(url)
  if row is None and check_days:
   print("JAEN_COMPROBANDO",d.isoformat(),flush=True)
   row=get_page(url,"JA",f"JAEN-{d.isoformat()}")
  if row is None:continue
  try:
   data=parse_jaen_digital(row,d,url)
   output["issues"].append(data)
   print("JAEN_EDICION",data["number"],data["date"],
         data["edictCount"],"originales enlazados",flush=True)
  except Exception as ex:
   output["noIssueOrMismatch"].append({"date":d.isoformat(),
      "status":row.get("status"),"reason":str(ex)[:170]})
  if check_days:time.sleep(0.3)
 output["issueNumbersRecovered"]=[x["number"] for x in output["issues"]]
 output["focusNumbersRecovered"]=sorted(set(output["issueNumbersRecovered"]) & {198,199,201})
 print("JAEN_RESULT",len(output["issues"]),"ediciones con índice y PDF oficial",
       "números 198,199,201 recuperados",output["focusNumbersRecovered"],
       "editorial full PDFs descargados",0,flush=True)
 return output
def save(out,data):
 out.parent.mkdir(parents=True,exist_ok=True)
 with ZipFile(out,"w",ZIP_DEFLATED,compresslevel=7) as z:
  z.writestr("auditoria_local_v2.json",json.dumps(data,ensure_ascii=False,indent=2))
  z.writestr("LEER.txt","Evidencia parcial del editor oficial. NO supone certificación de cobertura.\n"
    "No incluye contraseñas, cookies ni archivos personales. Enviar este ZIP para auditoría independiente.\n")
 print("ZIP_GENERADO",str(out),flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--input",type=Path)
 p.add_argument("--output",type=Path)
 p.add_argument("--self-test",action="store_true")
 p.add_argument("--max-bon-originales",type=int,default=180)
 p.add_argument("--max-fallos-consecutivos",type=int,default=3)
 p.add_argument("--solo-navarra",action="store_true")
 p.add_argument("--solo-jaen",action="store_true")
 p.add_argument("--no-jaen-daily",action="store_true")
 args=p.parse_args()
 if args.self_test:
  assert classify("Oposición de 4 plazas de administrativo/a")=="Plaza / oposición"
  assert classify("Concurso-oposición de una plaza de bombero")=="Plaza / oposición"
  assert classify("Bolsa de trabajo de personal laboral")=="Bolsa de trabajo"
  assert classify("Oposición de 4 plazas. Lista definitiva de admitidos") is None
  assert classify("Convocatoria de subvenciones para ayudas a empresas") is None
  assert parse_es_date("30 de octubre de 2026")==date(2026,10,30)
  from types import SimpleNamespace
  example_date=date(2026,10,8)
  first="https://bop.dipujaen.es/descargarws.dip?fechaBoletin=2026-10-08&ejercicioBop=2026&numeroBoletin=198&boletinSuplemento=0"
  test_page={"status":"public_page_captured","http":200,
    "finalOfficialUrl":"https://bop.dipujaen.es/bop/08-10-2026",
    "page":{"publicText":"Boletín N�: 198 Jueves, 8 de octubre de 2026",
    "links":[{"url":first+"&tipo=bopCompleto","text":"Boletín Completo"},
             {"url":first+"&tipo=bopSumario","text":"Sumario"},
             {"url":"https://bop.dipujaen.es/descargarws.dip?fechaBoletin=2026-10-08&ejercicioBop=2026&boletinSuplemento=0&tipo=bop&anioExpedienteEdicto=2026&numeroEdicto=4845","text":"Edicto"}]}}
  assert parse_jaen_digital(test_page,example_date,"https://bop.dipujaen.es/bop/08-10-2026")["number"]==198
  try:parse_jaen_digital(test_page,date(2026,10,9),"https://bop.dipujaen.es/bop/08-10-2026")
  except ValueError:pass
  else:raise AssertionError("No se detectó la fecha de Jaén incorrecta")
  assert safe_url("https://bon.navarra.es/es/anuncio/-/texto/2026/218/0")
  from tempfile import TemporaryDirectory
  with TemporaryDirectory() as d:
   q=Path(d)/"avance.zip"
   save_bon_checkpoint(q,{"originalCandidates":[{"originalVerified":False}]},[])
   with ZipFile(q) as check:
    assert check.namelist()==["bon_navarra_avance.json","LEER.txt"]
    assert json.loads(check.read("bon_navarra_avance.json"))["complete30Days"] is False
  assert args.max_fallos_consecutivos>0
  print("OK: filtros, fechas, checkpoint local y controles fail-closed",flush=True)
  return
 folder=Path.home()/"Documents"/"OpoAlert"
 files=sorted(folder.glob("OpoAlert_evidencias_oficiales_*.zip"),key=lambda x:x.stat().st_mtime,reverse=True)
 source=args.input or (files[0] if files else None)
 if source is None:raise SystemExit("No se encontró el ZIP inicial en Documentos/OpoAlert")
 original=load_evidence(source)
 end=date.fromisoformat(original["requestedPeriod"][1])
 rows=original["results"]
 out={"generatedUTC":datetime.now(timezone.utc).isoformat(),
     "baseEvidenceSHA256":hashlib.sha256(source.read_bytes()).hexdigest(),
     "requestedPeriod":[str(end-timedelta(days=29)),str(end)],
     "complete30Days":False,"readOnly":True,"officialPublisherOnly":True,
     "sources":{},"failures":{}}
 checkpoint=folder/("OpoAlert_avance_navarra_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".zip")
 tasks=(("NA",lambda:run_bon(rows,end,args.max_bon_originales,checkpoint,
                 max(1,args.max_fallos_consecutivos))),
        ("AS",lambda:run_asturias(rows,end)),
        ("JA",lambda:run_jaen(rows,end,not args.no_jaen_daily)))
 for code,task in tasks:
  if args.solo_navarra and code!="NA":continue
  if args.solo_jaen and code!="JA":continue
  try:out["sources"][code]=task()
  except Exception as e:
   out["failures"][code]=type(e).__name__+": "+str(e)[:350]
   print("SOURCE_FAILED",code,out["failures"][code],flush=True)
 name="OpoAlert_auditoria_local_v2_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".zip"
 save(args.output or folder/name,out)
if __name__=="__main__":main()
