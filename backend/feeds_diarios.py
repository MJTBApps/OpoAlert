#!/usr/bin/env python3
"""Feeds diarios de los boletines de España: ejecutar lector, validar y publicar.

Cada fuente de SOURCES tiene un lector que audita sus últimos 30 días. Este
módulo lo ejecuta, comprueba el resultado con las MISMAS reglas que aplica la
app Android (leídas de Province.kt) y solo entonces lo copia a docs/ para
GitHub Pages. Nunca se publica un archivo parcial: si algo falla, se conserva
el feed anterior.

Uso:
  python backend/feeds_diarios.py matrix [--where casa]  # códigos para GitHub Actions o el PC de casa
  python backend/feeds_diarios.py run MD --out out       # lector + validación
  python backend/feeds_diarios.py validate MD out/madrid_bocm.json
  python backend/feeds_diarios.py publish out --docs docs
  python backend/feeds_diarios.py manifest --docs docs   # fuentes_activas.json para la app
"""
from __future__ import annotations
import argparse,collections,json,os,re,subprocess,sys,shutil
from datetime import date,datetime,timedelta,timezone
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[1]
PROVINCE_KT=ROOT/"app/src/main/java/es/opoalert/app/Province.kt"

# código -> (lector en backend/, argumentos extra, archivo publicado en docs/)
SOURCES={
    "HB":("huelva_bop.py",[],"huelva_bop.json"),
    "MD":("madrid_bocm.py",["--days","30"],"madrid_bocm.json"),
    "CR":("clm_ciudad_real.py",[],"ciudad_real_bop.json"),
    "GJ":("clm_guadalajara.py",[],"guadalajara_bop.json"),
    "TO":("clm_toledo.py",[],"toledo_bop.json"),
    "CM":("clm_docm.py",[],"castilla_mancha_docm.json"),
    "AV":("avila_bop.py",[],"avila_bop.json"),
    "LN":("leon_bop.py",[],"leon_bop.json"),
    "PL":("palencia_bop.py",[],"palencia_bop.json"),
    "ZM":("zamora_bop.py",[],"zamora_bop.json"),
    "SR":("soria_bop.py",[],"soria_bop.json"),
    "CY":("cyl_bocyl.py",[],"castilla_leon_bocyl.json"),
    "BD":("badajoz_bop.py",[],"badajoz_bop.json"),
    "CC":("caceres_bop.py",[],"caceres_bop.json"),
    "EX":("extremadura_doe.py",[],"extremadura_doe.json"),
    "MU":("murcia_borm.py",[],"murcia_borm.json"),
    "BI":("bizkaia_bob.py",[],"bizkaia_bob.json"),
    "GP":("gipuzkoa_bog.py",[],"gipuzkoa_bog.json"),
    "PV":("pais_vasco_bopv.py",[],"pais_vasco_bopv.json"),
    "AC":("galicia_coruna.py",[],"galicia_coruna.json"),
    "PO":("galicia_pontevedra.py",[],"galicia_pontevedra.json"),
    "OU":("galicia_ourense.py",[],"galicia_ourense.json"),
    "DG":("galicia_dog.py",[],"galicia_dog.json"),
    "DV":("dogv_autonomico.py",[],"valencia_dogv.json"),
    "AR":("alava_botha.py",[],"alava_botha.json"),
    "LU":("galicia_lugo.py",[],"galicia_lugo.json"),
    "IC":("canarias_boc.py",[],"canarias_boc.json"),
    "LP":("canarias_bop_provincial.py",["--province","lp"],"canarias_las_palmas.json"),
    "TF":("canarias_bop_provincial.py",["--province","tf"],"canarias_santa_cruz.json"),
    "RI":("rioja_bor.py",[],"rioja_bor.json"),
    "ML":("melilla_bome.py",[],"melilla_bome.json"),
    "IB":("baleares_boib.py",[],"baleares_boib.json"),
    "BJ":("boja_autonomico.py",[],"andalucia_boja.json"),
    "SA":("salamanca_bop.py",[],"salamanca_bop.json"),
    "SG":("segovia_bop.py",[],"segovia_bop.json"),
    "DC":("dogc_autonomico.py",[],"cataluna_dogc.json"),
    "AO":("boa_autonomico.py",[],"aragon_boa.json"),
    "NA":("navarra_bon.py",[],"navarra_bon.json"),
    "AS":("asturias_bopa.py",[],"asturias_bopa.json"),
    "CE":("ceuta_bocce.py",[],"ceuta_bocce.json"),
    "AB":("albacete_bop.py",[],"albacete_bop.json"),
    "CN":("cantabria_boc.py",[],"cantabria_boc.json"),
    "VD":("valladolid_bop.py",[],"valladolid_bop.json"),
    "BU":("burgos_bop.py",[],"burgos_bop.json"),
    "JA":("jaen_bop.py",[],"jaen_bop.json"),
    "LE":("lleida_bop.py",[],"lleida_bop.json"),
}
# Portales que no responden a los servidores de GitHub pero sí desde una
# conexión española: se leen con el ejecutor propio de casa
# (revisar-espana-casa.yml, ver EJECUTOR_CASA.md).
HOME_ONLY={"NA","AS","CE","AB","CN","VD","BU","JA","LE"}
# Se leen en GitHub y, como respaldo, también desde casa (fallan a ratos en GitHub).
HOME_BACKUP={"RI","CC"}
TYPES=("Bolsa de trabajo","Plaza / oposición")
# Sedes oficiales que sirven sus documentos en un puerto propio.
OFFICIAL_PORTS={"se1.dipucr.es":4443}
# Un feed nuevo con menos de esta fracción de anuncios que el anterior se
# considera una lectura incompleta del portal y no se publica.
MIN_RATIO_VS_PREVIOUS=0.5

