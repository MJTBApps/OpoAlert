#!/usr/bin/env python3
"""Explore official Cádiz BOP edition and original announcement endpoints."""
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urljoin
import requests,re
from bs4 import BeautifulSoup
ROOT="https://www.bopcadiz.es/"
URLS=[
 ROOT,ROOT+"boletin",ROOT+"boletin?fecha=28/10/2026",
 ROOT+"boletin?anio=2026&numero=208",
 ROOT+"boletin/208-2026",ROOT+"boletin/2026/208",
 ROOT+"boletin?numero=208&ano=2026",
 ROOT+"boletin?fechaBoletin=28%2F10%2F2026",
 ROOT+"boletin/2026-208",ROOT+"boletin?year=2026&number=208",
 "https://bopcadiz.es/"
]
def inspect(url):
 print("\nURL",url,flush=True)
 try:
  r=requests.get(url,headers={"User-Agent":"Mozilla/5.0 OpoAlert audit","Accept-Language":"es"},timeout=(8,22))
  print("STATUS",r.status_code,"URL",r.url,"CTYPE",r.headers.get("content-type"),"BYTES",len(r.content),flush=True)
  if r.content[:4]==b"%PDF":print("PDF OK",repr(r.content[:28]),flush=True);return
  soup=BeautifulSoup(r.content,"html.parser")
  print("TITLE",soup.title.get_text(" ",strip=True) if soup.title else "-",flush=True)
  print("BODY",soup.get_text(" ",strip=True)[:2500],flush=True)
  print("LINKS",[(a.get("href"),a.get_text(" ",strip=True)[:110]) for a in soup.select("a[href]")[:85]],flush=True)
  print("FORMS",[(f.get("action"),f.get("method"),[(i.get("name"),i.get("value")) for i in f.select("input[name]")[:12]]) for f in soup.select("form")[:5]],flush=True)
  print("SELECTS",[(s.get("name"),[(o.get("value"),o.get_text(" ",strip=True)) for o in s.select("option")[:8]]) for s in soup.select("select")[:4]],flush=True)
 except Exception as e:print("ERROR",type(e).__name__,str(e)[:240],flush=True)
with ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(inspect,URLS))
