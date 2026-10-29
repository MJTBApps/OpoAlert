#!/usr/bin/env python3
from collections import Counter
from bs4 import BeautifulSoup
from urllib.parse import urlsplit
import requests,xml.etree.ElementTree as ET
U="https://www.bocm.es"
def get(url):
 r=requests.get(url,timeout=(12,30),headers={"User-Agent":"Mozilla/5.0"})
 print("GET",r.status_code,url,len(r.content),flush=True)
 r.raise_for_status()
 return r
for day,n in [("2026/10/16",247),("2026/10/28",258)]:
 r=get(f"{U}/boletin/CM_Boletin_BOCM/{day}/BOCM-{day.replace('/','')}{n}.xml")
 root=ET.fromstring(r.content)
 pmap={c:p for p in root.iter() for c in p}
 ds=root.findall(".//disposicion")
 print("ISSUE",n,"records",len(ds),flush=True)
 for d in ds[:6]+ds[-6:]:
  x=d
  chain=[]
  while x in pmap:
   x=pmap[x]
   if x.tag in ("organismo","seccion","apartado"):
    chain.append((x.tag,x.attrib, x.findtext("titulo"),x.findtext("nombre")))
  print("ROW",d.findtext("identificador"),"PATH",str(chain)[:1300],"title",repr(d.findtext("titulo"))[:240],flush=True)
for day,num in [("2026/10/28",37),("2026/10/16",2)]:
 u=f"{U}/boletin/CM_Orden_BOCM/{day}/BOCM-{day.replace('/','')}-{num}.json"
 r=get(u)
 data=r.json()
 print("JSON",list(data),"VALUES",str(data)[:5100],flush=True)
