#!/usr/bin/env python3
"""Investigate anomalous official BOPZ days only, without printing personal data."""
from datetime import date
from urllib.parse import urlencode
from collections import Counter
import requests,json,re,xml.etree.ElementTree as ET
END="https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI"
P={"CMD":"VERLST","OUTPUTMODE":"JSON","BASE":"BZHT","DOCS":"1-10000",
"SEC":"OPENDATABOAJSON","SORT":"-PUBL","SEPARADOR":"","@PUBL-GE":"","@PUBL-LE":"",
"NUMB":"","RANG":"","TITU-C":"","FDIS-C":"","TITU":"","ORGA-C":"","TEXT-C":"",
"SECC-C":"zaragoza","SECC":"","SUBS-C":""}
s=requests.Session()
for d in [date(2026,9,30),date(2026,10,22),date(2026,10,24),date(2026,10,26)]:
 p={**P,"@PUBL-GE":d.strftime("%Y%m%d"),"@PUBL-LE":d.strftime("%Y%m%d")}
 for fmt in ["JSON","XML"]:
  p.update({"OUTPUTMODE":fmt,"SEC":"OPENDATABOAJSON" if fmt=="JSON" else "OPENDATABOAXML"})
  try:
   r=s.get(END,params=p,timeout=18)
   print("DAY",d,fmt,"HTTP",r.status_code,"bytes",len(r.content),"head",repr(r.content[:120]),flush=True)
   if fmt=="JSON":
    try:
     j=r.json()
     print("JSON_COUNT",len(j),"NUMBERS",Counter(x.get("Numeroboletin") for x in j).most_common(),"SAMPLES",[(x.get("DOCN"),x.get("Numeroboletin"),x.get("NOrden")) for x in j[:3]],flush=True)
    except json.JSONDecodeError as ex:
     a=max(0,ex.pos-50);b=min(len(r.text),ex.pos+75)
     excerpt=r.text[a:b]
     print("JSON_ERROR",type(ex).__name__,str(ex)[:140],"AROUND",repr(excerpt),flush=True)
     fixed=re.sub(r"\\(?![\"\\/bfnrtu])",r"\\\\",r.text)
     try:
      j=json.loads(fixed)
      print("REPAIRED_COUNT",len(j),"NUMBERS",Counter(x.get("Numeroboletin") for x in j),"SECOND_ERROR",None,flush=True)
     except Exception as fx:print("SECOND_ERROR",str(fx)[:180],flush=True)
    except Exception as ex:print("OTHER_ERROR",str(ex)[:180],flush=True)
   else:
    try:
     root=ET.fromstring(r.content)
     regs=root.findall("registro")
     print("XML_COUNT",len(regs),"ROOT",root.tag,"TAGNAMES", [x.tag for x in regs[0]][:18] if regs else [],flush=True)
    except Exception as ex:print("XML_ERROR",str(ex)[:180],flush=True)
  except Exception as ex:print("NETWORK_ERROR",d,fmt,type(ex).__name__,str(ex)[:160],flush=True)
