#!/usr/bin/env python3
"""Only first-party Malaga BOP public data discovery, no scraping challenge or coverage claim."""
import requests, json, time, concurrent.futures, re, platform
from urllib.parse import urlsplit

ROOT="https://opendata.malaga.es"
DS="f9fde2a3-ced6-43e0-9b94-821dfd604c5c"
URLS={
 "ckan_package_uuid": ROOT+"/api/3/action/package_show?id="+DS,
 "ckan_package_slug": ROOT+"/api/3/action/package_show?id=edictos",
 "ckan_portal": ROOT+"/dataset/edictos",
 "ckan_api": ROOT+"/api/3/action/package_search?q=edictos",
 "diputacion_catalogue": "https://www.malaga.es/opendata/",
 "bopma_2026_early": "https://www.bopmalaga.es/sumario.php?fecha=01-10-2026",
 "bopma_2026_late": "https://www.bopmalaga.es/sumario.php?fecha=28-10-2026",
 "bopma_2026_late_alt": "https://www.bopmalaga.es/sumario.php.?fecha=28-10-2026",
}
def run(p):
 k,u=p
 t=time.monotonic()
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert public original index audit)","Accept-Language":"es-ES,es;q=0.9"})
   r=s.get(u,timeout=(5,17),allow_redirects=True,stream=True)
   b=b""
   for chunk in r.iter_content(16384):
    b+=chunk
    if len(b)>420000:break
   r.close()
   obj={"name":k,"http":r.status_code,"final":r.url,"bytes":len(b),"mime":r.headers.get("content-type",""),"official_host":urlsplit(r.url).hostname in {"opendata.malaga.es","www.malaga.es","www.bopmalaga.es"},"seconds":round(time.monotonic()-t,2)}
   txt=b.decode("utf-8","replace")
   if "json" in r.headers.get("content-type","").lower():
    try:
     data=json.loads(txt)
     if data.get("success") and isinstance(data.get("result"),dict):
      v=data["result"]
      obj.update({"package":v.get("name"),"modified":v.get("metadata_modified"),
       "resources":[{"name":x.get("name"),"url":x.get("url"),"format":x.get("format"),"size":x.get("size"),"modified":x.get("last_modified")} for x in v.get("resources",[])][-40:]})
     else:obj["head"]=txt[:850]
    except Exception as e:obj["parse_error"]=str(e)[:140];obj["head"]=txt[:550]
   else:
    obj.update({"title":re.search(r"<title[^>]*>(.*?)</title>",txt,re.I|re.S).group(1).strip()[:100] if re.search(r"<title[^>]*>(.*?)</title>",txt,re.I|re.S) else "",
                "evidence_year2026":"2026" in txt[:250000],"date_2026_10_28":bool(re.search(r"28[/ -]10[/ -]2026|28[/ -]octubre[/ -]2026",txt,re.I)),
                "page_sample":re.sub("<[^>]+>"," ",txt[:1200])[:700]})
   return obj
 except Exception as ex:return {"name":k,"error":type(ex).__name__+":"+str(ex)[:180],"seconds":round(time.monotonic()-t,2)}
print("HOSTED_RUNNER",platform.platform(),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=8) as p:
 rows=list(p.map(run,URLS.items()))
for row in rows:print("MALAGA_OPENDATA",json.dumps(row,ensure_ascii=True),flush=True)
s=[r for r in rows if r.get("resources")]
print("MALAGA_2026_OFFICIAL_RESOURCES",json.dumps([x for r in s for x in r["resources"] if "2026" in (str(x.get("name"))+" "+str(x.get("url")))]),flush=True)
print("NO_COVERAGE_CLAIM: confirm original PDFs and strict 30-day calendar separately",flush=True)
