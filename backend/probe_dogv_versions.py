import requests,json
B="https://dogv.gva.es/dogv-portal/dogv"
for n,d in [(10473,"2026-10-19"),(10468,"2026-10-08"),(10480,"2026-10-27"),(10482,"2026-10-29")]:
 r=requests.get(f"{B}/{n}/versionesSumario",timeout=35)
 try:versions=r.json()
 except ValueError:print("BAD",n,r.status_code,r.text[:300]);continue
 print("DOGV_VERSIONS",n,d,versions,flush=True)
 for version in versions:
  t=requests.get(f"{B}/{n}",params={"ordenSumario":version,"lang":"es_es"},timeout=38)
  try:obj=t.json()
  except ValueError:print("DOGV_BAD",n,version,t.status_code);continue
  docs=obj.get("disposiciones",[])
  print("DOGV_VERSION",n,version,"HTTP",t.status_code,"fecha",obj.get("fechaSumario"),"esBis",obj.get("esBis"),"urlPdf",obj.get("urlPdf"),"total",len(docs),"ids",[x.get("codigoInsercion") for x in docs[:30]],flush=True)
