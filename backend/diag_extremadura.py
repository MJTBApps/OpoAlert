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

print("\n#### DEEP DIAGNOSTICS",flush=True)
CASES=[
  ("BA-28","https://www.dip-badajoz.es/bop/index.php?FechaSolicitada=20261028"),
  ("BA-SEPT","https://www.dip-badajoz.es/bop/index.php?FechaSolicitada=202609"),
  ("CC-script","https://bop.dip-caceres.es/bop/js/consultas.js"),
  ("CC-index-html","https://bop.dip-caceres.es/bop/index.html"),
  ("CC-sumario-html","https://bop.dip-caceres.es/bop/sumario.html?busqueda=numBop&id=6163"),
  ("CC-notice-html","https://bop.dip-caceres.es/bop/anuncio.html?csv=BOP-2026-4651"),
  ("DOE-29-full","https://doe.juntaex.es/ultimosdoe/mostrardoe.php?fecha=20261029&t=o"),
  ("DOE-extra","https://doe.juntaex.es/ultimosdoe/mostrardoe.php?fecha=20261028&t=e"),
  ("DOE-sept","https://doe.juntaex.es/ultimosdoe/mostrardoe.php?fecha=20260930&t=o"),
]
def deep(pair):
  name,url=pair
  try:
    r=requests.get(url,timeout=(11,30),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"})
    out={"name":name,"status":r.status_code,"length":len(r.content),"url":r.url}
    raw=r.text
    if name=="CC-script":
      out["script"]=raw[:14500]
    else:
      soup=BeautifulSoup(raw,"html.parser")
      if name.startswith("BA"):
        main=soup.select_one("#sumario_dinamico") or soup.select_one("main")
        out["mainHTML"]=str(main)[:9000]
        out["dayLinks"]=[(x.get_text(" ",strip=True),x.get("href")) for x in soup.select('a[href*="FechaSolicitada"]') if re.fullmatch(r"\\d{1,2}",x.get_text(" ",strip=True))][:35]
        a=next((a for a in soup.select('a[href*="ventana_anuncio.php"]') if "id_anuncio" in a.get("href","")),None)
        out["noticeAncestor"]=str(a.parent.parent.parent)[:4000] if a else ""
      elif name.startswith("CC"):
        out["firstTags"]=str(soup.body)[:6000]
        out["tailTags"]=str(soup.body)[-4700:]
        out["matches"]=[(w,[m.start() for m in list(re.finditer(w,raw,re.I))[:5]]) for w in ("BOP-2026","document.write","getSumario","ajax","calendar","sumario","pdf")]
        out["scripts"]=[str(s)[-1600:] for s in soup.select("script") if not s.get("src")][-6:]
      elif name.startswith("DOE"):
        elements=soup.select("div.justificado")
        out["justificadoCount"]=len(elements)
        out["justificadoExamples"]=[str(el)[:2800] for el in elements[:3]]
        out["headerText"]=soup.get_text(" ",strip=True)[-5500:-4000]
        out["firstPdf"]=[(a.get("href"),a.parent.parent.get_text(" ",strip=True)[:300]) for a in soup.select('a[href$=".pdf"]')[:5]]
    return out
  except Exception as e:return {"name":name,"error":repr(e)}
with ThreadPoolExecutor(max_workers=6) as pool:
  for row in pool.map(deep,CASES):
    print("DEEP",json.dumps(row,ensure_ascii=False),flush=True)

print("\n#### CACERES SERVICE MAP AND STRUCTURE",flush=True)
url="https://bop.dip-caceres.es/bop/js/consultas.js"
response=requests.get(url,timeout=(12,28))
js=response.text
print("CC_API_MAP",json.dumps(sorted(set(re.findall(r"""[\"'](/bop/services/[^\"']{2,140})[\"']""",js))),ensure_ascii=False),flush=True)
print("CC_JS_FUNCNAMES",re.findall(r"function\s+(\w+)\s*\(",js)[:140],flush=True)
for function in ("mostrarFicheroHtml","mostrarSumario","obtenerSumario","cargaBoletin","loadBoletin","getBoletin","getBop","cargaDatosBoletin","cargaCalendario"):
  m=re.search(r"function\s+"+function+r"\s*\(",js)
  if m: print("CC_JS_FN",function,js[m.start():m.start()+3700],flush=True)
for marker in ("services/boletines/","services/anuncios/","fecha", "sumario.html","busqueda=numBop"):
  hits=list(re.finditer(re.escape(marker),js,re.I))
  print("CC_JS_MARKER",marker,len(hits),[js[max(0,x.start()-240):x.end()+260] for x in hits[:6]],flush=True)
for name,u in [("BA-SEPT-30","https://www.dip-badajoz.es/bop/index.php?FechaSolicitada=20260930"),("BA-SEPT-CALENDAR","https://www.dip-badajoz.es/bop/index.php?FechaSolicitada=202609"),("DOE-SEPT-POST","https://doe.juntaex.es/index.php")]:
 try:
  r=requests.post(u,data={"messel":"9","aniosel":"2026"},timeout=(12,27)) if name=="DOE-SEPT-POST" else requests.get(u,timeout=(12,27))
  soup=BeautifulSoup(r.content,"html.parser")
  items=[(a.get_text(" ",strip=True),a.get("href")) for a in soup.select("a[href]") if ("FechaSolicitada=202609" in a.get("href","") or "fecha=202609" in a.get("href",""))]
  print("DIAG",name,"HTTP",r.status_code,"TITLE",soup.title.get_text(" ",strip=True) if soup.title else "", "DAY",[(x.name,x.get_text(" ",strip=True)[:140]) for x in soup.select("h1,h3,h4") if "Día" in x.get_text() or "Septiembre" in x.get_text() or "Boletín" in x.get_text()][:4],"ITEMS",items[:35],flush=True)
 except Exception as e:print("DIAG_ERR",name,repr(e),flush=True)

print("#### EXTREMADURA PRECISE NEW PROBES",flush=True)
for name in ("loadAnunciosAnunciantes","loadBopFecha","pintarUnCalendario","pintarCalendarios","mostrarUltimoBop","cargaDias","mostrarAnunciosAnunciantes","mostrarAnunciosAnunciantesPorFecha","mostrarFechaUltimoBop"):
    m=re.search(r"function\s+"+name+r"\s*\(",js)
    if m:print("CC_FN",name,js[m.start():m.start()+2500].replace("\n"," "),flush=True)
for day in ("20261001","20261002","20261012","20261013","20261029"):
  u="https://www.dip-badajoz.es/bop/index.php?FechaSolicitada="+day
  try:
    z=requests.get(u,timeout=15)
    h=BeautifulSoup(z.content,"html.parser")
    print("BA_DATE",day,z.status_code,[(t.name,t.get_text(" ",strip=True)) for t in h.select("h1,h3,h4") if "Día" in t.get_text() or "Boletín ordinario" in t.get_text() or "Boletín extraordinario" in t.get_text()][:6],flush=True)
  except Exception as e:print("BA_ERR",day,repr(e),flush=True)

print("#### CACERES REST CONTRACTS",flush=True)
API=[
 ("MONTH-OCT","https://bop.dip-caceres.es/bop/services/boletines/bopMes",{"mes":10,"anio":2026}),
 ("MONTH-SEP","https://bop.dip-caceres.es/bop/services/boletines/bopMes",{"mes":9,"anio":2026}),
 ("MONTH-CALENDAR","https://bop.dip-caceres.es/bop/services/boletines/bopMesCalendario",{"mes":10,"anio":2026}),
 ("ISSUE","https://bop.dip-caceres.es/bop/services/anuncios/anunciosAnunciantes",{"idBoletin":6163}),
 ("ISSUE-LAST","https://bop.dip-caceres.es/bop/services/boletines/ultimoBop",{}),
 ("SAMPLE-ANN","https://bop.dip-caceres.es/bop/services/anuncios/contenidoPdfIdAnuncio",{"csv":"BOP-2026-4651"}),
 ("SAMPLE-BOP","https://bop.dip-caceres.es/bop/services/boletines/contenidoPdfIdBolentin",{"idBoletin":6163}),
]
def probe_api(x):
 name,u,params=x
 try:
  r=requests.get(u,params=params,timeout=(11,30),stream=True)
  if "pdf" in r.headers.get("Content-Type","").lower():
   raw=next(r.iter_content(140),b"")
   v={"name":name,"status":r.status_code,"pdf":repr(raw[:40]),"type":r.headers.get("Content-Type")}
   r.close()
   return v
  body=r.content
  try:
   j=r.json()
   data=j.get("data") if isinstance(j,dict) else None
   return {"name":name,"status":r.status_code,"total":j.get("total") if isinstance(j,dict) else None,
       "keys":list(j) if isinstance(j,dict) else None,"dataType":type(data).__name__,
       "dataCount":len(data) if isinstance(data,list) else None,
       "first":data[:2] if isinstance(data,list) else data,
       "last":data[-1] if isinstance(data,list) and data else None}
  except ValueError:return {"name":name,"status":r.status_code,"type":r.headers.get("Content-Type"),"bytes":repr(body[:200])}
 except Exception as e:return {"name":name,"error":repr(e)}
with ThreadPoolExecutor(max_workers=7) as pool:
 for x in pool.map(probe_api,API):print("CC_REST",json.dumps(x,ensure_ascii=False)[:9000],flush=True)

print("#### BADAJOZ HEADER SPECIAL CASES",flush=True)
for day in ("20261021","20261012","20261029"):
  r=requests.get("https://www.dip-badajoz.es/bop/index.php?FechaSolicitada="+day,timeout=(9,22))
  h=BeautifulSoup(r.content,"html.parser")
  print("BADAJOZ_HEADERS",day,"HTTP",r.status_code,"H3",[x.get_text(" ",strip=True) for x in h.select("h3") if "Boletín" in x.get_text()],"ARTICLES",len(h.select("#sumario_dinamico article")),"DETAILS",[(s.get("class"),len(s.select("article")),s.get_text(" ",strip=True)[:300]) for s in h.select("#sumario_dinamico > details")],"PDFLINKS",[(a.get_text(" ",strip=True),a.get("href","")) for a in h.select('a[href*="boletin_completo"]')],flush=True)
