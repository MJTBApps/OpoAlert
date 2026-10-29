#!/usr/bin/env python3
"""Strict validation of five official Galicia 30-day private Android snapshots."""
from __future__ import annotations
from pathlib import Path
from datetime import datetime,date
from urllib.parse import urlsplit
import json,re,argparse
SOURCE={
 "AC":("A Coruña","https://bop.dacoruna.gal/bopportal/ultimoBoletin","bop.dacoruna.gal",21,645,52,187,207),
 "LU":("Lugo","https://deputacionlugo.gal/gl/boletin-oficial-da-provincia-de-lugo/bop","deputacionlugo.gal",25,359,48,224,248),
 "OU":("Ourense","https://bop.depourense.es/portalapi/api/boletin/getFecha","bop.depourense.es",22,279,51,187,208),
 "PO":("Pontevedra","https://boppo.depo.gal/es/consulta-do-boppo","boppo.depo.gal",22,435,24,188,209),
 "DG":("Galicia (DOG)","https://www.xunta.gal/diario-oficial-galicia/Welcome.do?lang=es","www.xunta.gal",22,547,129,186,207),
}
def date_from_notice(r):
    return datetime.strptime(r["date"],"%d/%m/%Y").date()
def valid_pdf(code,u,row):
    p=u.path
    d=date_from_notice(row)
    tail=row["id"]
    if code=="AC":
        m=re.fullmatch(r"/bopportal/publicado/2026/(\d{2})/(\d{2})/2026_(\d{10})\.pdf",p)
        return bool(m and int(m[1])==d.month and int(m[2])==d.day and int(m[3])==int(tail[8:]))
    if code=="LU":
        m=re.fullmatch(r"/sites/deputacionlugo\.org/files/inline-files/(\d{2}-\d{2}-2026)(?:_\d{1,3})?\.pdf",p)
        return bool(m and m[1]==d.strftime("%d-%m-%Y") and re.fullmatch(r"LU-2026-\d{2,6}",tail))
    if code=="OU":
        m=re.fullmatch(r"/portalapi/api/edicto/descargar/pdf/(\d{3,9})/idioma/gl",p)
        return bool(m and tail==f"OU-2026-{m[1]}")
    if code=="PO":
        m=re.fullmatch(r"/web/boppo/detalle/-/boppo/2026/(\d{2})/(\d{2})/(2026\d{6,8})/an\.bop\.PONTEVEDRA\.(2026\d{4})\.(2026\d{6,8})\.pdf",p)
        if not m:return False
        try:stamp=datetime.strptime(m[4],"%Y%m%d").date()
        except ValueError:return False
        return bool(int(m[1])==d.month and int(m[2])==d.day and m[3]==m[5] and
              tail=="PO-"+m[3] and abs((stamp-d).days)<=10)
    if code=="DG":
        m=re.fullmatch(r"/dog/Publicados/2026/(\d{8})/(Anuncio[A-Za-z0-9-]+)_es\.pdf",p)
        return bool(m and m[1]==d.strftime("%Y%m%d") and tail=="DG-2026-"+m[2])
    return False
def audit(root:Path):
    ids=set();total_issues=total_announcements=total_opportunities=0
    for code,(province,source,host,issue_count,ann_count,opp_count,first,last) in SOURCE.items():
        f=root/(code+".json")
        data=json.loads(f.read_text(encoding="utf-8"))
        cov=data.get("coverage",{}); hist=data.get("historyCoverage",{})
        if (data.get("schemaVersion")!=1 or data.get("province")!=province or data.get("source")!=source
            or cov.get("complete") is not True or hist.get("complete") is not True or cov.get("status")!="complete"
            or hist.get("rangeStart")!="2026-09-30" or hist.get("rangeEnd")!="2026-10-29"
            or cov.get("pagesVisited")!=issue_count or hist.get("issuesRead")!=issue_count
            or cov.get("announcementsRead")!=ann_count or hist.get("announcementsRead")!=ann_count
            or cov.get("opportunities")!=opp_count or hist.get("opportunities")!=opp_count):
            raise ValueError(f"{code}: fuente, contadores o periodo no acreditados")
        checked=datetime.fromisoformat(data.get("lastCheckedUTC",""))
        if checked.tzinfo is None or checked.date()!=date(2026,10,29):
            raise ValueError(f"{code}: fecha de comprobación incorrecta")
        dates=hist.get("publicationDates",[]);bulletins=hist.get("bulletins",[])
        if (not isinstance(dates,list) or len(dates)!=issue_count or dates!=sorted(dates)
            or dates[0]!="2026-09-30" or dates[-1] not in ("2026-10-28","2026-10-29")
            or not isinstance(bulletins,list) or len(bulletins)!=issue_count
            or len(set(bulletins))!=issue_count or bulletin_dates_bad(dates)
            or bulletins[0]!=str(first) or bulletins[-1]!=str(last)):
            raise ValueError(f"{code}: BOP sin continuidad o fechas")
        numeric=[int(n) for n in bulletins]
        if any(b!=a+1 for a,b in zip(numeric,numeric[1:])):
            raise ValueError(f"{code}: falta una edición numerada")
        if code!="LU" and dates[-1]!="2026-10-29":
            raise ValueError(f"{code}: no contiene edición más reciente")
        notices=data.get("notices",[])
        if not isinstance(notices,list) or len(notices)!=opp_count:
            raise ValueError(f"{code}: coincidencias de empleo público no coinciden")
        for row in notices:
            u=urlsplit(row.get("url",""))
            try:day=date_from_notice(row)
            except Exception as e:raise ValueError(f"{code}: fecha de aviso incorrecta") from e
            ident=row.get("id","")
            if (not ident.startswith(code+"-2026-") or ident in ids
                or row.get("province")!=province
                or not row.get("title","").strip() or not row.get("entity","").strip()
                or row.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
                or day.isoformat() not in dates or str(row.get("bulletin")) not in bulletins
                or u.scheme!="https" or u.hostname!=host or u.port not in (None,443)
                or u.query or u.fragment or u.username or not valid_pdf(code,u,row)):
                raise ValueError(f"{code}: anuncio/PDF sin validar: {ident}, url={u.geturl()[:400]}, fecha={day}, bulletin={row.get('bulletin')}, title={row.get('title','')[:90]}, pdf_valid={valid_pdf(code,u,row)}, hostname={u.hostname}, type={row.get('type')}, fecha_en_indice={day.isoformat() in dates}")
            ids.add(ident)
        print(f"GALICIA VALIDADA {code}: {issue_count} boletines, {ann_count} anuncios, {opp_count} candidatas",flush=True)
        total_issues+=issue_count;total_announcements+=ann_count;total_opportunities+=opp_count
    print(f"GALICIA OK: cinco fuentes, {total_issues} boletines, {total_announcements} anuncios y {total_opportunities} posibles convocatorias",flush=True)
def bulletin_dates_bad(dates):
    try:
        parsed=[date.fromisoformat(d) for d in dates]
    except Exception:return True
    return len(set(parsed))!=len(parsed) or any(d<date(2026,9,30) or d>date(2026,10,29) for d in parsed)
if __name__=="__main__":
    ap=argparse.ArgumentParser();ap.add_argument("--root",type=Path,required=True)
    args=ap.parse_args();audit(args.root)
