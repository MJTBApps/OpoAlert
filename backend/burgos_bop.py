#!/usr/bin/env python3
"""Lector diario del BOP de Burgos (Boletín Oficial de la Provincia de Burgos).

Fuente: portal Drupal https://bopbur.diputaciondeburgos.es/ de la Diputación.
  * Hemeroteca mensual /hemeroteca/AAAA-MM: un enlace por boletín
    («Boletín BOPBUR-2026-207 - 30/10/2026» -> /bopbur-2026-207).
  * Página de cada boletín: cabecera con «núm. N», fecha y, si lo es,
    «Extraordinario»; debajo, TODOS los anuncios en una sola página, agrupados
    por sección y organismo, cada uno con su PDF oficial
    /sites/default/files/private/publicado/<boletín>/<boletín>-anuncio-<n>.pdf.
  * Dos series con numeración propia y anual: ordinarios (lunes a viernes) y
    extraordinarios («Extraordinario núm. 1», dirección /bopbur-2026-001-0).

Para la ventana de 30 días que acaba hoy se leen las hemerotecas de los meses
afectados (y la del mes anterior, para comprobar el boletín previo), cada
boletín completo y todos sus anuncios. Si algo no cuadra (huecos de
numeración, cabecera que no coincide con la hemeroteca, anuncio sin PDF
oficial, anuncio repetido, paginación inesperada, verificación anti-robots) el
lector falla y no escribe nada: nunca se publican datos parciales.

Contadores: announcementsRead = anuncios de todos los boletines leídos;
notices = anuncios cuyo título es una convocatoria o bolsa de empleo
(filtro conservador común, clm_common.employment).

El servidor solo acepta TLS 1.0 con cifrados antiguos, que el OpenSSL 3 de
Python rechaza por defecto. Para ESTE host se monta un adaptador con
verificación de certificado y de nombre de host activadas, versión mínima
TLS 1.0 y SECLEVEL=0. Nada más cambia.

Uso: python backend/burgos_bop.py --output out/burgos_bop.json
"""
from __future__ import annotations
import argparse,re,ssl,sys,threading,time,warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urljoin,urlsplit

import requests
from requests.adapters import HTTPAdapter
from bs4 import BeautifulSoup

sys.path.insert(0,str(Path(__file__).resolve().parent))
import clm_common
from provincial_common import ProvincialCoverageError,fold

SOURCE="https://bopbur.diputaciondeburgos.es/"
PROVINCE="Burgos"
CODE="BU"
HOST="bopbur.diputaciondeburgos.es"
BASE="https://"+HOST
PDF_PREFIX="/sites/default/files/private/publicado/"
MONTHS=("enero","febrero","marzo","abril","mayo","junio","julio","agosto",
        "septiembre","octubre","noviembre","diciembre")
ISSUE_PATH=re.compile(r"/bopbur-(\d{4})-(\d{3})(?:-(\d{1,2}))?")
LISTING_TEXT=re.compile(r"Bolet[ií]n BOPBUR-(\d{4})-(\d{3}) - (\d{2})/(\d{2})/(\d{4})")
NUMBER=re.compile(r"n[uú]m\.\s*(\d{1,3})",re.I)
DATE_TEXT=re.compile(r"(\d{1,2}) de ([a-záéíóú]+) de (\d{4})",re.I)
ANNOUNCE_ID=re.compile(r"bopbur-anuncio-(\d{6,10})")
ID_PATTERN=re.compile(r"BU-\d{4}-\d{6,10}")    # el mismo de Province.kt
MIN_ISSUES=12          # 30 días con Navidad: 15 boletines (6/12/2025-4/1/2026)
MAX_LOOKBACK_MONTHS=12
WORKERS=3
PAUSE=0.3

class BurgosCoverageError(ProvincialCoverageError):pass

def fail(message):
    raise BurgosCoverageError("Burgos BOP: "+str(message))

