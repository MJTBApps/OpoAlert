#!/usr/bin/env python3
"""Diagnose official BON/BOR connectivity from GitHub runners.

A successful job REQUIRES an HTTP 200 HTML response from both primary
official sites. Fallback domains are connectivity hints, not coverage proof.
Never publish or label a source audited on the basis of this diagnostic.
"""
from __future__ import annotations
import platform
import sys
import socket
from urllib.parse import urlsplit
import requests
from bs4 import BeautifulSoup

TARGETS = {
 "Navarra BON": [
  ("primary", "https://bon.navarra.es/es/inicio"),
  ("primary_issue", "https://bon.navarra.es/es/inicio/-/texto/2026/195/1"),
  ("alternate_official", "https://www.navarra.es/es"),
  ("alternate_archive", "https://www.navarra.es/home_es/Actualidad/BON/"),
 ],
 "La Rioja BOR": [
  ("primary", "https://web.larioja.org/bor-portada/bor"),
  ("primary_detail", "https://web.larioja.org/bor-portada/boranuncio?n=anu-576591"),
  ("alternate_official", "https://www.larioja.org"),
  ("alternate_official", "https://www.larioja.org/bor/es"),
  ("alternate_visor", "https://ias1.larioja.org/boletin/"),
 ]
}
print("PLATFORM", platform.platform(), "PYTHON", sys.version.split()[0], flush=True)
session = requests.Session()
session.trust_env = True
session.headers.update({
 "User-Agent": "Mozilla/5.0 (compatible; OpoAlert diagnostic/1.0)",
 "Accept-Language": "es-ES,es;q=0.9"
})
primaries = {}
for group, targets in TARGETS.items():
 print("\nGROUP", group, flush=True)
 primaries[group] = False
 for role, url in targets:
  hostname = urlsplit(url).hostname
  try:
   ips = sorted({x[4][0] for x in socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)})
   print("DNS", hostname, ",".join(ips[:6]), flush=True)
  except Exception as e:
   print("DNS_ERROR", hostname, type(e).__name__, str(e)[:180], flush=True)
  try:
   response = session.get(url, timeout=(5, 10), allow_redirects=True)
   body = response.content[:500000]
   parsed = BeautifulSoup(body, "html.parser")
   title = parsed.title.get_text(" ", strip=True)[:180] if parsed.title else ""
   print("HTTP", group, role, response.status_code, response.url,
         "bytes", len(response.content), "title", repr(title), flush=True)
   if role == "primary" and response.status_code == 200 and len(body) > 1500:
    expected = ("navarra" if group.startswith("Navarra") else "rioja")
    if expected in (title + parsed.get_text(" ", strip=True)[:1500]).lower():
     primaries[group] = True
   if response.status_code == 200 and role in ("primary", "primary_detail"):
    links = [(a.get_text(" ", strip=True)[:70], a.get("href", "")[:160])
             for a in parsed.select("a[href]")[:45]]
    print("LINKS", group, repr(links[:30]), flush=True)
  except requests.RequestException as e:
   print("HTTP_ERROR", group, role, type(e).__name__, str(e)[:380], flush=True)
print("\nPRIMARY_HTTP_ACCESS", repr(primaries), flush=True)
if not all(primaries.values()):
 print("FAILED CLOSED: access to official BON and/or BOR not confirmed; no audited feed or APK", flush=True)
 sys.exit(2)
print("NETWORK ACCESS ONLY: implement and validate 30-day calendar before activation", flush=True)
