#!/usr/bin/env python3
"""Lector diario del BOP de Jaén (bop.dipujaen.es): últimos 30 días, sin huecos.

Fuente oficial: https://bop.dipujaen.es/
  * /bop/DD-MM-AAAA: sumario HTML del boletín de ese día. Los días sin boletín
    devuelven 200 con «No hay ningún boletín publicado» (div#noBoletin).
  * Cada edicto va en <article><p class='edicto'> dentro de div#sumarioBoletin,
    con sección (p.seccion), organismo (p.subseccion) y departamento
    (p.departamento), y un único enlace a su PDF oficial:
    /descargarws.dip?fechaBoletin=...&numeroEdicto=N&boletinSuplemento=0
      &ejercicioBop=AAAA&tipo=bop&anioExpedienteEdicto=AAAA
  * El sumario en PDF (tipo=bopSumario) enumera los mismos edictos con su
    código BOP-AAAA-N: se usa como comprobación cruzada de que el HTML trae
    todos los edictos del boletín.

Identificador: JA-<anioExpedienteEdicto>-<numeroEdicto>, igual que el nombre
oficial del PDF (BOP-AAAA-N). En enero aún salen edictos con expediente del año
anterior (JA-2025-6244 en el BOP 1/2026), por eso el año es el del expediente
y no el del boletín.

Comprobaciones (si algo falla, ProvincialCoverageError y no se escribe feed):
  * se piden los 30 días de la ventana que acaba hoy; cada boletín muestra la
    fecha pedida y un número; la numeración es consecutiva (vuelve a 1 en
    enero, clm_common.numbering_ok) y enlaza con el boletín anterior a la
    ventana;
  * el sumario PDF de cada boletín lista exactamente los mismos edictos que
    el HTML, sin duplicados en toda la ventana;
  * cada candidata enlaza a su PDF oficial, que se descarga y comprueba
    (application/pdf, %PDF-, nombre BOP-AAAA-N.pdf).
Los suplementos (boletinSuplemento distinto de 0) no se han visto en el
archivo de 2025-2026: si aparece uno, el lector se detiene en vez de adivinar.

Uso: python backend/jaen_bop.py --output out/jaen_bop.json
"""
from __future__ import annotations
import argparse,re,sys,threading,time,unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import parse_qs,urljoin,urlsplit

import requests
from bs4 import BeautifulSoup

sys.path.insert(0,str(Path(__file__).resolve().parent))
import clm_common
from provincial_common import ProvincialCoverageError

SOURCE="https://bop.dipujaen.es/"
PROVINCE="Jaén"
CODE="JA"
HOST="bop.dipujaen.es"
PDF_PATH="/descargarws.dip"
WORKERS=3
PAUSE=0.3
MIN_INTERVAL=0.6         # segundos entre peticiones (todas las hebras): el portal responde 429 si se le apura
PREVIOUS_LOOKBACK=10     # días hacia atrás para encontrar el boletín anterior a la ventana
MONTHS=("enero","febrero","marzo","abril","mayo","junio","julio","agosto",
        "septiembre","octubre","noviembre","diciembre")
WEEKDAYS=("lunes","martes","miercoles","jueves","viernes","sabado","domingo")

class JaenCoverageError(ProvincialCoverageError):pass

def fail(message):
    raise JaenCoverageError("Jaén BOP: "+str(message))

def fold(text):
    t=unicodedata.normalize("NFD",str(text).casefold())
    return " ".join("".join(c for c in t if unicodedata.category(c)!="Mn").split())

def clean(text):
    return " ".join(str(text).replace("\xa0"," ").split())

# ---------------------------------------------------------------- HTTP
_LOCAL=threading.local()
def session():
    if not hasattr(_LOCAL,"s"):
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 OpoAlert",
                          "Accept-Language":"es-ES,es;q=0.9"})
        _LOCAL.s=s
    return _LOCAL.s

def official(url):
    u=urlsplit(url)
    return (u.scheme=="https" and u.hostname==HOST and u.port in (None,443)
            and not u.username and not u.password and not u.fragment)

ROBOT=("captcha","are you a robot","eres un robot","verificación de seguridad","cf-challenge","access denied")
_THROTTLE=threading.Lock();_LAST=[0.0]
def throttle():
    with _THROTTLE:
        wait=_LAST[0]+MIN_INTERVAL-time.monotonic()
        if wait>0:time.sleep(wait)
        _LAST[0]=time.monotonic()

