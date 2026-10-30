#!/usr/bin/env python3
"""BOP de Lleida (eBOP, Diputació de Lleida): todas las ediciones de 30 días.

Portal JSF https://ebop.diputaciolleida.cat/bop/ (misma aplicación que el BOP
de Girona). La portada muestra el último número; cada edición se lee en
  /bop/mostra-bop/<fecha>/<año>/<número>
(el portal solo usa año y número; la fecha de la ruta se ignora). Un número
inexistente redirige (302) a «/bop/?No trobo el BOP ...».

Una misma página puede contener la edición ordinaria («Bop número: 180/0») y
ediciones adicionales del mismo día («180/1»). Se leen todas y se cuentan como
una sola edición (mismo número y fecha).

PDF de cada edicto:
  https://ebop.diputaciolleida.cat/aplicacions/bop/bopV1/fitxers/pdf/<año>/<número>/<año><número><sufijo><edicto>.pdf
sin ceros a la izquierda (p. ej. 2026/5/20265035.pdf = BOP 5/0, edicto 35).
Identificador: LE-<nombre del PDF>.

Se recorre hacia atrás, número a número, desde el último boletín (o desde el
último publicado hasta «today» si se audita una fecha pasada) hasta la primera
edición anterior a la ventana. En enero la numeración vuelve a 1: el último
número del año anterior se localiza en el propio portal (búsqueda binaria) y
se comprueba que el siguiente no existe. Fechas, números, PDF y edictos deben
cuadrar; si algo falla se lanza ProvincialCoverageError y no se escribe feed.

Uso: python backend/lleida_bop.py --output out/lleida_bop.json
"""
from __future__ import annotations
import argparse,re,sys,threading,time
from concurrent.futures import ThreadPoolExecutor
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit

import requests
from bs4 import BeautifulSoup

sys.path.insert(0,str(Path(__file__).resolve().parent))
from clm_common import employment,numbering_ok,publish_audit,write_output,pdf_header
from provincial_common import ProvincialCoverageError,fold

SOURCE="https://ebop.diputaciolleida.cat/bop/"
PROVINCE="Lleida (BOP)"
HOST="ebop.diputaciolleida.cat"
PDF_PREFIX="/aplicacions/bop/bopV1/fitxers/pdf/"
ISSUE_URL=SOURCE+"mostra-bop/{day}/{year}/{number}"
# Debe coincidir con Province.LLEIDA_BOP.idPattern (la app rechaza el resto).
APP_ID=re.compile(r"LE-\d{7,14}")
HEADER=re.compile(r"Bop\s*n[úu]mero\s*:\s*(\d{1,3})\s*/\s*(\d{1,2})\s*-\s*(\d{2}/\d{2}/\d{4})",re.I)
PDF_PATH=re.compile(r"^"+re.escape(PDF_PREFIX)+r"(\d{4})/(\d{1,3})/(\d{7,16})\.pdf$")
EDICT=re.compile(r"^(\d{1,6})\s*-\s*")
MAX_NUMBER=400          # el BOP de Lleida publica unos 250 números al año
WORKERS=4
MAX_PAGE=3_000_000
UA=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/16.6 Safari/605.1.15")

def fail(message):
    raise ProvincialCoverageError("Lleida BOP: "+str(message))

def issue_url(year,number):
    # El portal no usa la fecha de la ruta; se pone el 1 de enero del año del BOP.
    return ISSUE_URL.format(day=f"{year}-01-01",year=year,number=number)

# ---------------------------------------------------------------- HTTP
_LOCAL=threading.local()
def session():
    if not hasattr(_LOCAL,"s"):
        s=requests.Session()
        s.headers.update({"User-Agent":UA,"Accept":"text/html,application/xhtml+xml",
                          "Accept-Language":"ca,es;q=0.8"})
        _LOCAL.s=s
    return _LOCAL.s

def download(url,retries=3):
    """HTML de la página oficial, o None si el portal dice que el BOP no existe."""
    u=urlsplit(url)
    if (u.scheme!="https" or u.hostname!=HOST or u.port not in (None,443) or u.username
            or u.password or u.fragment or u.query or not u.path.startswith("/bop/")):
        fail("URL fuera del portal oficial: "+url[:160])
    error=None
    for attempt in range(retries):
        try:
            r=session().get(url,timeout=(10,30),allow_redirects=False)
            if r.status_code in (301,302,303,307,308):
                loc=r.headers.get("Location","")
                lu=urlsplit(loc)
                if lu.hostname in (None,"",HOST) and lu.path.rstrip("/")=="/bop" and "No+trobo" in loc:
                    return None
                fail(f"redirección inesperada desde {url}: {loc[:160]}")
            if r.status_code in (403,429):
                fail(f"HTTP {r.status_code}: el portal bloquea la lectura (no se elude)")
            if r.status_code!=200:
                raise requests.RequestException(f"HTTP {r.status_code}")
            if not r.content or len(r.content)>MAX_PAGE:
                fail("página vacía o desmesurada: "+url)
            text=r.content.decode(r.encoding or "utf-8","replace")
            if re.search(r"captcha|recaptcha|hcaptcha|cf-challenge",text,re.I):
                fail("el portal pide una verificación anti-robots: no se elude")
            return text
        except requests.RequestException as ex:
            error=ex
            if attempt<retries-1:time.sleep(1.0*(attempt+1))
    fail(f"sin acceso a {url}: {error}")

