#!/usr/bin/env python3
"""Independent strict validator for official DOGC 30-day private APK snapshot.

This is intentionally separate from the source reader and fails closed for
missing main issues, annexes, notification supplements, or originals.
"""
from __future__ import annotations
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit,parse_qs
import argparse,json,re

START=date(2026,9,30); END=date(2026,10,29)
PROVINCE="Cataluña (DOGC)"
SOURCE="https://portaldogc.gencat.cat/eadop-rest/api/dogc/summaryDOGC"
CVE=re.compile(r"CVE-DOGC-[A-Z]-[A-Z0-9-]+-2026")
NUMBER=re.compile(r"\d{4,5}(?:A|B|C|SN)?")
def bad(why):raise ValueError("DOGC verificación independiente: "+why)

def validate(root:Path):
    path=root/"DC.json"
    o=json.loads(path.read_text(encoding="utf-8"))
    coverage=o.get("coverage",{});h=o.get("historyCoverage",{})
    if (o.get("schemaVersion")!=1 or o.get("source")!=SOURCE
        or o.get("province")!=PROVINCE or coverage.get("complete") is not True
        or h.get("complete") is not True or coverage.get("status")!="complete"
        or h.get("rangeStart")!=START.isoformat() or h.get("rangeEnd")!=END.isoformat()):
        bad("falta fuente oficial o auditoría completa")
    stamp=datetime.fromisoformat(o.get("lastCheckedUTC",""))
    if stamp.tzinfo is None or stamp.date() not in (END,END+timedelta(days=1)):
        bad("marca de auditoría no corresponde al período")
    cal=h.get("calendarEvidence")
    if not isinstance(cal,list) or len(cal)!=30:bad("calendario oficial de 30 días ausente")
    expected=[START+timedelta(days=i) for i in range(30)]
    if [x.get("date") for x in cal]!=[d.isoformat() for d in expected]:
        bad("fechas del calendario no consecutivas")
    actualMain=[int(x["mainBulletin"]) for x in cal if x.get("mainBulletin")]
    if actualMain!=list(range(9761,9784)) or h.get("mainIssues")!=23:
        bad("faltan números principales o calendario de publicaciones")
    summaries=h.get("sumariosVerificados")
    if not isinstance(summaries,list) or len(summaries)!=23:
        bad("faltan sumarios diarios originales")
    if [x.get("main") for x in summaries]!=[str(n) for n in actualMain]:
        bad("índices no corresponden a calendario original")
    publishedSupplementCount=sum(bool(row.get("supplement")) for row in summaries)
    if (h.get("supplementsAudited")!=publishedSupplementCount
        or not 5<=publishedSupplementCount<=23):
        bad("faltan suplementos de notificaciones publicados oficialmente")
    all_ids=set();numbers=[];days=[];total=0; main=annex=sup=0
    originalByIssue={}
    for group in summaries:
        day=date.fromisoformat(group["date"])
        names=group.get("editions")
        counts=group.get("counts")
        ids=group.get("originalIds")
        sid=group.get("supplementIds")
        has_supplement=bool(group.get("supplement"))
        if (not isinstance(names,list) or not names or
            not isinstance(counts,list) or len(names)!=len(counts) or
            not isinstance(ids,list) or sum(counts)!=len(ids)
            or (has_supplement and (not isinstance(sid,list) or not sid or group.get("supplementCount")!=len(sid)))
            or (not has_supplement and (sid is not None or group.get("supplementCount") is not None))
            or (has_supplement and group.get("supplement")!=group["main"]+"SN")):
            bad("índice principal/anexo/suplemento incompleto")
        if not has_supplement:sid=[]
        if names[0]!=group["main"] or any(not n.startswith(group["main"]) or not NUMBER.fullmatch(n) for n in names):
            bad("numero de edición o anexo no reconocido")
        if any(not isinstance(v,int) or not 1<=v<=350 for v in counts) or not 1<=len(sid)<=350:
            bad("sumario vacío o contador imposible")
        if len(set(ids+sid))!=len(ids)+len(sid):
            bad("publicaciones repetidas entre ediciones del mismo día")
        if any(not re.fullmatch(r"\d{6,9}",str(v)) or v in all_ids for v in ids+sid):
            bad("ID de publicación duplicado o no oficial")
        all_ids.update(ids+sid)
        for n,c in zip(names,counts):
            numbers.append(n); days.append(day.isoformat());total+=c
            originalByIssue[n]=(day.isoformat(),set(ids))
        if has_supplement:
            numbers.append(group["supplement"]);days.append(day.isoformat());total+=len(sid)
            originalByIssue[group["supplement"]]=(day.isoformat(),set(sid))
            sup+=1
        main+=1;annex+=len(names)-1
    if (h.get("annexIssues")!=annex or annex<1
        or coverage.get("pagesVisited")!=len(numbers)
        or h.get("issuesRead")!=len(numbers)
        or h.get("announcementsRead")!=total
        or coverage.get("announcementsRead")!=total
        or set(h.get("bulletins",[]))!=set(numbers)
        or len(h.get("bulletins",[]))!=len(numbers)):
        bad("conteos/ediciones/anexos no coinciden con calendario")
    notices=o.get("notices")
    evidence=h.get("candidateOriginalEvidence")
    if (not isinstance(notices,list) or not isinstance(evidence,list)
        or not notices or len(notices)!=len(evidence)
        or len(notices)!=coverage.get("opportunities")
        or len(notices)!=h.get("opportunities")
        or h.get("originalCandidateDocumentsVerified")!=len(notices)):
        bad("anuncios de empleo sin verificación original 1:1")
    verified={}
    for e in evidence:
        if (not isinstance(e,dict) or e.get("authenticityVerified") is not True
            or not re.fullmatch(r"\d{6,9}",str(e.get("id")))
            or not CVE.fullmatch(str(e.get("cve")))
            or not isinstance(e.get("textChars"),int) or e["textChars"]<110
            or e.get("issue") not in originalByIssue
            or e.get("date")!=originalByIssue[e["issue"]][0]
            or e["id"] not in originalByIssue[e["issue"]][1]
            or e["id"] in verified):
            bad("CVE/fecha/edición del documento original no acredita publicación")
        verified[e["id"]]=e
    seen=set()
    for n in notices:
        if not isinstance(n,dict):bad("anuncio vacío")
        url=urlsplit(n.get("url",""))
        q=parse_qs(url.query)
        m=re.fullmatch(r"DC-2026-(\d{6,9})",str(n.get("id","")))
        if (m is None or n["id"] in seen or m[1] not in verified
            or n.get("province")!=PROVINCE or not n.get("entity","").strip()
            or not n.get("title","").strip() or len(n["title"])>2800
            or n.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
            or url.scheme!="https" or url.hostname!="dogc.gencat.cat"
            or url.port not in (None,443) or url.path!="/ca/document-del-dogc/"
            or set(q)!={"documentId"} or q["documentId"]!=[m[1]]
            or n.get("bulletin")!=verified[m[1]]["issue"]
            or datetime.strptime(n["date"],"%d/%m/%Y").date().isoformat()!=verified[m[1]]["date"]):
            bad("aviso de empleo apunta a fuente distinta del original oficial")
        seen.add(n["id"])
    print(f"DOGC VERIFICADO INDEPENDIENTEMENTE: {main} principales, {annex} anexos, {sup} suplementos; "
          f"{total} avisos originales y {len(notices)} posibles procesos selectivos auténticos",flush=True)
    return len(numbers),total,len(notices)

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",required=True,type=Path)
    validate(p.parse_args().root)
