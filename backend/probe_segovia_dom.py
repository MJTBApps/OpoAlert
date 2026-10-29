#!/usr/bin/env python3
import requests,re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
url="https://www.dipsegovia.es/bop"
for key,u in [("BASE",url),("P1",url+"?page=1"),("DATE",url+"?fecha=28-10-2026")]:
 try:
  r=requests.get(u,timeout=(9,20),headers={"User-Agent":"Mozilla/5.0"})
  h=BeautifulSoup(r.content,"html.parser")
  print("\n###",key,r.status_code,len(r.content),r.url,flush=True)
  links=[a for a in h.select("a[href]") if "articleId=" in a["href"]]
  print("LINKS",len(links),[(x.get_text(" ",strip=True)[:70],x.get("href","")[-100:]) for x in links[:22]],flush=True)
  if links:
   a=links[0]
   print("CARD",str(a.parent.parent.parent)[:4500],flush=True)
  print("PAGINATION",[(x.name,x.get("class"),str(x)[:1500]) for x in h.select(".pagination,.lfr-pagination,.portlet-content-container")[:4]],flush=True)
  print("PDFS",[(a.get_text(" ",strip=True)[:65],a["href"][:210]) for a in h.select("a[href]") if ".pdf" in a["href"].lower()][:20],flush=True)
 except Exception as ex:print("ERROR",key,type(ex).__name__,str(ex)[:220],flush=True)
