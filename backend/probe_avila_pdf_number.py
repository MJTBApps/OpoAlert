#!/usr/bin/env python3
import requests,fitz
for day in ["05-10-2026","06-10-2026","07-10-2026"]:
 url=f"https://www.diputacionavila.es/bops/2026/{day}.pdf"
 try:
  r=requests.get(url,timeout=(10,25))
  print("FILE",day,r.status_code,len(r.content),r.headers.get("Content-Type"),flush=True)
  if r.content.startswith(b"%PDF-"):
   d=fitz.open(stream=r.content,filetype="pdf")
   print("TEXT",day,repr(d[0].get_text()[:1500]),flush=True)
 except Exception as e:print("ERROR",day,type(e).__name__,str(e)[:230],flush=True)
