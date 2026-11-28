#!/usr/bin/env python3
"""BOP Málaga (www.bopmalaga.es): acumular cada día el sumario público.

Solo la portada del portal es pública: muestra el sumario del último boletín y
el calendario del mes. Los sumarios anteriores, las fichas de edicto y los PDF
piden la verificación de Cloudflare (Turnstile), que **nunca se elude**: si el
portal la pide, el lector se detiene.

Por eso el ejecutor de casa (revisar-espana-casa.yml) guarda cada día la portada
en un estado persistente fuera del repositorio (por defecto
~/OpoAlert-estado/malaga_bop, o la carpeta de OPOALERT_ESTADO), y el feed de 30
días se construye solo a partir de ese histórico. Mientras falte algún boletín
del calendario oficial dentro de la ventana, no hay feed (regla 2: nunca un feed
parcial) y el programa termina con el código 3 («aún acumulando»).

  python backend/malaga_bop.py acumular            # guarda la portada de hoy
  python backend/malaga_bop.py estado              # qué falta para tener 30 días
  python backend/malaga_bop.py --output out/malaga_bop.json   # acumula y construye el feed
"""
from __future__ import annotations
import argparse,gzip,json,os,re,sys,tempfile,time
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urljoin,urlsplit,parse_qs
try:
    from zoneinfo import ZoneInfo
    MADRID=ZoneInfo("Europe/Madrid")
except Exception:  # pragma: no cover - sin tzdata
    MADRID=None
import requests
from bs4 import BeautifulSoup
from clm_common import employment,numbering_ok,publish_audit,write_output
from provincial_common import ProvincialCoverageError

HOME="https://www.bopmalaga.es/"
HOST="www.bopmalaga.es"
SOURCE=HOME
PROVINCE="Málaga"
EDICT=re.compile(r"(\d{8})-(\d{5})-(\d{4})-(\d{2})")
BULLETIN_PDF=re.compile(r"(\d{2})(\d{2})(\d{2})(\d{1,3})(?:a\d{2})?\.pdf",re.I)
CAL_TITLE=re.compile(r"^BOP\s+(\d{1,3})\s*:",re.I)
STILL_ACCUMULATING=3
UA=("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120 Safari/537.36")
CHALLENGE=(b"Just a moment",b"Un momento",b"challenges.cloudflare.com/cdn-cgi",b"cf-chl-",
           b"Verificaci\xc3\xb3n de seguridad en curso",b"Verificacion necesaria")

def invalid(message):
    raise ProvincialCoverageError(message)

def state_dir(path=None):
    if path:return Path(path)
    return Path(os.environ.get("OPOALERT_ESTADO") or Path.home()/"OpoAlert-estado")/"malaga_bop"

def today_madrid():
    return datetime.now(MADRID).date() if MADRID else date.today()

def notice_url(code):
    """Enlace oficial del anuncio en el portal (sin el «id» firmado de la portada,
    que caduca en un día). Abrirlo puede pedir la verificación de Cloudflare,
    que pasa la persona en su navegador; el lector nunca lo abre."""
    if not EDICT.fullmatch(code):invalid("Málaga: código de edicto incorrecto "+code)
    return f"{HOME}edicto.php?edicto={code}"

# ---------------------------------------------------------------- portada

def fetch_home(retries=3):
    error=None
    for attempt in range(retries):
        try:
            r=requests.get(HOME,timeout=(15,40),headers={"User-Agent":UA,"Accept-Language":"es"})
            head=r.content[:6000]
            if any(x in head for x in CHALLENGE) and b'id="seccionSumario"' not in r.content:
                invalid("Málaga: el portal pide verificación humana (Cloudflare); no se elude")
            if r.status_code==200 and urlsplit(r.url).hostname==HOST and 0<len(r.content)<=4_000_000:
                return r.content.decode("utf-8",errors="replace")
            error=f"HTTP {r.status_code}, {len(r.content)} bytes"
        except requests.RequestException as ex:error=str(ex)[:160]
        if attempt<retries-1:time.sleep(20*(attempt+1))
    invalid(f"Málaga: portada no disponible ({error})")

