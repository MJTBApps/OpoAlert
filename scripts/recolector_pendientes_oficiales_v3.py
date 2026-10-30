#!/usr/bin/env python3
"""OpoAlert: read-only original-publisher index collector for CB, CE, VD, CL.

Collects public issue indexes, sanctioned cross-links and local publisher
form/script metadata to diagnose 30-day archives from a Spanish PC.
- No cookies, credentials, login, browser profiles, CAPTCHA bypass or upload.
- Official source links only; no private aggregators or guessed data.
- A successfully retrieved homepage or PDF header is NOT complete coverage.
- Bounded requests, local checkpoint ZIP, source-specific errors and dates.
"""
from __future__ import annotations
import argparse,json,re,ssl,time
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin,urlsplit,urlunsplit,urlencode,parse_qsl
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from zipfile import ZipFile,ZIP_DEFLATED
from recolector_bop_local import OFFICIAL_HOSTS,PublicPageParser,safe_url

OFFICIAL_HOSTS.update({
 "ebop.diputaciolleida.cat","www.diputaciolleida.cat","www.diputaciolleida.es",
 "ceuta.es","bocce.ceuta.es","bop.sede.diputaciondevalladolid.es"
})
START=date(2026,9,30)
END=date(2026,10,29)
MAX_DOC_BYTES=9_000_000
MAX_HTML_BYTES=1_650_000
TIMEOUT=14
SEEDS={
 "CB":[
  "https://boc.cantabria.es/boces/",
  "https://boc.cantabria.es/boces/inicioCargaInicialBoletines.do",
  "https://boc.cantabria.es/boces/menu.do?dir=%2FinicioCargaInicialBoletines.do",
  "https://boc.cantabria.es/boces/menu.do?dir=%2FdescargaBoletines.do",
  "https://boc.cantabria.es/boces/menu.do?dir=%2FinicioBusquedaAnuncios.do",
  "https://boc.cantabria.es/boces/boletines.do?boton=fecha&fecha=29%2F10%2F2026",
  "https://boc.cantabria.es/boces/verBoletin.do?fecha=29%2F10%2F2026",
  "https://boc.gobcantabria.es/boces/",
 ],
 "CE":[
  "https://www.ceuta.es/ceuta/bocce",
  "https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1965-2026?Itemid=534",
  "https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1982-octubre?Itemid=534",
  "https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1981-septiembre?Itemid=534",
  "https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1982-octubre?Itemid=534&start=5",
  "https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1982-octubre?Itemid=534&start=10",
  "https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1982-octubre?Itemid=534&start=15",
 ],
 "VD":[
  "https://bop.sede.diputaciondevalladolid.es/calendario",
  "https://bop.sede.diputaciondevalladolid.es/ultimobop",
  "https://bop.sede.diputaciondevalladolid.es/busqueda",
  "https://bop.sede.diputaciondevalladolid.es/calendario?year=2026&month=10",
 ],
 "CL":[
  "https://ebop.diputaciolleida.cat/bop/",
  "https://ebop.diputaciolleida.cat/",
  "https://ebop.diputaciolleida.cat/bop/2026",
  "https://www.diputaciolleida.cat/ca/arees/area-darxius-estudis-i-informacio/recursos-i-subvencions/consultas-en-linia/butlleti-oficial-de-la-provincia-bop",
 ]
}
SENS=re.compile(r"password|token|auth|session|secret|csrf|apikey|api_key|^key$",re.I)
HOST_MAP={
 "CB":{"boc.cantabria.es","boc.gobcantabria.es","www.boc.cantabria.es"},
 "CE":{"www.ceuta.es","ceuta.es","bocce.ceuta.es"},
 "VD":{"bop.sede.diputaciondevalladolid.es","www.sede.diputaciondevalladolid.es"},
 "CL":{"ebop.diputaciolleida.cat","www.diputaciolleida.cat"}
}
class PublicMetadata(HTMLParser):
 def __init__(self,url,code):
  super().__init__(convert_charrefs=True)
  self.url=url;self.code=code;self.form=None
  self.forms=[];self.scripts=[];self.options=[];self.tables=[]
 def handle_starttag(self,tag,attrs):
  a=dict(attrs)
  if tag=="form":
   target=safe_url(urljoin(self.url,a.get("action","")))
   if target and urlsplit(target).hostname in HOST_MAP[self.code]:
    self.form={"action":target,"method":a.get("method","GET").upper(),"names":[]}
    self.forms.append(self.form)
   else:self.form=None
  elif tag in ("input","select","textarea","button") and self.form:
   name=a.get("name","")
   if name and not SENS.search(name) and len(name)<100:
    entry={"name":name,"tag":tag}
    if tag=="input":entry["type"]=a.get("type","text")
    self.form["names"].append(entry)
  elif tag=="script" and a.get("src"):
   url=safe_url(urljoin(self.url,a["src"]))
   if url and urlsplit(url).hostname in HOST_MAP[self.code] and url not in self.scripts:
    self.scripts.append(url)
 def handle_endtag(self,tag):
  if tag=="form":self.form=None

