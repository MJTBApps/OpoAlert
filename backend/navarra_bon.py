#!/usr/bin/env python3
"""BON Navarra: lector diario de los últimos 30 días del Boletín Oficial de Navarra.

Calendario: páginas mensuales oficiales del índice de boletines
(https://bon.navarra.es/es/boletines/-/boletinmes/AAAA/M), que listan todos
los boletines del mes, ordinarios y extraordinarios, con una única numeración
anual que vuelve a 1 en enero. De cada boletín de la ventana se lee el sumario
(/es/boletin/-/sumario/AAAA/N), se comprueba su número y fecha, y se cuentan
sus anuncios (/es/anuncio/-/texto/AAAA/N/I, índices 0..k-1 seguidos). Las
candidatas se comprueban en su texto original.

El portal no responde desde GitHub Actions: se ejecuta en un ejecutor propio
con conexión española. Nunca se publican datos parciales: ante cualquier
incoherencia el lector falla.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urlsplit
import argparse,html,re,threading,time
import requests
from clm_common import employment,publish_audit,write_output,numbering_ok
from provincial_common import ProvincialCoverageError,fold

SOURCE="https://bon.navarra.es/es/indice-boletines"
PROVINCE="Navarra"
HOST="bon.navarra.es"
BASE="https://bon.navarra.es"
MONTHS={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,
        "agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
ID_RE=re.compile(r"NA-\d{4}-\d{3}-\d{1,4}")   # Province.kt NAVARRA_BON
THREADS=3
TLS=threading.local()

def invalid(message):
    raise ProvincialCoverageError("Navarra BON: "+str(message))

def session():
    if not hasattr(TLS,"client"):
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert official bulletin audit)",
                          "Accept":"text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
                          "Accept-Language":"es-ES,es;q=0.9"})
        TLS.client=s
    return TLS.client

def fetch(url,attempts=3):
    """HTML oficial de bon.navarra.es; reintentos moderados y nada fuera del host."""
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname!=HOST or u.port or u.username or u.query or u.fragment:
        invalid("URL fuera del portal oficial: "+url[:160])
    error=None
    for i in range(attempts):
        try:
            r=session().get(url,timeout=(12,45),allow_redirects=True)
            final=urlsplit(r.url)
            if r.status_code==200 and final.hostname==HOST and final.path==u.path:
                if not r.content or len(r.content)>6_000_000:invalid("página vacía o desmesurada: "+url)
                r.encoding="utf-8"
                return r.text
            error=f"HTTP {r.status_code} ({r.url[:120]})"
            if r.status_code in (403,404,410):break
        except requests.RequestException as ex:
            error=str(ex)[:160]
        if i<attempts-1:time.sleep(2*(i+1))
    invalid(f"sin acceso a {url}: {error}")

def text(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>"," ",fragment)).split())

def es_date(raw):
    m=re.fullmatch(r"(\d{1,2}) de ([a-záéíóú]+) de (\d{4})",raw.strip().casefold())
    if not m or m[2] not in MONTHS:return None
    try:return date(int(m[3]),MONTHS[m[2]],int(m[1]))
    except ValueError:return None

def months(start,end):
    out=[];y,m=start.year,start.month
    while (y,m)<=(end.year,end.month):
        out.append((y,m));y,m=(y+1,1) if m==12 else (y,m+1)
    return out

def month_url(year,month):
    return f"{BASE}/es/boletines/-/boletinmes/{year}/{month}"

# Los atributos (title) de los extraordinarios llevan "<br/>": se saltan entre comillas.
ISSUE_LINK=re.compile(r'<a\s+href="https://bon\.navarra\.es/es/boletin/-/sumario/(\d{4})/(\d{1,4})"(?:\s+[\w-]+="[^"]*")*\s*>(.*?)</a>',re.S)

def parse_month(page,year,month):
    """[(fecha, número, extraordinario)] de la página mensual oficial; falla si es incoherente."""
    if "lfr-pagination" in page or "_cur=" in page:
        invalid(f"índice de {month}/{year} paginado: no se garantiza que esté completo")
    found={}
    for y,n,label in ISSUE_LINK.findall(page):
        t=text(label)
        m=re.fullmatch(r"Nº\s*(\d{1,4})\s*\|\s*(\d{1,2} de [A-Za-záéíóú]+ de \d{4})(\s+EXTRAORDINARIO)?",t,re.I)
        if not m:invalid(f"rótulo de boletín no reconocido en {month}/{year}: {t[:80]}")
        day=es_date(m[2])
        if (day is None or int(m[1])!=int(n) or int(y)!=year or day.year!=year or day.month!=month):
            invalid(f"boletín {n} con número o fecha contradictorios en {month}/{year}: {t[:80]}")
        entry=(day,int(n),bool(m[3]))
        if int(n) in found and found[int(n)]!=entry:invalid(f"boletín {n} repetido con datos distintos")
        found[int(n)]=entry
    nums=sorted(found)
    if len(set(re.findall(r'href="https://bon\.navarra\.es/es/boletin/-/sumario/\d{4}/(\d{1,4})"',page)))!=len(nums):
        invalid(f"índice de {month}/{year}: hay boletines que no se han podido leer")
    if nums and nums!=list(range(nums[0],nums[-1]+1)):
        invalid(f"faltan números en el índice de {month}/{year}: {nums}")
    return [found[n] for n in nums]

def calendar(end):
    start=end-timedelta(days=29)
    issues=[]
    for y,m in months(start,end):
        entries=parse_month(fetch(month_url(y,m)),y,m)
        if not entries and (y,m)!=(end.year,end.month):invalid(f"índice de {m}/{y} vacío")
        issues+= [e for e in entries if start<=e[0]<=end]
    issues.sort(key=lambda e:(e[0],e[1]))
    if not issues:invalid("ningún boletín en la ventana")
    if not numbering_ok([(d,n) for d,n,_ in issues]):
        invalid("numeración no consecutiva: "+", ".join(str(n) for _,n,_ in issues))
    if (issues[0][0]-start).days>3 or (end-issues[-1][0]).days>3:
        invalid(f"faltan boletines al principio o al final de {start}–{end}")
    return start,issues

HEAD=re.compile(r'<p\s+id="numero_boletin"[^>]*>(.*?)</p>',re.S)
TOKENS=re.compile(r'<p\s+class="hd\s+r-hn\d\s+(b-ambito|b-seccion|b-subseccion|b-denominacion)"[^>]*>(.*?)</p>'
                  # El title puede llevar comillas sin escapar: la etiqueta acaba en el último ">" de su línea.
                  r'|<a\s+href="(https://bon\.navarra\.es/es/anuncio/-/texto/(\d{4})/(\d{1,4})/(\d{1,5}))"[^\n]*>[ \t]*\r?\n(.*?)</a>',re.S)
ANNOUNCEMENT_HREF=re.compile(r'href="https://bon\.navarra\.es/es/anuncio/-/texto/')

def parse_summary(page,year,number,day):
    """Anuncios del sumario: [(índice, título, organismo, sección, url)]."""
    head=HEAD.search(page)
    m=re.fullmatch(r"BOLET[IÍ]N Nº\s*(\d{1,4})\s*[-–]\s*(\d{1,2} de [A-Za-záéíóú]+ de \d{4}).*",
                   text(head.group(1)) if head else "",re.I)
    if not m or int(m[1])!=number or es_date(m[2])!=day:
        invalid(f"el sumario {number}/{year} no corresponde al boletín del {day}")
    ambito=seccion=denominacion="";out=[]
    for kind,label,url,y,n,idx,inner in TOKENS.findall(page):
        if kind:
            t=re.sub(r"^\d+(?:\.\d+)*\.\s*","",text(label))
            if kind=="b-ambito":ambito,seccion,denominacion=t,"",""
            elif kind=="b-seccion":seccion,denominacion=t,""
            elif kind=="b-subseccion":seccion=t;denominacion=""
            else:denominacion=t
            continue
        if int(y)!=year or int(n)!=number:invalid(f"el sumario {number}/{year} enlaza un anuncio ajeno: {url}")
        title=text(inner)
        entity=denominacion or ambito
        if not title or not entity:invalid(f"anuncio {url} sin título u organismo")
        out.append((int(idx),title,entity,seccion,url))
    if not out:invalid(f"el sumario {number}/{year} no tiene anuncios")
    if len(ANNOUNCEMENT_HREF.findall(page))!=len(out):
        invalid(f"sumario {number}/{year}: hay enlaces a anuncios que no se han podido leer")
    if [x[0] for x in out]!=list(range(len(out))):
        invalid(f"anuncios del sumario {number}/{year} no consecutivos o repetidos")
    return out

SKIP_SECTIONS=("subvenciones","ceses, nombramientos","disposiciones generales")
REJECT=("recurso de alzada","recursos de alzada","se nombra","nombra ","nombrad","toma de posesion",
        "se aprueba la lista","se aprueban las listas","aprobacion de la lista","relacion de personas aprobadas",
        "aspirantes aprobad","calificaciones","propuesta de","excedencia","desiert","rectifica","corrige",
        "correccion de error","modificacion de la convocatoria","modificacion de las bases","ayudas",
        "subvencion","fecha de","lugar de celebracion","junta general","asamblea","sentencia","jubilacion",
        "concurso de traslado","servicios minimos","huelga","se modifica","se modifican",
        "anulacion","se anula","deja sin efecto","encomienda")

def kind(title,section):
    s=fold(section);t=" ".join(fold(title).split())
    if any(x in s for x in SKIP_SECTIONS) or any(x in t for x in REJECT):return None
    # En Navarra las bolsas se llaman "relaciones/listas de aspirantes a la contratación temporal".
    if (re.search(r"\b(?:relacion|relaciones|lista|listas) de aspirantes\b",t)
        and any(x in t for x in ("constitucion","contratacion temporal","pruebas selectivas"))
        and any(x in t for x in ("convocatoria","constitucion","bases"))
        and not any(x in t for x in ("admitid","excluid","definitiva","provisional","se aprueba"))):
        return "Bolsa de trabajo"
    return employment(title)

def check_original(note):
    """El texto original del anuncio debe estar publicado y corresponder al título."""
    page=fold(text(fetch(note["url"])))
    title=" ".join(fold(note["title"]).split())
    if len(page)<300 or title[:28] not in page:
        invalid(f"el texto original no corresponde al anuncio {note['id']} ({note['url']})")
    time.sleep(0.3)

def read_issue(entry):
    day,number,extra=entry
    url=f"{BASE}/es/boletin/-/sumario/{day.year}/{number}"
    items=parse_summary(fetch(url),day.year,number,day)
    time.sleep(0.3)
    notices=[]
    for idx,title,entity,section,link in items:
        role=kind(title,section)
        if not role:continue
        nid=f"NA-{day.year}-{number:03d}-{idx}"
        if not ID_RE.fullmatch(nid):invalid("identificador fuera del patrón de la app: "+nid)
        notices.append({"id":nid,"province":PROVINCE,"title":title[:2800],"entity":entity[:500],
            "date":day.strftime("%d/%m/%Y"),"bulletin":str(number),"type":role,"url":link})
    return {"day":day,"number":str(number),"read":len(items),"notices":notices,"extra":extra}

def audit(today=None,verify_originals=True):
    end=today or date.today()
    start,entries=calendar(end)
    with ThreadPoolExecutor(THREADS) as pool:
        issues=list(pool.map(read_issue,entries))
    candidates=[n for x in issues for n in x["notices"]]
    if verify_originals:
        with ThreadPoolExecutor(THREADS) as pool:list(pool.map(check_original,candidates))
    for i,x in enumerate(issues,1):
        print(f"NAVARRA BON {x['day']} n.º {x['number']}{' (extraordinario)' if x['extra'] else ''}: "
              f"{x['read']} anuncios, {len(x['notices'])} candidatas (edición {i}/{len(issues)})",flush=True)
    data=[{k:v for k,v in x.items() if k!="extra"} for x in issues]
    return publish_audit(SOURCE,PROVINCE,data,today=end)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    write_output(args.output,audit())
