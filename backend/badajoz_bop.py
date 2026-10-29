#!/usr/bin/env python3
"""BOP Badajoz: official 30-day archive, every notice and original PDF for candidates."""
from __future__ import annotations
import argparse,json,re,requests,threading
from pathlib import Path
from datetime import date,datetime,timedelta
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlsplit,urljoin,parse_qs
from bs4 import BeautifulSoup
from clm_common import employment,publish_audit,invalid

SOURCE="https://www.dip-badajoz.es/bop/"
HOST="www.dip-badajoz.es"
PDF_RE=re.compile(r"^/ficheros/bop/bopedictos/(\d{4})-(\d{2})-(\d{2})000000_([Rr]?\d{1,8})\.pdf$",re.I)
TLS=threading.local()
MONTHS={1:"enero",2:"febrero",3:"marzo",4:"abril",5:"mayo",6:"junio",
    7:"julio",8:"agosto",9:"septiembre",10:"octubre",11:"noviembre",12:"diciembre"}
def session():
    if not hasattr(TLS,"s"):
        s=requests.Session()
        s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
        TLS.s=s
    return TLS.s
def get(url,pdf=False):
    u=urlsplit(url)
    if (u.scheme!="https" or u.hostname!=HOST or u.username or u.password or u.fragment
        or u.port not in (None,443) or (pdf and not PDF_RE.fullmatch(u.path))):
        invalid("Badajoz: URL ajena al boletín")
    try:
        r=session().get(url,timeout=(12,30),stream=pdf,headers={"Range":"bytes=0-95"} if pdf else {})
        if r.status_code not in ((200,206) if pdf else (200,)) or urlsplit(r.url).hostname!=HOST:
            invalid(f"Badajoz: HTTP {r.status_code} en {url}")
        if pdf:
            prefix=b""
            for part in r.iter_content(120):
                prefix+=part
                if len(prefix)>=5:break
            if not prefix.startswith(b"%PDF-"):invalid("Badajoz: documento PDF no autenticado")
            r.close()
            return ""
        if not r.content or len(r.content)>2_000_000:invalid("Badajoz: HTML vacío o desmedido")
        return r.text
    except requests.RequestException as e:invalid("Badajoz: fallo de lectura oficial "+str(e)[:150])
def archive(start,end):
    results=set()
    for year,month in sorted({(start.year,start.month),(end.year,end.month)}):
        base=SOURCE+f"index.php?FechaSolicitada={year}{month:02}"
        soup=BeautifulSoup(get(base),"html.parser")
        label=next((h for h in soup.select("h4") if f"{MONTHS[month]} {year}" in h.get_text(" ",strip=True).lower()),None)
        if label is None:invalid(f"Badajoz: calendario oficial {year}-{month:02} ausente")
        for a in soup.select("a[href]"):
            u=urlsplit(urljoin(base,a["href"]))
            if u.hostname!=HOST or u.path!="/bop/index.php":continue
            d=parse_qs(u.query).get("FechaSolicitada",[])
            if len(d)!=1 or not re.fullmatch(r"\d{8}",d[0]):continue
            try: day=datetime.strptime(d[0],"%Y%m%d").date()
            except ValueError:continue
            if (day.year,day.month)==(year,month) and start<=day<=end:
                if a.get_text(" ",strip=True)!=str(day.day):invalid("Badajoz: enlace calendario inconsistente")
                results.add(day)
    result=sorted(results)
    if len(result)<18 or (result[0]-start).days>4 or (end-result[-1]).days>4:
        invalid(f"Badajoz: falta histórico de 30 días: {len(result)} días")
    return result
def normalize_code(code):
    c=code.upper()
    return ("R" if c.startswith("R") else "")+str(int(c.lstrip("R")))
