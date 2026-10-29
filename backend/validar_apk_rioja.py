#!/usr/bin/env python3
"""Independent offline validation of OpoAlert private BOR 30-day snapshot."""
import argparse
import json
import re
from pathlib import Path
from datetime import date,datetime
from urllib.parse import urlsplit,parse_qs
SOURCE="https://ias1.larioja.org/boletin/ExportarBoletinServlet"
PROVINCE="La Rioja (BOR)"
def validate(root):
    data=json.loads((root/"RI.json").read_text(encoding="utf-8"))
    cov=data.get("coverage",{});history=data.get("historyCoverage",{})
    if data.get("schemaVersion")!=1 or data.get("source")!=SOURCE or data.get("province")!=PROVINCE or cov.get("complete") is not True or history.get("complete") is not True:
        raise ValueError("BOR: esquema, origen o cobertura incompleta")
    if (history.get("rangeStart"),history.get("rangeEnd"))!=("2026-09-30","2026-10-29"):
        raise ValueError("BOR: intervalo distinto de 30 días")
    nums=[int(x) for x in history.get("bulletins",[])]
    if nums!=list(range(188,210)) or history.get("issuesRead")!=22 or cov.get("pagesVisited")!=22:
        raise ValueError("BOR: falta una edición oficial del 30/09 al 29/10")
    if cov.get("bulletin")!="209" or cov.get("announcementsRead",0)<250:
        raise ValueError("BOR: contadores insuficientes")
    if history.get("announcementsRead")!=cov.get("announcementsRead"):
        raise ValueError("BOR: sumario y cobertura no coinciden")
    dates=history.get("publicationDates",[])
    if len(dates)!=22 or dates[0]!="2026-09-30" or dates[-1]!="2026-10-29":
        raise ValueError("BOR: calendario oficial incompleto")
    notices=data.get("notices",[])
    if not notices or len(notices)!=cov.get("opportunities") or len({x["id"] for x in notices})!=len(notices):
        raise ValueError("BOR: avisos duplicados o faltantes")
    for n in notices:
        u=urlsplit(n.get("url",""))
        query=parse_qs(u.query)
        article=urlsplit(n.get("officialHtml",""))
        artq=parse_qs(article.query)
        format=n.get("originalFormat")
        published=datetime.strptime(n["date"],"%d/%m/%Y").date()
        if (not re.fullmatch(r"RI-2026-[0-9a-f]{18}",n.get("id",""))
            or n.get("province")!=PROVINCE or not str(n.get("entity","")).strip()
            or not str(n.get("title","")).strip()
            or n.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
            or published.isoformat() not in dates
            or u.scheme!="https" or u.hostname!="ias1.larioja.org"
            or article.scheme!="https" or article.hostname!="ias1.larioja.org"
            or article.path!="/boletin/ExportarBoletinServlet"
            or set(artq)!={"tipo","fecha","referencia"} or artq.get("tipo")!=["2"]
            or artq.get("fecha")!=[published.strftime("%Y/%m/%d")]
            or len(artq.get("referencia",[]))!=1
            or not re.fullmatch(r"[A-Za-z0-9-]{6,90}",artq["referencia"][0])
            or format not in ("pdf","official_xml")
            or set(query)!=({"referencia"} if format=="pdf" else {"tipo","fecha","referencia"})
            or (format=="pdf" and (u.path!="/boletin/Bor_Boletin_visor_Servlet"
                                   or len(query["referencia"])!=1
                                   or not re.fullmatch(r"[A-Za-z0-9-]{6,90}",query["referencia"][0])))
            or (format=="official_xml" and n["url"]!=n["officialHtml"])):
            raise ValueError("BOR: anuncio, formato o enlace no oficial "+repr(n.get("id")))
    pdf=sum(x["originalFormat"]=="pdf" for x in notices)
    print("BOR VALIDADO: 22 ediciones, "+str(cov["announcementsRead"])+
          " anuncios y "+str(len(notices))+" candidatas con texto íntegro oficial cotejado; "
          +str(pdf)+" PDF accesibles y "+str(len(notices)-pdf)+" XML oficiales alternativos",flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    args=p.parse_args()
    validate(args.root)
