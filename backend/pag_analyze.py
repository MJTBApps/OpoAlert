#!/usr/bin/env python3
"""Audit public Spanish employment XML (PAG), without publishing or storing user data."""
from collections import Counter
from datetime import datetime,date,timedelta
import re
from urllib.request import Request,urlopen
import xml.etree.ElementTree as ET
from urllib.parse import urlsplit
from pathlib import Path

BASE="https://administracion.gob.es/content/sling/endpoints/pag/front-elastic/empleo-elastic/exportar?type=xml"
req=Request(BASE,data=b"",method="POST",headers={
    "User-Agent":"OpoAlert/1.4; research public vacancies; MJTBApps/OpoAlert",
    "Accept":"application/xml,text/xml,*/*",
    "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
    "Referer":"https://administracion.gob.es/empleopublico/resultados-empleo"
})
with urlopen(req,timeout=65) as resp:
    size=resp.headers.get("content-length")
    raw=resp.read(45_000_001)
    print("HTTP",resp.status,"CONTENT TYPE",resp.headers.get("content-type"),"LEN",len(raw),"SERVER LEN",size,flush=True)
assert len(raw)<45_000_001
root=ET.fromstring(raw)
items=root.findall("./convocatorias")
print("ROOT",root.tag,"COUNT",len(items),flush=True)
print("ELEMENT TAG SAMPLE", sorted({child.tag for item in items[:25] for child in item}),flush=True)
cc=Counter();prov=Counter();state=Counter();scope=Counter();urlhost=Counter();dates=Counter();missing=Counter();valid=0
start=date.today()-timedelta(days=29)
for r in items:
    t=lambda tag: (r.findtext(tag) or "").strip()
    cc[t("comunidadautonoma")]+=1
    prov[t("provinciaId")]+=1
    scope[t("ambito")]+=1
    for d in r.findall("disposiciones"):
        pass
    dd=t("fechapublicacion")
    try:day=datetime.strptime(dd,"%d/%m/%Y").date()
    except ValueError: day=None; missing["bad date"]+=1
    if day and day>=start:
        valid+=1;dates[dd]+=1
    for link in r.findall("./disposiciones/masinformacion"):
        if link.text:
            try: urlhost[urlsplit(link.text).hostname]+=1
            except ValueError:pass
    for tag in ["id","titulo","organo","descripcion","fechapublicacion","comunidadautonoma"]:
        if not t(tag): missing[tag]+=1
print("COMMUNITIES", cc.most_common(30),flush=True)
print("PROVINCE IDs", prov.most_common(70),flush=True)
print("SCOPES",scope.most_common(20),flush=True)
print("HOSTS",urlhost.most_common(18),flush=True)
print("DAYS GE",start,len(dates),valid,"TOP DAYS",dates.most_common(15),flush=True)
print("MISSING",missing,flush=True)
for item in items[:3]:
    print("SAMPLE",[(c.tag,(c.text or "")[:120]) for c in item if c.tag in ("id","descripcion","titulo","organo","fechapublicacion","provinciaId","comunidadautonoma","ambito","diariopublicacion")],flush=True)
