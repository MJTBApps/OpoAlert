#!/usr/bin/env python3
"""Fail-closed verification of BOJA and Aragón BOA from official audit snapshots."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from datetime import datetime,date
from urllib.parse import urlsplit,parse_qs
SOURCES={
 "BJ":("Andalucía (BOJA)","https://www.juntadeandalucia.es/eboja/index.html","www.juntadeandalucia.es",21,1480,390,190,210),
 "AO":("Aragón (BOA)","https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI","www.boa.aragon.es",21,None,None,190,210),
}
def valid_pdf(code,row,u):
    if code=="BJ":
        m=re.fullmatch(r"/eboja/2026/(\d{3})/BOJA26-(\d{3})-[A-Za-z0-9-]+_(\d{8})\.pdf",u.path)
        return bool(m and m[1]==m[2]==str(row["bulletin"])
         and row["id"]==f"BJ-2026-{m[3]}")
    if code=="AO":
        qs=parse_qs(u.query)
        return (u.path=="/cgi-bin/EBOA/BRSCGI"
          and set(qs)=={"CMD","MLKOB"}
          and qs["CMD"]==["VEROBJ"]
          and len(qs["MLKOB"])==1
          and re.fullmatch(r"\d{9,18}",qs["MLKOB"][0]) is not None
          and re.fullmatch(r"AO-2026-\d{9}",row["id"]) is not None)
    return False
def audit(root:Path):
    total_i=total_r=total_n=0
    for code,(province,source,host,issues,expected_read,expected_candidates,num_first,num_last) in SOURCES.items():
        data=json.loads((root/(code+".json")).read_text(encoding="utf-8"))
        c=data.get("coverage",{});h=data.get("historyCoverage",{})
        if (data.get("schemaVersion")!=1 or data.get("province")!=province
            or data.get("source")!=source or c.get("complete") is not True
            or h.get("complete") is not True or c.get("status")!="complete"
            or h.get("rangeStart")!="2026-09-30" or h.get("rangeEnd")!="2026-10-29"
            or c.get("pagesVisited")!=issues or h.get("issuesRead")!=issues):
            raise ValueError(f"{code}: fuente oficial y rango histórico no acreditados")
        checked=datetime.fromisoformat(data.get("lastCheckedUTC",""))
        if checked.tzinfo is None or checked.date()!=date(2026,10,29):
            raise ValueError(f"{code}: auditoría de otra fecha")
        numbers=h.get("bulletins",[]);days=h.get("publicationDates",[])
        if (len(numbers)!=issues or len(days)!=issues
            or numbers[0]!=str(num_first) or numbers[-1]!=str(num_last)
            or any(int(b)!=int(a)+1 for a,b in zip(numbers,numbers[1:]))
            or days!=sorted(days) or len(set(days))!=issues
            or days[0]!="2026-09-30" or days[-1]!="2026-10-29"):
            raise ValueError(f"{code}: faltan números o días de publicación")
        read=c.get("announcementsRead")
        notices=data.get("notices",[])
        if (not isinstance(read,int) or read<400 or h.get("announcementsRead")!=read
            or expected_read is not None and read!=expected_read
            or not isinstance(notices,list) or len(notices)<15 or len(notices)>=read
            or len(notices)!=c.get("opportunities") or len(notices)!=h.get("opportunities")
            or expected_candidates is not None and len(notices)!=expected_candidates):
            raise ValueError(f"{code}: recuentos de anuncios y candidatas incongruentes")
        seen=set()
        for row in notices:
            name=row.get("id",""); u=urlsplit(row.get("url",""))
            try:day=datetime.strptime(row["date"],"%d/%m/%Y").date().isoformat()
            except Exception as e:raise ValueError(f"{code}: fecha inválida") from e
            if (name in seen or not name.startswith(code+"-2026-")
                or row.get("province")!=province
                or row.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
                or not row.get("entity","").strip() or not row.get("title","").strip()
                or str(row.get("bulletin")) not in numbers
                or day not in days or u.scheme!="https" or u.hostname!=host
                or u.port not in (None,443) or u.username or u.fragment
                or not valid_pdf(code,row,u)):
                raise ValueError(f"{code}: anuncio o PDF original incorrectos {name}")
            seen.add(name)
        total_i+=issues;total_r+=read;total_n+=len(notices)
        print(f"CIERRE VALIDADO {code}: {issues} ediciones, {read} anuncios, {len(notices)} candidatas",flush=True)
    print(f"CIERRE AUTONÓMICO OK: {total_i} ediciones, {total_r} anuncios, {total_n} posibles convocatorias",flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",required=True,type=Path)
    a=p.parse_args();audit(a.root)
