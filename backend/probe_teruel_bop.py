#!/usr/bin/env python3
"""Investigate official Teruel BOP publication and archive structure."""
from urllib.request import Request,urlopen
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from urllib.error import HTTPError
import re
urls=[
 "https://bender.dpteruel.es/dpt/bopt.nsf/inicio.xsp",
 "https://bender.dpteruel.es/dpt/bopt.nsf/",
 "https://www.dpteruel.es/DPTweb/la-diputacion/boletin-oficial/",
]
for url in urls:
 print("\nURL",url,flush=True)
 try:
  with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"}),timeout=22) as r:
   raw=r.read(900_000);print("STATUS",r.status,"FINAL",r.url,"TYPE",r.headers.get("content-type"),"BYTES",len(raw),flush=True)
  soup=BeautifulSoup(raw,"html.parser")
  print("TITLE",soup.title.get_text(" ",strip=True) if soup.title else "-",flush=True)
  print("TEXT",soup.get_text(" ",strip=True)[:2500],flush=True)
  print("FORMS",[(f.get("action"),f.get("id"),f.get("method")) for f in soup.select("form")[:10]],flush=True)
  print("LINKS",[(a.get("href"),a.get_text(" ",strip=True)[:80]) for a in soup.select("a[href]")[:110]],flush=True)
  print("INPUTS",[(i.get("name"),i.get("id"),i.get("value"),i.get("type")) for i in soup.select("input")[:35]],flush=True)
  print("SCRIPTS",[(x.get("src")) for x in soup.select("script[src]")[:20]],flush=True)
 except Exception as e:print("ERROR",type(e).__name__,str(e)[:400],flush=True)


# Inspect official announcement, historical search, calendar script and daily PDF.
from urllib.parse import urlsplit
MORE=[
 "https://bender.dpteruel.es/dpt/bopt.nsf/historicos.xsp",
 "https://bender.dpteruel.es/dpt/bopt.nsf/busquedas.xsp",
 "https://bender.dpteruel.es/dpt/bopt.nsf/busquedasn.xsp",
 "https://bender.dpteruel.es/dpt/bopt.nsf/0/78AF45C9E931954CC1258E9D0035774E",
 "https://bender.dpteruel.es/dpt/bopt.nsf/0/78AF45C9E931954CC1258E9D0035774E?OpenDocument",
 "https://bender.dpteruel.es/DPT/bopt.nsf/Redireccion?OpenPage&dia=20261028",
 "https://bender.dpteruel.es/DPT/bopt.nsf/Redireccion?OpenPage&dia=20261027",
 "https://bender.dpteruel.es/DPT/bopt.nsf/Redireccion?OpenPage&dia=20261024",
 "https://236ws.dpteruel.es/DPT/bopt.nsf/calendarportada-siniframe.js",
]
for url in MORE:
 print("\nPROBE",url,flush=True)
 try:
  with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0","Accept-Language":"es"}),timeout=20) as r:
   raw=r.read(750_000)
   print("HTTP",r.status,"URL",r.url,"TYPE",r.headers.get("content-type"),"SIZE",len(raw),"TOTAL",r.headers.get("content-length"),flush=True)
  if raw[:4]==b"%PDF":
   print("PDF HEADER",raw[:50],flush=True)
   continue
  soup=BeautifulSoup(raw,"html.parser")
  print("TEXT",soup.get_text(" ",strip=True)[:1800],flush=True)
  print("FORMS",[(f.get("action"),f.get("id")) for f in soup.select("form")[:8]],flush=True)
  print("LINKS",[(a.get("href"),a.get_text(" ",strip=True)[:65]) for a in soup.select("a[href]")[:55]],flush=True)
  print("INPUTS",[(i.get("name"),i.get("id"),i.get("type")) for i in soup.select("input")[:35]],flush=True)
  print("HTML EXCERPT",raw.decode("utf-8","replace")[:1900],flush=True)
 except Exception as e:print("ERROR",type(e).__name__,str(e)[:320],flush=True)
