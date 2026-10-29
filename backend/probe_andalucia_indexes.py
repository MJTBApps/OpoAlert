#!/usr/bin/env python3
"""Print official OCR text headings and verify direct edict PDFs."""
import requests,re
samples=[
 ("AL","https://app.dipalme.org/pandora/text.vm?id=0000392773&view=boletines"),
 ("JA","https://bophistorico.dipujaen.es/text.vm?id=0001747120&view=boletin"),
]
for name,url in samples:
 try:
  r=requests.get(url,timeout=28)
  lines=r.text.splitlines()
  print("\nSOURCE",name,"HTTP",r.status_code,"CHARS",len(r.text),"LINES",len(lines),flush=True)
  for i,line in enumerate(lines[:175]):
   if line.strip():
    print("L",i,repr(line[:180]),flush=True)
  for token in ["SUMARIO","Pág. 14435","BOP-2026-4568","002761-26","Número: 200"]:
   i=r.text.find(token)
   if i>=0:print("TOKEN",token,"AT",i,"EXCERPT",repr(r.text[max(0,i-120):i+650]),flush=True)
 except Exception as ex:print("ERROR",name,type(ex).__name__,str(ex)[:220],flush=True)
for u in [
 "https://app.dipalme.org/bop/services/manager/edicto/2026/2765/anuncio.pdf",
 "https://app.dipalme.org/bop/services/manager/edicto/2026/2792/anuncio.pdf",
]:
 try:
  r=requests.get(u,timeout=28,stream=True,headers={"Range":"bytes=0-100"})
  b=next(r.iter_content(128),b"")
  print("PDF",u,r.status_code,r.headers.get("Content-Type"),r.url,repr(b[:50]),flush=True);r.close()
 except Exception as e:print("PDF_ERROR",type(e).__name__,str(e)[:140],flush=True)
