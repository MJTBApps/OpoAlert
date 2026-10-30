#!/usr/bin/env python3
"""BOP Valladolid: lector diario de los últimos 30 días del Boletín Oficial de la Provincia.

Portal oficial (Liferay) https://bop.sede.diputaciondevalladolid.es/:
- Calendario: /o/BOP-Calendario/CalendarioControl?month=M&year=AAAA devuelve en
  JSON los días con boletín de ese mes.
- Edición: /ultimobop?...&_BOPVisualizaBoletin_WAR_BOPVisualizaBoletin_fecha=AAAA-MM-DD
  muestra el boletín de esa fecha completo, sin paginación: cabecera
  «BOLETIN Nº AAAA/N», fecha en letra y un <li class="un_anuncio"> por anuncio con
  el organismo (p.bop_tit_articulo), el título (p.bop_res_articulo) y su PDF
  /boletines/AAAA/<mes>/DD/BOPVA-A-AAAA-NNNNN.pdf.

Comprobaciones (si alguna falla no se escribe nada): cada día del calendario
tiene su boletín con esa fecha; números de boletín seguidos (vuelven a 1 en
enero); los números de anuncio de toda la ventana también son seguidos y sin
repetir (el BOPVA numera los anuncios de forma correlativa en el año), lo que
garantiza que no falta ningún anuncio ni ninguna edición; y cada candidata
enlaza un PDF oficial que responde como PDF.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from pathlib import Path
from urllib.parse import urlsplit,urlencode
import argparse,json,re,threading,time
import requests
from bs4 import BeautifulSoup
from clm_common import employment,publish_audit,write_output,numbering_ok
from provincial_common import ProvincialCoverageError,fold

SOURCE="https://bop.sede.diputaciondevalladolid.es/"   # Province.kt VALLADOLID_BOP
PROVINCE="Valladolid"
HOST="bop.sede.diputaciondevalladolid.es"
BASE="https://"+HOST
PDF_PREFIX="/boletines/"
ID_RE=re.compile(r"VD-\d{4}-\d{1,6}")
MONTHS=("enero","febrero","marzo","abril","mayo","junio","julio","agosto",
        "septiembre","octubre","noviembre","diciembre")
PORTLET="BOPVisualizaBoletin_WAR_BOPVisualizaBoletin"
THREADS=3
TLS=threading.local()

def invalid(message):
    raise ProvincialCoverageError("Valladolid BOP: "+str(message))

def session():
    if not hasattr(TLS,"client"):
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/129.0 Safari/537.36 (OpoAlert)",
                          "Accept-Language":"es-ES,es;q=0.9"})
        TLS.client=s
    return TLS.client

def fetch(url,attempts=3,pdf=False):
    """Respuesta oficial de bop.sede.diputaciondevalladolid.es; nada fuera del host."""
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname!=HOST or u.port or u.username or u.fragment:
        invalid("URL fuera del portal oficial: "+url[:160])
    error=None
    for i in range(attempts):
        try:
            r=session().get(url,timeout=(12,45),allow_redirects=True,stream=pdf)
            final=urlsplit(r.url)
            if r.status_code==200 and final.hostname==HOST and final.path==u.path:
                if pdf:
                    head=next(r.iter_content(chunk_size=16),b"");r.close()
                    if not head.startswith(b"%PDF-"):invalid("el enlace oficial no es un PDF: "+url)
                    return head
                if not r.content or len(r.content)>8_000_000:invalid("página vacía o desmesurada: "+url)
                r.encoding="utf-8"
                low=r.text[:20000].lower()
                if "captcha" in low or "are you a robot" in low:
                    invalid("el portal pide una verificación anti-robots: no se elude")
                return r.text
            error=f"HTTP {r.status_code} ({r.url[:120]})";r.close()
            if r.status_code in (403,404,410):break
        except requests.RequestException as ex:
            error=str(ex)[:160]
        if i<attempts-1:time.sleep(1.5*(i+1))
    invalid(f"sin acceso a {url}: {error}")

def months(start,end):
    out=[];y,m=start.year,start.month
    while (y,m)<=(end.year,end.month):
        out.append((y,m));y,m=(y+1,1) if m==12 else (y,m+1)
    return out

def calendar_url(year,month):
    return f"{BASE}/o/BOP-Calendario/CalendarioControl?month={month}&year={year}"

def issue_url(day):
    q={"p_p_id":PORTLET,"p_p_lifecycle":"0","p_p_state":"normal","p_p_mode":"view",
       "p_p_col_id":"column-1","p_p_col_count":"3",f"_{PORTLET}_fecha":day.isoformat()}
    return f"{BASE}/ultimobop?"+urlencode(q)

def parse_calendar(raw,year,month):
    try:data=json.loads(raw)
    except ValueError:invalid(f"calendario {month}/{year} ilegible")
    if not isinstance(data,list):invalid(f"calendario {month}/{year} con formato inesperado")
    out=set()
    for x in data:
        try:d=date.fromisoformat(str(x))
        except ValueError:invalid(f"fecha ilegible en el calendario {month}/{year}: {x!r}")
        if (d.year,d.month)!=(year,month):invalid(f"el calendario {month}/{year} trae {d}")
        out.add(d)
    if len(out)!=len(data):invalid(f"calendario {month}/{year} con días repetidos")
    return out

def calendar(end):
    start=end-timedelta(days=29)
    days=set()
    for y,m in months(start,end):
        found=parse_calendar(fetch(calendar_url(y,m)),y,m)
        if not found and (y,m)!=(end.year,end.month):invalid(f"calendario de {m}/{y} vacío")
        days|={d for d in found if start<=d<=end}
    days=sorted(days)
    if not days:invalid("ningún boletín en la ventana")
    if (days[0]-start).days>3 or (end-days[-1]).days>3:
        invalid(f"faltan boletines al principio o al final de {start}–{end}")
    return start,days

def clean(node):
    return " ".join(node.get_text(" ",strip=True).split()) if node else ""

PDF_RE=re.compile(r"/boletines/(\d{4})/([a-z]+)/(\d{2})/BOPVA-A-(\d{4})-(\d{1,6})\.pdf")

def parse_issue(page,day):
    """(número, [(n.º anuncio, organismo, título, url)]) de la página de una edición."""
    soup=BeautifulSoup(page,"html.parser")
    head=clean(soup.select_one("#bop_sumario_tit"))
    m=re.fullmatch(r"BOLET[IÍ]N N[ºo°]\s*(\d{4})/(\d{1,4})",head,re.I)
    if not m:invalid(f"el boletín del {day} no aparece (cabecera {head[:60]!r})")
    if int(m[1])!=day.year:invalid(f"el boletín del {day} es del año {m[1]}")
    number=int(m[2])
    if not 1<=number<=400:invalid(f"número de boletín imposible: {number}")
    fecha=" ".join(clean(soup.select_one("#bop_sumario_tit_fecha")).casefold().split())
    if fecha!=f"{day.day:02d} de {MONTHS[day.month-1]} de {day.year}":
        invalid(f"el boletín {number} no es del {day} ({fecha[:40]!r})")
    if len(soup.select("#bop_sumario_tit"))!=1:invalid(f"varias cabeceras de boletín el {day}")
    items=soup.select("li.un_anuncio")
    if not items:invalid(f"el boletín {number} ({day}) no tiene anuncios")
    if soup.select("ul.pagination, .lfr-pagination, .pagination-bar"):
        invalid(f"el boletín {number} ({day}) está paginado: no se garantiza que esté completo")
    out=[]
    for li in items:
        entity=clean(li.select_one("p.bop_tit_articulo"))
        a=li.select_one("p.bop_res_articulo a[href]")
        title=clean(a)
        if not a or not entity or not title:invalid(f"anuncio sin organismo, título o enlace en el boletín {number}")
        url=a["href"].strip()
        u=urlsplit(url)
        p=PDF_RE.fullmatch(u.path)
        if (u.scheme!="https" or u.hostname!=HOST or u.query or u.fragment or not p
            or not u.path.startswith(PDF_PREFIX)):
            invalid(f"enlace PDF inesperado en el boletín {number}: {url[:140]}")
        if (int(p[1]),p[2],int(p[3]),int(p[4]))!=(day.year,MONTHS[day.month-1],day.day,day.year):
            invalid(f"el PDF {url} no corresponde al boletín del {day}")
        out.append((int(p[5]),entity,title,url))
    nums=[x[0] for x in out]
    if len(set(nums))!=len(nums):invalid(f"anuncios repetidos en el boletín {number} ({day})")
    if page.count('class="un_anuncio"')!=len(out):
        invalid(f"el boletín {number}: hay anuncios que no se han podido leer")
    return number,sorted(out)

REJECT=("se nombra","nombra ","nombrad","toma de posesion","modificacion de las bases",
        "modificacion de la convocatoria","rectifica","correccion","desiert","calificaciones",
        "aspirantes aprobad","relacion de aprobados","propuesta de","fecha de","lugar de celebracion",
        "anulacion","se anula","deja sin efecto","subvencion","ayudas","aprobados","resultado",
        "senalamiento","nueva fecha","suspension","aprovechamiento","concesion","puestos de venta",
        "prorroga","ofertas")

def kind(title):
    t=" ".join(fold(title).split())
    if any(x in t for x in REJECT):return None
    return employment(title)

def read_issue(day):
    number,items=parse_issue(fetch(issue_url(day)),day)
    notices=[]
    for n,entity,title,url in items:
        role=kind(title)
        if not role:continue
        nid=f"VD-{day.year}-{n}"
        if not ID_RE.fullmatch(nid):invalid("identificador fuera del patrón de la app: "+nid)
        notices.append({"id":nid,"province":PROVINCE,"title":title[:2800],"entity":entity[:500],
            "date":day.strftime("%d/%m/%Y"),"bulletin":str(number),"type":role,"url":url})
    time.sleep(0.3)
    return {"day":day,"number":str(number),"read":len(items),"notices":notices,"ann":[x[0] for x in items]}

def check_continuity(issues):
    """Boletines y anuncios correlativos en toda la ventana (vuelta a 1 en enero)."""
    if not numbering_ok([(x["day"],int(x["number"])) for x in issues]):
        invalid("numeración de boletines no consecutiva: "+", ".join(x["number"] for x in issues))
    prev=None
    for x in issues:
        ann=x["ann"]
        if ann!=list(range(ann[0],ann[0]+len(ann))):
            invalid(f"faltan anuncios en el boletín {x['number']} ({x['day']}): {ann[0]}–{ann[-1]} con {len(ann)} anuncios")
        if prev is not None:
            pday,plast=prev
            if not (ann[0]==plast+1 or (x["day"].year!=pday.year and ann[0]==1)):
                invalid(f"salto en la numeración de anuncios entre el {pday} ({plast}) y el {x['day']} ({ann[0]})")
        prev=(x["day"],ann[-1])

def audit(today=None,verify_pdfs=True):
    end=today or date.today()
    start,days=calendar(end)
    with ThreadPoolExecutor(THREADS) as pool:
        issues=list(pool.map(read_issue,days))
    issues.sort(key=lambda x:x["day"])
    check_continuity(issues)
    candidates=[n for x in issues for n in x["notices"]]
    if verify_pdfs:
        with ThreadPoolExecutor(THREADS) as pool:list(pool.map(lambda n:fetch(n["url"],pdf=True),candidates))
    for i,x in enumerate(issues,1):
        print(f"VALLADOLID BOP {x['day']} n.º {x['number']}: {x['read']} anuncios "
              f"({x['ann'][0]}–{x['ann'][-1]}), {len(x['notices'])} candidatas (edición {i}/{len(issues)})",flush=True)
    data=[{k:v for k,v in x.items() if k!="ann"} for x in issues]
    return publish_audit(SOURCE,PROVINCE,data,today=end)

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output",required=True,type=Path)
    args=p.parse_args()
    write_output(args.output,audit())
