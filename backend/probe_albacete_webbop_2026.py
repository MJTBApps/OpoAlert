#!/usr/bin/env python3
"""Albacete: follow editor's WebBop redirect; do not infer 30-day coverage.

Uses only publisher-controlled HTTPS endpoints, normal client and short timeouts.
Never bypass security filters or publish a production feed.
"""
import concurrent.futures,json,re,requests,time
from bs4 import BeautifulSoup
from urllib.parse import urljoin,urlsplit
URLS={
 "webbop":"https://www.dipualba.es/WebBop",
 "webbop_slash":"https://www.dipualba.es/WebBop/",
 "webbop_default":"https://www.dipualba.es/WebBop/default.aspx",
 "bop_landing":"https://www.dipualba.es/bop/",
 "webbop_rss":"https://www.dipualba.es/WebBop/rss.aspx",
 "webbop_sitemap":"https://www.dipualba.es/sitemap.xml",
 "sede_public":"https://sede.dipualba.es/default.aspx",
}
HOSTS={"www.dipualba.es","sede.dipualba.es"}
def run(item):
 key,url=item
 started=time.monotonic()
 try:
  r=requests.get(url,timeout=(6,15),headers={
    "User-Agent":"Mozilla/5.0 (compatible; OpoAlert publisher official research)",
    "Accept-Language":"es-ES,es;q=0.9"},stream=True)
  if urlsplit(r.url).hostname not in HOSTS:return {"probe":key,"status":"untrusted_redirect"}
  data=b""
  for bit in r.iter_content(8192):
   data+=bit
   if len(data)>180000:break
  r.close()
  soup=BeautifulSoup(data,"html.parser")
  text=soup.get_text(" ",strip=True)
  links=[]
  for a in soup.select("a[href]"):
   h=urljoin(r.url,a["href"])
   if urlsplit(h).hostname in HOSTS and re.search("bop|bolet|2026|sumario|index|busca|webbop",a.get_text(" ",strip=True)+" "+h,re.I):
    links.append((a.get_text(" ",strip=True)[:65],h[:180]))
  scripts=[(s.get("src") or "")[:140] for s in soup.select("script[src]") if s.get("src")]
  forms=[{"action":urljoin(r.url,f.get("action",""))[:130],"method":f.get("method","get"),
           "fields":[x.get("name") for x in f.select("input[name]")[:15]]} for f in soup.select("form")[:4]]
  security=any(s in text.lower() for s in ("captcha","verificacion de seguridad","verification required"))
  return {"probe":key,"http":r.status_code,"final":r.url,"mime":r.headers.get("Content-Type"),
   "size":len(data),"title":soup.title.get_text(" ",strip=True)[:140] if soup.title else "",
   "head":text[:320],"links":links[:20],"forms":forms,"scripts":scripts[:15],
   "securityChallenge":security,"elapsed":round(time.monotonic()-started,1)}
 except Exception as e:return {"probe":key,"error":type(e).__name__+": "+str(e)[:190],
   "elapsed":round(time.monotonic()-started,1)}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
 for result in pool.map(run,URLS.items()):
  print("ALBACETE_WEBBOP",json.dumps(result,ensure_ascii=True),flush=True)
print("NOT_AUDITED: no Albacete 30-day feed without full original verified issues",flush=True)