class FeedError(Exception):pass

def fail(code,message):
    raise FeedError(f"{code}: {message}")

def annotate(title,text):
    """En GitHub Actions, el motivo del fallo como anotación visible sin iniciar sesión."""
    if os.environ.get("GITHUB_ACTIONS")=="true":
        body=text.replace("%","%25").replace("\r","").replace("\n","%0A")
        print(f"::error title={title}::{body}",flush=True)

def app_rules():
    """Reglas de cada fuente tal como las aplica Android (Province.kt)."""
    text=PROVINCE_KT.read_text(encoding="utf-8")
    entry=re.compile(r'\n\s{4}[A-Z_]+\(\s*"([A-Z]{2})",\s*"([^"]+)",\s*"([^"]+)",\s*"([^"]+)",'
                     r'\s*"([^"]+)",\s*"([^"]*)",\s*Regex\("((?:[^"\\]|\\.)*)"\)')
    rules={}
    for m in entry.finditer(text):
        code,label,feed,source,host,prefix,pattern=m.groups()
        rules[code]={"label":label,"feed":feed,"source":source,"host":host,"prefix":prefix,
                     "id":re.compile(pattern.replace("\\\\","\\"))}
    return rules

def validate(code,path,previous=None,today=None):
    rules=app_rules()
    if code not in rules:fail(code,"no figura en Province.kt")
    rule=rules[code]
    if Path(rule["feed"]).name!=SOURCES[code][2]:
        fail(code,f"Province.kt espera {rule['feed']}, el registro publica {SOURCES[code][2]}")
    try:data=json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception as ex:fail(code,f"JSON ilegible: {ex}")
    cov=data.get("coverage") or {};hist=data.get("historyCoverage") or {}
    if data.get("schemaVersion")!=1:fail(code,"schemaVersion distinto de 1")
    if data.get("province")!=rule["label"]:fail(code,f"provincia {data.get('province')!r} != {rule['label']!r}")
    if data.get("source")!=rule["source"]:fail(code,f"fuente {data.get('source')!r} != {rule['source']!r}")
    if cov.get("complete") is not True or cov.get("status")!="complete" or hist.get("complete") is not True:
        fail(code,"auditoría no marcada como completa")
    try:checked=datetime.fromisoformat(data.get("lastCheckedUTC",""))
    except ValueError:fail(code,"lastCheckedUTC ilegible")
    if checked.tzinfo is None or abs(datetime.now(timezone.utc)-checked)>timedelta(hours=36):
        fail(code,"comprobación sin zona horaria o de hace más de 36 horas")
    today=today or date.today()
    try:
        start=date.fromisoformat(hist["rangeStart"]);end=date.fromisoformat(hist["rangeEnd"])
    except Exception:fail(code,"periodo de fechas ausente")
    # 30 días; en enero, las fuentes cuyo archivo oficial empieza cada año de cero
    # cubren del 1 de enero a hoy.
    if not ((end-start).days==29 or (start==date(end.year,1,1) and (end-start).days<29)):
        fail(code,f"el periodo no es de 30 días: {start}–{end}")
    if not 0<=(today-end).days<=1:fail(code,f"el periodo termina el {end}, no hoy ({today})")
    dates=hist.get("publicationDates");numbers=hist.get("bulletins")
    if not isinstance(dates,list) or not isinstance(numbers,list) or not dates or len(dates)!=len(numbers):
        fail(code,"lista de ediciones ausente o descuadrada")
    try:days=[date.fromisoformat(d) for d in dates]
    except Exception:fail(code,"fecha de edición ilegible")
    if days!=sorted(days) or days[0]<start or days[-1]>end:fail(code,"ediciones fuera de orden o del periodo")
    if (days[0]-start).days>4 or (end-days[-1]).days>4:fail(code,"faltan ediciones al principio o al final")
    if len(set(zip(dates,map(str,numbers))))!=len(dates):fail(code,"edición duplicada")
    issues=len(dates)
    # pagesVisited puede incluir páginas de control (p. ej. el boletín anterior a la ventana).
    if not isinstance(cov.get("pagesVisited"),int) or cov["pagesVisited"]<issues or hist.get("issuesRead")!=issues:
        fail(code,"contador de ediciones incoherente")
    read=cov.get("announcementsRead")
    if not isinstance(read,int) or read<issues or hist.get("announcementsRead")!=read:
        fail(code,"contador de anuncios incoherente")
    notices=data.get("notices")
    if not isinstance(notices,list) or not notices:fail(code,"sin anuncios candidatos")
    if cov.get("opportunities")!=len(notices) or hist.get("opportunities")!=len(notices):
        fail(code,"contador de candidatas incoherente")
    seen=set();bulletins=set(map(str,numbers));dateset=set(dates)
    for n in notices:
        ident=n.get("id","")
        if not rule["id"].fullmatch(ident):fail(code,f"identificador {ident!r} fuera del patrón de la app")
        if ident in seen:fail(code,f"anuncio duplicado {ident}")
        seen.add(ident)
        if n.get("province")!=rule["label"] or n.get("type") not in TYPES:fail(code,f"{ident}: provincia o tipo")
        if not str(n.get("title","")).strip() or not str(n.get("entity","")).strip():fail(code,f"{ident}: sin título u organismo")
        try:day=datetime.strptime(n.get("date",""),"%d/%m/%Y").date()
        except ValueError:fail(code,f"{ident}: fecha ilegible")
        if day.isoformat() not in dateset or str(n.get("bulletin")) not in bulletins:
            fail(code,f"{ident}: fecha o boletín que no están entre las ediciones leídas")
        u=urlsplit(n.get("url",""))
        if (u.scheme!="https" or u.hostname!=rule["host"] or u.port not in (None,443,OFFICIAL_PORTS.get(u.hostname))
            or u.username or not u.path.startswith(rule["prefix"])):
            fail(code,f"{ident}: enlace fuera del documento oficial ({n.get('url','')[:120]})")
    if previous and Path(previous).exists():
        try:
            old=json.loads(Path(previous).read_text(encoding="utf-8"))
            old_read=old["coverage"]["announcementsRead"];old_issues=old["historyCoverage"]["issuesRead"]
        except Exception:old_read=old_issues=None
        if old_read and read<MIN_RATIO_VS_PREVIOUS*old_read:
            fail(code,f"solo {read} anuncios frente a {old_read} en el feed anterior: lectura incompleta")
        if old_issues and issues<old_issues-5:
            fail(code,f"solo {issues} ediciones frente a {old_issues} en el feed anterior")
    return {"code":code,"label":rule["label"],"issues":issues,"read":read,"notices":len(notices),
            "range":f"{start}–{end}"}