def text(node):
    return re.sub(r"\s+"," ",node.get_text(" ",strip=True)).strip() if node else ""

def parse_calendar(h):
    """Días del mes que muestra la portada con su número de BOP."""
    days={}
    table=h.select_one("table#table_calendario") or h
    for a in table.select("a[href]"):
        t=a.select_one("time[datetime]");m=CAL_TITLE.search(a.get("title",""))
        q=parse_qs(urlsplit(urljoin(HOME,a["href"])).query).get("fecha",[""])[0]
        if not t or not m:continue
        try:day=date.fromisoformat(t["datetime"])
        except ValueError:invalid("Málaga: fecha del calendario ilegible")
        if q!=day.strftime("%d-%m-%Y"):invalid("Málaga: enlace del calendario con otra fecha")
        n=int(m[1])
        if days.get(day.isoformat(),n)!=n:invalid("Málaga: día con dos números de BOP")
        days[day.isoformat()]=n
    if not days:invalid("Málaga: calendario oficial vacío")
    months={d[:7] for d in days}
    if len(months)!=1:invalid("Málaga: el calendario mezcla meses")
    return months.pop(),days

def parse_home(html):
    """Portada -> boletín del día con todos sus edictos. Falla ante cualquier duda."""
    h=BeautifulSoup(html,"html.parser")
    mark=h.select_one("#main h2 time[datetime]") or h.select_one("h2 time[datetime]")
    if mark is None:invalid("Málaga: portada sin fecha del sumario")
    try:day=date.fromisoformat(mark["datetime"])
    except ValueError:invalid("Málaga: fecha del sumario ilegible")
    month,cal=parse_calendar(h)
    number=cal.get(day.isoformat())
    if number is None:invalid(f"Málaga: el sumario del {day} no figura en el calendario")
    head=h.select_one("#lista_pdf header time[datetime]")
    if head is None or head["datetime"]!=day.isoformat():invalid("Málaga: lista de PDF de otro día")
    pdfs=[]
    for a in h.select('#lista_pdf a[href*="verificacion.php"]'):
        f=parse_qs(urlsplit(urljoin(HOME,a["href"])).query).get("archivo",[""])[0]
        m=BULLETIN_PDF.fullmatch(f)
        if not m or f[:6]!=day.strftime("%d%m%y") or int(m[4])!=number:
            invalid(f"Málaga: PDF del boletín no coincide con el BOP {number} del {day}")
        pdfs.append(f)
    if not pdfs:invalid("Málaga: boletín sin PDF")
    box=h.select_one("#seccionSumario")
    if box is None:invalid("Málaga: portada sin sumario")
    edicts=[]
    for section in box.find_all("section",recursive=False):
        group=text(section.find("h3",recursive=False)).upper()
        if not group:invalid("Málaga: sección sin nombre")
        for art in section.find_all("article",recursive=False):
            summ=art.select_one("p.vista_sumario");full=art.select_one("p.vista_edicto")
            link=(summ or art).select_one('a[href*="edicto.php?edicto="]')
            if summ is None or link is None:invalid("Málaga: anuncio sin resumen o sin enlace de edicto")
            code=parse_qs(urlsplit(urljoin(HOME,link["href"])).query).get("edicto",[""])[0]
            m=EDICT.fullmatch(code)
            if not m or m[1]!=day.strftime("%Y%m%d"):invalid(f"Málaga: edicto {code!r} de otra fecha")
            town=text(summ.find("b"))
            for s in summ.select("span.span_enlaces"):s.extract()
            body=text(summ)
            title=body[len(town):].lstrip(" .").strip() if town and body.startswith(town) else body
            if full is not None:
                for s in full.select("span.span_enlaces"):s.extract()
            if not title:invalid(f"Málaga: edicto {code} sin resumen")
            edicts.append({"code":code,"section":group,"town":town,"title":title,
                           "preview":text(full)[:600]})
    codes=[e["code"] for e in edicts]
    if not edicts or len(set(codes))!=len(codes):invalid("Málaga: sumario vacío o con edictos repetidos")
    return {"date":day.isoformat(),"number":number,"pdfs":pdfs,"edicts":edicts,
            "calendarMonth":month,"calendar":cal}