# ---------------------------------------------------------------- HTTP
class LegacyTLSAdapter(HTTPAdapter):
    """TLS 1.0 y cifrados antiguos SOLO para este host; certificado y nombre verificados."""
    def _context(self):
        ctx=ssl.create_default_context()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore",DeprecationWarning)
            ctx.minimum_version=ssl.TLSVersion.TLSv1
        ctx.set_ciphers("DEFAULT:@SECLEVEL=0")
        assert ctx.verify_mode==ssl.CERT_REQUIRED and ctx.check_hostname
        return ctx
    def init_poolmanager(self,*args,**kwargs):
        kwargs["ssl_context"]=self._context()
        return super().init_poolmanager(*args,**kwargs)
    def proxy_manager_for(self,*args,**kwargs):
        kwargs["ssl_context"]=self._context()
        return super().proxy_manager_for(*args,**kwargs)

_LOCAL=threading.local()
def session():
    if not hasattr(_LOCAL,"s"):
        s=requests.Session()
        s.mount(BASE+"/",LegacyTLSAdapter())
        s.headers.update({"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/130.0 Safari/537.36 OpoAlert",
                          "Accept-Language":"es-ES,es;q=0.9"})
        _LOCAL.s=s
    return _LOCAL.s

def official(url):
    u=urlsplit(url)
    return (u.scheme=="https" and u.hostname==HOST and u.port in (None,443)
            and not u.username and not u.password and not u.fragment and "/../" not in u.path)

def anti_robot(text):
    t=text[:200_000].lower()
    return any(w in t for w in ("captcha","cf-challenge","are you a robot","verificación de seguridad"))

def fetch(url,retries=3,limit=6_000_000):
    """HTML de una página oficial (texto)."""
    if not official(url):fail("URL fuera del portal oficial: "+url[:160])
    error=None
    for i in range(retries):
        try:
            r=session().get(url,timeout=(15,60),allow_redirects=True)
            if not official(r.url):fail("redirección fuera del portal oficial: "+r.url[:160])
            if r.status_code!=200:raise requests.HTTPError(f"HTTP {r.status_code}")
            if not r.content or len(r.content)>limit:fail("página vacía o desmesurada: "+url)
            text=r.text
            if anti_robot(text):
                fail("el portal pide una verificación anti-robots; no se elude: "+url)
            time.sleep(PAUSE)
            return text
        except requests.RequestException as ex:
            error=ex
            if i<retries-1:time.sleep(2*(i+1))
    fail(f"sin acceso a {url}: {error}")

def pdf_ok(url,retries=3):
    """El enlace de un anuncio es de verdad un PDF oficial (solo se leen los primeros bytes)."""
    if not official(url):fail("PDF fuera del portal oficial: "+url[:160])
    error=None
    for i in range(retries):
        try:
            with session().get(url,timeout=(15,60),stream=True,allow_redirects=True) as r:
                if not official(r.url) or r.status_code!=200:raise requests.HTTPError(f"HTTP {r.status_code}")
                head=next(r.iter_content(chunk_size=64),b"")
                if not head.startswith(b"%PDF-"):fail("el enlace oficial no es un PDF: "+url)
                return True
        except requests.RequestException as ex:
            error=ex
            if i<retries-1:time.sleep(2*(i+1))
    fail(f"sin acceso al PDF {url}: {error}")

# ---------------------------------------------------------------- hemeroteca
def month_url(year,month):
    return f"{BASE}/hemeroteca/{year}-{month:02d}"

