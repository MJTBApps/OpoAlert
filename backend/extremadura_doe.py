#!/usr/bin/env python3
"""DOE Extremadura: authenticated 30-day indexes and original official PDF files."""
from __future__ import annotations
import argparse,json,re,requests,threading
from pathlib import Path
from datetime import date,datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit,urljoin,parse_qs
from bs4 import BeautifulSoup
from clm_common import employment,publish_audit,invalid

SOURCE="https://doe.juntaex.es/"
HOST="doe.juntaex.es"
PDF_RE=re.compile(r"^/pdfs/doe/(\d{4})/(\d{1,4}0[oe])/(\d{8})\.pdf$",re.I)
ISSUE_RE=re.compile(r"^/pdfs/doe/(\d{4})/(\d{1,4}0[oe])/\2\.pdf$",re.I)
TLS=threading.local()
MONTHS={1:"enero",2:"febrero",3:"marzo",4:"abril",5:"mayo",6:"junio",
    7:"julio",8:"agosto",9:"septiembre",10:"octubre",11:"noviembre",12:"diciembre"}
def session():
    if not hasattr(TLS,"s"):
        c=requests.Session()
        c.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
        TLS.s=c
    return TLS.s
def get(url,pdf=False,post=None):
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname!=HOST or u.username or u.password or u.fragment or u.port not in (None,443):
        invalid("DOE: URL fuera de la sede oficial")
    if pdf and not (PDF_RE.fullmatch(u.path) or ISSUE_RE.fullmatch(u.path)):
        invalid("DOE: URL de PDF fuera del diario")
    try:
        r=(session().post(url,data=post,timeout=(12,32)) if post is not None else
           session().get(url,timeout=(12,32),stream=pdf,headers={"Range":"bytes=0-120"} if pdf else {}))
        if r.status_code not in ((200,206) if pdf else (200,)) or urlsplit(r.url).hostname!=HOST:
            invalid(f"DOE: HTTP {r.status_code} en {url}")
        if pdf:
            header=b""
            for chunk in r.iter_content(160):
                header+=chunk
                if len(header)>=5:break
            if not header.startswith(b"%PDF-"):invalid("DOE: respuesta no es PDF firmado")
            r.close()
            return ""
        if not r.content or len(r.content)>2_000_000:invalid("DOE: página vacía o demasiado extensa")
        return r.text
    except requests.RequestException as ex:invalid("DOE: sede no disponible "+str(ex)[:190])
def calendar(start,end):
    editions=set()
    for year,month in sorted({(start.year,start.month),(end.year,end.month)}):
        html=get(SOURCE+"index.php",post={"messel":str(month),"aniosel":str(year)})
        h=BeautifulSoup(html,"html.parser")
        matching=0
        for a in h.select('a[href*="mostrardoe.php"]'):
            u=urlsplit(urljoin(SOURCE,a["href"]))
            if u.hostname!=HOST or u.path!="/ultimosdoe/mostrardoe.php":continue
            q=parse_qs(u.query);d=q.get("fecha",[]);t=q.get("t",[])
            if len(d)!=1 or len(t)!=1 or not re.fullmatch(r"\d{8}",d[0]) or t[0] not in ("o","e"):continue
            day=datetime.strptime(d[0],"%Y%m%d").date()
            if (day.year,day.month)!=(year,month):continue
            matching+=1
            if start<=day<=end:editions.add((day,t[0]))
        if matching<18:invalid(f"DOE: calendario {year}-{month} sin todas sus ediciones ({matching})")
    ordered=sorted(editions)
    ords=[day for day,t in ordered if t=="o"]
    if len(ords)<18 or (ords[0]-start).days>3 or (end-ords[-1]).days>3:
        invalid("DOE: faltan diarios del intervalo móvil")
    return ordered
