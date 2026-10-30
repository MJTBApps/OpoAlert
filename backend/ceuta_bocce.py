#!/usr/bin/env python3
"""Lector diario del BOCCE (Boletín Oficial de la Ciudad de Ceuta).

Fuente: archivo jDownloads de www.ceuta.es (un PDF completo por boletín,
categorías año -> mes). Hay dos series con numeración propia:
  * ordinarios (BOCCE_6658_06-10-2026): numeración continua entre años;
  * extraordinarios (BOCCE_Extra51_28-10-2026): vuelven a 1 en enero.
Cada boletín trae en su primera(s) página(s) un SUMARIO con todos sus edictos
numerados («681.- Decreto ... Pág.3592»). La numeración de edictos es anual y
propia de cada serie y continúa de un boletín al siguiente.

Para cada boletín de la ventana de 30 días que acaba hoy se descarga el PDF
completo, se comprueban fecha y número en el propio PDF, se leen TODOS los
edictos del sumario y se localiza cada uno en el cuerpo del PDF. Contadores:
  announcementsRead = edictos del sumario leídos (todos, no solo convocatorias).
  notices = edictos cuyo título es una convocatoria o bolsa de empleo.
Si algo no cuadra (huecos de numeración de boletines o edictos, PDF que no
corresponde, edicto del sumario que no aparece en el cuerpo) el lector falla:
nunca se publican datos parciales.

El portal no responde desde GitHub Actions: se ejecuta en un PC con conexión
española (ejecutor propio).

Uso: python backend/ceuta_bocce.py --output out/ceuta_bocce.json
"""
from __future__ import annotations
import argparse,hashlib,re,sys,threading,time,unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urljoin,urlsplit

import requests
from bs4 import BeautifulSoup

sys.path.insert(0,str(Path(__file__).resolve().parent))
import clm_common
from provincial_common import ProvincialCoverageError

SOURCE="https://www.ceuta.es/ceuta/bocce"
PROVINCE="Ceuta (BOCCE)"
HOST="www.ceuta.es"
BASE="https://www.ceuta.es"
FINISH_PREFIX="/ceuta/component/jdownloads/finish/"
CATEGORY_URL=BASE+"/ceuta/component/jdownloads/viewcategory/{slug}?Itemid=534"
ENTITY_DEFAULT="Ciudad Autónoma de Ceuta"
MONTHS=("enero","febrero","marzo","abril","mayo","junio","julio","agosto",
        "septiembre","octubre","noviembre","diciembre")
MAX_PDF_BYTES=90_000_000
MIN_ORDINARY=6          # martes y viernes: 8-9 en 30 días; margen para festivos
MAX_LOOKBACK_MONTHS=13  # para encontrar el extraordinario anterior a la ventana
WORKERS=2
PAUSE=0.6

class CeutaCoverageError(ProvincialCoverageError):pass

def fail(message):
    raise CeutaCoverageError("Ceuta BOCCE: "+str(message))

def fold(text):
    t=unicodedata.normalize("NFD",str(text).casefold())
    return " ".join("".join(c for c in t if unicodedata.category(c)!="Mn").split())

# ---------------------------------------------------------------- HTTP
_LOCAL=threading.local()
def session():
    if not hasattr(_LOCAL,"s"):
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert lector BOCCE)",
                          "Accept-Language":"es-ES,es;q=0.9"})
        _LOCAL.s=s
    return _LOCAL.s

def official(url):
    u=urlsplit(url)
    return (u.scheme=="https" and u.hostname==HOST and u.port in (None,443)
            and not u.username and not u.password and not u.fragment
            and u.path.startswith("/ceuta/") and "/../" not in u.path)

