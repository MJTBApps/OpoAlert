#!/usr/bin/env python3
"""BOC Cantabria: lector diario de los últimos 30 días del Boletín Oficial de Cantabria.

Calendario: el listado mensual oficial en JSON
(https://boc.cantabria.es/boces/busquedaBoletines.do?mes=M&year=AAAA), que da
cada boletín con su id interno, tipo, número y fecha:
  * tipoBol 0: ordinario (numeración anual, vuelve a 1 en enero);
  * tipoBol 1: extraordinario (serie propia, también anual);
  * tipoBol 3: día con VARIOS extraordinarios. El listado solo da el primero;
    los demás se leen de la página oficial del día
    (verBoletin.do?dia=D&mes=M&anio=AAAA&tipoBol=1).
Se comprueba que ambas series son consecutivas dentro de la ventana y que el
boletín anterior a la ventana existe (para no perder uno al principio).

De cada boletín se lee su sumario HTML (verBoletin.do?idBolOrd=ID u
verBoletinExtraordinario.do?id=ID) y se contrasta con el XML oficial del
boletín (verXmlAction.do?idBlob=ID): mismo número de disposiciones y mismos
pares CVE/PDF. Cada anuncio enlaza su PDF oficial
(verAnuncioAction.do?idAnuBlob=N, «PDF (BOC-AAAA-NNNN ...)»); el identificador
es CN-AAAA-NNNN a partir de ese CVE. El PDF de cada candidata se comprueba
(cabecera %PDF y nombre AAAA-NNNN.pdf).

No se usa la portada «último boletín» (puede servir una copia antigua).
Nunca se publican datos parciales: ante cualquier incoherencia el lector falla.
"""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo
import argparse,html,json,re,threading,time
import requests
from clm_common import employment,publish_audit,write_output,numbering_ok
from provincial_common import ProvincialCoverageError,fold

SOURCE="https://boc.cantabria.es/boces/"     # Province.kt CANTABRIA_BOC
PROVINCE="Cantabria (BOC)"
HOST="boc.cantabria.es"
BASE="https://boc.cantabria.es/boces/"
PDF_PATH="/boces/verAnuncioAction.do"
ID_RE=re.compile(r"CN-\d{4}-\d{1,6}")        # Province.kt CANTABRIA_BOC
MADRID=ZoneInfo("Europe/Madrid")
MONTHS={"enero":1,"febrero":2,"marzo":3,"abril":4,"mayo":5,"junio":6,"julio":7,
        "agosto":8,"septiembre":9,"octubre":10,"noviembre":11,"diciembre":12}
ORD,EXT,EXTS=0,1,3
THREADS=3
PAUSE=0.3
LOOKBACK_MONTHS=12
TLS=threading.local()

def invalid(message):
    raise ProvincialCoverageError("Cantabria BOC: "+str(message))

# ---------------------------------------------------------------- HTTP
def session():
    if not hasattr(TLS,"client"):
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert official bulletin audit)",
                          "Accept-Language":"es-ES,es;q=0.9"})
        TLS.client=s
    return TLS.client

def official(url):
    u=urlsplit(url)
    return (u.scheme=="https" and u.hostname==HOST and u.port in (None,443) and not u.username
            and not u.password and not u.fragment and u.path.startswith("/boces/") and ".." not in u.path)

def fetch(url,attempts=3,limit=60_000_000):
    """Respuesta oficial de boc.cantabria.es (bytes, cabeceras); reintentos breves."""
    if not official(url):invalid("URL fuera del portal oficial: "+url[:160])
    error=None
    for i in range(attempts):
        try:
            with session().get(url,timeout=(12,60),stream=True,allow_redirects=True) as r:
                if not official(r.url):invalid("redirección fuera del portal oficial: "+r.url[:160])
                if r.status_code==200:
                    body=bytearray()
                    for chunk in r.iter_content(65536):
                        body+=chunk
                        if len(body)>limit:invalid("documento desmesurado: "+url)
                    if body:return bytes(body),r.headers
                    error="respuesta vacía"
                else:
                    error=f"HTTP {r.status_code}"
                    if r.status_code in (403,404,410):break
        except requests.RequestException as ex:
            error=str(ex)[:160]
        if i<attempts-1:time.sleep(2*(i+1))
    invalid(f"sin acceso a {url}: {error}")

