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

# Inspect public form constraints and export endpoint, without caching personal data.
from urllib.parse import urlencode
from urllib.request import Request
from urllib.error import HTTPError
soup=BeautifulSoup(raw.decode(charset,"replace"),"html.parser")
export=soup.select_one('button[data-extra-parameters="type=xml"]')
if export:
    print("\nEXPORT PARENT",str(export.parent)[:4600],flush=True)
print("HIDDEN FORM INPUTS",[(i.get("name"),str(i.get("value",""))[:100]) for i in soup.select('form input[type="hidden"]')][:35],flush=True)
target="https://administracion.gob.es/content/sling/endpoints/pag/front-elastic/empleo-elastic/exportar?type=xml"
for method,payload in [("POST",b""),("POST",urlencode({"type":"xml"}).encode())]:
    print("\nEXPORT DIRECT",target,"PAYLOAD",payload,flush=True)
    try:
        req=Request(target,data=payload,method=method,headers={
            "User-Agent":"Mozilla/5.0 (OpoAlert public administrative employment reader)",
            "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
            "Accept":"application/xml,text/xml,*/*",
            "Referer":"https://administracion.gob.es/empleopublico/resultados-empleo",
        })
        with urlopen(req,timeout=35) as resp:
            b=resp.read(4200)
            print("EXPORT HTTP",resp.status,"CONTENT",resp.headers.get("content-type"),"LEN",resp.headers.get("content-length"),"SAMPLE",b.decode("utf-8","replace")[:2400],flush=True)
    except HTTPError as exc:
        print("EXPORT HTTP ERR",exc.code,exc.read(1200).decode("utf-8","replace"),flush=True)
    except Exception as exc:
        print("EXPORT ERROR",type(exc).__name__,str(exc),flush=True)