def parse_day(html,day):
    h=BeautifulSoup(html,"html.parser")
    exact=f"Día {day.day} de {MONTHS[day.month]} de {day.year}"
    if not any(exact in " ".join(x.get_text(" ",strip=True).split()) for x in h.select("h1")):
        invalid(f"Badajoz: sumario no corresponde a {day}")
    numbers=[re.search(r"Boletín\s+(ordinario|extraordinario)\s+n[.º°\s]*([0-9]{1,3})",x.get_text(" ",strip=True),re.I)
        for x in h.select("h3")]
    issues=[m for m in numbers if m]
    if len(issues)!=1:invalid("Badajoz: número de boletines del día ambiguo")
    number=issues[0][2]
    root=h.select_one("#sumario_dinamico")
    if root is None:invalid("Badajoz: falta sumario oficial")
    docs=root.select("article")
    if not docs:invalid("Badajoz: índice sin anuncios")
    seen=set();rows=[]
    for article in docs:
        dt=article.select_one("dl dt")
        pdf=article.select_one('a[href*="/ficheros/bop/bopedictos/"]')
        link=article.select_one('a[href*="ventana_anuncio.php?id_anuncio="]')
        if not dt or not pdf or not link:invalid("Badajoz: artículo incompleto")
        code=re.fullmatch(r"\[\s*([Rr]?\d{1,8})\s*\]",dt.get_text(" ",strip=True))
        url=urljoin(SOURCE,pdf["href"]);p=urlsplit(url);m=PDF_RE.fullmatch(p.path)
        ann=urlsplit(urljoin(SOURCE,link["href"]))
        id_values=parse_qs(ann.query).get("id_anuncio",[])
        requested=parse_qs(ann.query).get("FechaSolicitada",[])
        title=" ".join(link.get_text(" ",strip=True).split())
        agency_tag=article.find_previous("p",class_="nivel3")
        agency=" ".join(agency_tag.get_text(" ",strip=True).split()) if agency_tag else ""
        if not (code and m and int(m[1])==day.year and int(m[2])==day.month and int(m[3])==day.day
            and normalize_code(m[4])==normalize_code(code[1]) and ann.hostname==HOST and ann.path=="/bop/ventana_anuncio.php"
            and len(id_values)==1 and re.fullmatch(r"\d{5,9}",id_values[0])
            and requested==[day.strftime("%Y%m%d")+"000000"] and title and agency):
            invalid(f"Badajoz {day}: anuncio/PDF incoherente: código={code[1] if code else None}, PDF={url}, urlAnuncio={ann.geturl()}, id={id_values}, fecha={requested}, título={title[:100]}, entidad={agency[:100]}")
        ident=f"BD-{day.year}-{id_values[0]}"
        if ident in seen:invalid("Badajoz: duplicado")
        seen.add(ident)
        role=employment(title)
        if role:rows.append({"id":ident,"province":"Badajoz","title":title,"entity":agency,
            "date":day.strftime("%d/%m/%Y"),"bulletin":number,
            "type":role,"url":url})
    return {"day":day,"number":number,"read":len(seen),"notices":rows}
def scan(day):
    data=parse_day(get(SOURCE+"index.php?FechaSolicitada="+day.strftime("%Y%m%d")),day)
    for notice in data["notices"]:get(notice["url"],pdf=True)
    print("BADAJOZ",day,"BOP",data["number"],"anuncios",data["read"],"candidatas",len(data["notices"]),flush=True)
    return data
def audit(today=None):
    end=today or date.today();start=end-timedelta(days=29)
    days=archive(start,end)
    with ThreadPoolExecutor(max_workers=5) as pool:
        issues=list(pool.map(scan,days))
    numbers=[int(x["number"]) for x in issues]
    if any(b!=a+1 for a,b in zip(numbers,numbers[1:])):
        invalid("Badajoz: números de boletín discontinuos o extraordinarios omitidos")
    return publish_audit(SOURCE,"Badajoz",issues,today=end)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",type=Path,required=True)
    a=p.parse_args();v=audit();a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(v,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"BADAJOZ AUDITADO: {v['historyCoverage']['issuesRead']} boletines, "
          f"{v['coverage']['announcementsRead']} anuncios y {len(v['notices'])} candidatas",flush=True)
