#!/usr/bin/env python3
"""Check official BOP availability across different GitHub-hosted runner networks.

Read-only. Only records reachability and response type, never declares
full coverage or considers a 200 homepage an audited bulletin.
"""
from concurrent.futures import ThreadPoolExecutor
import requests,json,platform,re
from urllib.parse import urlsplit
TARGETS={
 "CE_BOC_2026":"https://www.ceuta.es/ceuta/component/jdownloads/finish/1982-octubre/23280-bocce-6657-02-10-2026?Itemid=534",
 "BU_BOP_2026":"https://bopbur.diputaciondeburgos.es/sites/default/files/private/publicado/bopbur-2026-051/bopbur-2026-051.pdf",
 "AS_BOPA_2026":"https://miprincipado.asturias.es/ast/bopa-sumario?p_p_id=pa_sede_bopa_web_portlet_SedeBopaSummaryWeb&p_p_lifecycle=0&p_r_p_summaryDate=10%2F09%2F2026&p_r_p_summaryIsSearch=false",
 "AS_DATA_2026":"https://descargas.asturias.es/asturias/opendata/LegislacionyJusticia/BOPA2019-28/dataset-sum-bopa-2026.json",
 "CB_BOC":"https://boc.cantabria.es/boces/",
 "CU_DIPU":"https://www.dipucuenca.es/boletin-oficial-de-la-provincia",
 "VD_BOP":"https://bop.sede.diputaciondevalladolid.es/calendario",
 "AB_BOP":"https://bop.dipualba.es/",
 "NA_BON":"https://bon.navarra.es/es/inicio",
 "JA_BOP":"https://bop.dipujaen.es/",
 "MA_BOP":"https://www.bopmalaga.es/sumario.php?fecha=01-10-2026",
 "CONTROL_SA":"https://www.lasalina.es/documentacion/bop/2026/20261028/BOP-SA-20261028-000.pdf",
 "CONTROL_SG":"https://www.dipsegovia.es/bop"
}
def check(item):
 code,url=item
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert public archive audit)","Accept-Language":"es-ES,es;q=0.9"})
   r=s.get(url,timeout=(5,9),stream=True,allow_redirects=True)
   raw=b""
   for chunk in r.iter_content(8192):
    raw+=chunk
    if len(raw)>=16384:break
   r.close()
   body=raw.decode("utf-8","replace")
   return {"key":code,"http":r.status_code,"final":r.url,
    "mime":r.headers.get("Content-Type",""),
    "pdf":raw.startswith(b"%PDF-"),
    "html":b"<html" in raw[:500].lower() or b"<!doctype" in raw[:500].lower(),
    "security":bool(re.search("human verification|verificaci[oó]n de seguridad|verificacion necesaria|captcha|turnstile",body,re.I)),
    "sample":repr(raw[:70]) if not raw.startswith(b"%PDF-") else ""}
 except Exception as ex:return {"key":code,"error":type(ex).__name__+":"+str(ex)[:185]}
print("RUNNER_NETWORK",platform.platform(),flush=True)
with ThreadPoolExecutor(max_workers=12) as pool:
 for x in pool.map(check,TARGETS.items()):
  print("NETWORK_REGION",json.dumps(x,ensure_ascii=True),flush=True)
