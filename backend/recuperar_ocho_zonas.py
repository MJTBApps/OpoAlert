#!/usr/bin/env python3
"""Non-invasive official-endpoint inventory for eight OpoAlert blocked zones.

Only probes connectivity and publisher identity. NEVER interprets an HTTP 200
as audited 30-day coverage; no feeds, APK assets or notices are generated.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

TARGETS = {
    "JA": (
        "https://bop.dipujaen.es/anioCompleto",
        "https://bop.dipujaen.es/bop/13-10-2026",
        "https://bophistorico.dipujaen.es/advanced.vm?s=1&view=boletin",
    ),
    "AB": (
        "https://bop.dipualba.es/",
        "https://sede.dipualba.es/",
    ),
    "CU": (
        "https://www.dipucuenca.es/boletin-oficial-de-la-provincia",
        "https://www.dipucuenca.es/",
    ),
    "BU": (
        "https://bopbur.diputaciondeburgos.es/bopbur-2026-200",
        "https://www.burgos.es/servicios/bop",
    ),
    "VD": (
        "https://bop.sede.diputaciondevalladolid.es/calendario",
        "https://bop.sede.diputaciondevalladolid.es/ultimobop",
    ),
    "AS": (
        "https://descargas.asturias.es/asturias/opendata/LegislacionyJusticia/BOPA2019-28/dataset-sum-bopa-2026.json",
        "https://descargas.asturias.es/asturias/opendata/LegislacionyJusticia/BOPA2019-28/dataset-sum-bopa-2026.xml",
        "https://miprincipado.asturias.es/ast/bopa-sumario",
    ),
    "CB": (
        "https://boc.cantabria.es/boces/",
        "https://boc.cantabria.es/boces/verAnuncioAction.do?idAnuBlob=430408",
    ),
    "CE": (
        "https://www.ceuta.es/ceuta/bocce",
        "https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1965-2026?Itemid=534",
        "https://www.ceuta.es/ceuta/documentos",
    ),
}

ALLOWED = {urlsplit(u).hostname for group in TARGETS.values() for u in group}
MAX_BYTES = 90_000
TIMEOUT = 12
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; OpoAlert/1.29; official-access-audit)",
    "Accept": "text/html,application/xhtml+xml,application/xml,application/json,application/pdf;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9",
}

class Title(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.words = []
    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True
    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False
    def handle_data(self, data):
        if self.in_title:
            self.words.append(data)
    @property
    def text(self):
        return " ".join(" ".join(self.words).split())[:120]

def permitted(url):
    try:
        p = urlsplit(url)
        return p.scheme == "https" and p.hostname in ALLOWED and p.username is None and p.password is None and p.port in (None, 443)
    except ValueError:
        return False

def probe(area, url):
    result = {"territory": area, "url": url, "officialPublisher": True,
              "audited30Days": False, "candidateForReader": False}
    start = time.monotonic()
    try:
        req = Request(url, headers=HEADERS)
        with urlopen(req, timeout=TIMEOUT, context=ssl.create_default_context()) as res:
            final = res.geturl()
            result["http"] = res.status
            result["contentType"] = res.headers.get("Content-Type", "").split(";")[0]
            result["finalUrl"] = final if permitted(final) else "[not-official]"
            result["officialPublisher"] = permitted(final)
            raw = res.read(MAX_BYTES + 1)
        result["readBytes"] = len(raw)
        result["pdfSignature"] = raw.startswith(b"%PDF-")
        result["truncated"] = len(raw) > MAX_BYTES
        if not permitted(final):
            result["status"] = "untrusted_redirect"
        elif raw.startswith(b"%PDF-"):
            result["status"] = "official_pdf_sample"
        elif b"<html" in raw[:1000].lower() or result["contentType"] in ("text/html", "application/xhtml+xml"):
            parser = Title()
            parser.feed(raw[:MAX_BYTES].decode("utf-8", "replace"))
            result["title"] = parser.text
            lower = raw[:MAX_BYTES].decode("utf-8", "replace").lower()
            if any(w in lower for w in ("captcha", "turnstile", "verificación de seguridad", "verificacion necesaria")):
                result["status"] = "human_verification"
            else:
                result["status"] = "official_html_sample"
        elif result["contentType"] in ("application/json", "text/xml", "application/xml"):
            result["status"] = "official_structured_sample"
        else:
            result["status"] = "unverified_content"
    except HTTPError as e:
        result["http"] = e.code
        result["status"] = "http_error"
    except (URLError, OSError, TimeoutError, ValueError) as e:
        result["status"] = "connection_error"
        result["errorClass"] = type(e).__name__
    result["durationSeconds"] = round(time.monotonic() - start, 2)
    return result

def self_test():
    assert len(TARGETS) == 8
    assert len(ALLOWED) >= 8
    assert all(permitted(u) for group in TARGETS.values() for u in group)
    assert not permitted("https://example.org/")
    assert not permitted("https://bop.dipujaen.es@evil.example/")
    assert not permitted("http://boc.cantabria.es/boces/")
    assert not permitted("https://boc.cantabria.es:9999/boces/")
    t = Title(); t.feed("<html><title>Boletín Oficial</title></html>")
    assert t.text == "Boletín Oficial"
    print("OK: 8 territories, official HTTPS allowlist, no untrusted redirects", flush=True)

def run(output):
    pairs = [(area, url) for area, urls in TARGETS.items() for url in urls]
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(lambda x: probe(*x), pairs))
    summary = {}
    for area in TARGETS:
        items = [x for x in rows if x["territory"] == area]
        summary[area] = {
            "probes": len(items),
            "officialResponses": sum(x["status"] in ("official_pdf_sample", "official_html_sample", "official_structured_sample") for x in items),
            "httpErrors": [x["http"] for x in items if x["status"] == "http_error"],
            "connectionErrors": sum(x["status"] == "connection_error" for x in items),
            "audited30Days": False,
        }
    result = {"dateUTC": datetime.now(timezone.utc).isoformat(),
              "purpose": "official_endpoint_connectivity_only",
              "audited30Days": False, "territories": summary, "results": rows}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for row in rows:
        print("OFFICIAL_PROBE", json.dumps(row, ensure_ascii=False), flush=True)
    print("OFFICIAL_SUMMARY", json.dumps(summary, ensure_ascii=False), flush=True)
    print("NO TERRITORIES CERTIFIED BY THIS CHECK", flush=True)

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, default=Path("out/8-zonas-oficiales.json"))
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    if args.self_test:
        self_test()
    else:
        run(args.output)
