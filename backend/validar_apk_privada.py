#!/usr/bin/env python3
"""Validate private Android embedded feeds; never publish to docs or GitHub Pages."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from datetime import date,datetime,timedelta
from urllib.parse import urlsplit
SOURCES={
 "MD":("Madrid","https://www.bocm.es/listado-de-boletines","www.bocm.es",r"^MD-\d{8}-\d{1,5}$",316),
 "HB":("Huelva","https://s2.diphuelva.es/servicios/bope_web/busquedaCalendario","s2.diphuelva.es",r"^HB-\d{4}-\d{1,8}$",43),
 "CR":("Ciudad Real","https://bop.dipucr.es/","se1.dipucr.es",r"^CR-\d{4}-\d{1,8}$",26),
 "GJ":("Guadalajara","https://boletin.dguadalajara.es/boletin/","boletin.dguadalajara.es",r"^GJ-\d{4}-\d{1,8}$",12),
 "TO":("Toledo","https://bop.diputoledo.es/webEbop/","bop.diputoledo.es",r"^TO-\d{4}-\d{1,8}$",33),
 "CM":("Castilla-La Mancha (DOCM)","https://docm.jccm.es/docm/","docm.jccm.es",r"^CM-\d{4}-\d{1,8}$",31),
}
def validate(root:Path):
    grand=0
    for code,(province,source,host,pattern,count) in SOURCES.items():
        path=root/f"{code}.json"
        data=json.loads(path.read_text(encoding="utf-8"))
        coverage=data.get("coverage",{})
        history=data.get("historyCoverage",{})
        if (data.get("province")!=province or data.get("source")!=source
            or coverage.get("complete") is not True or history.get("complete") is not True
            or coverage.get("status")!="complete"
            or history.get("rangeStart")!="2026-09-30" or history.get("rangeEnd")!="2026-10-29"):
            raise ValueError(f"{code}: fuente o intervalo no auditado")
        rows=data.get("notices",[])
        if len(rows)!=count or len({r["id"] for r in rows})!=len(rows):
            raise ValueError(f"{code}: recuentos de candidatas incorrectos")
        if coverage.get("opportunities")!=count or coverage.get("announcementsRead",0)<count:
            raise ValueError(f"{code}: estadísticas incoherentes")
        for n in rows:
            u=urlsplit(n.get("url",""))
            if (not re.fullmatch(pattern,n.get("id",""))
                or n.get("province")!=province or n.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
                or not n.get("entity","").strip() or not n.get("title","").strip()
                or u.scheme!="https" or u.hostname!=host or u.fragment or u.username):
                raise ValueError(f"{code}: anuncio o enlace no comprobado")
        print(f"APK PRIVADA {code}: {len(rows)} convocatorias, {coverage['announcementsRead']} anuncios",flush=True)
        grand+=count
    print(f"APK PRIVADA VALIDADA: 6 fuentes, {grand} candidatas y 30 días desde boletines oficiales",flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",required=True,type=Path)
    x=p.parse_args();validate(x.root)
