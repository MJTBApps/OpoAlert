#!/usr/bin/env python3
"""Locate BOPZ 246 across official day and number searches."""
import requests,json,collections,re
END="https://www.boa.aragon.es/cgi-bin/EBOA/BRSCGI"
BASE={"CMD":"VERLST","OUTPUTMODE":"JSON","BASE":"BZHT","DOCS":"1-10000",
"SEC":"OPENDATABOAJSON","SORT":"-PUBL","SEPARADOR":"",
"@PUBL-GE":"20261023","@PUBL-LE":"20261027",
"NUMB":"","RANG":"","TITU-C":"","FDIS-C":"","TITU":"",
"ORGA-C":"","TEXT-C":"","SECC-C":"zaragoza","SECC":"","SUBS-C":""}
s=requests.Session();s.headers["User-Agent"]="Mozilla/5.0"
for name,opts in [
 ("num246",{"NUMB":"246"}),
 ("num245",{"NUMB":"245"}),
 ("num247",{"NUMB":"247"}),
 ("from23to27",{}),
 ("day24",{"@PUBL-GE":"20261024","@PUBL-LE":"20261024"}),
 ("day26",{"@PUBL-GE":"20261026","@PUBL-LE":"20261026"}),
]:
 try:
  r=s.get(END,params={**BASE,**opts},timeout=20)
  print("QUERY",name,r.status_code,len(r.content),"TYPE",r.headers.get("Content-Type"),flush=True)
  try:
   j=r.json();print("RESULTS",len(j),"NUMBERS",dict(collections.Counter(x.get("Numeroboletin") for x in j)),
    "DATES",dict(collections.Counter(x.get("FechaPublicacion") for x in j)),
    "SAMPLES",[(x.get("DOCN"),x.get("FechaPublicacion"),x.get("Numeroboletin")) for x in j[:8]],flush=True)
  except Exception as ex: print("ERROR",str(ex)[:160],"HEAD",repr(r.content[:200]),flush=True)
 except Exception as ex:print("NETWORK",str(ex)[:120],flush=True)
