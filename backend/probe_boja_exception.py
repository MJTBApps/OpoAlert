import requests,json
from bs4 import BeautifulSoup
for n in [203,209,210]:
 u=f"https://www.juntadeandalucia.es/eboja/2026/{n}/s57.html"
 try:
  r=requests.get(u,timeout=30);h=BeautifulSoup(r.content,"html.parser")
  blocks=h.select("div.item.punteado_izquierda")
  print("SPECIAL",n,"HTTP",r.status_code,"ITEMS",len(blocks),flush=True)
  for i,b in enumerate(blocks):
   if len(b.select("a.item_pdf_grupo[href]"))!=1:
    print("SPECIAL_MISSING",n,i,json.dumps({"text":b.get_text(" ",strip=True)[:550],"anchors":[(x.get_text(" ",strip=True)[:95],x.get("href")) for x in b.select("a[href]")],"html":str(b)[:3200]},ensure_ascii=False)[:4500],flush=True)
 except Exception as e:print("SPECIAL_ERROR",n,repr(e)[:250],flush=True)
