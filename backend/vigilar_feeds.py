"""Detecta lectores averiados sin esperar a que el feed se quede viejo.

Lo usa la tarea programada del iMac: si sale con código 0 no hay nada que hacer;
si sale con 1, imprime qué falla para que Claude lo arregle.

Un fallo suelto no es una avería (portales que cortan, la primera ronda del día…).
Se avisa cuando:
  - las **dos últimas lecturas** de una fuente han fallado, contando juntas las de
    GitHub y las del ejecutor de casa (las fuentes de respaldo fallan casi siempre
    en GitHub y se leen bien en casa: eso no es avería), o
  - algún feed lleva más de 30 horas laborables sin una lectura validada
    (lo mismo que comprueba `salud_feeds.py`).

Solo usa la API pública de GitHub, sin token (60 consultas por hora).

    python backend/vigilar_feeds.py [--json]

Códigos de salida: 0 todo bien, 1 hay avería, 2 no se pudo consultar GitHub
(límite de consultas o sin red; se vuelve a probar en la siguiente revisión).
"""
import argparse,json,re,sys,urllib.request
from datetime import datetime,timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parent))
import salud_feeds

API="https://api.github.com/repos/MJTBApps/OpoAlert/actions"
# Workflows que no leen boletines o que se cancelan a propósito.
IGNORE=("Publicar portada","Salud de los feeds")
RUNS_PER_WORKFLOW=2

def get(url):
    req=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json","User-Agent":"opoalert-vigilar"})
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.load(r)

def source_key(workflow,job):
    """Las fuentes de feeds_diarios van como «auditar (XX)» en varios workflows."""
    m=re.fullmatch(r"auditar \(([A-Z]{2,3})\)",job)
    return m.group(1) if m else f"{workflow} / {job}"

def attempts(runs,jobs_of):
    """Lista de (fuente, fecha, ok, paso fallido, url) a partir de las ejecuciones."""
    by_wf={}
    for r in runs:
        if r["status"]!="completed" or r["conclusion"] in ("cancelled","skipped"):continue
        if any(x in r["name"] for x in IGNORE):continue
        by_wf.setdefault(r["name"],[]).append(r)
    out=[]
    for name,rs in by_wf.items():
        for r in sorted(rs,key=lambda r:r["created_at"],reverse=True)[:RUNS_PER_WORKFLOW]:
            for j in jobs_of(r["id"]):
                if j["conclusion"] in ("cancelled","skipped",None):continue
                bad=[s["name"] for s in j.get("steps",[]) if s["conclusion"]=="failure"]
                if j["name"] in ("fuentes","publicar") and not bad:continue
                out.append((source_key(name,j["name"]),j.get("started_at") or r["created_at"],
                            not bad and j["conclusion"]=="success",", ".join(bad),j.get("html_url",r.get("html_url",""))))
    return out

def broken(items):
    """Fuentes cuyas dos lecturas más recientes han fallado."""
    by_src={}
    for it in items:by_src.setdefault(it[0],[]).append(it)
    res=[]
    for src,its in sorted(by_src.items()):
        its.sort(key=lambda x:x[1],reverse=True)
        if len(its)>=2 and not its[0][2] and not its[1][2]:
            res.append({"fuente":src,"ultimo_fallo":its[0][1],"paso":its[0][3],"log":its[0][4]})
    return res

def main():
    ap=argparse.ArgumentParser(description=__doc__,formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json",action="store_true")
    a=ap.parse_args()
    try:
        runs=get(f"{API}/runs?per_page=100")["workflow_runs"]
        jobs=lambda rid:get(f"{API}/runs/{rid}/jobs?per_page=100")["jobs"]
        rotos=broken(attempts(runs,jobs))
    except Exception as ex:
        print(f"No se pudo consultar GitHub: {ex}");sys.exit(2)
    viejos=salud_feeds.check(salud_feeds.ROOT/"docs",datetime.now(timezone.utc))
    if a.json:
        print(json.dumps({"lectores_rotos":rotos,"feeds_viejos":viejos},ensure_ascii=False,indent=1))
    else:
        for r in rotos:print(f"LECTOR ROTO {r['fuente']}: {r['paso']} ({r['ultimo_fallo']}) {r['log']}")
        for v in viejos:print(f"FEED VIEJO {v}")
        if not rotos and not viejos:print("Todo en orden")
    sys.exit(1 if rotos or viejos else 0)

if __name__=="__main__":
    main()