def page(url):
    body,headers=fetch(url)
    m=re.search(r"charset=([\w-]+)",headers.get("Content-Type",""),re.I)
    text=body.decode(m[1] if m else "iso-8859-1",errors="strict")
    if re.search(r"captcha|recaptcha|hcaptcha",text,re.I):
        invalid("el portal pide una verificación anti-robots: no se elude")
    return text

def text(fragment):
    return " ".join(html.unescape(re.sub(r"<[^>]+>"," ",fragment)).split())

def es_date(raw):
    m=re.fullmatch(r"(\d{1,2}) de ([a-záéíóú]+) de (\d{4})",raw.strip().casefold())
    if not m or m[2] not in MONTHS:return None
    try:return date(int(m[3]),MONTHS[m[2]],int(m[1]))
    except ValueError:return None

# ---------------------------------------------------------------- calendario
def month_url(year,month):
    return f"{BASE}busquedaBoletines.do?mes={month}&year={year}"

def day_url(day):
    return f"{BASE}verBoletin.do?dia={day.day}&mes={day.month}&anio={day.year}&tipoBol=1"

def issue_url(kind,bid):
    return f"{BASE}verBoletin.do?idBolOrd={bid}" if kind==ORD else f"{BASE}verBoletinExtraordinario.do?id={bid}"

def xml_url(bid):
    return f"{BASE}verXmlAction.do?idBlob={bid}"

def parse_month(raw,year,month):
    """[(tipo, número, fecha, id)] del listado mensual; falla si es incoherente."""
    try:rows=json.loads(raw)
    except ValueError:invalid(f"listado de {month}/{year} ilegible")
    if not isinstance(rows,list):invalid(f"listado de {month}/{year} inesperado")
    out=[]
    for x in rows:
        try:
            kind,num,bid=int(x["tipoBol"]),int(x["numBol"]),int(x["id"])
            day=es_date(x["fecBolString"])
            local=datetime.fromtimestamp(int(x["fecBolMilis"])/1000,MADRID).date()
        except (KeyError,TypeError,ValueError,OverflowError):
            invalid(f"fila del listado de {month}/{year} no reconocida: {str(x)[:120]}")
        if kind not in (ORD,EXT,EXTS):invalid(f"tipo de boletín desconocido {kind} en {month}/{year}")
        if day is None or day!=local or (day.year,day.month)!=(year,month) or num<1 or bid<1:
            invalid(f"boletín {num} con fecha contradictoria en el listado de {month}/{year}")
        out.append((kind,num,day,bid))
    if len({x[3] for x in out})!=len(out):invalid(f"ids repetidos en el listado de {month}/{year}")
    return out

DAY_ENTRY=re.compile(r'<a\s+name="contenido"\s+href="verBoletinExtraordinario\.do\?id=(\d+)"[^>]*>\s*'
                     r'<span class="negrita">\s*Bolet&iacute;n Extraordinario\s+(\d{1,2} de [a-z]+ de \d{4})\s*'
                     r'N&uacute;mero\s+(\d{1,4})\s*</span>',re.S)

def parse_day(page_text,day):
    """Extraordinarios de un día con varios: [(número, id)]."""
    found=[(int(n),int(i)) for i,d,n in DAY_ENTRY.findall(page_text) if es_date(d)==day]
    links=re.findall(r'href="verBoletinExtraordinario\.do\?id=\d+"',page_text)
    if len(found)<2 or len(found)!=len(links):
        invalid(f"página de extraordinarios del {day} incompleta o irreconocible")
    if len({n for n,_ in found})!=len(found):invalid(f"extraordinarios repetidos el {day}")
    return sorted(found)

def months_between(a,b):
    y,m=a;out=[]
    while (y,m)<=b:
        out.append((y,m));y,m=(y+1,1) if m==12 else (y,m+1)
    return out

def prev_month(y,m):
    return (y-1,12) if m==1 else (y,m-1)

class Archive:
    """Listados mensuales leídos y extraordinarios desplegados por día."""
    def __init__(self):
        self.months={}
        self.days={}
    def month(self,y,m):
        if (y,m) not in self.months:
            body,_=fetch(month_url(y,m))
            self.months[(y,m)]=parse_month(body.decode("utf-8"),y,m)
            time.sleep(PAUSE)
        return self.months[(y,m)]
    def extras(self,day,rows):
        """Extraordinarios (número, id) de un día, desplegando los de tipo 3."""
        here=[(n,i) for k,n,d,i in rows if d==day and k in (EXT,EXTS)]
        if any(k==EXTS for k,_,d,_ in rows if d==day):
            if day not in self.days:
                self.days[day]=parse_day(page(day_url(day)),day)
                time.sleep(PAUSE)
            full=self.days[day]
            for n,i in here:
                if (n,i) not in full:invalid(f"el extraordinario {n} del {day} no figura en la página del día")
            here=full
        return sorted(set(here))