def fetch(url,limit=4_000_000,retries=3):
    if not official(url):fail("URL fuera del portal oficial: "+url[:160])
    error=None
    for i in range(retries):
        try:
            with session().get(url,timeout=(15,90),stream=True,allow_redirects=True) as r:
                if not official(r.url):fail("redirección fuera del portal oficial: "+r.url[:160])
                if r.status_code!=200:raise requests.HTTPError(f"HTTP {r.status_code}")
                body=bytearray()
                for chunk in r.iter_content(65536):
                    body+=chunk
                    if len(body)>limit:fail(f"documento mayor de {limit} bytes: {url}")
                if not body:raise requests.RequestException("respuesta vacía")
                return bytes(body),r.headers.get("Content-Type","")
        except requests.RequestException as ex:
            error=ex
            if i<retries-1:time.sleep(2*(i+1))
    fail(f"sin acceso a {url}: {error}")

def html(url):
    body,_=fetch(url)
    return BeautifulSoup(body,"html.parser")

# ---------------------------------------------------------------- calendario
_CATS={}
def year_category(year):
    if year not in _CATS:
        soup=html(SOURCE)
        slugs={m[1] for a in soup.select("a[href]")
               if (m:=re.search(r"/jdownloads/viewcategory/(\d+-(\d{4}))(?:\?|$)",a["href"])) and m[2]==str(year)}
        if len(slugs)!=1:fail(f"el archivo no ofrece el año {year}")
        ysoup=html(CATEGORY_URL.format(slug=slugs.pop()))
        months={}
        for a in ysoup.select("a[href]"):
            m=re.search(r"/jdownloads/viewcategory/(\d+-([a-z]+))(?:\?|$)",a["href"])
            if m and m[2] in MONTHS:months.setdefault(MONTHS.index(m[2])+1,set()).add(m[1])
        if any(len(v)!=1 for v in months.values()):fail(f"meses duplicados en el archivo de {year}")
        _CATS[year]={k:v.pop() for k,v in months.items()}
        time.sleep(PAUSE)
    return _CATS[year]

SLUG=re.compile(r"(\d+)-bocce-(extra)?(\d{1,5})-(\d{2})-(\d{2})-(\d{4})")
def parse_listing(soup,cat,year,month):
    """Boletines de la página de un mes: {url: (extra, número, día)}.

    El archivo a veces repite un boletín en el mes anterior (p. ej. el 6570
    del 2/12/2025 también está en noviembre): se admite y calendar() se queda
    con una sola copia."""
    found={}
    for a in soup.select("a[href]"):
        p=urlsplit(urljoin(BASE+"/",a["href"]))
        if not p.path.startswith(FINISH_PREFIX):continue
        rest=p.path[len(FINISH_PREFIX):]
        if not rest.startswith(cat+"/"):continue   # p. ej. actas de otras categorías
        slug=rest[len(cat)+1:]
        if "bocce" not in slug:continue
        m=SLUG.fullmatch(slug)
        if not m:fail("boletín con nombre desconocido en el archivo: "+slug)
        try:day=date(int(m[6]),int(m[5]),int(m[4]))
        except ValueError:fail("fecha imposible en el archivo: "+slug)
        url=f"{BASE}{p.path}?Itemid=534"
        found[url]=(bool(m[2]),int(m[3]),day)
    return found

def month_listing(year,month):
    cats=year_category(year)
    if month not in cats:return {}
    cat=cats[month]
    soup=html(CATEGORY_URL.format(slug=cat))
    if soup.select(".pagination a, a[href*='limitstart'], a[href*='start=']"):
        fail(f"el mes {month}/{year} tiene varias páginas; el lector solo conoce listados de una")
    time.sleep(PAUSE)
    return parse_listing(soup,cat,year,month)

def months_back(y,m,n):
    for _ in range(n):
        y,m=(y-1,12) if m==1 else (y,m-1)
    return y,m