def fetch(url,limit=6_000_000,retries=5,head_only=False):
    """(bytes, cabeceras). Con head_only se leen solo los primeros bytes."""
    if not official(url):fail("URL fuera del portal oficial: "+url[:160])
    error=None
    for i in range(retries):
        delay=2.0*(i+1)
        try:
            throttle()
            with session().get(url,timeout=(12,45),stream=True,allow_redirects=True) as r:
                if not official(r.url):fail("redirección fuera del portal oficial: "+r.url[:160])
                if r.status_code in (429,503):
                    ra=r.headers.get("Retry-After","")
                    delay=min(60.0,float(ra)) if ra.isdigit() else 5.0*2**i
                    raise requests.HTTPError(f"HTTP {r.status_code}")
                if r.status_code!=200:raise requests.HTTPError(f"HTTP {r.status_code}")
                body=bytearray()
                for chunk in r.iter_content(65536 if not head_only else 1024):
                    body+=chunk
                    if head_only and len(body)>=1024:break
                    if len(body)>limit:fail(f"documento mayor de {limit} bytes: {url}")
                if not body:raise requests.RequestException("respuesta vacía")
                return bytes(body),r.headers
        except requests.RequestException as ex:
            error=ex
            if i<retries-1:time.sleep(delay)
    fail(f"sin acceso a {url}: {error}")

def decode(raw):
    """El portal sirve ISO-8859-1 (en la práctica, Windows-1252)."""
    try:return raw.decode("utf-8")
    except UnicodeDecodeError:pass
    try:return raw.decode("cp1252")
    except UnicodeDecodeError:return raw.decode("latin-1")

def day_url(day):
    return f"{SOURCE}bop/{day:%d-%m-%Y}"

# ---------------------------------------------------------------- sumario HTML
HEADER=re.compile(r"bolet[ií]n\s*n\s*[º°o]\s*:?\s*(\d{1,4})\s+([a-záéíóú]+),\s*(\d{1,2})\s+de\s+([a-z]+)\s+de\s+(\d{4})",re.I)