# ---------------------------------------------------------------- filtro
# Edictos que no son una convocatoria abierta (listas, tribunales, nombramientos,
# correcciones, subvenciones, premios...). Textos en catalán, castellano y aranés.
EXCLUDED=("admes","exclos","admitid","excluid","llista","llistat","lista ","relacio provisional",
    "relacio definitiva","tribunal","resultat","resultado","qualificacio","puntuacio","aprovats",
    "correccio d","correccion d","rectificacio","esmena","resolucio de la convocatoria",
    "resolucio per la qual","subvenci","ajut","beca","beques","premi","licitaci","adjudicaci",
    "lloguer","subhasta","jutge de pau","jutgessa de pau","juez de paz","assemblea","junta general",
    "concurrencia competitiva","cessament","presa de possessio","trasllat","nombramiento",
    "contractacio de personal laboral fix en la placa")
# Puestos que se cubren por «nomenament provisional/interí» sí son convocatorias.
NOMENAMENT_OK=("nomenament provisional","nomenament interi")
JOB=("placa","places","lloc de treball","llocs de treball","borsa","proces selectiu",
    "proces de seleccio","seleccio de personal","proves selectives","concurs-oposicio",
    "concurs oposicio","oposicio","promocio interna","promocions internes","provisio interina",
    "provisio no definitiva","provisio definitiva","funcionari","personal laboral","interi")
def candidate(title):
    """Filtro común (employment) más el vocabulario catalán del BOP de Lleida."""
    t=" ".join(fold(title).replace("\u2019","'").replace("`","'").split())
    if any(w in t for w in EXCLUDED):return None
    rest=t
    for w in NOMENAMENT_OK:rest=rest.replace(w," ")
    if "nomenament" in rest:return None
    kind=employment(title)
    if kind:return kind
    if any(w in t for w in ("convocat","bases","oferta publica d'ocupacio")) and any(w in t for w in JOB):
        return "Bolsa de trabajo" if "borsa" in t else "Plaza / oposición"
    return None

# ---------------------------------------------------------------- edición
def parse_issue(html,year=None,number=None):
    soup=BeautifulSoup(html,"html.parser")
    blocks=[];current=None;edicts=[]
    for node in soup.find_all(["h1","li"]):
        if node.name=="h1":
            m=HEADER.search(" ".join(node.get_text(" ",strip=True).split()))
            if not m:continue
            current={"number":int(m[1]),"suffix":int(m[2]),
                     "day":datetime.strptime(m[3],"%d/%m/%Y").date(),"count":0}
            blocks.append(current)
        elif "edicte" in (node.get("class") or []):
            if current is None:fail("edicto antes de la cabecera del BOP")
            current["count"]+=1
            edicts.append((current,node))
    if not blocks:fail("cabecera del BOP ilegible")
    num=blocks[0]["number"];day=blocks[0]["day"]
    if any(b["number"]!=num or b["day"]!=day for b in blocks):
        fail(f"BOP {num}: la página mezcla ediciones distintas")
    if [b["suffix"] for b in blocks]!=list(range(len(blocks))):
        fail(f"BOP {num}: ediciones adicionales no consecutivas {[b['suffix'] for b in blocks]}")
    if number is not None and num!=number:fail(f"BOP {num} recibido, esperado {number}")
    if year is not None and day.year!=year:fail(f"BOP {num} de {day.year}, esperado {year}")
    if any(b["count"]==0 for b in blocks):fail(f"BOP {num}: edición sin edictos")
    rows=[];seen=set()
    for block,li in edicts:
        a=li.select_one("a.linkAjuda[href]")
        if a is None:fail(f"BOP {num}: edicto sin enlace")
        href=a.get("href","").strip()
        p=urlsplit(href)
        m=PDF_PATH.fullmatch(p.path)
        if (p.scheme!="https" or p.hostname!=HOST or p.port not in (None,443) or p.query
                or p.fragment or p.username or not m):
            fail(f"BOP {num}: PDF no oficial {href[:140]}")
        fileyear,pathnum,filename=m.groups()
        span=a.select_one("span")
        agency=" ".join(span.get_text(" ",strip=True).split()) if span else ""
        full=" ".join(a.get_text(" ",strip=True).split())
        pm=EDICT.match(full)
        if not agency or not pm:fail(f"BOP {num}: edicto sin entidad o registro")
        edict=int(pm[1])
        if (int(fileyear)!=day.year or int(pathnum)!=num
                or filename!=f"{day.year}{num}{block['suffix']}{edict}"):
            fail(f"BOP {num}: el PDF {filename} no corresponde al edicto {edict}")
        if (block["suffix"],edict) in seen:fail(f"BOP {num}: edicto {edict} repetido")
        seen.add((block["suffix"],edict))
        rest=full[pm.end():]
        if not rest.startswith(agency):fail(f"BOP {num}: entidad del edicto {edict} no coincide")
        title=rest[len(agency):].lstrip(" -–:")
        if not title or len(title)>2800:fail(f"BOP {num}: edicto {edict} sin título")
        kind=candidate(title)
        if kind is None:continue
        ident="LE-"+filename
        if not APP_ID.fullmatch(ident):
            fail(f"identificador {ident} fuera del patrón de la app (Province.kt LE-\\d{{7,14}}); "
                 "con números de BOP de 1-2 cifras el PDF tiene menos dígitos")
        rows.append({"id":ident,"province":PROVINCE,"title":title,"entity":agency,
                     "date":day.strftime("%d/%m/%Y"),"bulletin":str(num),"type":kind,
                     "url":p.geturl()})
    return {"day":day,"number":num,"year":day.year,"editions":len(blocks),
            "read":len(edicts),"notices":rows}

