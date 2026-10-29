#!/usr/bin/env python3
"""Independent fail-closed validation of BORM Murcia private Android snapshot."""
from __future__ import annotations
from datetime import datetime,date
from urllib.parse import urlsplit
from pathlib import Path
import argparse,json,re
SOURCE="https://transparencia.carm.es/rest-services/services/restFile/BORMIndice.json"
PROVINCE="Región de Murcia (BORM)"
def validate(root:Path):
    d=json.loads((root/"MU.json").read_text(encoding="utf-8"))
    c=d.get("coverage",{});h=d.get("historyCoverage",{})
    if (d.get("schemaVersion")!=1 or d.get("province")!=PROVINCE or d.get("source")!=SOURCE
        or c.get("complete") is not True or h.get("complete") is not True
        or c.get("status")!="complete" or h.get("rangeStart")!="2026-09-30"
        or h.get("rangeEnd")!="2026-10-29" or c.get("pagesVisited")!=26
        or c.get("announcementsRead")!=593 or h.get("announcementsRead")!=593
        or h.get("issuesRead")!=26 or c.get("opportunities")!=50 or h.get("opportunities")!=50):
        raise ValueError("MU: cobertura, rango o fuente oficial no verificados")
    checked=datetime.fromisoformat(d.get("lastCheckedUTC",""))
    if checked.tzinfo is None or checked.date()!=date(2026,10,29):
        raise ValueError("MU: fecha de auditoría incorrecta")
    dates=h.get("publicationDates",[]);bulletins=h.get("bulletins",[])
    if (len(dates)!=26 or len(bulletins)!=26 or dates!=sorted(dates) or
        len(set(dates))!=26 or dates[0]!="2026-09-30" or dates[-1]!="2026-10-29"
        or bulletins[0]!="226" or bulletins[-1]!="250" or bulletins.count("2E")!=1
        or set(bulletins)!={str(n) for n in range(226,251)}|{"2E"}):
        raise ValueError("MU: números de BORM incompletos o extraordinario no identificado")
    rows=d.get("notices",[])
    if len(rows)!=50 or len({r.get("id") for r in rows})!=50:
        raise ValueError("MU: anuncios candidatos duplicados o ausentes")
    for row in rows:
        u=urlsplit(row.get("url",""))
        try:date_text=datetime.strptime(row["date"],"%d/%m/%Y").date().isoformat()
        except Exception as e:raise ValueError("MU: anuncio con fecha incorrecta") from e
        if (not re.fullmatch(r"MU-2026-\d{1,8}",row.get("id",""))
            or not row.get("title","").strip() or not row.get("entity","").strip()
            or row.get("province")!=PROVINCE
            or row.get("type") not in ("Plaza / oposición","Bolsa de trabajo")
            or str(row.get("bulletin")) not in bulletins
            or date_text not in dates
            or u.scheme!="https" or u.hostname!="www.borm.es" or u.port not in (None,443)
            or u.username or u.fragment or u.query or
            not re.fullmatch(r"/services/anuncio/\d{5,9}/pdf",u.path)):
            raise ValueError("MU: anuncio o URL PDF original no acreditados")
    print("MURCIA VALIDADA: 26 ediciones (1 extraordinaria), 593 anuncios, 50 candidatas, intervalo de 30 días",flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    a=p.parse_args();validate(a.root)
