#!/usr/bin/env python3
"""Official Gipuzkoa BOG 30-day daily HTML index and original PDF audit."""
from __future__ import annotations
from concurrent.futures import ThreadPoolExecutor
from datetime import date,timedelta
from urllib.parse import urlsplit,urljoin
from pathlib import Path
from bs4 import BeautifulSoup
import argparse,requests,re,threading
from clm_common import employment,publish_audit,write_output,invalid

SOURCE="https://egoitza.gipuzkoa.eus/es/bog"
HOST="egoitza.gipuzkoa.eus"
PDF_RE=re.compile(r"^/gao-bog/castell/bog/(2026)/(\d{2})/(\d{2})/c(26\d{5})\.pdf$",re.I)
S=threading.local()
def session():
    if not hasattr(S,"req"):
        x=requests.Session();x.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es"});S.req=x
    return S.req
def request(url,pdf=False):
    u=urlsplit(url)
    if u.scheme!="https" or u.hostname!=HOST or u.fragment or u.username or u.port not in (None,443):
        invalid("Gipuzkoa: URL externa al boletín")
    try:
        r=session().get(url,timeout=(12,32),stream=pdf,allow_redirects=False)
        if r.status_code in (404,410) and not pdf:return None
        if r.status_code not in ((200,206) if pdf else (200,)):
            invalid(f"Gipuzkoa: HTTP {r.status_code} en {url}")
        if pdf:
            h=b""
            for chunk in r.iter_content(140):
                h+=chunk
                if len(h)>=5:break
            good=h.startswith(b"%PDF-") and "pdf" in r.headers.get("Content-Type","").lower()
            r.close()
            if not good:invalid("Gipuzkoa: documento PDF no autenticado "+url)
            return ""
        if len(r.content)<2000 or len(r.content)>900000:
            invalid("Gipuzkoa: sumario incompleto")
        return r.content
    except requests.RequestException as e:invalid("Gipuzkoa: error HTTP "+str(e)[:200])
def issue_url(day):
    return f"https://{HOST}/gao-bog/castell/bog/{day:%Y/%m/%d}/bc{day:%y%m%d}.htm"
def read_day(day):
    url=issue_url(day)
    html=request(url)
    if html is None:return None
    soup=BeautifulSoup(html,"html.parser")
    root=soup.select_one("div#sumario")
    if not root:invalid(f"Gipuzkoa {day}: sin índice oficial")
    head=root.select_one("h2")
    matched=re.search(r"Bolet[ií]n\s+(\d{2}-\d{2}-\d{4}),\s*N[uú]mero\s+(\d{1,3})",head.get_text(" ",strip=True) if head else "",re.I)
    if not matched or matched[1]!=day.strftime("%d-%m-%Y"):
        invalid(f"Gipuzkoa {day}: cabecera oficial incorrecta")
    num=int(matched[2])
    sumario=root.select_one('a[href$=".pdf"]')
    if not sumario or not urljoin(url,sumario["href"]).endswith(f"/ib{day:%y%m%d}.pdf"):
        invalid(f"Gipuzkoa {day}: falta PDF índice")
    ads=root.select("ul.anuncios > li")
    if not ads:invalid("Gipuzkoa: publicación vacía")
    seen=set();notices=[]
    for item in ads:
        title_tag=item.select_one(".titulo_anuncio")
        link=next((a for a in item.select("a[href]") if a.get("href","").lower().endswith(".pdf")),None)
        parent=item.find_parent("li",class_="organismo")
        agency=(parent.find("a",attrs={"name":True}) if parent else None)
        title=" ".join(title_tag.get_text(" ",strip=True).split()) if title_tag else ""
        organ=" ".join(agency.get_text(" ",strip=True).split()) if agency else ""
        pdf=urljoin(url,link["href"]) if link else ""
        m=PDF_RE.fullmatch(urlsplit(pdf).path)
        if not (title and organ and m and int(m[1])==day.year and int(m[2])==day.month
            and int(m[3])==day.day and urlsplit(pdf).hostname==HOST):
            invalid(f"Gipuzkoa {day}: anuncio sin título, organismo o PDF verificable: {title[:65]}, agency={organ[:65]}, PDF={pdf[:170]}")
        ident=f"GP-2026-{m[4]}"
        if ident in seen:invalid("Gipuzkoa: anuncio duplicado "+ident)
        seen.add(ident)
        kind=employment(title)
        if kind:notices.append({"id":ident,"province":"Gipuzkoa","title":title,
            "entity":organ,"date":day.strftime("%d/%m/%Y"),
            "bulletin":str(num),"type":kind,"url":pdf})
    for note in notices:request(note["url"],pdf=True)
    print("GIPUZKOA",day,num,len(seen),"anuncios",len(notices),"candidatas",flush=True)
    return {"day":day,"number":str(num),"read":len(seen),"notices":notices}
def audit(today=None):
    end=today or date.today()
    start=end-timedelta(days=29)
    days=[start+timedelta(days=x) for x in range(30)]
    with ThreadPoolExecutor(max_workers=5) as pool:issues=[i for i in pool.map(read_day,days) if i]
    nums=[int(x["number"]) for x in issues]
    if len(issues)<19 or len(issues)>27 or any(b!=a+1 for a,b in zip(nums,nums[1:])):
        invalid(f"Gipuzkoa: boletines no consecutivos, encontrados {nums}")
    return publish_audit(SOURCE,"Gipuzkoa",issues,today=end)
if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--output",required=True,type=Path)
    args=p.parse_args();write_output(args.output,audit())