# ---------------------------------------------------------------- recorrido
class Portal:
    def __init__(self,fetch):
        self.fetch=fetch;self.cache={};self.last={};self.lock=threading.Lock()
    def issue(self,year,number):
        key=(year,number)
        if key not in self.cache:
            html=self.fetch(issue_url(year,number))
            self.cache[key]=None if html is None else parse_issue(html,year,number)
        return self.cache[key]
    def last_of(self,year):
        """Último número publicado en un año ya cerrado (búsqueda binaria)."""
        if year not in self.last:
            if self.issue(year,1) is None:fail(f"no existe el BOP 1 de {year}")
            if self.issue(year,MAX_NUMBER) is not None:fail(f"{year}: más de {MAX_NUMBER} números")
            lo,hi=1,MAX_NUMBER
            while hi-lo>1:
                mid=(lo+hi)//2
                if self.issue(year,mid) is None:hi=mid
                else:lo=mid
            if self.issue(year,lo+1) is not None:fail(f"{year}: numeración con huecos")
            self.last[year]=lo
        return self.last[year]
    def latest_until(self,end,latest):
        """Último BOP con fecha <= end, partiendo del último publicado."""
        if latest["day"]<=end:return latest["year"],latest["number"]
        year=end.year
        hi=latest["number"] if latest["year"]==year else self.last_of(year)
        first=self.issue(year,1)
        if first is None or first["day"]>end:
            return year-1,self.last_of(year-1)
        lo=1
        while hi-lo>1:
            mid=(lo+hi)//2
            got=self.issue(year,mid)
            if got is None:fail(f"{year}: falta el BOP {mid}")
            if got["day"]<=end:lo=mid
            else:hi=mid
        if self.issue(year,hi)["day"]<=end:lo=hi
        return year,lo
    def previous(self,year,number):
        return (year,number-1) if number>1 else (year-1,self.last_of(year-1))

def audit(today=None,fetch=None):
    end=today or date.today()
    start=end-timedelta(days=29)
    real=fetch is None
    fetch=fetch or download
    home=fetch(SOURCE)
    if home is None:fail("portada no disponible")
    latest=parse_issue(home)
    if latest["day"]>date.today()+timedelta(days=1):fail(f"último BOP con fecha futura {latest['day']}")
    portal=Portal(fetch)
    portal.cache[(latest["year"],latest["number"])]=latest
    key=portal.latest_until(end,latest)
    issues=[];visited=0;done=False
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        while not done:
            keys=[key]
            for _ in range(WORKERS-1):keys.append(portal.previous(*keys[-1]))
            got=list(pool.map(lambda k:portal.issue(*k),keys))
            for k,issue in zip(keys,got):
                if issue is None:fail(f"falta el BOP {k[1]}/{k[0]} dentro del recorrido")
                visited+=1
                if issues and issue["day"]>=issues[-1]["day"]:
                    fail(f"fechas no decrecientes en el BOP {issue['number']}")
                if issue["day"]<start:
                    done=True;break
                if issue["day"]>end:fail(f"BOP {issue['number']} posterior a la ventana")
                issues.append(issue)
                print(f"Lleida {issue['day']}: BOP {issue['number']} · {issue['editions']} ed. · "
                      f"{issue['read']} edictos · {len(issue['notices'])} candidatas",flush=True)
            if not done:key=portal.previous(*keys[-1])
            if visited>60:fail("no se encuentra la edición anterior a la ventana")
    issues.reverse()
    if not numbering_ok([(x["day"],x["number"]) for x in issues]):
        fail(f"numeración no consecutiva {[x['number'] for x in issues]}")
    if real:
        newest=next((n for x in reversed(issues) for n in x["notices"]),None)
        if newest:pdf_header(newest["url"],{HOST})
    feed=publish_audit(SOURCE,PROVINCE,issues,today=end)
    feed["coverage"]["pagesVisited"]=visited
    return feed

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--output",type=Path,required=True)
    args=ap.parse_args()
    write_output(args.output,audit())
