from urllib.request import Request,urlopen
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.error import HTTPError
urls=[
 "https://bop.diba.cat/anteriors/2026-10-28",
 "https://bop.diba.cat/anteriors/2026-10-24",
 "https://bop.diba.cat/anunci/ver-pdf/3872372",
 "https://www.ddgi.cat/bop/mostra-bop/2026-10-26/2026/206",
]
for u in urls:
 print("\nEXAMPLE",u,flush=True)
 try:
  with urlopen(Request(u,headers={"User-Agent":"Mozilla/5.0","Accept-Language":"ca,es;q=0.8"}),timeout=12) as r:
   if "pdf" in r.headers.get("content-type",""):
    print("PDF RESPONSE",r.status,r.headers.get("content-type"),"HEAD",r.read(10),flush=True);continue
   html=r.read(600_000)
  soup=BeautifulSoup(html,"html.parser")
  print("TITLE",soup.title.get_text(" ",strip=True) if soup.title else "",flush=True)
  print("TEXT",soup.get_text(" ",strip=True)[-1500:],flush=True)
  for card in soup.select("div.card.bg-white")[:2]:
   print("CARD HTML",str(card)[:5500],flush=True)
  for a in soup.select('a[href*=".pdf"]')[:3]:
   print("PDF ANCHOR",str(a.parent)[:2600],flush=True)
  print("PAGINATION",[(a.get("href"),a.get_text(" ",strip=True)[:50]) for a in soup.select("a[href]") if any(x in a.get("href","") for x in ("/2","/3","/4","pagination"))][-20:],flush=True)
 except HTTPError as e:print("HTTP ERR",e.code,flush=True)
 except Exception as e:print("ERROR",type(e).__name__,str(e),flush=True)
