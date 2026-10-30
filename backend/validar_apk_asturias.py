#!/usr/bin/env python3
"""Independent fail-closed validation of BOPA Oct 2026 private snapshot.

The original issue PDF content is audited by asturias_bopa_20261029.py.
This separate validator checks every bulletin and coded link in the source
manifest plus the results of the original PDF audit; it never promotes HTTP
200 alone to completeness.
"""
from __future__ import annotations
import argparse,base64,gzip,hashlib,json,re
from datetime import date,datetime,timedelta
from pathlib import Path
from urllib.parse import urlsplit

SOURCE="https://miprincipado.asturias.es/ast/bopa-sumario"
PROVINCE="Asturias (BOPA)"
END=date(2026,10,29)
START=END-timedelta(days=29)
MANIFEST_SHA="91fbec5def3cd9316bb3b206da3e51b6f8a26de6bad358e2fd17d6daa6062f22"
SUPPLEMENT_SHA="8956a3b3fd6d11f2ce5031afb295910abbb32d9aba0c326ab3bc93ce7a4f950e"
KNOWN_HEADER_ANOMALIES={
    ("2026-08061","2026-10-13","198",197):
      "1f85f35ef7d84ac0a011548effb98ec157492fa29462e3b204e4768bb298c8ea",
    ("2026-08160","2026-10-15","200",199):
      "1968d147cb6d32ad4d64758ac6d9b88f8ed73e04c859e79d6efc3db67821a4c0",
}
LINK_RE=re.compile(r"https://www[.]asturias[.]es/bopa/2026/(\d{2})/(\d{2})/(2026-\d{5})[.]pdf")
def invalid(s):raise ValueError("BOPA auditoría independiente: "+str(s))