def calendar(end,archive=None):
    """Boletines [(fecha, tipo, número, id)] de end-29..end, comprobados."""
    a=archive or Archive()
    start=end-timedelta(days=29)
    first=prev_month(start.year,start.month)
    rows=[r for ym in months_between(first,(end.year,end.month)) for r in a.month(*ym)]
    if not any(r[2].month==end.month and r[2].year==end.year for r in rows) and end.day>4:
        invalid(f"el listado de {end.month}/{end.year} está vacío")
    ords=sorted((d,n,i) for k,n,d,i in rows if k==ORD)
    if len({(d.year,n) for d,n,_ in ords})!=len(ords) or len({d for d,_,_ in ords})!=len(ords):
        invalid("ordinarios repetidos en el listado")
    window=[(d,ORD,n,i) for d,n,i in ords if start<=d<=end]
    before=[(d,n) for d,n,_ in ords if d<start]
    if not window:invalid("ningún boletín ordinario en la ventana")
    if not before:invalid("no aparece el boletín ordinario anterior a la ventana")
    chain=[before[-1]]+[(d,n) for d,_,n,_ in window]
    if not numbering_ok(chain):
        invalid("numeración de ordinarios no consecutiva: "+", ".join(str(n) for _,n in chain))
    # Extraordinarios (tipos 1 y 3) de los días de la ventana.
    ext_days=sorted({d for k,_,d,_ in rows if k in (EXT,EXTS) and start<=d<=end})
    extras=[(d,EXT,n,i) for d in ext_days for n,i in a.extras(d,rows)]
    if extras:
        chain=[(d,n) for d,_,n,_ in extras]
        if len({n for _,n in chain})!=len(chain):invalid("extraordinarios repetidos en la ventana")
        d0,n0=chain[0]
        if n0!=1:   # el 1 abre la serie del año: no hay anterior que buscar
            prior=previous_extra(a,start,rows)
            if prior is None:invalid(f"no aparece el extraordinario anterior al {n0} del {d0}")
            chain=[prior]+chain
        if not numbering_ok(chain):
            invalid("numeración de extraordinarios no consecutiva: "+", ".join(str(n) for _,n in chain))
    issues=sorted(window+extras,key=lambda x:(x[0],x[1],x[2]))
    if len({x[3] for x in issues})!=len(issues):invalid("el mismo boletín aparece dos veces")
    return start,issues

def previous_extra(a,start,rows):
    """Último extraordinario (fecha, número) anterior a la ventana, hasta un año atrás."""
    y,m=start.year,start.month
    for _ in range(LOOKBACK_MONTHS+1):
        month_rows=[r for r in a.month(y,m) if r[2]<start and r[0] in (EXT,EXTS)]
        if month_rows:
            day=max(r[2] for r in month_rows)
            n,_=a.extras(day,a.month(y,m))[-1]
            return day,n
        y,m=prev_month(y,m)
    return None

# ---------------------------------------------------------------- sumario
HEAD=re.compile(r'<span class="titulo2">Bolet&iacute;n Oficial de Cantabria:\s*'
                r'(\d{1,2} de [a-z]+ de \d{4}),\s*(ORD|EXT)\.\s*N&uacute;m\.\s*(\d{1,4})\s*</span>')
# Enlaces de referencia a otro anuncio («Corrige a», «Es corregido por»): no son anuncios del boletín.
REFS=re.compile(r'<span class="negritaAnuncio">([^<]*)</span>\s*<a href="verAnuncioAction\.do\?idAnuBlob=\d+"[^>]*>[^<]*</a>')
REF_LABELS=("corrige a","es corregido por")
TOKENS=re.compile(r'<span class="titulo2 margin-bottom-12">(.*?)</span>'
                  r'|<span class="spanH5">(.*?)</span>'
                  r'|<span class="spanH4">(.*?)</span>'
                  r'|<span class="spanH6">(.*?)</span>'
                  r'|<p>(.*?)</p>'
                  r'|<a href="verAnuncioAction\.do\?idAnuBlob=(\d+)"[^>]*>\s*PDF \(BOC-(\d{4})-(\d{1,6}) - [^)<]*\)\s*</a>',re.S)

