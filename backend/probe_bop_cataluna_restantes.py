#!/usr/bin/env python3
"""Inspect HTML routes, official references and export formats for three pending Catalan provincial BOP. No feeds are published."""
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from html.parser import HTMLParser
import re
import time
class Inspect(HTMLParser):
    def __init__(self):
        super().__init__();self.forms=[];self.links=[];self.controls=[];self._current_form=None
    def handle_starttag(self, tag, attrs):
        a=dict(attrs)
        if tag=="form":
            self._current_form={"method":a.get("method"),"action":a.get("action"),"controls":[]};self.forms.append(self._current_form)
        if tag=="a" and "href" in a:self.links.append((a["href"],a.get("title","")))
        if tag in ("input","button","select","option"):
            fields={k:v for k,v in a.items() if k in ("type","name","id","value","data-endpoint","action","selected","placeholder")}
            if fields:
                self.controls.append(fields)
                if self._current_form:self._current_form["controls"].append(fields)
    def handle_endtag(self,tag):
        if tag=="form":self._current_form=None
URLS=[
    "https://www.ddgi.cat/bop/",
    "https://www.ddgi.cat/bop/cerca",
    "https://www.ddgi.cat/bop/?data=2026-10-27",
    "https://www.ddgi.cat/bop/2026/207",
    "https://bop.diba.cat/",
    "https://bop.diba.cat/cercador-butlletins",
    "https://www.diputaciolleida.cat/publicacions-i-bases-de-dades/butlleti-oficial-de-la-provincia-bop/",
    "https://www.diputaciolleida.cat/",
    "https://bop.diputaciolleida.cat/",
]
for url in URLS:
    print("\nSITE",url,flush=True)
    try:
        with urlopen(Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; OpoAlert source verification/1.5)","Accept-Language":"ca,es;q=0.8","Accept":"text/html,application/xhtml+xml,*/*"}),timeout=22) as r:
            raw=r.read(300000)
            print("HTTP",r.status,"FINAL",r.url,"TYPE",r.headers.get("content-type"),"BYTES",len(raw),flush=True)
        html=raw.decode("utf-8","replace")
        p=Inspect();p.feed(html)
        print("TITLE",re.findall(r"<title[^>]*>(.*?)</title>",html,re.I|re.S)[:1],flush=True)
        print("FORMS",str(p.forms)[:6500],flush=True)
        print("CONTROLS",str(p.controls[:60])[:6000],flush=True)
        print("LINKS",str(p.links[:70])[:10000],flush=True)
        print("HEAD",re.sub(r"\s+"," ",html)[:1250],flush=True)
    except HTTPError as e:
        print("HTTP ERR",e.code,e.read(500).decode("utf-8","replace"),flush=True)
    except Exception as e:print("ERROR",type(e).__name__,str(e)[:350],flush=True)
    time.sleep(.1)
