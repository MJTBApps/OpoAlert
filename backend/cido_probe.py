"""Probe official CIDO public jobs API. Never publish until provenance confirmed."""
import json
from urllib.request import Request, urlopen
from urllib.error import HTTPError
import time

BASE="https://api.diba.cat/dadesobertes/cido/v1/oposicions"
URLS=[BASE, BASE+"?page=1&limit=2",BASE+"?limit=2",BASE+"?per_page=2"]
for url in URLS:
    print("\nCIDO URL",url,flush=True)
    try:
        request=Request(url,headers={"Accept":"application/json","User-Agent":"OpoAlert/1.4 source audit (public open data)"})
        with urlopen(request,timeout=30) as resp:
            body=resp.read(11000)
            print("STATUS",resp.status,"TYPE",resp.headers.get("content-type"),"BYTES",len(body),"FINAL",resp.url,flush=True)
        try:
            data=json.loads(body)
            print("ROOT",type(data).__name__,list(data.keys())[:30] if isinstance(data,dict) else "array",flush=True)
            print("SAMPLE",json.dumps(data,ensure_ascii=False)[:7800],flush=True)
        except Exception as e:
            print("BODY",body[:5000].decode("utf-8","replace"),str(e),flush=True)
    except HTTPError as exc:
        print("HTTP ERR",exc.code,exc.read(1000).decode("utf-8","replace"),flush=True)
    except Exception as exc:
        print("ERR",type(exc).__name__,str(exc),flush=True)
    time.sleep(0.2)
