import requests,re,json
from bs4 import BeautifulSoup
from urllib.parse import parse_qs,urlsplit,urljoin
for key,base in [("LP","https://www.boplaspalmas.net/nbop2/"),("TF","https://www.bopsantacruzdetenerife.es/bopsc2/")]:
 u=base+"main1.php"
 r=requests.get(u,timeout=(10,30))
 s=BeautifulSoup(r.content,"html.parser")
 records=[]
 for x in s.select("a[href]"):
  a=urlsplit(urljoin(u,x["href"]))
  q=parse_qs(a.query)
  if "fecha_mas_reciente" in q:
   records.append((x.get_text(" ",strip=True),q["fecha_mas_reciente"][0]))
 print("ARCHIVE",key,"http",r.status_code,"date_links",json.dumps(records,ensure_ascii=False),flush=True)
 for day in ["2026-09-30","2026-10-02","2026-10-28"]:
  z=requests.get(base+"sumario.php",params={"codigopub":"1","fecha_mas_reciente":day},timeout=(10,32))
  soup=BeautifulSoup(z.content,"html.parser",from_encoding="utf-8")
  tables=[a for a in soup.select("td") if a.select_one("b i")]
  rowtexts=[]
  for td in tables:
   lines=td.get_text("\n",strip=True).splitlines()
   rowtexts.append({"n":len(lines),"t":len([l for l in lines if l.startswith("- ")]),"ag":len(td.select("b i")),"sample":lines[:8]})
  print("DATE",key,day,"code",z.status_code,"sum",soup.get_text(" ",strip=True)[:95],"rows",json.dumps(rowtexts,ensure_ascii=False)[:1800],flush=True)
