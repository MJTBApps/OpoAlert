#!/usr/bin/env python3
"""Check official Jaen edition identifiers and whether gaps are indexed elsewhere."""
from datetime import date
from pandora_bop import JAEN,session,fetch_index,get,text_url,pdf_url
import re
s=session()
issues,total,pages=fetch_index(JAEN,date(2026,9,29),date(2026,10,29),s)
for row in issues:
 print("EDITION",row["date"],row["id"],row["pages"],row["pdf"][:150],flush=True)
print("TOTAL",len(issues),"ARCHIVE_TOTAL",total,"ARCHIVE_PAGES",pages,flush=True)
for row in issues[-6:]:
 text=get(s,text_url(JAEN,row["id"])).content.decode("utf-8")
 print("LAST_HEADER",row["id"],repr(text[:300]),flush=True)