def url_ok(raw,code):
 u=safe_url(raw)
 if not u:return None
 p=urlsplit(u)
 if p.hostname not in HOST_MAP[code]:return None
 # A public issue URL can't be another publisher, even after a redirect.
 return u

def fetch(code,name,raw):
 url=url_ok(raw,code)
 if not url:return {"code":code,"name":name,"status":"invalid_url"}
 row={"code":code,"name":name,"officialUrl":url}
 started=time.monotonic()
 try:
  req=Request(url,headers={"User-Agent":"Mozilla/5.0 (OpoAlert; public official gazette reader)",
    "Accept-Language":"es-ES,es;q=0.9,ca;q=0.8",
    "Accept":"text/html,application/xhtml+xml,application/pdf,application/json,application/xml;q=0.9,*/*;q=0.8"})
  with urlopen(req,timeout=TIMEOUT,context=ssl.create_default_context()) as res:
   mime=res.headers.get("Content-Type","")
   final=url_ok(res.geturl(),code)
   data=res.read(MAX_DOC_BYTES+1 if "pdf" in mime.lower() else MAX_HTML_BYTES+1)
   row.update({"http":res.status,"finalOfficialUrl":final,"mime":mime.split(";")[0],
    "readBytes":len(data)})
  if not final:
   row["status"]="redirected_off_publisher"
  elif data[:5]==b"%PDF-":
   row["pdfSignature"]="%PDF-"
   if len(data)>MAX_DOC_BYTES:
    row["status"]="pdf_too_large_to_hash"
   else:
    import hashlib
    row["status"]="complete_pdf_original_captured"
    row["pdfSHA256"]=hashlib.sha256(data).hexdigest()
    row["pdfBytes"]=len(data)
  elif len(data)>MAX_HTML_BYTES:
   row["status"]="html_too_large"
  elif "html" in mime.lower() or data.lstrip()[:6].lower() in (b"<html>",b"<!doct"):
   import re as _re
   cs=_re.search(r"charset\s*=\s*([\w-]+)",mime,re.I)
   encoding=(cs[1] if cs else "utf-8")
   try:html=data.decode(encoding,"replace")
   except LookupError:html=data.decode("utf-8","replace")
   p=PublicPageParser(final);p.feed(html)
   meta=PublicMetadata(final,code);meta.feed(html)
   plain=" ".join(p.content)
   first=plain[:4000].lower()
   if any(s in first for s in ("captcha","turnstile","verificación de seguridad","verificacion necesaria")):
    row["status"]="human_verification"
   elif len(plain)<70:row["status"]="short_or_dynamic_page"
   else:row["status"]="public_index_captured"
   row["page"]={"headings":p.headings[:120],"links":[l for l in p.links[:1700]
                 if url_ok(l.get("url"),code)],"publicText":plain[:130_000]}
   row["metadata"]={"forms":meta.forms[:12],
                     "publicScriptSources":meta.scripts[:28]}
  elif "xml" in mime.lower() or "json" in mime.lower():
   row["status"]="structured_publisher_excerpt"
   row["structuredExcerpt"]=data[:50_000].decode("utf-8","replace")
  else:row["status"]="unverified_content"
 except HTTPError as e:
  row.update({"status":"http_error","http":e.code})
 except (URLError,TimeoutError,OSError,ValueError) as e:
  row.update({"status":"connection_error","errorType":type(e).__name__})
 row["seconds"]=round(time.monotonic()-started,1)
 return row