# ---------------------------------------------------------------- estado

def atomic_write(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,tmp=tempfile.mkstemp(dir=path.parent,prefix=".tmp-")
    with os.fdopen(fd,"wb") as f:f.write(data)
    os.replace(tmp,path)

def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))

def store(parsed,html,folder,observed):
    """Guarda el boletín y la foto del calendario. Nunca encoge lo ya guardado."""
    folder=Path(folder);observed=observed.isoformat()
    target=folder/"boletines"/f"{parsed['date']}.json"
    issue={k:parsed[k] for k in ("date","number","pdfs","edicts")}
    if target.exists():
        old=load_json(target)
        if old["number"]!=issue["number"]:invalid(f"Málaga: el {issue['date']} cambia de número de BOP")
        old_codes={e["code"] for e in old["edicts"]};new_codes={e["code"] for e in issue["edicts"]}
        if not old_codes<=new_codes:
            invalid(f"Málaga: el sumario del {issue['date']} ha perdido edictos respecto al guardado")
        if old.get("firstSeenUTC"):issue["firstSeenUTC"]=old["firstSeenUTC"]
        changed=old_codes!=new_codes or old["pdfs"]!=issue["pdfs"]
    else:changed=True
    now=datetime.now(timezone.utc).isoformat(timespec="seconds")
    issue.setdefault("firstSeenUTC",now)
    issue["lastSeenUTC"]=now
    atomic_write(target,(json.dumps(issue,ensure_ascii=False,indent=1)+"\n").encode())
    if changed:
        atomic_write(folder/"html"/f"{parsed['date']}.html.gz",gzip.compress(html.encode("utf-8")))
    cal={"observed":observed,"month":parsed["calendarMonth"],"days":parsed["calendar"]}
    atomic_write(folder/"calendario"/f"{observed}.json",(json.dumps(cal,ensure_ascii=False)+"\n").encode())
    return issue,changed

def accumulate(folder=None,observed=None,html=None):
    folder=state_dir(folder);html=html if html is not None else fetch_home()
    parsed=parse_home(html)
    issue,changed=store(parsed,html,folder,observed or today_madrid())
    print(f"MALAGA guardado BOP {issue['number']} del {issue['date']}: {len(issue['edicts'])} edictos"
          +(" (nuevo o ampliado)" if changed else " (ya estaba)"),flush=True)
    return issue

def load_state(folder):
    folder=Path(folder)
    issues={}
    for p in sorted((folder/"boletines").glob("*.json")):
        x=load_json(p);issues[x["date"]]=x
    cals=[load_json(p) for p in sorted((folder/"calendario").glob("*.json"))]
    return issues,cals

def official_days(cals,start,end):
    """Calendario oficial de la ventana a partir de las fotos guardadas.

    Un día cuenta como conocido si alguna foto de su mes se tomó ese día o después
    (los días sin enlace en esa foto no tuvieron BOP). Devuelve ({fecha: número},
    [días aún desconocidos]). El último día (hoy) puede quedar sin boletín si a
    primera hora aún no está colgado: entra en la siguiente ronda."""
    bops={};unknown=[]
    d=start
    while d<=end:
        iso=d.isoformat();known=False
        for c in cals:
            if c["month"]==iso[:7] and c["observed"]>=iso:
                known=True
                if iso in c["days"]:
                    n=int(c["days"][iso])
                    if bops.get(iso,n)!=n:invalid(f"Málaga: el {iso} figura con dos números de BOP")
                    bops[iso]=n
        if not known and d!=end:unknown.append(iso)
        d+=timedelta(days=1)
    return bops,unknown

def missing(folder,today):
    """Qué impide aún construir los 30 días: días sin foto de calendario y boletines sin sumario."""
    issues,cals=load_state(folder)
    start=today-timedelta(days=29)
    bops,unknown=official_days(cals,start,today)
    absent=[f"{d} (BOP {n})" for d,n in sorted(bops.items()) if d not in issues]
    wrong=[d for d,n in bops.items() if d in issues and int(issues[d]["number"])!=n]
    return {"start":start,"end":today,"bops":bops,"unknownDays":unknown,"missingIssues":absent,
            "wrongNumber":sorted(wrong),"stored":len(issues)}