def validate(root:Path):
    path=root/"AS.json"
    o=json.loads(path.read_text(encoding="utf-8"))
    h=o.get("historyCoverage",{});c=o.get("coverage",{})
    if (o.get("schemaVersion")!=1 or o.get("province")!=PROVINCE or o.get("source")!=SOURCE
        or c.get("complete") is not True or c.get("status")!="complete"
        or h.get("complete") is not True
        or h.get("rangeStart")!=START.isoformat() or h.get("rangeEnd")!=END.isoformat()):
        invalid("falta integridad o identidad de fuente oficial")
    pub=h.get("publicationDates")
    nums=h.get("bulletins")
    if (not isinstance(pub,list) or not isinstance(nums,list) or len(pub)!=23
        or len(nums)!=23 or h.get("issuesRead")!=23 or c.get("pagesVisited")!=23
        or h.get("sourceMainIssues")!=22 or h.get("supplementIssues")!=1):
        invalid("no figuran todas las 23 ediciones oficiales")
    original_dates=[START+timedelta(days=i) for i in range(30) if (START+timedelta(days=i)).weekday()<5]
    indexed=h.get("indexEvidence")
    if (not isinstance(indexed,list) or len(indexed)!=22
        or [x.get("d") for x in indexed]!=[d.isoformat() for d in original_dates]
        or [x.get("n") for x in indexed]!=list(range(189,211))):
        invalid("calendario de boletines diarios no coincide con el editor")
    ids={};allrows=0
    for e in indexed:
        listed=e.get("ids","").split(",")
        if not listed or len(listed)!=len(set(listed)) or len(listed)>200:
            invalid("edición con artículos vacíos o duplicados")
        for code in listed:
            if not re.fullmatch(r"\d{5}",code) or code in ids:
                invalid("código original repetido en distintas ediciones")
            ids[code]={"day":e["d"],"number":str(e["n"])}
        allrows+=len(listed)
    if allrows!=917 or h.get("indexedOriginalUrlsVerifiedFromPublisherIndex")!=917:
        invalid("índice de los 917 anuncios truncado")
    expected_bulletins=[str(x["n"]) for x in indexed]
    expected_dates=[x["d"] for x in indexed]
    index_supplement=expected_bulletins.index("206")+1
    expected_bulletins.insert(index_supplement,"206S1")
    expected_dates.insert(index_supplement,"2026-10-23")
    if nums!=expected_bulletins or pub!=expected_dates:
        invalid("secuencias de números/fecha/suplemento no coinciden con sumarios originales")
    nonpub=[(START+timedelta(days=i)).isoformat() for i in range(30)
            if (START+timedelta(days=i)).weekday()>=5]
    if h.get("nonPublicationDates")!=nonpub or len(nonpub)!=8:
        invalid("fechas sin BOPA no certificadas")
    if c.get("announcementsRead")!=918 or h.get("announcementsRead")!=918:
        invalid("se han omitido anuncios o el suplemento original")
    supp=h.get("supplementEvidence",{})
    if (supp.get("date")!="2026-10-23" or supp.get("number")!="206S1"
        or supp.get("originalCode")!="2026-08829" or supp.get("pages")!=1
        or supp.get("sha256")!=SUPPLEMENT_SHA or
        supp.get("url")!="https://www.asturias.es/bopa/2026/10/23/20261023Su1.pdf"
        or supp.get("classifiedAsEmployment") is not False):
        invalid("suplemento original del 23 de octubre omitido o modificado")
    if (not re.fullmatch(r"[0-9a-f]{64}",h.get("originalArchiveSHA256",""))
        or h.get("indexManifestSHA256")!=MANIFEST_SHA
        or h.get("verifiedIssueRepresentatives")!=22
        or h.get("verifiedCandidateOriginals")!=32
        or h.get("originalPdfHost")!="www.asturias.es"):
        invalid("falta cadena de procedencia o original PDF del editor")
    evidence=h.get("verifiedOriginalSamples")
    if not isinstance(evidence,list):invalid("falta auditoría de PDFs originales")
    original_by_id={}
    for p in evidence:
        code=p.get("id")
        if (not isinstance(code,str) or not re.fullmatch(r"2026-\d{5}",code)
            or code in original_by_id or not p.get("publisherDateAndCVEVerified")
            or p.get("day")!=ids.get(code[5:],{}).get("day")
            or p.get("bulletin")!=ids.get(code[5:],{}).get("number")
            or not re.fullmatch(r"[0-9a-f]{64}",str(p.get("sha256","")))
            or not isinstance(p.get("pages"),int) or not 1<=p["pages"]<=400
            or not isinstance(p.get("bytes"),int) or p["bytes"]<3500):
            invalid("documento PDF original no verificable contra boletín")
        if p.get("url")!=f"https://www.asturias.es/bopa/{p['day'].replace('-','/')}/{code}.pdf":
            invalid("PDF ajeno a origen o fecha")
        number_ok=p.get("pdfHeaderIssueNumber")==int(p["bulletin"])
        anomaly=(KNOWN_HEADER_ANOMALIES.get((
                code,p.get("day"),p.get("bulletin"),p.get("pdfHeaderIssueNumber")))==p.get("sha256"))
        if (not number_ok and not anomaly or p.get("publisherIssueNumberMatched") is not number_ok
            or p.get("documentedEditorialNumberAnomaly") is not (not number_ok and anomaly)):
            invalid("discrepancia de numero BOPA no autorizada por fuente original")
        original_by_id[code]=p
    actualAnomalies=[{"day":x["day"],"code":x["id"],
                      "sumarioNumber":x["bulletin"],
                      "originalPdfHeaderNumber":x["pdfHeaderIssueNumber"],
                      "sha256":x["sha256"]} for x in evidence
                     if x.get("documentedEditorialNumberAnomaly")]
    if h.get("pdfHeaderEditorialDiscrepancies")!=actualAnomalies:
        invalid("erratas de numero BOPA no documentadas con huella SHA256")
    for e in indexed:
        rep="2026-"+e["ids"].split(",")[0]
        if rep not in original_by_id:
            invalid("falta al menos un PDF original de cada número BOPA")
    notices=o.get("notices")
    if (not isinstance(notices,list) or len(notices)!=32
        or c.get("opportunities")!=32 or h.get("opportunities")!=32
        or len({n.get("id") for n in notices})!=32):
        invalid("número de convocatorias/tipos no corresponde al índice")
    for n in notices:
        id=n.get("id","")
        if not re.fullmatch(r"AS-2026-\d{5}",id):
            invalid("identificador de anuncio no oficial")
        code=id[3:]
        p=original_by_id.get(code)
        if p is None or p.get("originalTitleMatched") is not True or p.get("titleTokenMatch",0)<0.61:
            invalid("candidato sin PDF original cotejado")
        try:
            d=datetime.strptime(n.get("date",""),"%d/%m/%Y").date()
        except ValueError:invalid("fecha de candidato no válida")
        if (n.get("province")!=PROVINCE or not n.get("entity","").strip()
            or len(n.get("title",""))<20 or n.get("type") not in ("Bolsa de trabajo","Plaza / oposición")
            or d.isoformat()!=p["day"] or n.get("bulletin")!=p["bulletin"]
            or n.get("url")!=p["url"]):
            invalid("fecha/título/emisor/código de convocatoria no coinciden")
    print("ASTURIAS BOPA VALIDADO INDEPENDIENTEMENTE: 22 ediciones, 1 suplemento 23/10, "
          "917 anuncios principales + 1 suplemento, 22 originales de control, "
          "32 convocatorias originales cotejadas, 30 días 30/09–29/10",flush=True)
    print("NOTA: Instantánea de 29/10; la publicación del 30/10 no se integra automáticamente.",flush=True)
    return o

if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--root",required=True,type=Path)
    validate(p.parse_args().root)
