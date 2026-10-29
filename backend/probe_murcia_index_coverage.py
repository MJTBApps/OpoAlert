#!/usr/bin/env python3
"""Cross-check official BORM open-data rows against live BORM publication calendar."""
import requests,re,json
from zoneinfo import ZoneInfo
from collections import Counter,defaultdict
from datetime import datetime,date,timezone
from urllib.parse import urlsplit
from clm_common import employment
INDEX="https://transparencia.carm.es/rest-services/services/restFile/BORMIndice.json"
BORM="https://www.borm.es/"
END=date(2026,10,29);START=date(2026,9,30)
s=requests.Session()
r=s.get(INDEX,timeout=(12,90))
r.raise_for_status()
v=r.json()
rows=[x for x in v if isinstance(x,list) and len(x)==21 and START<=date.fromisoformat(x[4][:10])<=END]
calendar=[]
try:
 rr=s.get(BORM+"services/boletin/fechas",timeout=(10,25))
 print("MURCIA_CALENDAR_HTTP",rr.status_code,"URL",rr.url[:150],"TYPE",rr.headers.get("Content-Type"),flush=True)
 maybe=rr.json()
 if isinstance(maybe,list): calendar=maybe
except Exception as e:print("MURCIA_CALENDAR_UNAVAILABLE",str(e)[:250],flush=True)
caldates={datetime.fromtimestamp(int(ms)/1000,ZoneInfo("Europe/Madrid")).date() for ms in calendar}
iss=defaultdict(list)
for x in rows:iss[(x[4][:10],str(x[3]),x[0])].append(x)
byday=Counter(x[0] for x in rows)
print("MURCIA_RANGE","total_2026",len(v),"rows_30days",len(rows),"dates",len(set(x[4][:10] for x in rows)),
      "editions",len(iss),"types",byday,flush=True)
for key,items in sorted(iss.items()):print("MURCIA_ISSUE",key,"announcements",len(items),"candidates",sum(bool(employment(x[5])) for x in items),flush=True)
indexdates={date.fromisoformat(x[4][:10]) for x in rows}
seldates={d for d in caldates if START<=d<=END}
print("MURCIA_CALENDAR","count",len(calendar),"max",max(caldates) if caldates else None,"range",len(seldates),
      "missing_from_index",sorted(seldates-indexdates),
      "unlisted_in_calendar",sorted(indexdates-seldates),flush=True)
print("MURCIA_ALL_SOURCE_TYPES",Counter(x[0] for x in v))
print("MURCIA_AGENCIES",Counter(x[6] for x in rows),flush=True)
print("MURCIA_CANDIDATES_FIRST",json.dumps([{"id":x[1],"npe":x[16],"date":x[4],"title":x[5][:250],"agency":x[9],"pdf":x[18],"publication":x[0]} for x in rows if employment(x[5])][:12],ensure_ascii=False),flush=True)
print("MURCIA_NPE_BAD",len([x for x in rows if not re.fullmatch(r"A-\d{6}-\d{1,7}",str(x[16]))]))
print("MURCIA_PDF_BAD",len([x for x in rows if not re.fullmatch(r"https://www\.borm\.es/services/anuncio/\d+/pdf",str(x[18]))]))
print("MURCIA_DISTINCT_NUM",Counter(str(x[3]) for x in rows).most_common(10))
