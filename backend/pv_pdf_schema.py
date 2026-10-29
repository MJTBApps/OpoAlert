import requests,json
r=requests.get("https://api.euskadi.eus/bopv/administrative-acts/2026/10?itemsOfPage=1&currentPage=1&lang=SPANISH",timeout=(12,35));r.raise_for_status();j=r.json();a=j["items"][0]
print("PV_FIELDS",json.dumps({k:v for k,v in a.items() if k!="text"},ensure_ascii=False)[:6000],flush=True)
print("PV_TEXT",json.dumps(a.get("text"),ensure_ascii=False)[:700],flush=True)
print("PV_META",json.dumps({k:j[k] for k in ("totalItems","totalPages","currentPage","itemsOfPage")}),flush=True)
