#!/usr/bin/env python3
"""Discover official alternate publication channels; never infer verified coverage."""
import requests, concurrent.futures, socket, os, sys
from bs4 import BeautifulSoup
from io import BytesIO
from urllib.parse import urljoin
urls = {
"rioja_api_documentation":"https://ias1.larioja.org/opendata/download?r=Y2Q9MzIxfGNmPTE2",
"rioja_opendata":"https://ias1.larioja.org/opendata/",
"rioja_old_home":"https://www2.larioja.org/pls/dad_user/G04.bor_home",
"rioja_ias1_boletin":"https://ias1.larioja.org/boletin/",
"rioja_ias1_opendata_root":"https://ias1.larioja.org/opendata",
"rioja_actualidad":"https://actualidad.larioja.org/",
"rioja_ias1_robots":"https://ias1.larioja.org/robots.txt",
"rioja_ias1_download_http":"http://ias1.larioja.org/opendata/download?r=Y2Q9MzIxfGNmPTE2",
"navarra_open_data":"https://datosabiertos.navarra.es/es/dataset",
"navarra_open_data_api":"https://datosabiertos.navarra.es/es/api/3/action/package_search?q=boletin",
"navarra_gobiernoabierto":"https://gobiernoabierto.navarra.es/es/open-data",
"navarra_lex":"https://www.lexnavarra.navarra.es/",
"navarra_cf":"https://www.cfnavarra.es/BON/BONIDX.HTM",
"navarra_sede":"https://sede.navarra.es/",
"navarra_navarraportal":"https://portal.navarra.es/",
"navarra_bon_apex":"https://bon.navarra.es/",
"navarra_bon_http":"http://bon.navarra.es/es/inicio",
"navarra_cdn":"https://www.navarra.es/",
"navarra_educa":"https://www.educacion.navarra.es/",
}
def probe(item):
 key,url=item
 try:
  with requests.Session() as s:
   s.headers.update({"User-Agent":"Mozilla/5.0 (compatible; OpoAlert diagnostic/1.0)","Accept-Language":"es"})
   r=s.get(url,timeout=(4,10),allow_redirects=True,stream=True)
   content=b""
   for part in r.iter_content(8192):
    content+=part
    if len(content)>240000:break
   mime=r.headers.get("Content-Type","")
   title=""
   text=""
   links=[]
   if content.startswith(b"%PDF-"):
    try:
     from pypdf import PdfReader
     reader=PdfReader(BytesIO(content))
     title="PDF pages="+str(len(reader.pages))
     text=" ".join((x.extract_text() or "") for x in reader.pages[:7])[:20000]
    except Exception as e: text="PDF PARSE ERROR: "+repr(e)
   elif "xml" in mime or content.lstrip().startswith(b"<?xml"):text=content.decode("utf-8","replace")[:7000]
   else:
    soup=BeautifulSoup(content,"html.parser")
    title=soup.title.get_text(" ",strip=True) if soup.title else ""
    text=soup.get_text(" ",strip=True)[:2200]
    links=[(a.get_text(" ",strip=True)[:35],urljoin(r.url,a.get("href",""))[:150]) for a in soup.select("a[href]")[:15]]
   return (key,url,r.status_code,r.url,mime,len(content),title,text,links)
 except Exception as e:return (key,url,"ERROR",type(e).__name__+":"+str(e)[:140],"",0,"","",[])
with concurrent.futures.ThreadPoolExecutor(max_workers=12) as pool:
 for result in pool.map(probe,urls.items()):
  key,url,status,final,mime,size,title,txt,links=result
  print("\nRESULT",key,"HTTP",status,"url",final,"mime",mime,"size",size,"title",repr(title),flush=True)
  print("TEXT",txt[:12000 if key=="rioja_api_documentation" else 1100],flush=True)
  if links:print("LINKS",repr(links),flush=True)
