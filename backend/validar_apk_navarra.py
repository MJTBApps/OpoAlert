#!/usr/bin/env python3
"""Independent offline validator for locally recovered BON Navarra 30-day snapshot.

Provenance: 30/09..29/10/2026, 24 official editions #194..217, including
three extraordinary issues. Evidence validated against user-provided original
publisher pages before encoding; this test independently checks the immutable
snapshot's hash, structure, issuance, numbering, links and conservative notices.

WARNING: On 30/10/2026 the new BON #218 is NOT covered by this dated
snapshot. Do not advertise automatic ongoing daily completeness.
"""
from __future__ import annotations
import argparse,base64,gzip,hashlib,json,re
from pathlib import Path
from datetime import date,datetime,timedelta
from urllib.parse import urlsplit

ENCODED=Path(__file__).parent/"snapshots"/"NA_20261029.json.gz.b64"
SOURCE="https://bon.navarra.es/es/indice-boletines"
HASH="e369c9fdf50cdae604d3f105acaf85145df5ae82891911dbcd702b2d4673452f"
COMPRESSED_HASH="03935854871676b942c29a883921eab21c7ae10bc70b0243ed56d95289b8d6a1"
START=date(2026,9,30);END=date(2026,10,29)
COUNTS=[29,74,60,34,49,12,67,53,5,1,46,16,63,48,51,63,154,61,48,25,41,122,40,1]
EXTRAS=["202","203","217"]
PATTERN=re.compile(r"NA-2026-(\d{3})-(\d{1,4})")

def invalid(msg):raise ValueError("BON Navarra: "+msg)

def unpack(to:Path):
    raw=ENCODED.read_text(encoding="ascii").strip()
    blob=base64.b64decode(raw,validate=True)
    if hashlib.sha256(blob).hexdigest()!=COMPRESSED_HASH:
        invalid("evidencia codificada dañada o sustituida")
    content=gzip.decompress(blob)
    if hashlib.sha256(content).hexdigest()!=HASH:
        invalid("instantánea distinta de la validada")
    to.parent.mkdir(parents=True,exist_ok=True)
    to.write_bytes(content)
    return to

def validate(root:Path):
    path=root/"NA.json"
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=HASH: invalid("SHA-256 del JSON no coincide con original auditado")
    x=json.loads(raw)
    c=x.get("coverage",{});h=x.get("historyCoverage",{})
    if (x.get("schemaVersion")!=1 or x.get("province")!="Navarra" or x.get("source")!=SOURCE
        or c.get("status")!="complete" or c.get("complete") is not True
        or h.get("complete") is not True
        or h.get("rangeStart")!=START.isoformat() or h.get("rangeEnd")!=END.isoformat()):
        invalid("origen, periodo o auditoría de 30 días no conformes")
    nums=[str(n) for n in range(194,218)]
    pub=h.get("publicationDates")
    if (not isinstance(pub,list) or len(pub)!=24 or h.get("bulletins")!=nums
        or h.get("issuesRead")!=24 or c.get("pagesVisited")!=24
        or pub[0]!=START.isoformat() or pub[-1]!=END.isoformat()
        or h.get("extraordinaryBulletins")!=EXTRAS
        or c.get("bulletin")!="217"):
        invalid("ediciones, extremos o extras del calendario inconsistentes")
    if (h.get("editionArticleCounts")!=COUNTS or sum(COUNTS)!=1163
        or c.get("announcementsRead")!=1163
        or h.get("announcementsRead")!=1163):
        invalid("faltan anuncios originales de uno o más sumarios")
    dates=[date.fromisoformat(p) for p in pub]
    if dates!=sorted(dates) or any(not START<=d<=END for d in dates):
        invalid("publicaciones fuera del intervalo o desordenadas")
    calendar_set={START+timedelta(days=i) for i in range(30)}
    actual_nonpub=[d.isoformat() for d in sorted(calendar_set-set(dates))]
    if h.get("nonPublicationDates")!=actual_nonpub:
        invalid("calendario de no publicación incompleto")
    evidence=h.get("originalEvidence")
    if (not isinstance(evidence,list) or len(evidence)!=52
        or h.get("candidateOriginalsVerified")!=52
        or h.get("originalTextExcerptsTruncated")!=12
        or len({e.get("id") for e in evidence})!=52
        or any(not re.fullmatch(r"[0-9a-f]{64}",str(e.get("sha256",""))) for e in evidence)):
        invalid("no se acreditan los 52 textos originales de candidatos")
    candidate_ids={e["id"] for e in evidence}
    notices=x.get("notices")
    if (not isinstance(notices,list) or len(notices)!=41
        or c.get("opportunities")!=41 or h.get("opportunities")!=41
        or len({n.get("id") for n in notices})!=41):
        invalid("lista conservadora de 41 convocatorias incompleta")
    for n in notices:
        match=PATTERN.fullmatch(n.get("id",""))
        if match is None:invalid("ID ajeno al BON")
        issue=int(match[1]);article=int(match[2])
        if not 195<=issue<=217 or n["id"] not in candidate_ids:
            invalid("anuncio sin documento original certificado")
        p=urlsplit(n.get("url",""))
        if (p.scheme!="https" or p.hostname!="bon.navarra.es" or p.port not in (None,443)
            or p.username or p.password or p.fragment or p.query
            or p.path!=f"/es/anuncio/-/texto/2026/{issue}/{article}"):
            invalid("enlace a documento original no oficial")
        day=datetime.strptime(n["date"],"%d/%m/%Y").date()
        if (n.get("province")!="Navarra" or n.get("bulletin")!=str(issue)
            or day!=date.fromisoformat(pub[issue-194])
            or n.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
            or not 5<len(n.get("title",""))<2600
            or not 2<len(n.get("entity",""))<180):
            invalid("fecha, clasificación, editor o titulo no coinciden con el BON")
        lowered=n["title"].casefold()
        if any(z in lowered for z in ("propuesta de contratación","propuesta de nombramiento","lista definitiva","declaración de excedencia")):
            invalid("se ha incluido un resultado que no es nueva convocatoria")
    print("BON NAVARRA VALIDADO: 24 ediciones, 1.163 anuncios originales indexados, 52 originales de candidatos comprobados y 41 convocatorias conservadoras (30/09 a 29/10)",flush=True)
    print("AVISO: El BON 218 del 30/10 no está incluido; instantánea fija, no feed automático",flush=True)
    return x

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--root",type=Path,required=True)
    p.add_argument("--decode",action="store_true")
    args=p.parse_args()
    if args.decode:unpack(args.root/"NA.json")
    validate(args.root)