def calendar(end,listing=None):
    """Boletines (url, extra, número, día) de la ventana end-29..end, comprobados."""
    listing=listing or month_listing
    start=end-timedelta(days=29)
    archive={};keys={}
    def add(found):
        for url,v in found.items():
            e,n,d=v;key=(e,n,d.year if e else 0)
            if key in keys:
                old=keys[key]
                if archive[old][2]!=d:fail(f"boletín {label(e,n)} con dos fechas en el archivo")
                if f"-{MONTHS[d.month-1]}/" in old:continue   # nos quedamos con la copia de su mes
                del archive[old]
            keys[key]=url;archive[url]=v
    y,m=start.year,start.month
    while (y,m)<=(end.year,end.month):
        add(listing(y,m));y,m=(y+1,1) if m==12 else (y,m+1)
    loaded=(start.year,start.month)
    def load_previous():
        nonlocal loaded
        loaded=months_back(*loaded,1)
        add(listing(*loaded))
    load_previous()     # boletín ordinario anterior a la ventana
    window=sorted(((u,v) for u,v in archive.items() if start<=v[2]<=end),key=lambda x:(x[1][2],x[1][0],x[1][1]))
    ordinary=[(v[2],v[1]) for _,v in window if not v[0]]
    extras=[(v[2],v[1]) for _,v in window if v[0]]
    if len(ordinary)<MIN_ORDINARY:fail(f"solo {len(ordinary)} boletines ordinarios en 30 días")
    if (end-ordinary[-1][0]).days>4:fail(f"el archivo no tiene boletines desde el {ordinary[-1][0]}")
    if any(b[1]!=a[1]+1 for a,b in zip(ordinary,ordinary[1:])):fail("huecos en la numeración de ordinarios")
    if not clm_common.numbering_ok(extras):fail("huecos en la numeración de extraordinarios")
    def exists(extra,n,year=None):
        return any(v[0]==extra and v[1]==n and v[2]<start and (year is None or v[2].year==year)
                   for v in archive.values())
    if not exists(False,ordinary[0][1]-1):fail(f"no aparece el ordinario {ordinary[0][1]-1}, anterior a la ventana")
    if extras and extras[0][1]>1:
        n,year=extras[0][1]-1,extras[0][0].year
        tries=0
        while not exists(True,n,year):
            if tries>=MAX_LOOKBACK_MONTHS or loaded<(year,1):
                fail(f"no aparece el extraordinario {n}/{year}, anterior a la ventana")
            load_previous();tries+=1
    return [(u,)+v for u,v in window]

# ---------------------------------------------------------------- PDF
DASHES=re.compile("[­‐-―−]")
# «681.-», «681 .-» y, alguna vez, «770-» (pero no «2021-2027» ni «2025-.»).
ENTRY=re.compile(r"(?m)^[ \t]*(\d{1,4})[ \t]*(?:\.[ \t]*-|-(?=[ \t]*(?:$|[A-Za-zÁÉÍÓÚÑ])))")
PAG=re.compile(r"P[áa]g[ \t]*\.?[ \t]*(?:\d{1,5}|x{2,5})",re.I)
RUNNING=re.compile(r"bocce\s+(?:extraordinario\s+)?n\s*[º°o]",re.I)
SECTIONS={"autoridades y personal","disposiciones generales","otras disposiciones y acuerdos",
          "administracion de justicia","anuncios","otras disposiciones","sumario"}
JUNK=re.compile(r"^(?:bocce.*|ordinario|extraordinari.*|ceuta|sumario|n\s*[º°o].*|d\.l\..*|ano\s+[ivxlc]+|"
                r"boletin.*|ciudad de ceuta|\d+|(?:lunes|martes|miercoles|jueves|viernes|sabado|domingo).*)$")

def norm(text):
    return DASHES.sub("-",text.replace("\xa0"," "))

def nice(heading):
    small={"de","del","la","las","el","los","en","y","e","a","para","por"}
    words=heading.lower().split()
    return " ".join(w if i and w in small else w[:1].upper()+w[1:] for i,w in enumerate(words))

SECTION_PREFIX=re.compile(r"^(?:autoridades y personal|disposiciones generales|otras disp\w*(?: y acuerdos?)?|"
                          r"administracion de justicia|anuncios|particulares)\b\s*")
CITY="ciudad autonoma de ceuta"

