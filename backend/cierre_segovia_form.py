#!/usr/bin/env python3
"""Find Segovia Sep 30 official BOP 117 via Liferay catalog form.

Only read-only queries on the publisher's public form.
"""
import json,re,requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
url="https://www.dipsegovia.es/bop"
with requests.Session() as s:
 r=s.get(url,timeout=(8,24),headers={"User-Agent":"Mozilla/5.0"})
 print("HOME",r.status_code,r.url,len(r.content),flush=True)
 h=BeautifulSoup(r.content,"html.parser")
 for i,f in enumerate(h.select("form")):
  txt=f.get_text(" ",strip=True)
  html=str(f)
  if any(w in (txt+html).lower() for w in ("bolet","ano","year","mes","month","2026")):
   print("FORM",i,"method",f.get("method"),"action",urljoin(url,f.get("action","")),"id",f.get("id"),"HTML",html[:12500],flush=True)
 for j,sel in enumerate(h.select("select")):
  attrs={k:v for k,v in sel.attrs.items() if k in ("id","name","onchange")}
  if any(w in str(sel).lower() for w in ("año","ano","mes","2026","septiembre")):
   print("SELECT",j,attrs,str(sel)[:4500],flush=True)
 for i,script in enumerate(h.select("script")):
  txt=script.string or script.get_text(" ",strip=True)
  if any(w in txt.lower() for w in ("bulletinsweb","searchbulletins","searchbulletin","mesbusqueda","searchform","searchbop")):
   print("SCRIPT_MATCH",i,txt[:5500],flush=True)
 for term in ("Septiembre","2026","calendar","form-bop","search-year","searchYear","articleId","Portlets","20260930","page="):
  matches=list(re.finditer(re.escape(term),r.text,re.I))
  print("OCC",term,len(matches),[(m.start(),r.text[max(0,m.start()-160):m.end()+300].replace("\n"," ")[:500]) for m in matches[:3]],flush=True)

 print("PREVIOUS_MONTH_LINKS", [(a.get("title"),urljoin(url,a.get("href",""))) for a in h.select('a[href]') if "septiembre 2026" in (a.get("title","")+" "+a.get_text(" ",strip=True)).lower()][:8],flush=True)
 month_links=[urljoin(url,a.get("href","")) for a in h.select("a[href]") if "p_r_p_startDate=01%2F09%2F2026" in a.get("href","") or "septiembre 2026" in a.get("title","").lower()]
 for k,link in enumerate(dict.fromkeys(month_links)):
  try:
   response=s.get(link,timeout=(8,28))
   doc=BeautifulSoup(response.content,"html.parser")
   cards=doc.select("div.card.card-box")
   print("SEPT_PAGE",k,response.status_code,response.url,len(response.content),"cards",len(cards),flush=True)
   for card in cards:
    print("SEPT_CARD",card.get_text(" ",strip=True)[:200],[(a.get_text(" ",strip=True)[:60],urljoin(link,a.get("href",""))) for a in card.select("a[href]")[:3]],flush=True)
   target=next((card for card in cards if "30 de septiembre" in card.get_text(" ",strip=True).lower()),None)
   if target:
    a=target.select_one('a[href*="articleId"]')
    if a:
     detail_url=urljoin(link,a.get("href",""))
     res=s.get(detail_url,timeout=(10,30))
     dh=BeautifulSoup(res.content,"html.parser")
     print("SEPT_30_DETAIL",res.status_code,detail_url,len(res.content),dh.get_text(" ",strip=True)[-2800:],flush=True)
     print("SEPT_30_PDF_LINKS",[(x.get_text(" ",strip=True)[:80],urljoin(detail_url,x.get("href",""))) for x in dh.select('a[href*="/documents/"]')][:50],flush=True)
  except Exception as ex:print("SEPT_ERROR",repr(ex),flush=True)
