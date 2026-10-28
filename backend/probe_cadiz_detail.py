#!/usr/bin/env python3
"""Inspect BOP Cadiz edition indexes and official PDF link structures."""
import requests,re
from bs4 import BeautifulSoup
URLS=["https://www.bopcadiz.es/",
 "https://www.bopcadiz.es/boletin/Boletin-numero-208-del-ano-2026/",
 "https://www.bopcadiz.es/boletin/Boletin-numero-188-del-ano-2026/",
 "https://www.bopcadiz.es/boletin/Boletin-numero-187-del-ano-2026/",
 "https://www.bopcadiz.es/export/sites/default/.boletines_pdf/2026/10_octubre/BOP208_28-10-26.pdf"]
for url in URLS:
 try:
  r=requests.get(url,timeout=25,headers={"User-Agent":"Mozilla/5.0 OpoAlert"});
  print("\nURL",url,"STATUS",r.status_code,"FINAL",r.url,"MIME",r.headers.get("Content-Type"),"BYTES",len(r.content),"HEAD",repr(r.content[:70]),flush=True)
  if r.content.startswith(b"%PDF"):continue
  soup=BeautifulSoup(r.content,"html.parser")
  print("TITLE",soup.title.get_text(" ",strip=True) if soup.title else None,flush=True)
  print("HEADINGS",[(x.name,x.get("class"),x.get_text(" ",strip=True)[:160]) for x in soup.select("h1,h2,h3,h4")[:60]],flush=True)
  print("SECTIONS",[(x.get("id"),x.get("class"),x.get_text(" ",strip=True)[:150]) for x in soup.select("main,article,section")[:35]],flush=True)
  pdf=[x for x in soup.select("a[href]") if ".pdf" in x.get("href","")]
  print("PDF_COUNT",len(pdf),flush=True)
  print("PDF_FIRST",[(x.get("href"),x.get_text(" ",strip=True)[:170],x.parent.name,x.parent.get("class"),x.parent.get_text(" ",strip=True)[:230]) for x in pdf[:15]],flush=True)
  print("PDF_LAST",[(x.get("href"),x.get_text(" ",strip=True)[:120],x.parent.name,x.parent.get("class")) for x in pdf[-8:]],flush=True)
  print("BODY",(soup.get_text(" ",strip=True))[:1200],flush=True)
  print("COUNT_HINTS",[(x.name,x.get("class"),x.get_text(" ",strip=True)[:120]) for x in soup.find_all(string=re.compile(r"\d+\s*(?:Pág|Anuncio|registros)",re.I))[:15] for x in [x.parent]],flush=True)
  if "208" in url:print("HTML_SNIPPET",str(pdf[2].parent.parent)[:6000] if len(pdf)>2 else "",flush=True)
 except Exception as ex:print("ERROR",url,type(ex).__name__,str(ex)[:230],flush=True)