def parse_day(html,day):
    """None si ese día no hay boletín; si no, dict con número y edictos."""
    low=fold(html[:200000])
    if any(w in low for w in ROBOT):fail(f"el portal pide una verificación anti-robots ({day}); no se elude")
    soup=BeautifulSoup(html,"html.parser")
    heads=soup.select("p.cabeceraSumario")
    root=soup.select("#sumarioBoletin")
    if soup.select_one("#noBoletin"):
        if heads or root or soup.select("article p.edicto"):fail(f"{day}: página sin boletín pero con edictos")
        text=fold(soup.select_one("#noBoletin").get_text(" "))
        if "no hay ningun boletin" not in text or f"{day:%d-%m-%Y}" not in text:
            fail(f"{day}: aviso de día sin boletín inesperado")
        return None
    if len(heads)!=1 or len(root)!=1:
        fail(f"{day}: se esperaba una cabecera y un sumario y hay {len(heads)} y {len(root)} (¿suplemento?)")
    m=HEADER.search(clean(heads[0].get_text(" ")))
    if not m:fail(f"{day}: cabecera del boletín ilegible")
    number=int(m[1])
    month=fold(m[4])
    if month not in MONTHS or fold(m[2]) not in WEEKDAYS:fail(f"{day}: fecha de cabecera ilegible")
    shown=date(int(m[5]),MONTHS.index(month)+1,int(m[3]))
    if shown!=day:fail(f"se pidió el {day} y el portal muestra el boletín del {shown}")
    if WEEKDAYS[shown.weekday()]!=fold(m[2]):fail(f"{day}: día de la semana incoherente")
    if not 1<=number<=400:fail(f"{day}: número de boletín imposible {number}")
    # Enlaces del boletín completo y del sumario PDF: mismo número y fecha.
    sumario_pdf=None
    for a in soup.select("a[href*='descargarws.dip']"):
        u=urljoin(SOURCE,a["href"]);q=parse_qs(urlsplit(u).query)
        tipo=q.get("tipo",[""])[0]
        if tipo not in ("bopCompleto","bopSumario"):continue
        if (q.get("numeroBoletin")!=[str(number)] or q.get("fechaBoletin")!=[day.isoformat()]
            or q.get("ejercicioBop")!=[str(day.year)]):
            fail(f"{day}: enlace {tipo} de otro boletín")
        if q.get("boletinSuplemento")!=["0"]:fail(f"{day}: suplemento no previsto en el lector")
        if tipo=="bopSumario":sumario_pdf=u
    if not sumario_pdf or not official(sumario_pdf):fail(f"{day}: falta el sumario PDF oficial")
    edicts=[];section=organism=department=None
    for el in root[0].find_all(["p","article"]):
        cls=el.get("class") or []
        if el.name=="article":
            texts=el.select("p.edicto")
            links=[a for a in el.select("a[href]") if "tipo=bop&" in a["href"]]
            if len(texts)!=1 or len(links)!=1:fail(f"{day}: edicto sin título o sin PDF único")
            title=clean(texts[0].get_text(" "))
            url=urljoin(SOURCE,links[0]["href"].strip())
            p=urlsplit(url);q=parse_qs(p.query)
            if not official(url) or p.path!=PDF_PATH:fail(f"{day}: PDF fuera del portal: {url[:150]}")
            try:
                nedict=int(q["numeroEdicto"][0]);year=int(q["anioExpedienteEdicto"][0])
            except (KeyError,ValueError):fail(f"{day}: enlace de edicto sin número o año")
            if (q.get("fechaBoletin")!=[day.isoformat()] or q.get("ejercicioBop")!=[str(day.year)]
                or q.get("tipo")!=["bop"]):fail(f"{day}: edicto {nedict} enlazado a otro boletín")
            if q.get("boletinSuplemento")!=["0"]:fail(f"{day}: suplemento no previsto en el lector")
            if not (day.year-2<=year<=day.year and 1<=nedict<=999999):fail(f"{day}: edicto {year}/{nedict} imposible")
            entity=organism or section
            if not title or not entity:fail(f"{day}: edicto {year}/{nedict} sin título u organismo")
            if department:entity=f"{entity}. {department}"
            edicts.append({"year":year,"number":nedict,"title":title,"entity":entity,"url":url,"section":section})
        elif "seccion" in cls:
            section=clean(el.get_text(" "));organism=department=None
        elif "subseccion" in cls:
            organism=clean(el.get_text(" "));department=None
        elif "departamento" in cls:
            department=clean(el.get_text(" ")).rstrip(".")
    if not edicts:fail(f"boletín {number} ({day}) sin edictos")
    keys=[(e["year"],e["number"]) for e in edicts]
    if len(set(keys))!=len(keys):fail(f"boletín {number} ({day}) con edictos repetidos")
    return {"day":day,"number":number,"edicts":edicts,"sumario":sumario_pdf}

# ---------------------------------------------------------------- sumario PDF
CODE_RE=re.compile(r"BOP-(\d{4})-(\d{1,6})(?!\d)")
def sumario_codes(data,day,number):
    import pymupdf
    try:doc=pymupdf.open(stream=data,filetype="pdf")
    except Exception as ex:fail(f"sumario PDF ilegible ({ex})")
    with doc:text="\n".join(p.get_text() for p in doc)
    head=fold(text[:3000])
    if (re.search(rf"numero\s+{number}(?!\d)",head) is None
        or re.search(rf"(?<!\d)0?{day.day}\s+de\s+{MONTHS[day.month-1]}\s+de\s+{day.year}",head) is None):
        fail(f"el sumario PDF no corresponde al boletín {number} del {day}")
    return [(int(a),int(b)) for a,b in CODE_RE.findall(text)]

def read_day(day):
    raw,_=fetch(day_url(day))
    time.sleep(PAUSE)
    issue=parse_day(decode(raw),day)
    if issue is None:return None
    data,headers=fetch(issue["sumario"],limit=20_000_000)
    if not data.startswith(b"%PDF-") or "pdf" not in headers.get("Content-Type","").lower():
        fail(f"el sumario del {day} no es un PDF")
    codes=sumario_codes(data,day,issue["number"])
    html_codes=sorted((e["year"],e["number"]) for e in issue["edicts"])
    if sorted(codes)!=html_codes:
        only_pdf=sorted(set(codes)-set(html_codes));only_html=sorted(set(html_codes)-set(codes))
        fail(f"boletín {issue['number']} ({day}): el sumario PDF y la web no coinciden "
             f"(solo PDF {only_pdf[:5]}, solo web {only_html[:5]}, {len(codes)} frente a {len(html_codes)})")
    time.sleep(PAUSE)
    return issue