def parse_month(html,year,month):
    """Boletines de la hemeroteca de un mes: lista de (url, número, fecha)."""
    soup=BeautifulSoup(html,"html.parser")
    if soup.select(".pager, ul.pager, a[href*='page=']"):
        fail(f"la hemeroteca de {month}/{year} tiene varias páginas; el lector no las conoce")
    found={}
    for a in soup.select("a[href]"):
        text=" ".join(a.get_text(" ",strip=True).split())
        m=LISTING_TEXT.fullmatch(text)
        if not m:
            if text.startswith("Boletín BOPBUR"):fail("entrada desconocida en la hemeroteca: "+text[:80])
            continue
        url=urljoin(BASE+"/",a["href"])
        p=urlsplit(url)
        pm=ISSUE_PATH.fullmatch(p.path)
        if not official(url) or p.query or not pm:fail("enlace de boletín inesperado: "+a["href"][:120])
        try:day=date(int(m[5]),int(m[4]),int(m[3]))
        except ValueError:fail("fecha imposible en la hemeroteca: "+text)
        if (day.year,day.month)!=(year,month):fail(f"la hemeroteca de {month}/{year} trae un boletín del {day}")
        if pm[1]!=m[1] or pm[2]!=m[2] or int(m[1])!=day.year:
            fail("dirección y nombre del boletín no coinciden: "+text)
        number=int(m[2])
        if not 1<=number<=400:fail("número de boletín imposible: "+text)
        if url in found and found[url]!=(number,day):fail("boletín repetido con datos distintos: "+text)
        found[url]=(number,day)
    return sorted(((u,)+v for u,v in found.items()),key=lambda x:(x[2],x[1],x[0]))

# ---------------------------------------------------------------- boletín
def spanish_date(text):
    m=DATE_TEXT.search(fold(text))
    if not m or m[2] not in MONTHS:fail("fecha ilegible en la cabecera: "+text[:80])
    return date(int(m[3]),MONTHS.index(m[2])+1,int(m[1]))

def parse_header(soup,url):
    top=soup.select("div.bopbur-top-boletin")
    if len(top)!=1:fail("cabecera de boletín ausente o repetida: "+url)
    top=top[0]
    num=top.select_one("span.title-number");dat=top.select_one("span.title-date")
    if not num or not dat:fail("cabecera sin número o fecha: "+url)
    m=NUMBER.search(num.get_text(" ",strip=True))
    if not m:fail("número ilegible en la cabecera: "+url)
    special=" ".join(x.get_text(" ",strip=True) for x in top.select("span.title-especial")).strip()
    if special and fold(special)!="extraordinario":fail(f"tipo de boletín desconocido «{special}»: {url}")
    return bool(special),int(m[1]),spanish_date(dat.get_text(" ",strip=True))

def heading(li):
    for child in li.children:
        if getattr(child,"name",None) in ("h2","h3","h4","h5","h6"):
            return " ".join(child.get_text(" ",strip=True).split())
    return ""

