#!/usr/bin/env python3
"""Inspect secondary Ceuta bulletin index only to locate official originals; never publish unverified secondary data."""
import requests,re,json
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlsplit
url="https://www.elperiodicodeceuta.es/ayudas-oposiciones-ceuta/"
r=requests.get(url,timeout=(10,36),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES"})
h=BeautifulSoup(r.content,"html.parser")
links=[(a.get_text(" ",strip=True)[:100],urljoin(r.url,a.get("href",""))) for a in h.select("a[href]")]
good=[x for x in links if "ceuta.es" in x[1] or ".pdf" in x[1].lower() or "bocce" in x[0].lower() or "bolet" in x[0].lower()]
texts=[(x.name,x.get_text(" ",strip=True)[:160]) for x in h.select("h1,h2,h3,h4") if re.search(r"bolet|bocce|666|octubr",x.get_text(" ",strip=True),re.I)]
print("CEUTA_MIRROR",json.dumps({"status":r.status_code,"bytes":len(r.content),"links":good[:65],"headings":texts[:35],
"raw":str(h.find(string=re.compile("BOCCE nº 6662",re.I)).parent.parent)[:3300] if h.find(string=re.compile("BOCCE nº 6662",re.I)) else "notfound",
"scriptSrcs":[x.get("src") for x in h.select("script[src]")[-15:]],
"summarySample":h.get_text(" ",strip=True)[3500:5800]},ensure_ascii=False)[:14500],flush=True)
