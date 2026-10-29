#!/usr/bin/env python3
"""Fail-closed independent audit of three Canary Islands source snapshots for APK."""
from __future__ import annotations
import argparse,json,re
from pathlib import Path
from datetime import date,datetime
from urllib.parse import urlsplit
FILES={
 "IC":("Canarias (BOC)","https://www.gobiernodecanarias.org/boc/archivo/2026/",
      "sede.gobiernodecanarias.org",22,361,50,196,217),
 "LP":("Las Palmas (BOP)","https://www.boplaspalmas.net/nbop2/main1.php",
      "www.boplaspalmas.net",13,375,35,117,129),
 "TF":("Santa Cruz de Tenerife (BOP)","https://www.bopsantacruzdetenerife.es/bopsc2/main1.php",
      "www.bopsantacruzdetenerife.es",13,522,27,117,129)
}
BOP_DAYS=["2026-09-30"]+[f"2026-10-{x:02}" for x in (2,5,7,9,12,14,16,19,21,23,26,28)]
def original(code,ident,url,day,num):
 u=urlsplit(url)
 if code=="IC":
  m=re.fullmatch(r"/boc/boc-a-2026-(\d{3})-(\d{1,8})\.pdf",u.path)
  if not m or int(m[1])!=int(num) or ident!=f"IC-2026-{int(m[2])}":return False
 else:
  m=re.fullmatch(r"/boletines/2026/(\d{1,2})-(\d{1,2})-26/(\d{1,2})-(\d{1,2})-26\.pdf",u.path)
  p=re.fullmatch(rf"{code}-2026(\d{{4}})-(\d{{3}})",ident)
  if (not m or not p or [int(x) for x in (m[1],m[2],m[3],m[4])] !=
        [day.day,day.month,day.day,day.month] or p[1]!=day.strftime("%m%d")
      or int(p[2])<1):return False
 return True
def audit(path:Path):
 total_issues=total_ads=total_opportunities=0
 for code,(province,source,host,count,ad_count,opps,lo,hi) in FILES.items():
  file=path/(code+".json")
  if not file.is_file():raise ValueError(f"Canarias: falta {file}")
  d=json.loads(file.read_text(encoding="utf-8"))
  c=d.get("coverage",{});h=d.get("historyCoverage",{})
  if (d.get("schemaVersion")!=1 or d.get("province")!=province or d.get("source")!=source
      or c.get("complete") is not True or c.get("status")!="complete"
      or h.get("complete") is not True or h.get("rangeStart")!="2026-09-30"
      or h.get("rangeEnd")!="2026-10-29" or h.get("issuesRead")!=count
      or c.get("pagesVisited")!=count or c.get("bulletin")!=str(hi)
      or h.get("announcementsRead")!=ad_count or c.get("announcementsRead")!=ad_count
      or h.get("opportunities")!=opps or c.get("opportunities")!=opps):
   raise ValueError(f"{code}: datos históricos o fuente no acreditados")
  stamp=datetime.fromisoformat(d.get("lastCheckedUTC",""))
  if stamp.tzinfo is None or stamp.date()!=date(2026,10,29):
   raise ValueError(f"{code}: auditoría fuera de fecha")
  bullets=h.get("bulletins",[])
  if bullets!=[str(n) for n in range(lo,hi+1)]:
   raise ValueError(f"{code}: faltan boletines o extraordinarios")
  dates=h.get("publicationDates",[])
  if code=="IC":
   if len(dates)!=21 or dates[0]!="2026-09-30" or dates[-1]!="2026-10-29":
    raise ValueError("BOC: calendario autonómico incompleto")
  elif dates!=BOP_DAYS:
   raise ValueError(f"BOP {province}: calendario provincial no coincide")
  notices=d.get("notices",[])
  if not isinstance(notices,list) or len(notices)!=opps or len({a.get("id") for a in notices})!=len(notices):
   raise ValueError(f"{code}: número de candidatas o identidades duplicadas")
  seen=set()
  for n in notices:
   ident=n.get("id","");u=urlsplit(n.get("url",""))
   try:day=datetime.strptime(n["date"],"%d/%m/%Y").date()
   except Exception as e:raise ValueError(f"{code}: fecha de anuncio incorrecta") from e
   if (not ident.startswith(code+"-") or ident in seen or day.isoformat() not in dates
       or n.get("province")!=province or str(n.get("bulletin")) not in bullets
       or n.get("type") not in ("Plaza / oposición","Bolsa de trabajo")
       or not str(n.get("title","")).strip() or not str(n.get("entity","")).strip()
       or u.scheme!="https" or u.hostname!=host or u.port not in (None,443)
       or u.query or u.fragment or u.username
       or not original(code,ident,n["url"],day,n["bulletin"])):
    raise ValueError(f"{code}: anuncio o PDF fuera de la publicación {ident}")
   seen.add(ident)
  total_issues+=count;total_ads+=ad_count;total_opportunities+=opps
  print(f"CANARIAS VALIDADO {code}: {count} boletines, {ad_count} anuncios, {opps} candidatas originales",flush=True)
 print(f"CANARIAS 30 DÍAS COMPLETOS: {total_issues} ediciones, {total_ads} anuncios, {total_opportunities} posibles convocatorias",flush=True)
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--root",required=True,type=Path)
 a=p.parse_args();audit(a.root)
