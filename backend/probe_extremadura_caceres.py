#!/usr/bin/env python3
"""Read-only Cáceres BOP API archive diagnostics."""
from concurrent.futures import ThreadPoolExecutor
import requests,json
BASE="https://bop.dip-caceres.es/bop/services/"
cases=[
("bopMesSep","boletines/bopMes",{"mes":9,"anio":2026}),
("bopMesCalendarSep","boletines/bopMesCalendario",{"mes":9,"anio":2026}),
("bopMesAntSigSep","boletines/bopMesAntSig",{"mes":9,"anio":2026}),
("bopMesAug","boletines/bopMesCalendario",{"mes":8,"anio":2026}),
("bopMesOct","boletines/bopMesCalendario",{"mes":10,"anio":2026}),
("fechaSep30","anuncios/fechaPublicacion",{"fechaPublic":"09/30/2026"}),
("fechaSep29","anuncios/fechaPublicacion",{"fechaPublic":"09/29/2026"}),
("anunciosSep","anuncios/anunciosAnunciantes",{"idBoletin":6159}),
]
def probe(a):
 name,path,p=a
 try:
  r=requests.get(BASE+path,params=p,timeout=(10,26),headers={"User-Agent":"Mozilla/5.0"})
  v=r.json();records=v.get("data") if isinstance(v,dict) else None
  if isinstance(records,list):
   row=[{k:x.get(k) for k in ("idBoletin","diaBop","fecha","numBop","fechaPublicacion","idAnuncio","csv","nombreEntidad","tituloAnuncio")} for x in records[:3]]
   tail=[{k:x.get(k) for k in ("idBoletin","diaBop","fecha","numBop","fechaPublicacion","idAnuncio","csv","nombreEntidad","tituloAnuncio")} for x in records[-2:]]
   return {"name":name,"status":r.status_code,"total":v.get("total"),"len":len(records),"head":row,"tail":tail}
  return {"name":name,"status":r.status_code,"body":str(v)[:900]}
 except Exception as e:return {"name":name,"error":repr(e)}
with ThreadPoolExecutor(max_workers=6) as pool:
 for result in pool.map(probe,cases):print("REST",json.dumps(result,ensure_ascii=False),flush=True)
