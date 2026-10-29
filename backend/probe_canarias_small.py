#!/usr/bin/env python3
"""Small reproducible summary of official Canary BOP navigation without log truncation."""
from bs4 import BeautifulSoup
import requests,re,json
from urllib.parse import urljoin
for code,base in [("LP","https://www.boplaspalmas.net/nbop2/"),("TF","https://www.bopsantacruzdetenerife.es/bopsc2/")]:
 for file in ["main1.php","indexc.php","sumario.php?fecha_mas_reciente=2026-10-28","sumario.php?fecha_mas_reciente=2026-10-29"]:
  try:
   url=urljoin(base,file)
   r=requests.get(url,timeout=(10,28),headers={"User-Agent":"Mozilla/5.0"},allow_redirects=False)
   soup=BeautifulSoup(r.content,"html.parser")
   links=[(a.get_text(" ",strip=True)[:70],a.get("href")) for a in soup.select("a[href]")]
   forms=[{"method":f.get("method"),"action":f.get("action"),"elements":[(a.name,a.get("name"),a.get("value")) for a in f.select("input,select")[:13]]} for f in soup.select("form")[:4]]
   rows=[z for z in soup.select("td") if z.select_one("b i")]
   textLines=[]
   for z in rows[:2]:
    text=z.get_text("\n",strip=True)
    lines=text.splitlines()
    textLines.append({"n_lines":len(lines),"first":lines[:14],
     "agencies":[v.get_text(" ",strip=True) for v in z.select("b i")[:5]],
     "titles":[v for v in lines if v.startswith("- ")][:7],
     "title_count":len([v for v in lines if v.startswith("- ")])})
   out={"code":code,"file":file,"status":r.status_code,"len":len(r.content),
    "linksN":len(links),"links":links[:20],"forms":forms,
    "tableN":len(soup.select("table")),"agencyRows":len(rows),"textLines":textLines,
    "text":soup.get_text(" ",strip=True)[:280]}
   print("CANARIA_SMALL",json.dumps(out,ensure_ascii=False)[:6400],flush=True)
  except Exception as e:print("CANARIA_SMALL_ERR",code,file,repr(e)[:280],flush=True)
