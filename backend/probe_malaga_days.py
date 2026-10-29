#!/usr/bin/env python3
"""Probe official Málaga BOP day-select and original-edict hyperlinks."""
import json,requests,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
s=requests.Session()
s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
for name,url in [
("28","https://www.bopmalaga.es/sumario.php?fecha=28-10-2026"),
("27","https://www.bopmalaga.es/sumario.php?fecha=27-10-2026"),
("30sep","https://www.bopmalaga.es/sumario.php?fecha=30-09-2026"),
("29","https://www.bopmalaga.es/sumario.php?fecha=29-10-2026"),
("29dot","https://www.bopmalaga.es/sumario.php.?fecha=29-10-2026"),
("octcalendar","https://www.bopmalaga.es/sumario.php?fecha=01-10-2026")
]:
 try:
  r=s.get(url,timeout=(7,20),allow_redirects=True)
  h=BeautifulSoup(r.content,"html.parser")
  event=h.select_one("h2 time[datetime]")
  entries=h.select("section article")
  calendar=h.select("#table_calendario a[href]")
  p=h.select('#lista_pdf a[href*="verificacion.php"]')
  article=h.select_one('a[href*="edicto.php?edicto="]')
  print("MALAGA_DAY",json.dumps({"name":name,"http":r.status_code,"url":r.url,"size":len(r.content),
   "title":h.title.get_text(" ",strip=True) if h.title else "",
   "datetime":event.get("datetime") if event else None,"h2":h.select_one("h2").get_text(" ",strip=True)[:130] if h.select_one("h2") else None,
   "calendar":len(calendar),"firstCal":[(x.get("title"),x.get("href")) for x in calendar[:4]],
   "items":len(entries),"pdfs":len(p),"firstPdf":[(x.get_text(" ",strip=True)[:110],x.get("href")) for x in p[:3]],
   "article":urljoin(r.url,article["href"]) if article else None,
   "text":h.get_text(" ",strip=True)[-450:]},ensure_ascii=True),flush=True)
 except Exception as ex:print("MALAGA_ERROR",name,type(ex).__name__,str(ex)[:260],flush=True)
