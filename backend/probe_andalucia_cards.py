#!/usr/bin/env python3
"""Inspect exact card container for day, issue and PDF; sample text heading extraction."""
import requests,re
from bs4 import BeautifulSoup
qs=[
 ("AL","https://app.dipalme.org/pandora/results.vm?q=parent:0000010919&view=boletines&s=48165"),
 ("JA","https://bophistorico.dipujaen.es/results.vm?q=parent:0000395018&view=boletin&s=41760"),
]
for name,url in qs:
 r=requests.get(url,timeout=25)
 soup=BeautifulSoup(r.text,"html.parser")
 a=soup.find("a",href=re.compile("high.raw"))
 print("HOST",name,"STATUS",r.status_code,"PDF",a.get("href") if a else "-",flush=True)
 for n in range(1,7):
  if not a:break
  a=a.parent
  print("PARENT",n,a.name,a.get("class"),a.get("id"),repr(a.get_text(" ",strip=True)[:460]),flush=True)
 print("SMALLHTML",str(a)[:1900] if a else "-",flush=True)
 if name=="AL":
  txt=requests.get("https://app.dipalme.org/pandora/text.vm?id=0000392773&view=boletines",timeout=20).text
  first_body=re.search(r"(?m)^\s*0?2761/26\b",txt)
  print("BODY",first_body.start() if first_body else "no",flush=True)
  hdr=txt[:first_body.start()] if first_body else txt[:10000]
  print("SUMMARY_IDS",re.findall(r"\b0?(\d{3,5})-26\b",hdr)[:60],flush=True)
  for m in list(re.finditer(r"(?m)^\s*(\d{3,5})/26\b",txt))[0:25]:
   print("ANNOUNCEMENT",m.group(1),repr(txt[m.start():m.start()+220]),flush=True)
 else:
  txt=requests.get("https://bophistorico.dipujaen.es/text.vm?id=0001747120&view=boletin",timeout=20).text
  first_body=re.search(r"(?m)^\s*2026/4568\b",txt)
  print("BODY",first_body.start() if first_body else "no",flush=True)
  hdr=txt[:first_body.start()] if first_body else txt[:10000]
  print("SUMMARY_IDS",re.findall(r"BOP-2026-(\d{3,5})",hdr)[:60],flush=True)
  for m in list(re.finditer(r"(?m)^\s*2026/(\d{3,5})\b",txt))[:25]:
   print("ANNOUNCEMENT",m.group(1),repr(txt[m.start():m.start()+220]),flush=True)