def add_discovered(rows,planned,code,max_new=45):
 # Only actual publisher links, issued in Sep/Oct 2026, may be followed.
 found=[]
 for r in rows:
  if r.get("code")!=code or r.get("status")!="public_index_captured":continue
  for a in r.get("page",{}).get("links",[]):
   u=url_ok(a.get("url"),code)
   if not u or u in planned or u in found:continue
   label=a.get("text","")
   path=urlsplit(u).path.lower()
   if code=="CE":
    active=bool(re.search(r"(?:2026|sep|octu|665[6-9]|666[0-6]|extra|bocce)",label+" "+u,re.I))
    active=active and bool(re.search("jdownloads/(?:viewcategory|viewdownload|finish)",path))
   elif code=="CB":
    active=bool(re.search(r"(?:2026|sep|octu)",label+" "+u,re.I))
    active=active and bool(re.search(r"verboletin|boletines[.]do|veranuncio",path))
   elif code=="VD":
    active=bool(re.search(r"(?:2026|octu|sept|bopva)",label+" "+u,re.I))
    active=active and bool(re.search(r"boletin|document|publicac|pdf",path))
   else:
    active=bool(re.search(r"(?:2026|octu|sept|edicte|butllet)",label+" "+u,re.I))
    active=active and "ebop.diputaciolleida.cat"==urlsplit(u).hostname
   if active:found.append(u)
   if len(found)>=max_new:break
  if len(found)>=max_new:break
 return found

def save(path,rows,checks):
 path.parent.mkdir(parents=True,exist_ok=True)
 report={"tool":"OpoAlert-Recolector-Pendientes-Oficiales-v3",
   "generatedUTC":datetime.now(timezone.utc).isoformat(),
   "requestedPeriod":[START.isoformat(),END.isoformat()],
   "audit30DaysComplete":False,
   "originalsAudited":False,
   "notes":"Capturas públicas parciales y PDF con SHA256 cuando están completos; NO activar feed sin 30 días y contraste independiente.",
   "readOnly":True,"automaticUpload":False,
   "summary":checks,"results":rows}
 tmp=path.with_name(path.stem+".tmp.zip")
 with ZipFile(tmp,"w",ZIP_DEFLATED,compresslevel=7) as z:
  z.writestr("evidencias_pendientes_v3.json",json.dumps(report,ensure_ascii=False,indent=2))
  z.writestr("LEER.txt","Solo fuentes oficiales y documentos públicos. No se han recopilado cookies, cuentas, contraseñas ni archivos personales.\n"
      "Este ZIP NO certifica 30 días completos ni se envía automáticamente. Súbelo al chat para auditar fuentes pendientes.\n")
 tmp.replace(path)

