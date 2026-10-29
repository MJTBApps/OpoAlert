#!/usr/bin/env python3
"""Inspect XML hierarchy and official PDF links for the Madrid BOCM 2026 archives."""
import requests,concurrent.futures,xml.etree.ElementTree as ET,re
from bs4 import BeautifulSoup
from collections import Counter
ROOT="https://www.bocm.es"
DATA=[("28-258","2026/10/28/BOCM-20261028258.xml"),("28-259","2026/10/28/BOCM-20261028259.xml"),
("27-257","2026/10/27/BOCM-20261027257.xml"),("16-247","2026/10/16/BOCM-20261016247.xml"),
("09-241","2026/10/09/BOCM-20261009241.xml"),("30-233","2026/09/30/BOCM-20260930233.xml")]
URLS=[(label,ROOT+"/boletin/CM_Boletin_BOCM/"+path) for label,path in DATA]
URLS+= [
 ("HTML-28-258",ROOT+"/boletin-completo/BOCM-20261028/258"),
 ("HTML-28-259",ROOT+"/boletin-completo/BOCM-20261028/259"),
 ("HTML-30-233",ROOT+"/boletin-completo/BOCM-20260930/233"),
]
def shape(e,level=0,depth=4,limit=4):
 if level>=depth:return ""
 tag=e.tag.rsplit("}",1)[-1]
 s=" "*level+f"<{tag}> ATTS={str(e.attrib)[:160]} TEXT={repr((e.text or '').strip()[:150])} children={len(e)}\n"
 for x in list(e)[:limit]:s+=shape(x,level+1,depth,limit)
 return s
def one(x):
 label,url=x
 try:
  r=requests.get(url,timeout=(10,33),headers={"User-Agent":"Mozilla/5.0 (compatible; OpoAlert/1.0)"})
  print("\n===",label,r.status_code,r.url,"TYPE",r.headers.get("Content-Type"),"LEN",len(r.content),flush=True)
  if "HTML" in label:
   bs=BeautifulSoup(r.content,"html.parser")
   titles=[(a.get_text(" ",strip=True)[:100],a.get("href","")) for a in bs.select("a[href]") if "BOCM-" in a.get("href","") or "BOCM-" in a.get_text(" ",strip=True)]
   print("HTML",repr(bs.get_text(" ",strip=True)[:1400]),"COUNT LINKS",len(titles),"LINKS",titles[:12],flush=True)
   return
  print("HEAD",repr(r.content[:420]),flush=True)
  if not r.ok or not r.content.lstrip().startswith(b"<?xml"):return
  root=ET.fromstring(r.content)
  print("ROOT",root.tag,"CHILDREN",len(root),"SHAPE\n"+shape(root),flush=True)
  print("TAGS",Counter(x.tag.rsplit("}",1)[-1] for x in root.iter()).most_common(25),flush=True)
  text=r.content.decode("utf-8","replace")
  for kw in ["BOCM-20261028-","BOCM-20261016-","plaza","convocatoria","oposici"]:
   m=re.search(kw,text,re.I)
   if m:print("SAMPLE_"+kw,repr(text[max(0,m.start()-250):m.start()+700]),flush=True)
 except Exception as exc:print("ERROR",label,type(exc).__name__,str(exc)[:300],flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:list(pool.map(one,URLS))