def parse_issue(page_text,day,kind,number):
    """Anuncios del sumario: [(cve_año, cve, blob, título, organismo, sección)]."""
    head=HEAD.search(page_text)
    want="ORD" if kind==ORD else "EXT"
    if not head or es_date(head[1])!=day or head[2]!=want or int(head[3])!=number:
        invalid(f"el sumario {want} {number} no corresponde al boletín del {day}")
    body=page_text[head.end():]
    stop=body.find("<footer")
    if stop<0:invalid(f"sumario {want} {number} cortado")
    body=body[:stop]
    refs=REFS.findall(body)
    if any(fold(text(r)) not in REF_LABELS for r in refs):
        invalid(f"sumario {want} {number}: enlace de referencia desconocido {sorted(set(refs))}")
    body=REFS.sub(" ",body)
    sec=sub=h4=h6="";title=None;out=[]
    for s,s5,s4,s6,p,blob,year,cve in TOKENS.findall(body):
        if s:sec,sub,h4,h6=text(s),"","","";continue
        if s5:sub=text(s5);continue
        if s4:h4,h6=text(s4),"";continue
        if s6:h6=text(s6);continue
        if p:
            if title is not None:invalid(f"{want} {number}: anuncio sin PDF ({title[:60]})")
            title=text(p);continue
        if title is None:invalid(f"{want} {number}: PDF BOC-{year}-{cve} sin título")
        entity=h4+(f". {h6}" if h6 and fold(h6) not in fold(h4) else "")
        if not title or not h4 or not sec:invalid(f"{want} {number}: BOC-{year}-{cve} sin título, organismo o sección")
        out.append((int(year),int(cve),int(blob),title,entity,(sub or sec)))
        title=None
    if title is not None:invalid(f"{want} {number}: último anuncio sin PDF")
    if not out:invalid(f"el sumario {want} {number} no tiene anuncios")
    if len(re.findall(r"idAnuBlob=",body))!=len(out):
        invalid(f"sumario {want} {number}: hay enlaces a anuncios que no se han podido leer")
    if len({(y,c) for y,c,*_ in out})!=len(out):invalid(f"sumario {want} {number}: CVE repetido")
    return out

def parse_xml(raw,kind,number):
    """Contraste con el XML oficial: {(cve_año, cve): blob}."""
    t=raw.decode("utf-8",errors="replace")
    m=re.search(r"<num_disposiciones>(\d+)</num_disposiciones>",t)
    k=re.search(r"<tipo_boletin>(\w+)</tipo_boletin>",t)
    want="ORD" if kind==ORD else "EXT"
    if not m or not k or k[1]!=want:invalid(f"XML del boletín {want} {number} irreconocible")
    pairs=re.findall(r"<numeroExp>\s*CVE-(\d{4})-(\d{1,6})\s*</numeroExp>.*?"
                     r'<num_exp url="https://boc\.cantabria\.es/boces/verAnuncioAction\.do\?idAnuBlob=(\d+)">',t,re.S)
    found={(int(y),int(c)):int(b) for y,c,b in pairs}
    if len(found)!=len(pairs) or len(pairs)!=int(m[1]) or t.count("<numeroExp>")!=len(pairs):
        invalid(f"XML del boletín {want} {number}: disposiciones descuadradas")
    return found

# ---------------------------------------------------------------- clasificación
# Solo la sección 2.2 «Cursos, Oposiciones y Concursos»: en las demás (nombramientos,
# subvenciones, varios...) los títulos con «selección» o «bolsa» no son convocatorias de empleo.
SECTION="cursos, oposiciones y concursos"
REJECT=("toma de posesion","cese","listado provisional","listado definitivo",
        "lista provisional","lista definitiva","relacion provisional","relacion definitiva",
        "admitid","excluid","exclusion","aprobad","han superado","calificacion","puntuacion",
        "propuesta de","desiert","correccion de error","rectificacion","se modifica","modificacion",
        "caducidad","subvencion","ayudas","fecha de","fecha, hora","lugar de celebracion",
        "emplazamiento","recurso","sentencia","jubilacion","concurso de traslado","adjudica",
        "anulacion","se anula","deja sin efecto","tribunal","plantilla de","resultado",
        "integrar la bolsa","se hace publica la bolsa","libre designacion","comision de servicios",
        "juez de paz","jueza de paz","juez/a de paz")
BASES=re.compile(r"^(?:resolucion[^,.]{0,60}por la que se aprueban? |se aprueban? )?(?:las )?bases\b.*\bconvocatoria\b"
                 r"|^convocatoria (?:para|del|de)\b")

