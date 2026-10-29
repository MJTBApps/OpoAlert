#!/usr/bin/env python3
"""Try last-resort transport and legacy official hosts for BON. Experimental only."""
import requests,concurrent.futures
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
TARGETS={
"navarra_legacy_noverify":"https://www.cfnavarra.es/BON/BONIDX.HTM",
"navarra_legacy_http":"http://www.cfnavarra.es/BON/BONIDX.HTM",
"navarra_legacy_bon_xml":"https://www.cfnavarra.es/bon/bonidx.htm",
"navarra_lex_legal":"https://www.lexnavarra.navarra.es/buscador.asp",
"bon_jina_home":"https://r.jina.ai/https://bon.navarra.es/es/inicio",
"bon_jina_issue195":"https://r.jina.ai/https://bon.navarra.es/es/boletin/-/sumario/2026/195",
"bon_jina_issue209":"https://r.jina.ai/https://bon.navarra.es/es/boletin/-/sumario/2026/209",
"bon_jina_issue213":"https://r.jina.ai/https://bon.navarra.es/es/boletin/-/sumario/2026/213",
"bon_jina_article":"https://r.jina.ai/https://bon.navarra.es/es/anuncio/-/texto/2026/195/3",
"bon_jina_no_protocol":"https://r.jina.ai/http://bon.navarra.es/es/inicio",
"bon_google_translate":"https://bon-navarra-es.translate.goog/es/boletin/-/sumario/2026/195?_x_tr_sl=es&_x_tr_tl=en&_x_tr_hl=en",
}
def task(arg):
 key,url=arg
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert access diagnostic/1.0)","Accept":"text/html,text/plain"})
   r=s.get(url,timeout=(5,25),allow_redirects=True,verify=not key.startswith("navarra_legacy_noverify"),stream=True)
   content=b""
   for part in r.iter_content(8192):
    content+=part
    if len(content)>110000:break
   txt=content.decode("utf-8","replace")
   if "text/html" in r.headers.get("Content-Type",""):
    soup=BeautifulSoup(content,"html.parser")
    txt=soup.get_text(" ",strip=True)
   return key, r.status_code, r.url, len(content), r.headers.get("content-type",""), txt[:2500]
 except Exception as e:
  return key,"ERROR",type(e).__name__+":"+str(e)[:150],0,"",""
with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
 for key,status,url,length,mime,txt in ex.map(task,TARGETS.items()):
  print("\nBON",key,"HTTP",status,"url",url,"bytes",length,"mime",mime,"\nTEXT",txt,flush=True)
