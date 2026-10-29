#!/usr/bin/env python3
"""BOR endpoint probe: compare PDF direct retrieval and official full HTML/XML."""
import requests,time,concurrent.futures
from urllib.parse import urlencode
HOST="https://ias1.larioja.org/boletin/"
targets={
"pdf_range":"Bor_Boletin_visor_Servlet?referencia=42945066-1-PDF-580468",
"pdf_plain":"Bor_Boletin_visor_Servlet?referencia=42945066-1-PDF-580468",
"pdf_edition":"Bor_Boletin_visor_Servlet?referencia=42944815-2-X",
"xml_article":"ExportarBoletinServlet?tipo=2&fecha=2026/10/28&referencia=42905592-3-HTML-580468-X",
"xml_article_week":"ExportarBoletinServlet?tipo=2&fecha=2026/10/29&referencia=42905592-3-HTML-580468-X",
}
def run(k):
 u=HOST+targets[k];start=time.time()
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0","Accept-Language":"es-ES,es;q=0.9"})
   args={"timeout":(5,18),"stream":True,"allow_redirects":False}
   if k=="pdf_range":args["headers"]={"Range":"bytes=0-128"}
   r=s.get(u,**args)
   body=b""
   for b in r.iter_content(chunk_size=8192):
    body+=b
    if len(body)>200:break
   return k,"HTTP "+str(r.status_code),str(round(time.time()-start,1))+"s",r.headers.get("content-type",""),repr(body[:160])
 except Exception as ex:return k,type(ex).__name__,str(round(time.time()-start,1))+"s","",str(ex)[:280]
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:
 for a in ex.map(run,targets):print("PROBE",*a,flush=True)