def parse_issue(html,url,number,day):
    """Lee la página completa de un boletín y comprueba cada anuncio."""
    soup=BeautifulSoup(html,"html.parser")
    if soup.select(".pager, ul.pager, a[href*='page=']"):fail("boletín con varias páginas: "+url)
    extra,head_number,head_day=parse_header(soup,url)
    if head_number!=number or head_day!=day:
        fail(f"{url}: la cabecera dice núm. {head_number} del {head_day}; la hemeroteca, {number} del {day}")
    slug=urlsplit(url).path.strip("/")
    base=re.escape(re.sub(r"-\d{1,2}$","",slug))
    # Extraordinario /bopbur-2026-001-0: boletín completo en bopbur-2026-001/bopbur-2026-001_0.pdf
    full=re.compile(re.escape(PDF_PREFIX)+base+r"(?:-\d{1,2})?/"+base+r"(?:_\d{1,2})?\.pdf")
    complete=[a for a in soup.select("div.bopbur-content-boletin a[href]")
              if official(urljoin(BASE+"/",a["href"])) and full.fullmatch(urlsplit(a["href"]).path)]
    if len(complete)!=1:fail(f"{url}: sin el PDF del boletín completo")
    items=soup.select("li.bopbur-anuncio")
    if not items:fail(f"{url}: boletín sin anuncios")
    file_links=[a for a in soup.select("p.bopbur-filefield-file a[href]") if "-anuncio-" in a["href"]]
    if len(file_links)!=len(items):fail(f"{url}: {len(items)} anuncios y {len(file_links)} PDF de anuncio")
    rows=[];ids=set()
    for li in items:
        m=ANNOUNCE_ID.fullmatch(li.get("id",""))
        if not m:fail(f"{url}: anuncio sin número oficial")
        n=m[1]
        if n in ids:fail(f"{url}: anuncio {n} repetido")
        ids.add(n)
        pdfs=[urljoin(BASE+"/",a["href"]) for a in li.select("a[href]")]
        expected=f"{BASE}{PDF_PREFIX}{slug}/{slug}-anuncio-{n}.pdf"
        if pdfs!=[expected]:fail(f"{url}: el anuncio {n} no enlaza su PDF oficial")
        title=" ".join(" ".join(p.get_text(" ",strip=True) for p in li.find_all("p",recursive=False)
                                if "bopbur-filefield-file" not in (p.get("class") or [])).split())
        if not title:fail(f"{url}: anuncio {n} sin título")
        chain=[]
        for cat in li.find_parents("li"):
            if "bopbur-categoria" in (cat.get("class") or []):chain.append((cat,heading(cat)))
        chain.reverse()     # sección, organismo, dependencia...
        if not chain or not all(h for _,h in chain):fail(f"{url}: anuncio {n} sin sección u organismo")
        organs=[h for cat,h in chain if "bopbur-categoria-level-0" not in (cat.get("class") or [])]
        entity=" – ".join(organs) if organs else re.sub(r"^[IVXL]+\.\s*","",chain[0][1])
        rows.append({"n":n,"title":title,"entity":entity,"url":expected})
    return {"extra":extra,"number":number,"day":day,"url":url,"announcements":rows}

def label(extra,number):
    return f"Extraordinario {number}" if extra else str(number)

# ---------------------------------------------------------------- auditoría
def months_between(a,b):
    y,m=a.year,a.month
    while (y,m)<=(b.year,b.month):
        yield y,m
        y,m=(y+1,1) if m==12 else (y,m+1)

def prev_month(y,m):
    return (y-1,12) if m==1 else (y,m-1)

class Portal:
    def __init__(self,get=None):
        self.get=get or fetch
        self.months={};self.headers={};self.pages=0
    def month(self,y,m):
        if (y,m) not in self.months:
            self.months[(y,m)]=parse_month(self.get(month_url(y,m)),y,m);self.pages+=1
        return self.months[(y,m)]
    def issue(self,entry):
        url,number,day=entry
        x=parse_issue(self.get(url),url,number,day);self.pages+=1
        self.headers[url]=x["extra"]
        return x
    def is_extra(self,entry):
        if entry[0] not in self.headers:
            soup=BeautifulSoup(self.get(entry[0]),"html.parser");self.pages+=1
            extra,n,d=parse_header(soup,entry[0])
            if (n,d)!=(entry[1],entry[2]):fail(f"{entry[0]}: cabecera distinta de la hemeroteca")
            self.headers[entry[0]]=extra
        return self.headers[entry[0]]

def check_predecessor(portal,extra,first,start):
    """El boletín anterior de la misma serie aparece antes de la ventana."""
    number,day=first
    if number==1:
        if day.month!=1 and not extra:fail(f"ordinario núm. 1 fuera de enero ({day})")
        return
    y,m=start.year,start.month
    # El ordinario anterior está en el mes de inicio o en el previo; un extraordinario
    # anterior puede estar en cualquier mes del mismo año.
    for _ in range(MAX_LOOKBACK_MONTHS+1 if extra else 2):
        if (y,m)<(day.year,1):break
        for e in portal.month(y,m):
            if e[1]==number-1 and e[2]<start and e[2].year==day.year and portal.is_extra(e)==extra:return
        y,m=prev_month(y,m)
    fail(f"no aparece el {label(extra,number-1)} de {day.year}, anterior a la ventana")