def headings(gap):
    """Rótulos de organismo (líneas en mayúsculas) entre dos edictos del sumario."""
    lines=[]
    for raw in gap.splitlines():
        line=" ".join(raw.split())
        letters=[c for c in line if c.isalpha()]
        if len(letters)<5 or line!=line.upper():continue
        f=fold(line)                    # misma longitud que line (solo quita tildes)
        if len(f)!=len(line):line=f
        rest=SECTION_PREFIX.sub("",f)
        if rest!=f:                     # rótulo de sección: el organismo va detrás
            lines=[]
            line=line[len(f)-len(rest):];f=rest
        if f.startswith("ciudad de ceuta "):f=f[16:];line=line[16:]
        f=f.rstrip(" .")
        if not f or JUNK.match(f):continue
        lines.append(line.strip())
    if len(lines)>1:lines=[x for x in lines if fold(x).rstrip(" .")!=CITY] or lines[:1]
    if not lines:return None
    text=nice(" ".join(lines))
    return ENTITY_DEFAULT if fold(text)==CITY else text

def sumario(pages):
    """Edictos del sumario: [(número, título, organismo)] y nº de páginas del sumario."""
    k=1
    while k<len(pages) and not RUNNING.search(pages[k][:300]) and PAG.search(pages[k]):k+=1
    text="\n".join(pages[:k])
    starts=list(ENTRY.finditer(text))
    if not starts:fail("sumario sin edictos")
    entity=headings(text[:starts[0].start()]) or ENTITY_DEFAULT
    edicts=[]
    for i,m in enumerate(starts):
        seg=text[m.end():starts[i+1].start() if i+1<len(starts) else len(text)]
        pag=None
        for pag in PAG.finditer(seg):break
        if not pag:fail(f"edicto {m[1]} del sumario sin página")
        title=" ".join(seg[:pag.start()].split()).lstrip("- ").strip()
        if not title:fail(f"edicto {m[1]} sin título")
        edicts.append((int(m[1]),title,entity))
        entity=headings(seg[pag.end():]) or entity
    return edicts,k

def header_ok(pages,extra,number,day):
    head=fold(" ".join(pages[:3]))
    when=f"{day.day} de {MONTHS[day.month-1]} de {day.year}"
    if when not in head:return False
    if extra:pat=rf"n\s*[º°o]\.?\s*0*{number}(?!\d)"
    else:
        s=str(number);pat=rf"n\s*[º°o]\.?\s*{s[:-3]}\.?{s[-3:]}(?!\d)" if len(s)>3 else rf"n\s*[º°o]\.?\s*{s}(?!\d)"
    return re.search(pat,head) is not None

def parse_pdf(data,extra,number,day):
    import pymupdf
    try:doc=pymupdf.open(stream=data,filetype="pdf")
    except Exception as ex:fail(f"PDF ilegible ({ex})")
    with doc:
        if doc.page_count<1:fail("PDF sin páginas")
        pages=[norm(p.get_text()) for p in doc]
    label=f"{'Extra ' if extra else ''}{number} ({day})"
    if not header_ok(pages,extra,number,day):fail(f"el PDF del boletín {label} no muestra esa fecha y número")
    edicts,k=sumario(pages)
    nums=[n for n,_,_ in edicts]
    if len(nums)!=len(set(nums)) or sorted(nums)!=list(range(min(nums),max(nums)+1)):
        fail(f"edictos del sumario de {label} no correlativos: {sorted(nums)}")
    body="\n".join(pages[k:])
    inbody={int(x) for x in ENTRY.findall(body)}
    missing=[n for n in nums if n not in inbody]
    # Boletín de un solo edicto cuyo cuerpo no repite el número (p. ej. Extra 42/2026).
    if missing==nums and len(nums)==1 and not inbody and len(body.split())>=20:missing=[]
    if missing:fail(f"edictos del sumario de {label} que no aparecen en el cuerpo: {missing}")
    return {"edicts":edicts,"pages":len(pages),"first":min(nums),"last":max(nums)}

def read_issue(item):
    url,extra,number,day=item
    data,ctype=fetch(url,MAX_PDF_BYTES)
    if not data.startswith(b"%PDF-") or "pdf" not in ctype.lower():fail("no es un PDF: "+url)
    out=parse_pdf(data,extra,number,day)
    out.update(url=url,extra=extra,number=number,day=day,sha256=hashlib.sha256(data).hexdigest(),bytes=len(data))
    time.sleep(PAUSE)
    return out

