#!/usr/bin/env python3
"""Probe first-party BOPA 2026 open data resources and official sumarios.

This does not activate a feed. Requires 2026 records, 30-day coverage, and
original references before a source can be considered complete.
"""
import concurrent.futures,requests,platform,json,re
from urllib.parse import urljoin
from bs4 import BeautifulSoup
ROOT="https://descargas.asturias.es/asturias/opendata/LegislacionyJusticia/BOPA2019-28/"
urls={
"bopa2026csv":ROOT+"dataset-sum-bopa-2026.csv",
"bopa2026json":ROOT+"dataset-sum-bopa-2026.json",
"bopa2026xml":ROOT+"dataset-sum-bopa-2026.xml",
"bopa2026underscore":ROOT+"dataset-sum_bopa_2026.json",
"bopa2025json":ROOT+"dataset-sum-bopa-2025.json",
"bopa2024json":ROOT+"dataset-sum-bopa-2024.json",
"bopa2026www":"https://www.asturias.es/portal/site/asturias/menuitem.4c6dc34aa8d6c40cd13e4b2e100000f7/?vgnextoid=0c0cb8d0f483f010VgnVCM100000b0030a0aRCRD",
"bopa2026oct":"https://miprincipado.asturias.es/ast/bopa-sumario?p_p_id=pa_sede_bopa_web_portlet_SedeBopaSummaryWeb&p_p_lifecycle=0&p_r_p_summaryDate=29%2F10%2F2026&p_r_p_summaryIsSearch=false",
"bopa2026sep":"https://miprincipado.asturias.es/ast/bopa-sumario?p_p_id=pa_sede_bopa_web_portlet_SedeBopaSummaryWeb&p_p_lifecycle=0&p_r_p_summaryDate=30%2F09%2F2026&p_r_p_summaryIsSearch=false",
"bopa_sede":"https://sede.asturias.es/ast/bopa-sumario",
"bopa_legacy":"https://www.asturias.es/bopa",
"bopa_down":"https://descargas.asturias.es/"
}
print("RUNNER",platform.platform(),flush=True)
def run(pair):
 name,url=pair
 try:
  s=requests.Session();s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
  r=s.get(url,timeout=(5,14),stream=True,allow_redirects=True)
  data=b""
  for block in r.iter_content(32768):
   data+=block
   if len(data)>160000:break
  r.close()
  obj={"key":name,"status":r.status_code,"final":r.url,"contentType":r.headers.get("Content-Type"),"partialSize":len(data),"serverLength":r.headers.get("Content-Length")}
  t=data.decode("utf-8","replace")
  if name.endswith("json"):
   try:
    j=json.loads(t)
    obj["jsonType"]=type(j).__name__
    obj["topKeys"]=list(j.keys())[:28] if isinstance(j,dict) else []
    obj["sample"]=str(j)[:1500]
   except Exception as e:obj["head"]=t[:1000]
  elif "csv" in name or "xml" in name or name.endswith("underscore"):
   obj["head"]=t[:1400]
  else:
   soup=BeautifulSoup(data,"html.parser")
   obj["title"]=soup.title.get_text(" ",strip=True)[:180] if soup.title else ""
   obj["text"]=soup.get_text(" ",strip=True)[:400]
   obj["links"]=[(a.get_text(" ",strip=True)[:50],urljoin(r.url,a.get("href",""))[:160]) for a in soup.select("a[href]") if "2026" in a.get("href","") or "2026" in a.get_text(" ",strip=True)][:12]
  return obj
 except Exception as e:return {"key":name,"error":type(e).__name__+": "+str(e)[:250]}
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as ex:
 for r in ex.map(run,urls.items()):
  print("BOPA_PROBE",json.dumps(r,ensure_ascii=False),flush=True)
