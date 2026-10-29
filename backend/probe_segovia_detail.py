#!/usr/bin/env python3
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests
BASE="https://www.dipsegovia.es/bop"
h=BeautifulSoup(requests.get(BASE,timeout=(9,19)).content,"html.parser")
a=next((a for a in h.select('a[href*="articleId="]') if "28 de octubre" in a.get_text(" ",strip=True)),None)
if a is None:
 a=next((a for a in h.select('a[href*="articleId="]') if "viernes" in a.get_text(" ",strip=True)),None)
if a:
 url=urljoin(BASE,a["href"])
 print("TARGET",url,flush=True)
 r=requests.get(url,timeout=(10,23))
 soup=BeautifulSoup(r.content,"html.parser")
 print("RESPONSE",r.status_code,len(r.content),r.url,"TITLE",soup.title.get_text(" ",strip=True) if soup.title else "-",flush=True)
 print("H",[(x.name,x.get_text(" ",strip=True)[:80]) for x in soup.select("h1,h2,h3,h4")[-20:],flush=True)
 print("TEXT",repr(soup.get_text(" ",strip=True)[-3000:]),flush=True)
 print("PDF",[(x.get_text(" ",strip=True)[:130],urljoin(r.url,x["href"])[:350]) for x in soup.select("a[href]") if ".pdf" in x["href"].lower() or "descargar" in x.get_text(" ",strip=True).lower()][-35:],flush=True)
 print("IFRAME",[(x.get("src"),x.get("id")) for x in soup.select("iframe")[:8]],flush=True)
