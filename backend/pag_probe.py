"""Explore official PAG public employment export links (no data published)."""
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
from bs4 import BeautifulSoup
import re
URLS=[
 "https://administracion.gob.es/empleopublico/resultados-empleo",
 "https://administracion.gob.es/empleopublico/resultadosEmpleo?_tipoPlazo=1&viaAcceso=2",
]
for url in URLS:
    print("\nPAG",url,flush=True)
    try:
        with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (OpoAlert / consultor empleo publico)","Accept-Language":"es-ES,es;q=0.9"}),timeout=35) as r:
            raw=r.read(2_000_000)
            print("HTTP",r.status,"BYTES",len(raw),"FINAL",r.url,flush=True)
            charset=r.headers.get_content_charset() or "utf-8"
        soup=BeautifulSoup(raw.decode(charset,"replace"),"html.parser")
        print("TITLE",soup.title.get_text(" ",strip=True) if soup.title else "",flush=True)
        print("FORMS",[(f.get("action"),f.get("method")) for f in soup.select("form")][:16],flush=True)
        for a in soup.select("a[href],button, input"):
            markup=str(a)
            if re.search(r"(?:xml|csv|exportar|descarga.*resultado)",markup,re.I):
                print("EXPORT",markup[:850],flush=True)
        print("PAGE SNIPPET",soup.get_text(" ",strip=True)[0:1200],flush=True)
    except (HTTPError,URLError,OSError) as e:
        print("ERROR",type(e).__name__,str(e),flush=True)