def run(code,out,docs=None):
    script,extra,feed=SOURCES[code]
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    target=out/feed
    cmd=[sys.executable,"-u",str(ROOT/"backend"/script),*extra,"--output",str(target)]
    print("$"," ".join(cmd),flush=True)
    tail=collections.deque(maxlen=12)
    with subprocess.Popen(cmd,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                          text=True,encoding="utf-8",errors="replace",
                          env={**os.environ,"PYTHONIOENCODING":"utf-8"}) as proc:
        for line in proc.stdout:
            print(line,end="",flush=True)
            tail.append(line.rstrip()[:400])
    rc=proc.returncode
    if rc!=0 or not target.exists():
        target.unlink(missing_ok=True)
        annotate(f"Lector {code}","\n".join(tail))
        fail(code,f"el lector terminó con error ({rc}); se conserva el feed anterior")
    try:
        result=validate(code,target,previous=Path(docs or ROOT/"docs")/feed)
    except FeedError:
        target.unlink(missing_ok=True)
        raise
    print(f"VALIDADO {code} {result['label']}: {result['issues']} ediciones, {result['read']} anuncios, "
          f"{result['notices']} candidatas, {result['range']}",flush=True)
    return result

def publish(out,docs):
    out=Path(out);docs=Path(docs);done=[];rejected=[]
    for code,(_,_,feed) in SOURCES.items():
        src=out/feed
        if not src.exists():continue
        try:
            result=validate(code,src,previous=docs/feed)
        except FeedError as ex:
            rejected.append(str(ex));continue
        shutil.copyfile(src,docs/feed)
        done.append(result)
    for r in done:
        print(f"PUBLICADO {r['code']} {r['label']}: {r['issues']} ediciones, {r['read']} anuncios, {r['notices']} candidatas")
    for r in rejected:print("RECHAZADO",r)
    return done,rejected

