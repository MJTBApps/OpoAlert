import requests,json
from concurrent.futures import ThreadPoolExecutor
BASE="https://bop.depourense.es/portalapi/api/boletin/"
ENDPOINTS=[
 ("last","ultimaFecha"),("fecha28","getFecha/20261028"),("fecha27","getFecha/20261027"),("fecha29","getFecha/20261029"),("fecha28slash","getFecha/28%2F10%2F2026"),
 ("detalle28","getDetalleBis/20261028"),("detalle28slash","getDetalleBis/28%2F10%2F2026"),
 ("listado28","listado?fecha=20261028"),("listado28slash","listado?fecha=28%2F10%2F2026"),
 ("getDetalle28","getDetalle?fecha=20261028&secciones=&tematicas=")
]
def summarise(o):
 if isinstance(o,dict):
  return {"keys":list(o),"flat":{k:v for k,v in o.items() if isinstance(v,(int,float,str,bool))},"children":{k:{"kind":type(v).__name__,"length":len(v),"first":str(v[:2] if isinstance(v,list) else list(v.items())[:3])[:2700]} for k,v in o.items() if isinstance(v,(list,dict))}}
 if isinstance(o,list):return {"kind":"array","length":len(o),"first":o[:2],"last":o[-1:] if len(o)>2 else []}
 return {"kind":type(o).__name__,"value":str(o)[:3500]}
def get(pair):
 name,path=pair
 try:
  r=requests.get(BASE+path,timeout=(10,32),headers={"Accept":"application/json","User-Agent":"Mozilla/5.0"})
  try:result=summarise(r.json())
  except ValueError:result={"text":r.text[:550]}
  return {"name":name,"status":r.status_code,"type":r.headers.get("Content-Type"),"len":len(r.content),"data":result}
 except Exception as e:return {"name":name,"error":str(e)[:230]}
with ThreadPoolExecutor(max_workers=8) as p:
 for row in p.map(get,ENDPOINTS):print("OUR_API",json.dumps(row,ensure_ascii=False)[:9500],flush=True)
