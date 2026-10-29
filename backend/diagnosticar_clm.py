#!/usr/bin/env python3
"""Source reconnaissance for Castilla-La Mancha, do not publish feeds."""
import concurrent.futures,requests,re,json
from bs4 import BeautifulSoup
from urllib.parse import urljoin
URLS={
"ALBACETE":["https://bop.dipualba.es/","https://bop.dipualba.es/servicesajax/descargararchivobopcompleto/?a=22646"],
"CIUDAD_REAL":["https://bop.dipucr.es/","https://bop.dipucr.es/buscador"],
"CUENCA":["https://www.dipucuenca.es/boletin-oficial-de-la-provincia","https://bop.dipucuenca.es/"],
"GUADALAJARA":["https://boletin.dguadalajara.es/boletin/","https://boletin.dguadalajara.es/boletin/index.php/9-general/66386-Boletin-Oficial-de-la-Provincia-de-Guadalajara-num-204-de-lunes-26-de-Octubre-de-2026"],
"TOLEDO":["https://bop.diputoledo.es/","https://bop.diputoledo.es/webEbop/","https://bop.diputoledo.es/webEbop/csv.jsp"],
"DOCM":["https://docm.jccm.es/docm/"]
}
def run(t):
 label,url=t
 try:
  z=requests.get(url,timeout=(8,18),headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"},allow_redirects=True)
  print("\n========",label,z.status_code,z.url,"type",z.headers.get("Content-Type"),"bytes",len(z.content),flush=True)
  if "html" not in z.headers.get("Content-Type","").lower():
   print("HEAD",repr(z.content[:110]),flush=True)
   return
  s=BeautifulSoup(z.content,"html.parser")
  print("TITLE",s.title.get_text(" ",strip=True)[:250] if s.title else "-",flush=True)
  print("BODY",repr(s.get_text(" ",strip=True)[:1550]),flush=True)
  links=[(x.get_text(" ",strip=True)[:85],urljoin(z.url,x["href"])) for x in s.select("a[href]")]
  ranked=[x for x in links if re.search(r"bop|boletin|boletín|2026|octubre|pdf|hemeroteca|rss|xml|busca|anuncio",str(x),re.I)]
  print("LINKCOUNT",len(links),"RANKED",json.dumps(ranked[:95],ensure_ascii=False),flush=True)
  print("FORMS",json.dumps([(x.get("action"),x.get("method"),[(v.get("name"),v.get("value")) for v in x.select("input[name]")[:9]]) for x in s.select("form")[:7]],ensure_ascii=False),flush=True)
  print("SCRIPTS",json.dumps([x.get("src") for x in s.select("script[src]")[-8:]],ensure_ascii=False),flush=True)
 except Exception as e:print("ERROR",label,url,type(e).__name__,str(e)[:270],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=7) as p:list(p.map(run,[(k,u) for k,ls in URLS.items() for u in ls]))
