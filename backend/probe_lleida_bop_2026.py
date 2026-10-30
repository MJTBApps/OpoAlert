#!/usr/bin/env python3
"""Determine whether publisher-owned Lleida BOP 2026 can be audited from CI.

Do not confuse CIDO catalog with BOP provincial issuer. All responses
are reachability checks only; never activate partial feed.
"""
import concurrent.futures,json,re,requests,platform,time
from bs4 import BeautifulSoup
from urllib.parse import urlsplit,urljoin
HOSTS={
 "ebop_root":"https://ebop.diputaciolleida.cat/",
 "ebop_bop":"https://ebop.diputaciolleida.cat/bop/",
 "ebop_bop_index":"https://ebop.diputaciolleida.cat/bop/index.html",
 "ebop_bop_2026":"https://ebop.diputaciolleida.cat/bop/butlleti/2026",
 "ebop_2026":"https://ebop.diputaciolleida.cat/bop/2026",
 "ebop_api":"https://ebop.diputaciolleida.cat/api/",
 "alternate_ebop":"https://ebop.diputaciolleida.es/bop/",
 "alternate_www":"https://www.diputaciolleida.cat/publicacions-i-bases-de-dades/butlleti-oficial-de-la-provincia-bop/",
 "alternate_cat":"https://www.diputaciolleida.cat/",
 "publisher_info":"https://www.diputaciolleida.cat/ca/arees/area-darxius-estudis-i-informacio/recursos-i-subvencions/consultas-en-linia/butlleti-oficial-de-la-provincia-bop",
 "historic_bop":"https://www.diputaciolleida.cat/ca/publicacions-i-bases-de-dades/butlleti-oficial-de-la-provincia-bop",
 "sample":"https://ebop.diputaciolleida.cat/bop/2026/10/29/",
}
def run(pair):
 name,url=pair;begin=time.monotonic()
 try:
  with requests.Session() as sess:
   sess.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert official BOP audit)",
    "Accept-Language":"ca-ES,ca;q=0.9,es;q=0.8"})
   with sess.get(url,timeout=(6,13),stream=True,allow_redirects=True) as r:
    body=b""
    for part in r.iter_content(16384):
     body+=part
     if len(body)>110000:break
    html=BeautifulSoup(body,"html.parser")
    links=[{"text":a.get_text(" ",strip=True)[:95],"url":urljoin(r.url,a.get("href",""))[:220]}
       for a in html.select("a[href]") if re.search(r"bop|2026|edicte|butllet|pdf",a.get_text(" ",strip=True)+" "+a.get("href",""),re.I)][:30]
    return {"key":name,"http":r.status_code,"final":r.url,"mime":r.headers.get("content-type"),
      "pdf":body.startswith(b"%PDF-"),"bytes":len(body),
      "title":html.title.get_text(" ",strip=True)[:130] if html.title else "",
      "text":html.get_text(" ",strip=True)[:650],"links":links}
 except Exception as e:return {"key":name,"error":type(e).__name__+":"+str(e)[:230],
                               "elapsed":round(time.monotonic()-begin,1)}
print("BOPL_RUNNER",platform.platform(),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as ex:
 for x in ex.map(run,HOSTS.items()):
  print("BOPL_OFFICIAL_ACCESS",json.dumps(x,ensure_ascii=True),flush=True)
