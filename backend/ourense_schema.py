import requests,json
for d in ["20261029","20261028","20260930","20261003"]:
 r=requests.get("https://bop.depourense.es/portalapi/api/boletin/getFecha/"+d,timeout=(12,35))
 try:j=r.json()
 except Exception as e:print("OUR_SHAPE",d,r.status_code,r.text[:250]);continue
 print("OUR_SHAPE",d,"http",r.status_code,"records",len(j) if isinstance(j,list) else type(j).__name__,flush=True)
 if not isinstance(j,list) or not j:continue
 for x in j[:2]:
  print("OUR_ROOT",d,"keys",list(x),"flat",{k:str(v)[:220] for k,v in x.items() if not isinstance(v,(list,dict))},flush=True)
  for k,v in x.items():
   if isinstance(v,dict):
    print("OUR_OBJECT",k,"keys",list(v),"flat",{q:str(w)[:250] for q,w in v.items() if not isinstance(w,(list,dict))},flush=True)
    for q,w in v.items():
     if isinstance(w,list):
      print("OUR_OBJECT_LIST",k,q,"count",len(w),"first",json.dumps(w[:1],ensure_ascii=False)[:4000],flush=True)
   if isinstance(v,list):
    print("OUR_LIST",k,"count",len(v),"first",json.dumps(v[:1],ensure_ascii=False)[:4000],flush=True)
