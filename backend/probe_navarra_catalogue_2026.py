#!/usr/bin/env python3
"""Navarra first-party open-data catalogue, metadata-only discovery.

This does NOT assert BON publication completeness or add a feed. Checks whether
the Navarra open data portal explicitly exposes an archival BON data resource.
"""
from __future__ import annotations
from pathlib import Path
from urllib.parse import urlencode,urlsplit
import json
import requests
import time
from datetime import datetime,timezone

HOST="datosabiertos.navarra.es"
API=f"https://{HOST}/es/api/3/action/package_search"
TERMS=["boletin","BON","diario oficial","Boletín Oficial de Navarra"]
def discover(term):
    url=API+"?"+urlencode({"q":term,"rows":25})
    try:
        with requests.Session() as s:
            s.headers.update({"User-Agent":"OpoAlert/1.30 (public open-data catalogue metadata audit)",
                "Accept":"application/json","Accept-Language":"es"})
            r=s.get(url,timeout=(7,22),stream=True)
            final=urlsplit(r.url)
            if final.hostname!=HOST or r.status_code!=200:
                return {"query":term,"http":r.status_code,"final":r.url,"official":False}
            content=b""
            for block in r.iter_content(16384):
                content+=block
                if len(content)>2_500_000:break
            if len(content)>2_500_000:return {"query":term,"error":"catalogue response too large"}
            try:
                raw=json.loads(content)
            except (json.JSONDecodeError,UnicodeDecodeError):
                return {"query":term,"http":200,"mime":r.headers.get("Content-Type",""),
                    "head":content[:250].decode("utf-8","replace"),"parsedJSON":False}
            records=[]
            if raw.get("success") is True and isinstance(raw.get("result"),dict):
                for entry in raw["result"].get("results",[])[:25]:
                    resources=[]
                    for resource in entry.get("resources",[])[:35]:
                        ref=resource.get("url","")
                        host=urlsplit(ref).hostname or ""
                        resources.append({"name":str(resource.get("name") or "")[:100],
                            "format":str(resource.get("format") or "")[:30],
                            "url":ref[:220],"firstPartyNavarra":host=="navarra.es" or host.endswith(".navarra.es")})
                    records.append({"id":entry.get("id"),"title":str(entry.get("title") or "")[:180],
                        "notes":str(entry.get("notes") or "")[:250],
                        "modified":entry.get("metadata_modified"),
                        "resources":resources})
                return {"query":term,"http":200,"parsedJSON":True,
                  "count":raw["result"].get("count"),"records":records}
            return {"query":term,"http":200,"parsedJSON":True,"validCKANResponse":False,
              "topKeys":list(raw)[:12]}
    except Exception as e:
        return {"query":term,"error":type(e).__name__+": "+str(e)[:210]}

def main():
    results=[]
    for term in TERMS:
        results.append(discover(term))
        time.sleep(1.0)
    out={"checkedUTC":datetime.now(timezone.utc).isoformat(),
      "source":API,"complete30Days":False,
      "purpose":"metadata discovery, not certified BON issue dataset",
      "queries":results}
    p=Path("out/navarra-bon-catalogo-parcial.json")
    p.parent.mkdir(exist_ok=True,parents=True)
    p.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    for res in results:
        print("NAVARRA_CATALOGUE",json.dumps(res,ensure_ascii=True)[:14500],flush=True)
    print("NOT_BON_FEED: no original 30-day audit or Android coverage",flush=True)
if __name__=="__main__":
    main()
