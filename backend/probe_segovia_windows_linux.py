#!/usr/bin/env python3
"""Cross-runner official Segovia monthly archive and bulletin 117 access.

Only public GET requests to Diputacion. No proxy, CAPTCHA or WAF bypass.
"""
import platform,requests,json
from bs4 import BeautifulSoup
from urllib.parse import urlencode,urljoin
S="https://www.dipsegovia.es/bop"
PAR="as_asac_asset_search_AssetSearchInstancePortlet_INSTANCE_r0jAmqbO3Q75"
SEARCH="as_asac_bulletins_portlet_BulletinsWebSearchPortlet_INSTANCE_MV6bNdGuf86u"
targets={
"base":S,
"sept_link":S+"?"+urlencode({"p_p_id":PAR,"p_p_lifecycle":"0","p_p_state":"normal","p_p_mode":"view","p_r_p_startDate":"01/09/2026","p_r_p_endDate":"30/09/2026"}),
"year_search":S+"?"+urlencode({"p_p_id":SEARCH,"p_p_lifecycle":"0","p_p_state":"normal","p_p_mode":"view","p_r_p_folderId":"14223415","p_r_p_searchText":"117","p_r_p_exactTerm":"false"}),
"date":S+"?"+urlencode({"p_r_p_startDate":"30/09/2026","p_r_p_endDate":"30/09/2026"}),
"without_www":"https://dipsegovia.es/bop",
"alternate_path":"https://www.dipsegovia.es/bop/",
"liferay_paging":S+"?"+urlencode({"p_p_id":"as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm","p_p_lifecycle":"0","p_p_state":"normal","p_p_mode":"view", "_as_asac_bulletins_web_BulletinsWebPortlet_INSTANCE_O7rkllS4nSVm_cur":"2"})
}
print("RUNNER",platform.platform(),flush=True)
with requests.Session() as s:
 s.headers.update({"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/127.0.0.0 Safari/537.36"})
 for name,url in targets.items():
  try:
   resp=s.get(url,timeout=(9,18))
   h=BeautifulSoup(resp.content,"html.parser")
   cards=h.select("div.card.card-box")
   sample=[c.get_text(" ",strip=True)[:130] for c in cards]
   print("SEGOVIA_ACCESS",json.dumps({"key":name,"status":resp.status_code,"size":len(resp.content),
     "final":resp.url,"title":h.title.get_text(" ",strip=True)[:110] if h.title else "",
     "cards":len(cards),"first":sample[:3],"last":sample[-3:],
     "hasSept30":any("30 de septiembre" in x.lower() for x in sample),
     "head":resp.text[:150] if resp.status_code!=200 else ""},ensure_ascii=False),flush=True)
  except Exception as e:print("SEGOVIA_ERROR",name,type(e).__name__,str(e)[:180],flush=True)
