#!/usr/bin/env python3
"""Check Huelva official PDF content type, partial download, 2026 documents."""
import requests
paths=[
"https://s2.diphuelva.es/portalweb/bope/anuncios/Anuncio_381433_BOP-208_2026.pdf",
"https://s2.diphuelva.es/portalweb/bope/anuncios/IndiceBOP_208_2026.pdf",
"https://s2.diphuelva.es/portalweb/bope/anuncios/Anuncio_380108_BOP-202_2026.pdf",
]
for path in paths:
 try:
  r=requests.get(path,timeout=(12,22),headers={"User-Agent":"Mozilla/5.0","Range":"bytes=0-85"},stream=True)
  head=next(r.iter_content(100),b"")
  print("CHECK",r.status_code,"MIME",r.headers.get("Content-Type"),"LEN",r.headers.get("Content-Length"),"END",r.url,"HEAD",repr(head[:55]),flush=True)
  r.close()
 except Exception as e:print("ERROR",path,type(e).__name__,str(e)[:300],flush=True)
