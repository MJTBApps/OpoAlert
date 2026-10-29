#!/usr/bin/env python3
import requests,ssl,json
from requests.adapters import HTTPAdapter
class Compat(HTTPAdapter):
 def init_poolmanager(self,*a,**kw):
  c=ssl.create_default_context();c.maximum_version=ssl.TLSVersion.TLSv1_2;c.set_ciphers('DEFAULT:@SECLEVEL=1')
  kw['ssl_context']=c
  return super().init_poolmanager(*a,**kw)
s=requests.Session();s.mount('https://portaldogc.gencat.cat',Compat())
for num in ['9761SN','9770SN','9782SN','9783SN']:
 try:
  r=s.post('https://portaldogc.gencat.cat/eadop-rest/api/suplement/summarySuplement',data={'language':'ca','numSuplement':num},timeout=(8,30))
  if r.status_code != 200:print('DOGC_SUP_RESULT',json.dumps({'id':num,'status':r.status_code,'text':r.text[:400]},ensure_ascii=False),flush=True);continue
  j=r.json()
  print('DOGC_SUP_RESULT',json.dumps({'id':num,'status':r.status_code,'bytes':len(r.content),'keys':list(j),'root_without_sections':{k:v for k,v in j.items() if not isinstance(v,(dict,list))},'data':str(j)[:5400]},ensure_ascii=False),flush=True)
 except Exception as e:print('DOGC_SUP_ERROR',num,type(e).__name__,str(e)[:170],flush=True)
