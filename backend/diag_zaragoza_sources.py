#!/usr/bin/env python3
"""Probe official Aragón BOPZ open-data endpoint and alternative Diputación portals."""
import requests
from urllib.parse import urlencode
import json
import re
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor

END="https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI"
BASE={
 "CMD":"VERLST","OUTPUTMODE":"JSON","BASE":"BZHT","DOCS":"1-10000",
 "SEC":"OPENDATABOAJSON","SORT":"-PUBL","SEPARADOR":"",
 "@PUBL-GE":"20261027","@PUBL-LE":"20261028",
 "NUMB":"","RANG":"","TITU-C":"","FDIS-C":"","TITU":"",
 "ORGA-C":"","TEXT-C":"","SECC-C":"zaragoza","SECC":"","SUBS-C":"sexta",
}
SEARCHES=[
 ("dataset 2 days",END,BASE),
 ("dataset month",END,{**BASE,"@PUBL-GE":"20260929"}),
 ("dataset year 2017",END,{**BASE,"@PUBL-GE":"20170102","@PUBL-LE":"20170104"}),
 ("without section",END,{**BASE,"@PUBL-GE":"20261027","@PUBL-LE":"20261028","SECC-C":"","SUBS-C":""}),
 ("xml one day",END,{**BASE,"OUTPUTMODE":"XML","SEC":"OPENDATABOAXML"}),
 ("bop.dpz.es","https://bop.dpz.es/BOPZ/",None),
 ("boletin.dpz.es","https://boletin.dpz.es/BOPZ/",None),
 ("www.dpz.es","https://www.dpz.es/ciudadano/boletin-oficial-provincia",None),
 ("www.boa.aragon.es portal","https://www.boa.aragon.es/",None),
]
def get(spec):
 name,url,params=spec
 print("\n=== PROBE",name,flush=True)
 try:
  with requests.Session() as sess:
   s=sess.get(url,params=params,timeout=25,headers={"User-Agent":"Mozilla/5.0","Accept":"application/json, application/xml, text/html;q=0.9"})
   raw=s.content[:60000]
   print("STATUS",s.status_code,"FINAL",s.url[:500],"CTYPE",s.headers.get("Content-Type"),"BYTES",len(s.content),flush=True)
   print("RAW",repr(raw[:5000].decode(s.encoding or "utf-8","replace")),flush=True)
   try:
    j=s.json()
    print("JSON_TYPE",type(j).__name__,"TOP_KEYS",list(j)[:20] if isinstance(j,dict) else "-","JSON",json.dumps(j,ensure_ascii=False)[:9000],flush=True)
   except Exception:pass
   if "html" in s.headers.get("Content-Type","").lower():
    soup=BeautifulSoup(raw,"html.parser")
    print("TITLE",soup.title.get_text(" ",strip=True) if soup.title else None,flush=True)
    print("TEXT",soup.get_text(" ",strip=True)[:2000],flush=True)
    print("LINKS",[(a.get("href"),a.get_text(" ",strip=True)[:50]) for a in soup.select("a[href]")[:55]],flush=True)
 except Exception as exc:print("ERROR",type(exc).__name__,str(exc)[:320],flush=True)
with ThreadPoolExecutor(max_workers=3) as pool:
 list(pool.map(get,SEARCHES))