def manifest(docs):
    """docs/fuentes_activas.json: fuentes con feed publicado. La app lo lee
    para mostrar las fuentes nuevas sin tener que instalar otra APK."""
    docs=Path(docs);rules=app_rules();active=[]
    for code,rule in sorted(rules.items()):
        if (docs/Path(rule["feed"]).name).exists():active.append(code)
    out=docs/"fuentes_activas.json"
    out.write_text(json.dumps({"schemaVersion":1,
        "updatedUTC":datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "active":active},ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
    print(f"MANIFIESTO {len(active)} fuentes activas: {' '.join(active)}")
    # version.json: la APK más reciente publicada; la app avisa de que hay una nueva.
    versions=[tuple(map(int,m.groups())) for p in docs.glob("OpoAlert-*.apk")
              if (m:=re.fullmatch(r"OpoAlert-(\d+)\.(\d+)\.(\d+)\.apk",p.name))]
    if versions:
        latest=".".join(map(str,max(versions)))
        (docs/"version.json").write_text(json.dumps({"schemaVersion":1,"latestVersion":latest,
            "apk":f"OpoAlert-{latest}.apk"},ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
        print(f"VERSIÓN publicada: {latest}")
    return active

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    sub=ap.add_subparsers(dest="cmd",required=True)
    mx=sub.add_parser("matrix");mx.add_argument("--where",choices=("github","casa"),default="github")
    r=sub.add_parser("run");r.add_argument("code",choices=sorted(SOURCES));r.add_argument("--out",required=True);r.add_argument("--docs")
    v=sub.add_parser("validate");v.add_argument("code",choices=sorted(SOURCES));v.add_argument("file");v.add_argument("--previous")
    p=sub.add_parser("publish");p.add_argument("out");p.add_argument("--docs",default=str(ROOT/"docs"))
    m=sub.add_parser("manifest");m.add_argument("--docs",default=str(ROOT/"docs"))
    a=ap.parse_args()
    try:
        if a.cmd=="matrix":
            codes=(set(SOURCES)-HOME_ONLY) if a.where=="github" else (HOME_ONLY|HOME_BACKUP)&set(SOURCES)
            print(json.dumps(sorted(codes)))
        elif a.cmd=="manifest":manifest(a.docs)
        elif a.cmd=="run":run(a.code,a.out,a.docs)
        elif a.cmd=="validate":print(json.dumps(validate(a.code,a.file,a.previous),ensure_ascii=False))
        elif a.cmd=="publish":
            done,rejected=publish(a.out,a.docs)
            if not done and rejected:sys.exit(1)
    except FeedError as ex:
        annotate("Feed rechazado",str(ex))
        print("ERROR",ex,file=sys.stderr);sys.exit(1)

if __name__=="__main__":
    main()