# ---------------------------------------------------------------- clasificación
NOT_NEW=("requiere documentacion","aspirante aprobad","aspirantes aprobad","se cesa","toma de posesion",
         "relacion de aprobados","aspirantes que han superado","lugar y hora","fecha de celebracion",
         "plantilla de puntuacion","plantilla de respuestas","plantilla provisional","plantilla definitiva",
         "se nombra","nombra a","nombra al","se anula","anulan","desierta","nulidad","propuesta de resolucion",
         "resolucion provisional","adjudicacion de plazas","solicitudes presentadas","concesion de plazas",
         "primer ciclo de educacion infantil","ayudas","programa fempa")
def kind(title):
    if any(x in fold(title) for x in NOT_NEW):return None
    return clm_common.employment(title)

def label(extra,number):
    return f"EXTRA{number:02d}" if extra else str(number)

def check_chain(issues):
    """La numeración de edictos de cada serie sigue de un boletín al siguiente."""
    for extra in (False,True):
        serie=[x for x in issues if x["extra"]==extra]
        for a,b in zip(serie,serie[1:]):
            ok=b["first"]==a["last"]+1 or (b["day"].year!=a["day"].year and b["first"]==1)
            if not ok:fail(f"edictos perdidos entre {label(extra,a['number'])} (hasta {a['last']}) "
                           f"y {label(extra,b['number'])} (desde {b['first']})")

def audit(today=None,listing=None,reader=None):
    end=today or date.today()
    items=calendar(end,listing)
    with ThreadPoolExecutor(WORKERS) as pool:
        issues=list(pool.map(reader or read_issue,items))
    check_chain(issues)
    issue_data=[];seen={};pages=0
    for x in issues:
        number=label(x["extra"],x["number"]);notices=[]
        for n,title,entity in x["edicts"]:
            t=kind(title)
            if not t:continue
            if n>9999:fail(f"edicto {n}: el identificador de la app admite hasta 4 cifras")
            # Los extraordinarios numeran sus edictos aparte: prefijo E para no chocar.
            nid=f"CE-{x['day'].year}-{'E' if x['extra'] else ''}{n:03d}"
            if nid in seen:fail(f"{nid} repetido en {seen[nid]} y {number}: los ordinarios y extraordinarios comparten número")
            seen[nid]=number
            notices.append({"id":nid,"province":PROVINCE,"title":title,"entity":entity,
                "date":x["day"].strftime("%d/%m/%Y"),"bulletin":number,"type":t,"url":x["url"],
                "publisherArticle":str(n)})
        issue_data.append({"day":x["day"],"number":number,"read":len(x["edicts"]),"notices":notices})
        pages+=x["pages"]
    try:
        feed=clm_common.publish_audit(SOURCE,PROVINCE,issue_data,today=end,min_issues=MIN_ORDINARY)
    except CeutaCoverageError:raise
    except ProvincialCoverageError as ex:
        fail(str(ex).replace("Castilla-La Mancha: ",""))
    meaning="edictos del sumario de cada BOCCE (ordinarios y extraordinarios), todos localizados en el PDF completo"
    feed["coverage"].update(announcementsReadMeaning=meaning,originalFullPdfIssues=len(issues),pdfPagesRead=pages)
    feed["historyCoverage"].update(
        regularBulletins=[label(False,x["number"]) for x in issues if not x["extra"]],
        extraordinaryBulletins=[label(True,x["number"]) for x in issues if x["extra"]],
        pdfEvidence=[{"number":label(x["extra"],x["number"]),"date":x["day"].isoformat(),"url":x["url"],
                      "sha256":x["sha256"],"bytes":x["bytes"],"pages":x["pages"],
                      "edicts":[x["first"],x["last"]]} for x in issues])
    return feed

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output",default="out/ceuta_bocce.json")
    ap.add_argument("--today",type=date.fromisoformat,help="solo para pruebas")
    a=ap.parse_args()
    clm_common.write_output(a.output,audit(a.today))

if __name__=="__main__":
    main()
