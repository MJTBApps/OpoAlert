#!/usr/bin/env python3
"""Check entire 30-day BOP Zaragoza official XML / corrected JSON in two requests."""
import requests,re,json,xml.etree.ElementTree as ET
from collections import Counter,defaultdict
ROOT="https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI"
p={"CMD":"VERLST","OUTPUTMODE":"JSON","BASE":"BZHT","DOCS":"1-10000",
"SEC":"OPENDATABOAJSON","SORT":"-PUBL","SEPARADOR":"","@PUBL-GE":"20260929",
"@PUBL-LE":"20261028","NUMB":"","RANG":"","TITU-C":"","FDIS-C":"",
"TITU":"","ORGA-C":"","TEXT-C":"","SECC-C":"zaragoza","SECC":"","SUBS-C":""}
s=requests.Session();s.headers["User-Agent"]="Mozilla/5.0 OpoAlert BOPZ 30 day audit"
docs={}
for fmt in ["JSON","XML"]:
 q={**p,"OUTPUTMODE":fmt,"SEC":"OPENDATABOAJSON" if fmt=="JSON" else "OPENDATABOAXML"}
 try:
  r=s.get(ROOT,params=q,timeout=50)
  print("RESPONSE",fmt,r.status_code,len(r.content),r.headers.get("Content-Type"),repr(r.content[:180]),flush=True)
  if fmt=="JSON":
   data=r.content.decode("ISO-8859-1")
   try:
    arr=json.loads(data)
    print("JSON NORMAL OK",flush=True)
   except Exception as ex:
    print("JSON ORIGINAL ERROR",str(ex)[:150],flush=True)
    fixed=re.sub(r"\\(?![\"\\/bfnrtu])",r"\\\\",data)
    arr=json.loads(fixed)
    print("JSON REPAIR OK",len(arr),"size delta",len(fixed)-len(data),flush=True)
   docs["JSON"]=set(x["DOCN"] for x in arr)
   print("COUNT JSON",len(arr),"DATES",Counter(x["FechaPublicacion"] for x in arr).most_common(31),
    "BOP",sorted(Counter((x["FechaPublicacion"],x["Numeroboletin"]) for x in arr).items()),
    "ORDINAL_FIRSTLAST",arr[0]["NOrden"],arr[-1]["NOrden"],flush=True)
  else:
   root=ET.fromstring(r.content)
   arr=root.findall("./registro")
   docs["XML"]=set(x.findtext("docn") for x in arr)
   print("COUNT XML",len(arr),"DATES",Counter(x.findtext("fecha") for x in arr).most_common(31),
    "TOP",root.tag,flush=True)
 except Exception as ex:
  print("ERROR",fmt,type(ex).__name__,str(ex)[:350],flush=True)
print("CROSSCHECK",len(docs.get("XML",set())^docs.get("JSON",set())),flush=True)
