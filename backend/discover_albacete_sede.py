#!/usr/bin/env python3
"""Read-only official BOP discovery from the accessible Albacete Diputacion sede.

Does not authenticate, submit forms, fetch third-party data or produce a feed.
An accessible sede landing page is not evidence of archived BOP coverage.
"""
from __future__ import annotations
from html.parser import HTMLParser
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json, re, sys

HOME = "https://sede.dipualba.es/"
ALLOWED = {"sede.dipualba.es", "www.dipualba.es", "bop.dipualba.es"}
MATCH = re.compile(r"bolet[ií]n|\bbop\b", re.I)

class Extract(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_link = False
        self.href = ""
        self.current = []
        self.links = []
    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.in_link = True
            self.href = dict(attrs).get("href", "")
            self.current = []
    def handle_data(self, data):
        if self.in_link:
            self.current.append(data)
    def handle_endtag(self, tag):
        if tag == "a" and self.in_link:
            self.links.append((self.href, " ".join(" ".join(self.current).split())))
            self.in_link = False

def safe(u, base):
    try:
        parsed = urlsplit(urljoin(base, u))
        return (parsed.geturl() if parsed.scheme == "https" and
                parsed.hostname in ALLOWED and parsed.username is None and
                parsed.password is None and parsed.port in (None, 443) else None)
    except ValueError:
        return None

def get(u):
    req = Request(u, headers={"User-Agent": "Mozilla/5.0 (OpoAlert official source diagnosis)",
                              "Accept-Language": "es-ES,es;q=0.9"})
    with urlopen(req, timeout=12) as r:
        actual = safe(r.geturl(), u)
        if not actual:
            raise ValueError("Redirect to non-official host")
        return actual, r.read(220_000).decode("utf-8", "replace")

def analyze(html, url):
    p = Extract(); p.feed(html)
    links = []
    for href, label in p.links:
        final = safe(href, url)
        if final and (MATCH.search(label) or MATCH.search(final)):
            links.append({"url": final, "label": label[:120]})
    snippets = [" ".join(html[max(0, m.start()-95):m.end()+140].split())[:240]
                for m in list(MATCH.finditer(html))[:15]]
    return {"linkMatches": links[:40], "rawMentions": snippets, "allLinks": len(p.links)}

def self_test():
    assert safe("/bop", HOME) == "https://sede.dipualba.es/bop"
    assert safe("https://bop.dipualba.es/", HOME) is not None
    assert safe("https://evil.example/", HOME) is None
    assert safe("//sede.dipualba.es@evil.example/x", HOME) is None
    r = analyze('<a href="/tramites/bop">Boletín Oficial de la Provincia</a>', HOME)
    assert len(r["linkMatches"]) == 1
    print("OK: enlaces oficiales, extraccion y filtrado", flush=True)

def main():
    if "--self-test" in sys.argv:
        self_test()
        return
    try:
        url, html = get(HOME)
        out = analyze(html, url)
        print("ALBACETE_SEDE", json.dumps({"http": 200, "url": url, **out, "certified": False},
                                           ensure_ascii=False), flush=True)
        urls = list(dict.fromkeys(x["url"] for x in out["linkMatches"]))[:5]
        for item in urls:
            try:
                actual, content = get(item)
                record = {"url": actual, "bytes": len(content), **analyze(content, actual),
                          "certified": False}
                print("ALBACETE_LINK", json.dumps(record, ensure_ascii=False), flush=True)
            except (URLError, HTTPError, TimeoutError, ValueError, OSError) as exc:
                print("ALBACETE_LINK_ERROR", item, type(exc).__name__, str(exc)[:110], flush=True)
    except (URLError, HTTPError, TimeoutError, ValueError, OSError) as exc:
        print("ALBACETE_SEDE_ERROR", type(exc).__name__, str(exc)[:150], flush=True)
    print("No provincial 30-day audit or source activation", flush=True)

if __name__ == "__main__":
    main()
