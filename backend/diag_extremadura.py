#!/usr/bin/env python3
"""Read-only official portal diagnostics for BOP Badajoz, BOP Caceres and DOE."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
import requests,re,json
from bs4 import BeautifulSoup
URLS=[
 ("BA-index","https://www.dip-badajoz.es/bop/"),
 ("BA-specific","https://www.dip-badajoz.es/bop/index.php?FechaSolicitada=20261028000000"),
 ("BA-sept","https://www.dip-badajoz.es/bop/index.php?mes=9&ano=2026"),
 ("BA-pdf","https://www.dip-badajoz.es/ficheros/bop/bopedictos/2026-10-16000000_4092.pdf"),
 ("CC-index","https://bop.dip-caceres.es/bop/index.html"),
 ("CC-sumario","https://bop.dip-caceres.es/bop/sumario.html?busqueda=numBop&id=6163"),
 ("CC-notice","https://bop.dip-caceres.es/bop/anuncio.html?csv=BOP-2026-4651"),
 ("DOE-index","https://doe.juntaex.es/"),
 ("DOE-28","https://doe.juntaex.es/ultimosdoe/mostrardoe.php?fecha=20261028&t=o"),
 ("DOE-29","https://doe.juntaex.es/ultimosdoe/mostrardoe.php?fecha=20261029&t=o"),
]
def inspect(case):
    name,url=case
    try:
        r=requests.get(url,timeout=(10,25),headers={"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130.0 Safari/537.36","Accept-Language":"es-ES,es;q=0.9"})
        print("\n##",name,"STATUS",r.status_code,"SIZE",len(r.content),"URL",r.url,"TYPE",r.headers.get("Content-Type"),flush=True)
        if r.content[:5]==b"%PDF-":
            print("PDF_BYTES",repr(r.content[:32]),flush=True)
            return
        h=BeautifulSoup(r.content[:1_800_000],"html.parser")
        print("TITLE",h.title.get_text(" ",strip=True)[:120] if h.title else None,flush=True)
        print("HEADINGS",[(x.name,x.get_text(" ",strip=True)[:140]) for x in h.select("h1,h2,h3,h4,h5")[-27:]],flush=True)
        print("FORMS",[(str(f.get('action'))[:170],f.get('method'),[(x.name,x.get('name'),x.get('value')) for x in f.select('input[name],select[name]')[:9]]) for f in h.select("form")[:7]],flush=True)
        all_links=[(a.get_text(" ",strip=True)[:100],urljoin(r.url,a.get("href",""))[:260]) for a in h.select("a[href]")]
        interesting=[x for x in all_links if re.search(r"pdf|bop|sumario|anuncio|doe|fecha|2026|bolet|anterior|siguiente|histor",x[0]+" "+x[1],re.I)]
        print("LINKS_COUNT",len(all_links),"INTERESTING",len(interesting),"FIRST",json.dumps(interesting[:22],ensure_ascii=False),flush=True)
        print("LINKS_LAST",json.dumps(interesting[-35:],ensure_ascii=False),flush=True)
        print("SCRIPTS",[(s.get("src"),s.get("type")) for s in h.select("script")][-25:],flush=True)
        print("DATA",[(x.name,x.get("id"),x.get("class")) for x in h.select("[data-date],[data-fecha],[id*='sumario'],[class*='anuncio'],[class*='boletin']")[:22]],flush=True)
        if name.startswith("CC"):
            anchor=next((a for a in h.select("a[href]") if "anuncio.html?" in a.get("href","")),None)
            print("CC_FIRST_ANUNCIO",str(anchor.parent.parent)[:3400] if anchor else "-",flush=True)
            print("CC_MAIN",str(h.select_one("main") or h.select_one("section") or h.body)[:3600],flush=True)
        if name.startswith("BA"):
            a=next((a for a in h.select("a[href]") if "ventana_anuncio.php" in a["href"]),None)
            print("BA_FIRST",str(a.parent.parent.parent)[:3500] if a else "-",flush=True)
            print("BA_CALENDAR_LINKS",[(a.get_text(" ",strip=True),a["href"]) for a in h.select("a[href]") if re.fullmatch(r"\d{1,2}",a.get_text(" ",strip=True))][:12],flush=True)
        if name.startswith("DOE"):
            s=str(h.select_one("#contenido") or h.select_one(".contenido") or h.body)
            print("DOE_HTML_AROUND_OPOS",s[re.search(r"(?:Convocatoria|Oposiciones|Personal|Plaza)",s,re.I).start()-450:re.search(r"(?:Convocatoria|Oposiciones|Personal|Plaza)",s,re.I).start()+1300] if re.search(r"(?:Convocatoria|Oposiciones|Personal|Plaza)",s,re.I) else s[-2800:],flush=True)
            print("DOE_PDF",json.dumps([(a.get_text(" ",strip=True)[:100],urljoin(r.url,a["href"])) for a in h.select("a[href]") if re.search(r"pdf|archivo|doe",a["href"],re.I)][:22],ensure_ascii=False),flush=True)
    except Exception as e:print("ERROR",name,type(e).__name__,str(e)[:400],flush=True)
with ThreadPoolExecutor(max_workers=6) as pool:
    list(pool.map(inspect,URLS))