def extract_issue(html,day,kind):
    h=BeautifulSoup(html,"html.parser")
    content=h.get_text(" ",strip=True)
    marker=re.search(r"N[uú]m\.\s*:\s*(\d{1,4})\s*\|\s*([^|]{5,65}?)\s*(?=Contenido del DOE|DOE Anterior|$)",content,re.I)
    if not marker:
        # The heading may contain extra typographic elements between number and date.
        marker=re.search(r"N[uú]m\.\s*:\s*(\d{1,4})",content,re.I)
    if not marker:invalid(f"DOE {day}: número de edición ausente")
    n=int(marker[1])
    expected=f"{day.day} de {MONTHS[day.month]} de {day.year}"
    if expected.lower() not in content.lower()[:1000]:
        invalid(f"DOE: fecha distinta de la solicitada {day}")
    full=[]
    for a in h.select('a[href$=".pdf"]'):
        u=urlsplit(urljoin(SOURCE,a["href"]))
        m=ISSUE_RE.fullmatch(u.path)
        if u.hostname==HOST and m and int(m[1])==day.year:
            full.append((m[2],urljoin(SOURCE,a["href"])))
    if len(set(full))!=1:invalid(f"DOE {day}: PDF de edición completo no encontrado")
    folder,original=full[0]
    if not folder.endswith("0"+kind) or int(folder[:-2])!=n:
        invalid(f"DOE {day}: número {n} no coincide con edición {folder}")
    blocks=h.select("div.justificado")
    if not blocks:invalid(f"DOE {day}: faltan publicaciones del sumario")
    seen=set();notices=[]
    for block in blocks:
        title=" ".join(block.get_text(" ",strip=True).split())
        pdfs=[urljoin(SOURCE,a["href"]) for a in block.select('a.enlace_dis[href$=".pdf"]')]
        if len(pdfs)!=1 or not title:invalid("DOE: anuncio sin PDF y texto individual")
        pdf=pdfs[0];u=urlsplit(pdf);m=PDF_RE.fullmatch(u.path)
        if not m or u.hostname!=HOST or int(m[1])!=day.year or m[2]!=folder:
            invalid(f"DOE {day}: documento original de otro boletín {pdf}, carpeta={folder}")
        nid=f"EX-{day.year}-{m[3]}"
        if nid in seen:invalid(f"DOE: documento duplicado {nid}")
        seen.add(nid)
        agency=""
        for p in block.find_all_previous("p",limit=70):
            if p.find_parent("div",class_="justificado"):continue
            name=" ".join(p.get_text(" ",strip=True).split())
            if len(name)>4 and len(name)<220 and name.isupper() and not re.match(
                r"^(?:I{1,4}\.|V\.|OPOSICIONES|NOMBRAMIENTOS|SUMARIO|CONTENIDO|ANUNCIOS)",name):
                agency=name
                break
        if not agency:invalid(f"DOE {day}: organismo no confirmado")
        role=employment(title)
        if role:
            notices.append({"id":nid,"province":"Extremadura (DOE)","title":title,
                "entity":agency,"date":day.strftime("%d/%m/%Y"),"bulletin":str(n)+kind.upper(),
                "type":role,"url":pdf})
    return {"day":day,"number":str(n)+kind.upper(),"read":len(blocks),
        "notices":notices,"issuePdf":original}
def scan(t):
    day,kind=t
    url=SOURCE+"ultimosdoe/mostrardoe.php?fecha="+day.strftime("%Y%m%d")+"&t="+kind
    item=extract_issue(get(url),day,kind)
    get(item["issuePdf"],pdf=True)
    for n in item["notices"]:get(n["url"],pdf=True)
    print("DOE",day,kind,"número",item["number"],"anuncios",item["read"],
        "candidatas",len(item["notices"]),flush=True)
    return item
def audit(today=None):
    end=today or date.today();start=end-timedelta(days=29)
    sources=calendar(start,end)
    with ThreadPoolExecutor(max_workers=5) as pool:issues=list(pool.map(scan,sources))
    ords=[int(x["number"][:-1]) for x in issues if x["number"].endswith("O")]
    if any(b!=a+1 for a,b in zip(ords,ords[1:])):
        invalid("DOE: numeración ordinaria no consecutiva")
    return publish_audit(SOURCE,"Extremadura (DOE)",issues,today=end)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path)
    a=p.parse_args();x=audit();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(x,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"DOE AUDITADO: {x['historyCoverage']['issuesRead']} ediciones, "
        f"{x['coverage']['announcementsRead']} anuncios y {len(x['notices'])} candidatas",flush=True)