# Bases de concursos que no son de empleo y que el clasificador común aún admite
# («adjudicación de puestos en el mercadillo municipal», BOP 229 de 27/11/2026).
NOT_EMPLOYMENT=re.compile(r"mercadillo|puestos? (?:de|en el) mercado|adjudicaci[oó]n de puestos",re.I)

def kind(e):
    if NOT_EMPLOYMENT.search(e["title"]):return None
    return employment(e["title"])

def build(folder=None,today=None):
    folder=state_dir(folder);today=today or today_madrid()
    info=missing(folder,today)
    if info["wrongNumber"]:invalid("Málaga: número de BOP distinto entre calendario y sumario: "+", ".join(info["wrongNumber"]))
    if info["unknownDays"] or info["missingIssues"]:
        return None,info
    issues,_=load_state(folder)
    rows=sorted(info["bops"].items())
    if not numbering_ok([(date.fromisoformat(d),n) for d,n in rows]):
        invalid("Málaga: salto en la numeración de los BOP de la ventana")
    data=[]
    for d,n in rows:
        x=issues[d];day=date.fromisoformat(d);notices=[]
        for e in x["edicts"]:
            t=kind(e)
            if t is None:continue
            m=EDICT.fullmatch(e["code"])
            notices.append({"id":f"MA-{m[1]}-{m[2]}-{m[4]}","province":PROVINCE,"title":e["title"],
                "entity":f"{e['section']} · {e['town']}" if e["town"] else e["section"],
                "date":day.strftime("%d/%m/%Y"),"bulletin":str(n),"type":t,"url":notice_url(e["code"])})
        data.append({"day":day,"number":str(n),"read":len(x["edicts"]),"notices":notices})
    feed=publish_audit(SOURCE,PROVINCE,data,today=today)
    feed["historyCoverage"]["method"]=("Sumario público de la portada guardado cada día desde el "
        "ejecutor de casa; los sumarios anteriores y los PDF piden verificación de Cloudflare y no se abren.")
    feed["historyCoverage"]["firstSeenUTC"]={d:issues[d].get("firstSeenUTC") for d,_ in rows}
    return feed,info

def report(info):
    print(f"MALAGA ventana {info['start']}–{info['end']}: {len(info['bops'])} BOP en el calendario, "
          f"{info['stored']} sumarios guardados en total",flush=True)
    if info["unknownDays"]:
        print(f"  días sin foto del calendario ({len(info['unknownDays'])}): {info['unknownDays'][0]} … {info['unknownDays'][-1]}",flush=True)
    if info["missingIssues"]:
        print(f"  boletines sin sumario guardado ({len(info['missingIssues'])}): {', '.join(info['missingIssues'][:8])}"
              +(" …" if len(info["missingIssues"])>8 else ""),flush=True)

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("orden",nargs="?",choices=("acumular","estado","feed"),default="feed")
    p.add_argument("--output",type=Path)
    p.add_argument("--estado",help="carpeta del estado (por defecto ~/OpoAlert-estado/malaga_bop)")
    p.add_argument("--sin-acumular",action="store_true",help="construir el feed sin leer la portada")
    a=p.parse_args(argv)
    folder=state_dir(a.estado)
    if a.orden=="acumular":
        accumulate(folder);return 0
    if a.orden=="estado":
        report(missing(folder,today_madrid()));return 0
    if a.output is None:p.error("falta --output")
    if not a.sin_acumular:accumulate(folder)
    feed,info=build(folder)
    report(info)
    if feed is None:
        print("ACUMULANDO: aún no hay 30 días completos; no se genera feed (regla 2: nunca un feed parcial)",flush=True)
        return STILL_ACCUMULATING
    write_output(a.output,feed)
    return 0

if __name__=="__main__":
    sys.exit(main())
