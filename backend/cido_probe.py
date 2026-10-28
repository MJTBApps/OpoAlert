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

# Endpoint filters/paging documented by Diputacio de Barcelona, not guessed coverage.
from urllib.parse import quote
EXTRA=[
    BASE+"?sort=-maxDataPublicacioDocument",
    BASE+"?sort=-documents.dataPublicacio",
    BASE+"?page[size]=2&sort=-maxDataPublicacioDocument",
    BASE+"?page[limit]=2&sort=-maxDataPublicacioDocument",
    BASE+"?filter[idEstat]=1,2,3&sort=-maxDataPublicacioDocument",
    BASE+"?filter[idAmbit]=8&sort=-maxDataPublicacioDocument",
]
for url in EXTRA:
    print("\nSORT/PAGE",url,flush=True)
    try:
        with urlopen(Request(url,headers={"Accept":"application/vnd.api+json","User-Agent":"OpoAlert/1.4"}),timeout=25) as resp:
            body=resp.read(3_000_000)
            print("HTTP",resp.status,"BYTES",len(body),flush=True)
        data=json.loads(body)
        print("META",data.get("meta"),"LINKS",data.get("links"),flush=True)
        for item in data.get("data",[])[:3]:
            a=item.get("attributes",{})
            print("RECORD",{"id":item.get("id"),"ambit":a.get("ambit"),"titol":a.get("titol"),"fecha":a.get("maxDataPublicacioDocument"),"estat":a.get("estat"),"urlCido":a.get("urlCido")},flush=True)
    except HTTPError as exc:
        print("HTTP ERROR",exc.code,exc.read(1200).decode("utf-8","replace"),flush=True)
    except Exception as exc:
        print("ERROR",type(exc).__name__,str(exc),flush=True)
    time.sleep(0.2)
