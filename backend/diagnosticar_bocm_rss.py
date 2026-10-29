#!/usr/bin/env python3
"""Find exact official BOCM XML/HTML issue paths, RSS item structure, and calendar pagination."""
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
import requests,concurrent.futures,re
URLS=[
("HOME","https://www.bocm.es/"),
("RSS-SUMARIOS","https://www.bocm.es/sumarios.rss"),
("RSS-BOLETINES","https://www.bocm.es/boletines.rss"),
("LISTADO-SUMARIOS","https://www.bocm.es/listado-de-sumarios"),
("LISTADO-SUMARIOS-1","https://www.bocm.es/listado-de-sumarios?page=1"),
("LISTADO-BOLETINES","https://www.bocm.es/listado-de-boletines"),
("LISTADO-BOLETINES-1","https://www.bocm.es/listado-de-boletines?page=1"),
("PORTADA-BOCM","https://www.bocm.es/ultimo-bocm"),
]
def work(t):
 name,url=t
 try:
  z=requests.get(url,timeout=(10,24),headers={"User-Agent":"Mozilla/5.0"})
  print("\n====",name,z.status_code,z.url,"L",len(z.content),"TYPE",z.headers.get("Content-Type"),flush=True)
  if name.startswith("RSS"):
   if z.status_code!=200:return
   root=ET.fromstring(z.content)
   ch=root.find("channel")
   nodes=ch.findall("item") if ch is not None else []
   print("RSS_ITEMS",len(nodes),"CHANNEL",ch.findtext("title") if ch is not None else "-",flush=True)
   for it in nodes[:5]+nodes[-2:]:
    print("RSS_ITEM",repr(it.findtext("title")),repr(it.findtext("link")),repr(it.findtext("pubDate")),flush=True)
    txt=it.findtext("description") or ""
    h=BeautifulSoup(txt,"html.parser")
    print("DESC_LEN",len(txt),"TEXT",repr(h.get_text(" ",strip=True)[:750]),flush=True)
    print("DESC_LINKS",[(a.get_text(" ",strip=True)[:80],a.get("href")) for a in h.select("a[href]")[:12]],flush=True)
   return
  soup=BeautifulSoup(z.content,"html.parser")
  print("BODY-TEXT",repr(soup.get_text(" ",strip=True)[:950]),flush=True)
  a=[(t.get_text(" ",strip=True)[:65],urljoin(url,t.get("href",""))) for t in soup.select("a[href]") if any(w in (t.get("href","")+" "+t.get_text(" ",strip=True)).lower() for w in ["xml","bocm","sumario","boletin","boletín","2026","pdf","page=","fecha"])]
  print("LINKS",a[:80],flush=True)
  print("FORMS",[(f.get("action"),f.get("method")) for f in soup.select("form")[:10]],flush=True)
  if name=="HOME":
   print("HOME-KEYWORDS",[(match.group(0),z.text[max(0,match.start()-250):match.start()+450]) for match in list(re.finditer(r"CM_Sumario_BOCM|application/xml|Sumario|20261028|download-xml",z.text,re.I))[:14]],flush=True)
 except Exception as e:print("ERROR",name,type(e).__name__,str(e)[:280],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as p:list(p.map(work,URLS))
