#!/usr/bin/env python3
"""One entrypoint for all five Castilla-La Mancha provinces and autonomous DOCM.

No feed is published or labelled complete until each source passes its independent
official archive audit. Provinces with blocked official portals stay pending.
"""
from __future__ import annotations
import argparse,json,concurrent.futures
from pathlib import Path
from datetime import datetime,timezone
from clm_common import write_output
from clm_ciudad_real import audit as audit_cr
from clm_docm import audit as audit_docm
from clm_guadalajara import audit as audit_gj
from clm_toledo import audit as audit_toledo

SOURCES=[
  ("Albacete","albacete_bop.json",None,"No se puede verificar el histórico: el servidor BOP Albacete agota conexiones externas."),
  ("Ciudad Real","ciudad_real_bop.json",audit_cr,None),
  ("Cuenca","cuenca_bop.json",None,"El BOP de la Diputación de Cuenca responde con bloqueo F5/403 a consultas automatizadas."),
  ("Guadalajara","guadalajara_bop.json",audit_gj,None),
  ("Toledo","toledo_bop.json",audit_toledo,None),
  ("Castilla-La Mancha (DOCM)","castilla_mancha_docm.json",audit_docm,None)
]
def run_source(spec):
    label,filename,func,reason=spec
    if func is None:return label,{"state":"blocked","reason":reason,"file":filename}
    try:
        feed=func()
        return label,{"state":"verified","feed":feed,"file":filename}
    except Exception as e:
        return label,{"state":"failed","reason":str(e)[:650],"file":filename}
def main(output_dir):
    output_dir.mkdir(parents=True,exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        results=dict(pool.map(run_source,SOURCES))
    statuses={}
    for label,filename,func,reason in SOURCES:
        res=results[label]
        if res["state"]=="verified":
            feed=res["feed"]
            write_output(output_dir/filename,feed)
            statuses[label]={"state":"verified","issuesRead":feed["historyCoverage"]["issuesRead"],
                "announcementsRead":feed["coverage"]["announcementsRead"],
                "opportunities":len(feed["notices"]),"filename":filename}
        else:statuses[label]={"state":res["state"],"reason":res["reason"]}
    complete=all(x["state"]=="verified" for x in statuses.values())
    report={"community":"Castilla-La Mancha","complete":complete,
      "checkedUTC":datetime.now(timezone.utc).isoformat(),"sources":statuses}
    (output_dir/"estado_clm.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print("CASTILLA-LA MANCHA COMPLETA" if complete else "CASTILLA-LA MANCHA PARCIAL / SIN PUBLICAR",flush=True)
    for label,v in statuses.items():print(label,v,flush=True)
    return 0 if complete else 2
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--output-dir",type=Path,default=Path("auditados"))
    a=p.parse_args()
    raise SystemExit(main(a.output_dir))
