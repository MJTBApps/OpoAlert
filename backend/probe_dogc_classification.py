#!/usr/bin/env python3
"""Read-only sample of publisher metadata to calibrate conservative DOGC employment classification."""
import sys,collections,json
sys.path.insert(0,"backend")
from dogc_autonomico import collect_main,official_original,calendars,request_json
for number,day in [("9761","30/09/2026"),("9770","09/10/2026"),("9782","28/10/2026"),("9783","29/10/2026")]:
 from datetime import datetime
 editions,ts,metadata=collect_main(number,datetime.strptime(day,"%d/%m/%Y").date())
 print("CANDIDATE_SAMPLE",json.dumps({"issue":number,"read":sum(x["read"] for x in editions),
   "candidateCount":len(ts),"firstTitles":[{"did":n[0],"kind":n[4],"title":n[1]} for n in ts[:45]]},
    ensure_ascii=False),flush=True)
try:
 p=request_json("dogc/documentDOGC",{"documentId":"1056071","language":"ca"})
 print("MISMATCH_ORIGINAL",json.dumps({"id":"1056071","title":p.get("titleDocument"),"issue":p.get("documentData",{}).get("numDOGC"),"date":p.get("documentData",{}).get("dateDOGC")},ensure_ascii=False),flush=True)
except Exception as ex:print("MISMATCH_ERROR",type(ex).__name__,str(ex)[:230],flush=True)