def audit(today=None,get=None,workers=WORKERS,check_pdfs=True):
    end=today or date.today()
    start=end-timedelta(days=29)
    portal=Portal(get)
    entries=[]
    for y,m in months_between(start,end):
        entries.extend(e for e in portal.month(y,m) if start<=e[2]<=end)
    if len({e[0] for e in entries})!=len(entries):fail("boletín repetido en la hemeroteca")
    if len(entries)<MIN_ISSUES:fail(f"solo {len(entries)} boletines en 30 días")
    with ThreadPoolExecutor(max(1,min(workers,4))) as pool:
        issues=list(pool.map(portal.issue,entries))
    issues.sort(key=lambda x:(x["day"],x["extra"],x["number"]))
    keys=[(x["extra"],x["number"],x["day"].year) for x in issues]
    if len(set(keys))!=len(keys):fail("número de boletín repetido en la misma serie")
    for extra in (False,True):
        serie=[(x["day"],x["number"]) for x in issues if x["extra"]==extra]
        if not serie:
            if not extra:fail("ningún boletín ordinario en 30 días")
            continue
        if not clm_common.numbering_ok(serie):
            fail(f"huecos en la numeración de {'extraordinarios' if extra else 'ordinarios'}: {[n for _,n in serie]}")
        check_predecessor(portal,extra,(serie[0][1],serie[0][0]),start)
    ordinary=[x for x in issues if not x["extra"]]
    if (end-ordinary[-1]["day"]).days>4:fail(f"la hemeroteca no tiene boletines desde el {ordinary[-1]['day']}")
    seen={};issue_data=[];checks=[]
    for x in issues:
        number=label(x["extra"],x["number"]);notices=[]
        for a in x["announcements"]:
            nid=f"{CODE}-{x['day'].year}-{a['n']}"
            if not ID_PATTERN.fullmatch(nid):fail("identificador fuera del patrón de la app: "+nid)
            if a["n"] in seen:fail(f"anuncio {a['n']} en {seen[a['n']]} y en {number}")
            seen[a["n"]]=number
            kind=clm_common.employment(a["title"])
            if not kind:continue
            notices.append({"id":nid,"province":PROVINCE,"title":a["title"],"entity":a["entity"],
                "date":x["day"].strftime("%d/%m/%Y"),"bulletin":number,"type":kind,"url":a["url"],
                "publisherArticle":a["n"]})
        if notices:checks.append(notices[0]["url"])
        issue_data.append({"day":x["day"],"number":number,"read":len(x["announcements"]),"notices":notices})
        print("BURGOS",x["day"],"boletín",number,"anuncios",len(x["announcements"]),"candidatas",len(notices),flush=True)
    if check_pdfs:
        with ThreadPoolExecutor(max(1,min(workers,4))) as pool:
            list(pool.map(pdf_ok,checks))
    try:
        feed=clm_common.publish_audit(SOURCE,PROVINCE,issue_data,today=end,min_issues=MIN_ISSUES)
    except BurgosCoverageError:raise
    except ProvincialCoverageError as ex:
        fail(str(ex).replace("Castilla-La Mancha: ",""))
    feed["coverage"].update(pagesVisited=portal.pages,
        announcementsReadMeaning="anuncios de todos los boletines (ordinarios y extraordinarios) con su PDF oficial",
        pdfChecked=len(checks))
    feed["historyCoverage"].update(
        regularBulletins=[label(False,x["number"]) for x in issues if not x["extra"]],
        extraordinaryBulletins=[label(True,x["number"]) for x in issues if x["extra"]],
        issueUrls=[x["url"] for x in issues])
    return feed

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output",required=True)
    ap.add_argument("--today",type=date.fromisoformat,help="solo para pruebas")
    a=ap.parse_args()
    clm_common.write_output(a.output,audit(a.today))

if __name__=="__main__":
    main()