def kind(title,section):
    """Convocatorias nuevas de empleo o bolsa; nunca listas, tribunales ni resultados."""
    if SECTION not in fold(section):return None
    t=" ".join(fold(title).split())
    if any(x in t for x in REJECT):return None
    # «Bases ... y convocatoria ... para el nombramiento como interino» es una convocatoria:
    # employment() lo descartaría por la palabra «nombramiento».
    if BASES.search(t) and any(x in t for x in ("seleccion","selectiv","plaza","puesto","bolsa","personal","cobertura")):
        return "Bolsa de trabajo" if re.search(r"\bbolsas?\b",t) else "Plaza / oposición"
    if "nombra" in t:return None
    return employment(title)

def read_issue(entry):
    day,btype,number,bid=entry
    items=parse_issue(page(issue_url(btype,bid)),day,btype,number)
    time.sleep(PAUSE)
    xml,_=fetch(xml_url(bid))
    official=parse_xml(xml,btype,number)
    mine={(y,c):b for y,c,b,*_ in items}
    if mine!=official:
        invalid(f"boletín {label(btype,number)} ({day}): sumario HTML y XML oficial no coinciden")
    time.sleep(PAUSE)
    bulletin=label(btype,number);notices=[]
    for year,cve,blob,title,entity,section in items:
        role=kind(title,section)
        if not role:continue
        nid=f"CN-{year}-{cve}"
        if not ID_RE.fullmatch(nid):invalid("identificador fuera del patrón de la app: "+nid)
        notices.append({"id":nid,"province":PROVINCE,"title":title[:2800],"entity":entity[:500],
            "date":day.strftime("%d/%m/%Y"),"bulletin":bulletin,"type":role,
            "url":f"https://{HOST}{PDF_PATH}?idAnuBlob={blob}"})
    return {"day":day,"number":bulletin,"read":len(items),"notices":notices,"bid":bid,
            "ext":btype!=ORD,"cves":[(y,c) for y,c,*_ in items]}

def label(btype,number):
    return str(number) if btype==ORD else f"Ext. {number}"

def check_pdf(note):
    body,headers=fetch(note["url"],limit=80_000_000)
    want=note["id"][3:]+".pdf"
    if (not body.startswith(b"%PDF-") or "pdf" not in headers.get("Content-Type","").lower()
            or want not in headers.get("Content-Disposition","")):
        invalid(f"el PDF oficial no corresponde al anuncio {note['id']} ({note['url']})")
    time.sleep(PAUSE)

def dedupe(issues):
    """Un anuncio repetido en otro boletín (reedición) cuenta como leído en ambos,
    pero como candidata solo en su primera publicación dentro de la ventana."""
    seen=set()
    for x in issues:
        keep=[]
        for n in x["notices"]:
            if n["id"] in seen:continue
            seen.add(n["id"]);keep.append(n)
        x["notices"]=keep

def audit(today=None,verify_pdfs=True,archive=None):
    t0=time.time()
    end=today or date.today()
    start,entries=calendar(end,archive)
    with ThreadPoolExecutor(THREADS) as pool:
        issues=list(pool.map(read_issue,entries))
    dedupe(issues)
    candidates=[n for x in issues for n in x["notices"]]
    if verify_pdfs:
        with ThreadPoolExecutor(THREADS) as pool:list(pool.map(check_pdf,candidates))
    for i,x in enumerate(issues,1):
        print(f"CANTABRIA BOC {x['day']} n.º {x['number']}: {x['read']} anuncios, "
              f"{len(x['notices'])} candidatas (edición {i}/{len(issues)})",flush=True)
    data=[{k:x[k] for k in ("day","number","read","notices")} for x in issues]
    feed=publish_audit(SOURCE,PROVINCE,data,today=end)
    feed["coverage"]["announcementsReadMeaning"]=("anuncios (CVE) del sumario de cada BOC, ordinarios y "
        "extraordinarios, contrastados con el XML oficial del boletín")
    feed["historyCoverage"].update(
        regularBulletins=[x["number"] for x in issues if not x["ext"]],
        extraordinaryBulletins=[x["number"] for x in issues if x["ext"]],
        officialIssueIds=[x["bid"] for x in issues])
    print(f"Cantabria BOC: lectura en {time.time()-t0:.0f} s",flush=True)
    return feed

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--output",required=True,type=Path)
    p.add_argument("--today",type=date.fromisoformat,help="solo para pruebas")
    args=p.parse_args()
    write_output(args.output,audit(args.today))
