#!/usr/bin/env python3
"""Inspect official Málaga BOP headings and editions using reachable macOS network."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
from bs4 import BeautifulSoup
import requests,re
DAYS=["29-10-2026","28-10-2026","20-10-2026","01-10-2026","30-09-2026"]
def run(d):
 url="https://www.bopmalaga.es/sumario.php?fecha="+d
 try:
  r=requests.get(url,timeout=(8,18),headers={"User-Agent":"Mozilla/5.0"})
  soup=BeautifulSoup(r.content,"html.parser")
  print("\n=== DAY",d,r.status_code,r.url,"SIZE",len(r.content),"TITLE",soup.title.get_text(" ",strip=True) if soup.title else "-",flush=True)
  print("HEADINGS",[(h.name,h.get_text(" ",strip=True)[:170],str(h.parent)[:400]) for h in soup.select("h1,h2,h3,h4")[:24]],flush=True)
  print("TEXT",repr(soup.get_text(" ",strip=True)[:1300]),flush=True)
  links=[a for a in soup.select("a[href]") if "pdf" in a.get("href","").lower() or "edicto" in a.get("href","").lower()]
  print("PDFS",[(a.get_text(" ",strip=True)[:90],urljoin(url,a.get("href",""))) for a in links[:24]],flush=True)
  print("TABLES",[(x.get("class"),len(x.select("tr")),str(x)[:1600]) for x in soup.select("table")[:6]],flush=True)
  print("ALL-DL",str(soup.select_one("main") or soup.select_one("#contenedor") or soup.body)[-8500:],flush=True)
 except Exception as ex:print("ERR",d,type(ex).__name__,str(ex)[:300],flush=True)
with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run,DAYS))
