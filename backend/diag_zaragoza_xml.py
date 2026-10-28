#!/usr/bin/env python3
"""Validate official BOPZ XML for 30 days, compare JSON per day and issue numbers."""
from datetime import date,timedelta
from urllib.parse import urlsplit
from concurrent.futures import ThreadPoolExecutor
from collections import Counter,defaultdict
import requests,json,re,xml.etree.ElementTree as ET
ROOT="https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI"
BASE={"CMD":"VERLST","OUTPUTMODE":"XML","BASE":"BZHT","DOCS":"1-10000",
"SEC":"OPENDATABOAXML","SORT":"-PUBL","SEPARADOR":"",
"@PUBL-GE":"","@PUBL-LE":"","NUMB":"","RANG":"","TITU-C":"",
"FDIS-C":"","TITU":"","ORGA-C":"","TEXT-C":"","SECC-C":"zaragoza",
"SECC":"","SUBS-C":""}
start=date(2026,9,29);end=date(2026,10,28)
def request(day):
 params={**BASE,"@PUBL-GE":day.strftime("%Y%m%d"),"@PUBL-LE":day.strftime("%Y%m%d")}
 sess=requests.Session()
 sess.headers["User-Agent"]="Mozilla/5.0 (OpoAlert BOPZ audit)"
 try:
  r=sess.get(ROOT,params=params,timeout=28)
  try:
   root=ET.fromstring(r.content)
   rows=root.findall("./registro")
   if not rows: print("XML_EMPTY",day,r.status_code,len(r.content),"HEAD",repr(r.content[:220]),flush=True)
   xml=[{"id":x.findtext("docn"),"date":x.findtext("fecha"),"section":x.findtext("seccion"),
    "subsection":x.findtext("subseccion"),"url":x.findtext("url")} for x in rows]
   allids={x["id"] for x in xml}
   if len(allids)!=len(xml):print("XML_DUPES",day,len(xml),len(allids),flush=True)
  except Exception as ex:
   print("XML_ERROR",day,type(ex).__name__,str(ex)[:200],"HEAD",repr(r.content[:150]),flush=True);xml=[]
  params.update({"OUTPUTMODE":"JSON","SEC":"OPENDATABOAJSON"})
  r2=sess.get(ROOT,params=params,timeout=28)
  try:
   js=r2.json()
   if not isinstance(js,list):raise ValueError(type(js))
   ids=[x.get("DOCN") for x in js]
   totals={x.get("NOrden","").split(" de ")[-1] for x in js}
   if len(js)!=len(xml) or set(ids)!={x["id"] for x in xml}:
    print("DIFF",day,len(js),len(xml),"diff_ids",sorted(set(ids)^{x["id"] for x in xml})[:12],flush=True)
   json_summary=f"JSON {len(js)} totals={totals}"
  except Exception as ex:json_summary=f"JSON ERROR {type(ex).__name__} {str(ex)[:140]}"
  print("DAY",day.isoformat(),"XML",len(xml),"JSON",json_summary,
   "sections",Counter(x["subsection"] for x in xml).most_common(4),
   "one",xml[0] if xml and day.day==28 else "",flush=True)
  return day,xml
 except Exception as ex:print("NETWORK_ERROR",day,type(ex).__name__,str(ex)[:190],flush=True);return day,[]
 finally:sess.close()
days=[start+timedelta(days=i) for i in range(30)]
with ThreadPoolExecutor(max_workers=4) as p:
 results=list(p.map(request,days))
print("TOTALS",sum(len(x) for _,x in results),"pubdates",[str(d) for d,x in results if x],
 "nonpub",[str(d) for d,x in results if not x],flush=True)