def collect(output,sources,max_pages):
 rows=[];planned=set();queue=[]
 for code in sources:
  for n,url in enumerate(SEEDS[code]):
   u=url_ok(url,code)
   if u and u not in planned:
    planned.add(u);queue.append((code,code+"-base-"+str(n+1),u))
 print("OpoAlert: recopilar SOLO índices públicos desde fuentes originales",flush=True)
 # bounded parallel groups, save local checkpoint after every batch
 n=0;batchsize=5
 while queue and n<max_pages:
  batch=queue[:min(batchsize,max_pages-n)]
  queue=queue[len(batch):]
  with ThreadPoolExecutor(max_workers=3) as pool:
   new=list(pool.map(lambda a:fetch(*a),batch))
  rows.extend(new);n+=len(new)
  for r in new:
   print(r["code"],r["name"],r["status"],"links",len(r.get("page",{}).get("links",[])),flush=True)
  # Discover only from the fresh batch, not recursively from every response.
  for code in sources:
   discovered=add_discovered(new,planned,code,max_new=20)
   for u in discovered:
    planned.add(u)
    queue.append((code,code+"-discover-"+str(len(planned)),u))
  summary={code:{"pages":sum(x["code"]==code for x in rows),
    "officialIndexes":sum(x["code"]==code and x["status"]=="public_index_captured" for x in rows),
    "hashedOriginalPDFs":sum(x["code"]==code and x["status"]=="complete_pdf_original_captured" for x in rows),
    "blocked":sum(x["code"]==code and x["status"] in ("connection_error","http_error","human_verification") for x in rows),
    "audit30DaysComplete":False} for code in sources}
  save(output,rows,summary)
  print("CHECKPOINT_GUARDADO",str(output),"consultas",n,flush=True)
  if any(x["status"]=="human_verification" for x in new):
   print("Un editor exige verificación humana. Se conserva avance sin eludirla.",flush=True)
   # Only stop querying the particular source; no hidden bypass.
   blocked_sources={x["code"] for x in new if x["status"]=="human_verification"}
   queue=[t for t in queue if t[0] not in blocked_sources]
 print("ZIP_GENERADO",str(output),"PAGINAS",len(rows),flush=True)
def main():
 p=argparse.ArgumentParser()
 p.add_argument("--self-test",action="store_true")
 p.add_argument("--sources",default="CB,CE,VD,CL")
 p.add_argument("--max-pages",type=int,default=75)
 p.add_argument("--output",type=Path)
 args=p.parse_args()
 if args.self_test:
  assert safe_url("https://ebop.diputaciolleida.cat/bop/")=="https://ebop.diputaciolleida.cat/bop/"
  assert url_ok("https://evil.example.com/", "CB") is None
  assert url_ok("http://boc.cantabria.es/boces/","CB") is None
  assert safe_url("https://boc.cantabria.es/boces/?token=SECRET&fecha=2026")=="https://boc.cantabria.es/boces/?fecha=2026"
  p1=PublicMetadata("https://boc.cantabria.es/boces/","CB")
  p1.feed('<form action="/boces/search.do" method="post"><input name="fecha" value="29-10-2026"/>'
          '<input name="csrf_token" value="SENSITIVE"/></form><script src="/boces/public.js"></script>')
  assert p1.forms[0]["method"]=="POST" and p1.forms[0]["names"]==[{"name":"fecha","tag":"input","type":"text"}]
  assert len(p1.scripts)==1 and p1.scripts[0].startswith("https://boc.cantabria.es/")
  assert all(len(SEEDS[x])>=3 for x in ("CB","CE","VD","CL"))
  from tempfile import TemporaryDirectory
  with TemporaryDirectory() as d:
   dest=Path(d)/"test.zip"
   save(dest,[{"code":"CB","name":"sample","status":"public_index_captured"}],{"CB":{"audit30DaysComplete":False}})
   with ZipFile(dest) as z:
    assert json.loads(z.read("evidencias_pendientes_v3.json"))["audit30DaysComplete"] is False
  print("OK: fuentes oficiales, sin tokens, metadatos públicos y ZIP parcial",flush=True)
  return
 sources=[x.strip().upper() for x in args.sources.split(",") if x.strip()]
 if not sources or len(set(sources))!=len(sources) or any(x not in SEEDS for x in sources):
  raise SystemExit("Fuentes válidas: CB,CE,VD,CL (separadas por comas)")
 folder=Path.home()/"Documents"/"OpoAlert"
 output=args.output or folder/("OpoAlert_pendientes_oficiales_v3_"+datetime.now().strftime("%Y%m%d_%H%M%S")+".zip")
 collect(output,sources,min(95,max(1,args.max_pages)))
if __name__=="__main__":main()
