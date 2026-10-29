#!/usr/bin/env python3
"""Private APK DOGV verification: full 30-day official calendar and bis/ter/quarter."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from datetime import date,datetime
from urllib.parse import urlsplit
SOURCE="https://dogv.gva.es/dogv-portal/dogv"
NAME="Comunidad Valenciana (DOGV)"
PDF_RE=re.compile(r"^/datos/2026/(\d{2})/(\d{2})/pdf/2026_(\d{1,8})_es\.pdf$")
def validate(root:Path):
    obj=json.loads((root/"DV.json").read_text(encoding="utf-8"))
    c=obj.get("coverage",{});h=obj.get("historyCoverage",{})
    if (obj.get("schemaVersion")!=1 or obj.get("province")!=NAME or obj.get("source")!=SOURCE
        or c.get("complete") is not True or h.get("complete") is not True or c.get("status")!="complete"
        or h.get("rangeStart")!="2026-09-30" or h.get("rangeEnd")!="2026-10-29"):
        raise ValueError("DOGV: fuente oficial o intervalo no verificado")
    stamp=datetime.fromisoformat(obj.get("lastCheckedUTC",""))
    if stamp.tzinfo is None or stamp.date()!=date(2026,10,29):raise ValueError("DOGV: fecha de auditoría errónea")
    dates=h.get("publicationDates",[]);nums=h.get("bulletins",[])
    count=h.get("issuesRead")
    if (not isinstance(count,int) or count<21 or count>35 or c.get("pagesVisited")!=count
        or len(dates)!=count or len(nums)!=count
        or dates!=sorted(dates) or dates[0]!="2026-09-30" or dates[-1]!="2026-10-29"
        or nums[0]!="10462" or nums[-1]!="10482" or len(set(nums))!=count):
        raise ValueError("DOGV: faltan números, bis o fechas del mes")
    main=[int(n) for n in nums if re.fullmatch(r"\d+",str(n))]
    if len(main)!=21 or main!=list(range(10462,10483)):
        raise ValueError("DOGV: ediciones ordinarias de 30 días no consecutivas")
    if not any(n.endswith("B") for n in nums) or not any(n.endswith("T") for n in nums) or not any(n.endswith("Q") for n in nums):
        raise ValueError("DOGV: falta boletín extraordinario bis, ter o quarter")
    notice=obj.get("notices",[])
    read=c.get("announcementsRead")
    if (not isinstance(read,int) or read<850 or read!=h.get("announcementsRead")
        or not isinstance(notice,list) or len(notice)<120
        or len(notice)!=c.get("opportunities") or len(notice)!=h.get("opportunities")
        or len({n.get("id") for n in notice})!=len(notice)):
        raise ValueError("DOGV: contadores de disposiciones no coherentes")
    for row in notice:
        url=urlsplit(row.get("url",""));ident=row.get("id","")
        try:day=datetime.strptime(row["date"],"%d/%m/%Y").date()
        except Exception as e:raise ValueError("DOGV: fecha del anuncio incorrecta") from e
        m=PDF_RE.fullmatch(url.path)
        if (not re.fullmatch(r"DV-2026-\d{1,8}",ident)
            or not m or int(m[1])!=day.month or int(m[2])!=day.day
            or int(m[3])!=int(ident[8:])
            or row.get("province")!=NAME or row.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
            or not row.get("title","").strip() or not row.get("entity","").strip()
            or day.isoformat() not in dates or str(row.get("bulletin")) not in nums
            or url.scheme!="https" or url.hostname!="dogv.gva.es" or url.port not in (None,443)
            or url.fragment or url.query or url.username):
            raise ValueError(f"DOGV: anuncio original no acreditado {ident}")
    print(f"DOGV VERIFICADO: {len(main)} boletines ordinarios + {count-len(main)} versiones extraordinarias, {read} anuncios, {len(notice)} candidatas",flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",type=Path,required=True)
    args=p.parse_args();validate(args.root)