# ---------------------------------------------------------------- clasificación
NOT_EMPLOYMENT=("mercadillo","mercado","venta ambulante","kiosco","quiosco","caseta","feria","nicho",
    "vivienda","taxi","parada","huerto","local comercial","explotacion","fecha de examen","fecha del examen",
    "calificacion","aprobados","aprobadas","toma de posesion","se nombra","nombra a","nombra al","cese",
    "desierta","propuesta de resolucion","plantilla de respuestas","plantilla provisional","plantilla definitiva",
    "baremacion","valoracion de meritos","modificacion de la oferta","presupuesto","bases de ejecucion",
    "adjudicacion de puesto","exclusion de integrantes","reglamento","ordenanza")
def kind(title):
    t=fold(title)
    if any(w in t for w in NOT_EMPLOYMENT):return None
    return clm_common.employment(title)

def check_pdf(url,year,nedict):
    data,headers=fetch(url,head_only=True)
    if not data.startswith(b"%PDF-") or "pdf" not in headers.get("Content-Type","").lower():
        fail("el enlace oficial no devuelve un PDF: "+url)
    disp=headers.get("Content-Disposition","")
    m=re.search(r'filename="?([^";]+)',disp)
    if m and m[1].strip()!=f"BOP-{year}-{nedict}.pdf":
        fail(f"el PDF de {year}/{nedict} es otro documento ({m[1]})")
    time.sleep(PAUSE)

# ---------------------------------------------------------------- auditoría
def previous_issue(start,reader):
    for k in range(1,PREVIOUS_LOOKBACK+1):
        issue=reader(start-timedelta(days=k))
        if issue:return issue
    fail(f"no hay boletín en los {PREVIOUS_LOOKBACK} días anteriores a la ventana")

def audit(today=None,reader=None,pdf_check=None):
    end=today or date.today()
    start=end-timedelta(days=29)
    reader=reader or read_day;pdf_check=pdf_check or check_pdf
    days=[start+timedelta(days=i) for i in range(30)]
    with ThreadPoolExecutor(WORKERS) as pool:
        found=list(pool.map(reader,days))
    issues=[x for x in found if x]
    if not issues:fail("no hay boletines en la ventana")
    prev=previous_issue(start,reader)
    chain=[(prev["day"],prev["number"])]+[(x["day"],x["number"]) for x in issues]
    if not clm_common.numbering_ok(chain):
        fail(f"numeración de boletines con huecos: {[n for _,n in chain]}")
    seen={};issue_data=[];candidates=[]
    for x in issues:
        notices=[]
        for e in x["edicts"]:
            key=(e["year"],e["number"])
            if key in seen:fail(f"edicto {key} repetido en los boletines {seen[key]} y {x['number']}")
            seen[key]=x["number"]
            t=kind(e["title"])
            if not t:continue
            nid=f"{CODE}-{e['year']}-{e['number']}"
            row=clm_common.record(CODE,PROVINCE,nid,e["title"],e["entity"],x["day"],x["number"],e["url"])
            row["type"]=t
            notices.append(row);candidates.append(row)
        issue_data.append({"day":x["day"],"number":x["number"],"read":len(x["edicts"]),"notices":notices})
        print("JAÉN",x["day"],"boletín",x["number"],"edictos",len(x["edicts"]),"candidatas",len(notices),flush=True)
    with ThreadPoolExecutor(WORKERS) as pool:
        list(pool.map(lambda n:pdf_check(n["url"],*map(int,n["id"].split("-")[1:])),candidates))
    try:
        feed=clm_common.publish_audit(SOURCE,PROVINCE,issue_data,today=end)
    except JaenCoverageError:raise
    except ProvincialCoverageError as ex:
        fail(str(ex).replace("Castilla-La Mancha: ",""))
    feed["coverage"].update(
        announcementsReadMeaning="edictos del sumario de cada BOP (web y sumario PDF coinciden)",
        pdfLinksVerified=len(candidates))
    feed["historyCoverage"].update(
        daysRequested=len(days),previousBulletin={"number":str(prev["number"]),"date":prev["day"].isoformat()})
    return feed

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output",required=True)
    ap.add_argument("--today",type=date.fromisoformat,help="solo para pruebas")
    a=ap.parse_args()
    clm_common.write_output(a.output,audit(a.today))

if __name__=="__main__":
    main()
