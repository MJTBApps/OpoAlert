#!/usr/bin/env python3
"""Inspect official DOGC endpoint TLS compatibility without suppressing certificate validation.
A transport response is not an audited 30-day official source."""
import requests, ssl,json, platform
from requests.adapters import HTTPAdapter
from urllib3.poolmanager import PoolManager
from urllib.parse import urlsplit
URI="https://portaldogc.gencat.cat/eadop-rest/api/dogc/summaryDOGC?numDOGC=9782"
class CompatAdapter(HTTPAdapter):
 def __init__(self,ctx,*a,**kw):self.ctx=ctx;super().__init__(*a,**kw)
 def init_poolmanager(self,*args,**kw):
  kw["ssl_context"]=self.ctx
  return super().init_poolmanager(*args,**kw)
def run(name,ciphers,max12=False,legacy=False):
 try:
  ctx=ssl.create_default_context()
  if ciphers: ctx.set_ciphers(ciphers)
  if max12:ctx.maximum_version=ssl.TLSVersion.TLSv1_2
  if legacy:ctx.options |= 0x4
  s=requests.Session()
  s.mount("https://",CompatAdapter(ctx))
  r=s.get(URI,timeout=(8,15),stream=True,allow_redirects=True)
  data=b""
  for x in r.iter_content(8192):
   data+=x
   if len(data)>60000:break
  r.close()
  return {"name":name,"status":r.status_code,"final":r.url,"bytes":len(data),"mime":r.headers.get("Content-Type",""),"head":data[:140].decode("utf-8","replace")}
 except Exception as ex:return {"name":name,"error":type(ex).__name__+":"+str(ex)[:230]}
print("RUNTIME",platform.platform(),ssl.OPENSSL_VERSION,flush=True)
variants=[
 ("default",None,False,False),("legacy_reneg",None,False,True),
 ("tls12_default","DEFAULT:@SECLEVEL=1",True,False),
 ("tls12_legacy","DEFAULT:@SECLEVEL=1",True,True),
 ("tls12_RSA_AES256","AES256-SHA:@SECLEVEL=1",True,True),
 ("tls12_CBC","AES256-SHA:AES128-SHA:@SECLEVEL=1",True,False),
]
for p in variants:
 print("DOGC_TLS",json.dumps(run(*p),ensure_ascii=True),flush=True)
print("NO_AUDIT: only HTTPS with valid CA chain and complete issue/original verification can enable DOGC",flush=True)
