#!/usr/bin/env python3
"""Verify original PDF download and textual index extraction on official Pandora sites."""
import requests,io,re
from pypdf import PdfReader
SAMPLES=[
 ("AL-15oct","https://app.dipalme.org/pandora/high.raw?id=0000392773&name=00000001.original.pdf"),
 ("JA-01oct","https://bophistorico.dipujaen.es/high.raw?id=0001747120&name=00000001.original.pdf&attachment=0001747120.pdf"),
]
for label,url in SAMPLES:
 print("\nSAMPLE",label,url,flush=True)
 try:
  r=requests.get(url,timeout=(15,45),headers={"User-Agent":"Mozilla/5.0"})
  print("HTTP",r.status_code,"LEN",len(r.content),"CTYPE",r.headers.get("Content-Type"),"FINAL",r.url,"MAGIC",repr(r.content[:45]),flush=True)
  if not r.content.startswith(b"%PDF-"):continue
  pdf=PdfReader(io.BytesIO(r.content))
  print("PAGES",len(pdf.pages),"METADATA",str(pdf.metadata)[:150],flush=True)
  for ix in range(min(3,len(pdf.pages))):
   text=pdf.pages[ix].extract_text(extraction_mode="layout")
   print("PAGE",ix+1,"CHARS",len(text),"EXCERPT",repr(text[:7000]),flush=True)
  print("OUTLINE",[(str(x))[:150] for x in pdf.outline[:12]] if pdf.outline else "NONE",flush=True)
 except Exception as ex:print("ERROR",type(ex).__name__,str(ex)[:500],flush=True)
