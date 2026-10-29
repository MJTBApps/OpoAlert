#!/usr/bin/env python3
"""Independent offline checks for BOP Salamanca private APK snapshot."""
from __future__ import annotations
import argparse,json,re
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit
SOURCE="https://www.lasalina.es/documentacion/bop/"
def fail(msg):raise ValueError("Salamanca: "+str(msg))
def check(root):
    x=json.loads((root/"SA.json").read_text(encoding="utf-8"))
    c=x.get("coverage",{});h=x.get("historyCoverage",{})
    if (x.get("schemaVersion")!=1 or x.get("source")!=SOURCE or x.get("province")!="Salamanca" or
        c.get("complete") is not True or h.get("complete") is not True):
        fail("fuente oficial o auditoría incompleta")
    if (h.get("rangeStart"),h.get("rangeEnd"))!=("2026-09-30","2026-10-29"):
        fail("rango temporal incorrecto")
    days=[date.fromisoformat(x) for x in h.get("publicationDates",[])]
    start=date(2026,9,30)
    expected=[start+timedelta(days=i) for i in range(30) if (start+timedelta(days=i)).weekday()<5]
    nums=list(map(int,h.get("bulletins",[])))
    if (days!=expected or nums!=list(range(189,211)) or c.get("bulletin")!="210"
        or h.get("issuesRead")!=22 or c.get("pagesVisited")!=22):
        fail("hay huecos o boletines duplicados")
    summary=h.get("summaryPDFs",[]);counts=h.get("CVECounts",[])
    if (len(summary)!=22 or len(set(summary))!=22 or len(counts)!=22 or
        any(not isinstance(v,int) or v<1 or v>150 for v in counts)):
        fail("faltan sumarios originales CVE")
    if (sum(counts)!=c.get("announcementsRead") or
        sum(counts)!=h.get("announcementsRead") or
        sum(counts)!=h.get("originalPDFsChecked") or sum(counts)<200):
        fail("no hay evidencia de todas las publicaciones oficiales")
    for day,u in zip(days,summary):
        want=f"https://www.lasalina.es/documentacion/bop/2026/{day:%Y%m%d}/BOP-SA-{day:%Y%m%d}-000.pdf"
        if u!=want:fail("enlace sumario ajeno a fecha")
    n=x.get("notices",[])
    if not n or len(n)!=c.get("opportunities") or len(n)!=h.get("opportunities"):
        fail("candidatas inconsistentes")
    ids=set()
    for it in n:
        m=re.fullmatch(r"SA-(\d{8})-(\d{3})",it.get("id",""))
        if m is None or it["id"] in ids:fail("id mal formado o duplicado")
        ids.add(it["id"])
        d=datetime.strptime(it["date"],"%d/%m/%Y").date()
        if d not in days or m[1]!=d.strftime("%Y%m%d") or int(m[2])>counts[days.index(d)]:
            fail("anuncio no pertenece a boletín")
        if it.get("bulletin")!=str(nums[days.index(d)]) or it.get("province")!="Salamanca":
            fail("provincia o número inconsistente")
        if it.get("type") not in ("Plaza / oposición","Bolsa de trabajo"):
            fail("clasificación inesperada")
        if not 5<len(str(it.get("title","")).strip())<=1300 or not 4<len(str(it.get("entity","")).strip())<500:
            fail("título o entidad vacíos")
        want=f"https://www.lasalina.es/documentacion/bop/2026/{d:%Y%m%d}/BOP-SA-{d:%Y%m%d}-{int(m[2]):03d}.pdf"
        if it.get("url")!=want:fail("PDF ajeno al CVE oficial")
    print(f"BOPSA VALIDADO: 22 sumarios PDF, {sum(counts)} anuncios con enlaces originales contrastados, {len(n)} candidatas",flush=True)
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True);a=ap.parse_args();check(a.root)
