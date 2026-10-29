#!/usr/bin/env python3
"""Independent fail-closed verification of CyL private APK snapshots; not for Pages."""
import json,re,argparse
from pathlib import Path
from urllib.parse import urlsplit
from datetime import datetime,date,timedelta,timezone

SOURCES={
 "AV":("Ávila","https://www.diputacionavila.es/boletin-oficial/2026/","www.diputacionavila.es","/bops/2026/",r"AV-\d{4}-\d{1,7}",22,226,4),
 "LN":("León","https://bop.dipuleon.es/publica/consulta-de-bops/","bop.dipuleon.es","/export/sites/bop/.galleries/Documentos-Anuncios-en-PDF/",r"LN-\d{4}-\d{6}",20,531,32),
 "ZM":("Zamora","https://www.diputaciondezamora.es/opencms/servicios/BOP/busqueda-en-el-bop/","www.diputaciondezamora.es","/opencms/export/sites/dipu-zamora/servicios/BOP/.Archivos/documentos/BOP/anuncios/",r"ZM-\d{9}",14,225,4),
 "SR":("Soria","https://bop.dipsoria.es/index.php/mod.boloficial/relmenu.149","bop.dipsoria.es","/index.php/mod.documentos/mem.descargar/fichero.documentos_",r"SR-\d{4}-\d{1,6}",11,257,3),
 "CY":("Castilla y León (BOCYL)","https://bocyl.jcyl.es/","bocyl.jcyl.es","/boletines/",r"CY-\d{8}-\d{1,4}",21,869,205),
}
def validate(root):
    total=0;allread=0
    for code,(name,source,host,prefix,pattern,expected_issues,expected_read,expected_candidates) in SOURCES.items():
        path=root/f"{code}.json"
        d=json.loads(path.read_text(encoding="utf-8"))
        h=d.get("historyCoverage",{});c=d.get("coverage",{})
        if (d.get("province")!=name or d.get("source")!=source or c.get("complete") is not True
           or h.get("complete") is not True or c.get("status")!="complete"
           or h.get("rangeStart")!="2026-09-30" or h.get("rangeEnd")!="2026-10-29"
           or h.get("issuesRead")!=expected_issues or
           c.get("announcementsRead")!=expected_read or
           h.get("announcementsRead")!=expected_read):
            raise ValueError(f"{code}: origen o alcance no auditado")
        stamp=datetime.fromisoformat(d["lastCheckedUTC"])
        if stamp.tzinfo is None or not date(2026,10,29)==stamp.date():raise ValueError(f"{code}: fecha auditoría incorrecta")
        notice=d.get("notices",[])
        if len(notice)!=expected_candidates or len({x["id"] for x in notice})!=len(notice):
            raise ValueError(f"{code}: candidatas no coinciden con auditoría")
        dates=h.get("publicationDates",[]);nums=h.get("bulletins",[])
        if len(dates)!=expected_issues or len(nums)!=expected_issues or dates!=sorted(set(dates)):
            raise ValueError(f"{code}: calendario incoherente")
        for n in notice:
            u=urlsplit(n.get("url",""))
            if not (re.fullmatch(pattern,n.get("id",""))
                and n.get("province")==name and n.get("type") in ("Plaza / oposición","Bolsa de trabajo")
                and n.get("title","").strip() and n.get("entity","").strip()
                and u.scheme=="https" and u.hostname==host and u.path.startswith(prefix)
                and u.username is None and not u.query):
                raise ValueError(f"{code}: registro o PDF original ajeno al BOP")
        total+=len(notice);allread+=expected_read
        print(f"CYL VERIFICADO {code}: {expected_issues} boletines, {expected_read} anuncios, {len(notice)} candidatas",flush=True)
    print(f"CYL VALIDA: 5 fuentes, {allread} anuncios, {total} candidatas",flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True);a=p.parse_args();validate(a.root)
