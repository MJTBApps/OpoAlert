#!/usr/bin/env python3
"""Independent strict check of official BOPMA 30-day summaries for private APK.

Does NOT claim PDF bytes were downloaded. Official verificacion.php requires
human Turnstile and its links are only verified against publisher's own
edict pages. This validator fails if fewer than all 22 BOPMA editions exist.
"""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from datetime import datetime,date,timedelta
from urllib.parse import urlsplit,parse_qs

SOURCE="https://www.bopmalaga.es/sumario.php"
def bad(s):raise ValueError("BOP Málaga: "+str(s))
def main(root):
    path=root/"MA.json"
    j=json.loads(path.read_text(encoding="utf-8"))
    c=j.get("coverage",{});h=j.get("historyCoverage",{})
    if j.get("schemaVersion")!=1 or j.get("province")!="Málaga" or j.get("source")!=SOURCE:
        bad("origen o esquema incorrectos")
    if c.get("complete") is not True or h.get("complete") is not True:
        bad("histórico no auditado")
    if (h.get("rangeStart"),h.get("rangeEnd"))!=("2026-09-30","2026-10-29"):
        bad("intervalo de 30 días incorrecto")
    days=[date.fromisoformat(x) for x in h.get("publicationDates",[])]
    nums=list(map(int,h.get("bulletins",[])))
    if (len(days)!=22 or len(set(days))!=22 or days!=sorted(days)
        or days[0]!=date(2026,9,30) or days[-1]!=date(2026,10,29)
        or nums!=list(range(188,210))
        or c.get("pagesVisited")!=22 or h.get("issuesRead")!=22 or c.get("bulletin")!="209"):
        bad("hueco o duplicado de boletín oficial")
    original=h.get("editionsPDFLinks",[])
    if len(original)<22 or len(set(original))!=len(original):
        bad("faltan enlaces a originales de ediciones oficiales")
    for u in original:
        parsed=urlsplit(u);query=parse_qs(parsed.query)
        if (parsed.scheme!="https" or parsed.hostname!="www.bopmalaga.es"
            or parsed.path!="/verificacion.php" or set(query)!={"archivo"}
            or len(query["archivo"])!=1
            or not re.fullmatch(r"\d{6}\d{2,3}(?:a\d{2})?\.pdf",query["archivo"][0])):
            bad("enlace de PDF de edición fuera del dominio editor: "+u)
    if "Turnstile" not in h.get("pdfAccess",""):
        bad("No se ha declarado la limitación de acceso al PDF (Turnstile)")
    notices=j.get("notices",[])
    if (not notices or len(notices)!=c.get("opportunities")
        or len(notices)!=h.get("opportunities")
        or len({n["id"] for n in notices})!=len(notices)):
        bad("avisos o contadores inconsistentes")
    for n in notices:
        u=urlsplit(n.get("url",""));q=parse_qs(u.query)
        m=re.fullmatch(r"MA-(\d{8})-(\d{5})",n.get("id",""))
        if not m:bad("id fuera del esquema: "+str(n.get("id")))
        day=datetime.strptime(n.get("date",""),"%d/%m/%Y").date()
        if (day not in days or m[1]!=day.strftime("%Y%m%d")
            or n.get("bulletin")!=str(nums[days.index(day)])
            or n.get("province")!="Málaga"
            or n.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
            or not 5<len(n.get("title","").strip())<2000
            or not 5<len(n.get("entity","").strip())<500):
            bad("aviso inconsistente")
        if (u.scheme!="https" or u.hostname!="www.bopmalaga.es" or
            u.path!="/verificacion.php" or set(q)!={"archivo"}
            or len(q["archivo"])!=1
            or not re.fullmatch(rf"{m[1]}-{m[2]}-2026-\d{{2}}\.pdf",q["archivo"][0])):
            bad("aviso sin URL PDF oficial cotejada")
    if c.get("announcementsRead",0)<120 or c.get("announcementsRead")!=h.get("announcementsRead"):
        bad("recuento de todos los sumarios insuficiente")
    print("BOPMA VALIDADO: 22 ediciones y "+str(c["announcementsRead"])+" sumarios, "+
          str(len(notices))+" candidatas; PDF original con validación humana necesaria",flush=True)
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True)
    a=ap.parse_args();main(a.root)
