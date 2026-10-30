#!/usr/bin/env python3
"""OpoAlert: public official gazette evidence capture from a Spanish local connection.

Standalone stdlib program, suitable for PyInstaller. Never logs in, solves
CAPTCHA, accesses local files, collects cookies, or sends captured data away.
Only allowlisted original editors are queried. This is not a 30-day audit.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from io import BytesIO
import json
from pathlib import Path
import re
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit, urlunsplit, parse_qsl
from urllib.request import Request, urlopen
from zipfile import ZIP_DEFLATED, ZipFile

START = date(2026, 9, 30)
END = date(2026, 10, 29)
LIMIT = 1_300_000
TIMEOUT = 12
SENSITIVE = ("token", "auth", "session", "csrf", "secret", "password", "apikey", "api_key", "key")
OFFICIAL_HOSTS = {
    "miprincipado.asturias.es", "sede.asturias.es", "descargas.asturias.es",
    "boc.cantabria.es", "www.boc.cantabria.es", "boc.gobcantabria.es",
    "www.ceuta.es", "sede.ceuta.es",
    "bopbur.diputaciondeburgos.es", "www.burgos.es",
    "www.dipucuenca.es", "bop.dipualba.es", "www.dipualba.es",
    "bop.sede.diputaciondevalladolid.es", "www.sede.diputaciondevalladolid.es",
    "bon.navarra.es", "www.navarra.es",
    "www.bopmalaga.es", "bop.dipujaen.es", "bophistorico.dipujaen.es",
}

BASES = {
    "AS": ["https://miprincipado.asturias.es/ast/bopa-sumario?p_p_id=pa_sede_bopa_web_portlet_SedeBopaSummaryWeb&p_p_lifecycle=0&p_r_p_summaryDate=29%2F10%2F2026&p_r_p_summaryIsSearch=false",
           "https://descargas.asturias.es/asturias/opendata/LegislacionyJusticia/BOPA2019-28/dataset-sum-bopa-2026.json"],
    "CB": ["https://boc.cantabria.es/boces/",
           "https://boc.cantabria.es/boces/menu.do?dir=%2FinicioCargaInicialBoletines.do"],
    "CE": ["https://www.ceuta.es/ceuta/bocce",
           "https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1982-octubre?Itemid=534",
           "https://www.ceuta.es/ceuta/component/jdownloads/viewcategory/1981-septiembre?Itemid=534"],
    "BU": ["https://bopbur.diputaciondeburgos.es/bopbur-2026-195",
           "https://bopbur.diputaciondeburgos.es/bopbur-2026-200"],
    "AB": ["https://bop.dipualba.es/"],
    "CU": ["https://www.dipucuenca.es/boletin-oficial-de-la-provincia"],
    "VD": ["https://bop.sede.diputaciondevalladolid.es/calendario"],
    "NA": ["https://bon.navarra.es/es/inicio"],
    "MA": ["https://www.bopmalaga.es/sumario.php?fecha=29-10-2026"],
    "JA": ["https://bop.dipujaen.es/"],
}

def safe_url(url: str) -> str | None:
    """Keep only official HTTPS links; drop sensitive query arguments."""
    try:
        p = urlsplit(url)
        if p.scheme != "https" or p.hostname not in OFFICIAL_HOSTS or p.username or p.password or p.port not in (None, 443):
            return None
        if re.search(r";jsessionid=|/login|/auth", p.path, re.I):
            return None
        params = []
        for key, value in parse_qsl(p.query, keep_blank_values=True):
            if any(part in key.lower() for part in SENSITIVE):
                continue
            if len(key) < 130 and len(value) < 300:
                params.append((key, value))
        return urlunsplit((p.scheme, p.netloc, p.path, urlencode(params), ""))
    except (ValueError, AttributeError):
        return None

class PublicPageParser(HTMLParser):
    """Extract visible public text and official anchor destinations only."""
    def __init__(self, base):
        super().__init__(convert_charrefs=True)
        self.base = base
        self.skip = 0
        self.content = []
        self.links = []
        self.current_link = None
        self.headings = []
        self.heading = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "iframe", "form"):
            self.skip += 1
            return
        if self.skip:
            return
        attrs = dict(attrs)
        if tag == "a" and "href" in attrs:
            self.current_link = [safe_url(urljoin(self.base, attrs["href"])), []]
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.heading = [tag, []]

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript", "iframe", "form"):
            self.skip = max(0, self.skip - 1)
            return
        if self.skip:
            return
        if tag == "a" and self.current_link:
            url, parts = self.current_link
            title = " ".join(" ".join(parts).split())[:350]
            if url:
                self.links.append({"url": url, "text": title})
            self.current_link = None
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6") and self.heading:
            t, parts = self.heading
            title = " ".join(" ".join(parts).split())[:400]
            if title:
                self.headings.append({"level": t, "text": title})
            self.heading = None

    def handle_data(self, data):
        if self.skip or not data.strip():
            return
        text = " ".join(data.split())
        if not text:
            return
        self.content.append(text)
        if self.current_link is not None:
            self.current_link[1].append(text)
        if self.heading is not None:
            self.heading[1].append(text)

def get_page(url, code, name):
    url = safe_url(url)
    if not url:
        return {"code": code, "name": name, "status": "invalid_url"}
    now = time.monotonic()
    row = {"code": code, "name": name, "officialUrl": url}
    try:
        req = Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; OpoAlert public official evidence collector)",
            "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.9,*/*;q=0.8",
            "Accept-Language": "es-ES,es;q=0.9",
        })
        with urlopen(req, timeout=TIMEOUT, context=ssl.create_default_context()) as res:
            status = res.status
            final = safe_url(res.geturl())
            content_type = res.headers.get("Content-Type", "")
            data = res.read(LIMIT + 1)
        row.update({"http": status, "finalOfficialUrl": final,
                    "mime": content_type.split(";")[0], "readBytes": len(data)})
        if not final:
            row["status"] = "unverified_redirect"
        elif len(data) > LIMIT:
            row["status"] = "too_large_to_capture"
        elif data[:5] == b"%PDF-":
            row["status"] = "pdf_header_only"
            row["signature"] = "%PDF-"
        elif "html" in content_type.lower():
            parser = PublicPageParser(final)
            parser.feed(data.decode("utf-8", "replace"))
            visible = " ".join(parser.content)
            first = visible[:4000].lower()
            if any(x in first for x in ("turnstile", "captcha", "verificacion de seguridad",
                                        "verificación de seguridad", "verificacion necesaria",
                                        "verificación necesaria")):
                row["status"] = "human_verification"
            elif len(visible) < 250:
                row["status"] = "unverified_short_page"
            else:
                row["status"] = "public_page_captured"
                row["page"] = {
                    "headings": parser.headings[:350],
                    "links": parser.links[:1800],
                    "publicText": visible[:170_000],
                }
        elif "xml" in content_type.lower() or "json" in content_type.lower():
            # Structured files may have publication references. Keep only a
            # bounded public excerpt, not server headers or private browser state.
            row["status"] = "structured_data_sample"
            row["publicDataExcerpt"] = data[:170_000].decode("utf-8", "replace")
        else:
            row["status"] = "unverified_content"
    except HTTPError as ex:
        row.update({"status": "http_error", "http": ex.code})
    except (URLError, TimeoutError, OSError, ValueError) as ex:
        row.update({"status": "connection_error", "errorType": type(ex).__name__})
    row["seconds"] = round(time.monotonic() - now, 1)
    return row

def asturias_date_url(day):
    params = {
        "p_p_id": "pa_sede_bopa_web_portlet_SedeBopaSummaryWeb",
        "p_p_lifecycle": "0",
        "p_r_p_summaryDate": day.strftime("%d/%m/%Y"),
        "p_r_p_summaryIsSearch": "false",
    }
    return "https://miprincipado.asturias.es/ast/bopa-sumario?" + urlencode(params)

def source_tasks():
    result = []
    for key, urls in BASES.items():
        for n, u in enumerate(urls):
            result.append((key, f"{key}-entry-{n+1}", u))
    return result

def more_tasks(summaries):
    tasks = []
    reachable = {
        code for code, rows in summaries.items()
        if any(x["status"] in ("public_page_captured", "structured_data_sample")
               for x in rows)
    }
    if "AS" in reachable:
        for i in range((END - START).days + 1):
            day = START + timedelta(days=i)
            tasks.append(("AS", "BOPA-" + day.isoformat(), asturias_date_url(day)))
    if "BU" in reachable:
        # Every edition number is checked against the actual headline during
        # later independent audits; this deliberately covers an over-range.
        for n in range(182, 213):
            tasks.append(("BU", f"BOPBUR-{n}", f"https://bopbur.diputaciondeburgos.es/bopbur-2026-{n}"))
    return tasks

def self_test():
    assert safe_url("https://boc.cantabria.es/boces/?token=SECRET&fecha=2026-10-29") == "https://boc.cantabria.es/boces/?fecha=2026-10-29"
    assert safe_url("https://evil.example/steal") is None
    assert safe_url("https://boc.cantabria.es@evil.example/") is None
    assert safe_url("http://boc.cantabria.es/boces/") is None
    p = PublicPageParser("https://boc.cantabria.es/boces/")
    p.feed('<html><h1>BOC de hoy</h1><script>SECRET_CSFR_123</script>'
           '<form><input name="password" value="secret"></form>'
           '<p>Boletín oficial de Cantabria, convocatoria pública de empleo 2026</p>'
           '<a href="/boces/mostrar.do?fecha=2026-10-29&token=SECRET">Ver boletín</a></html>')
    assert "SECRET" not in " ".join(p.content)
    assert p.links[0]["url"] == "https://boc.cantabria.es/boces/mostrar.do?fecha=2026-10-29"
    assert len(source_tasks()) >= 10
    assert len(more_tasks({"AS": [{"status": "public_page_captured"}]})) == 30
    print("OK: captura pública, filtrado de credenciales y calendario local")

def collect(path):
    rows = []
    plans = source_tasks()
    print("OpoAlert: comprobando diez fuentes oficiales desde esta conexión", flush=True)
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda a: get_page(a[2], a[0], a[1]), plans))
    grouped = {}
    for row in rows:
        grouped.setdefault(row["code"], []).append(row)
        print(row["name"], row["status"], flush=True)
    extras = more_tasks(grouped)
    if extras:
        print("Recopilando sumarios de 30 días de los boletines accesibles...", flush=True)
        # Avoid request bursts on the editor's server: sequential, limited,
        # public GET requests only. CAPTCHA is never followed.
        for key, name, url in extras:
            result = get_page(url, key, name)
            rows.append(result)
            print(name, result["status"], flush=True)
            if result["status"] == "human_verification":
                print("Detenido: el editor requiere intervención humana", flush=True)
                break
            time.sleep(0.4)
    summary = {}
    for code in BASES:
        items = [x for x in rows if x["code"] == code]
        summary[code] = {
            "pagesCaptured": sum(x["status"] == "public_page_captured" for x in items),
            "pdfHeaders": sum(x["status"] == "pdf_header_only" for x in items),
            "blocked": sum(x["status"] in ("connection_error", "http_error", "human_verification") for x in items),
            "totalRequested": len(items),
            "audit30DaysComplete": False,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "tool": "OpoAlert-Recolector-Oficial",
        "generatedUTC": datetime.now(timezone.utc).isoformat(),
        "requestedPeriod": [START.isoformat(), END.isoformat()],
        "audit30DaysComplete": False,
        "summary": summary,
        "readOnly": True,
        "automaticUpload": False,
        "results": rows,
    }
    with ZipFile(path, "w", ZIP_DEFLATED, compresslevel=7) as z:
        z.writestr("evidencias_oficiales.json", json.dumps(payload, ensure_ascii=False, indent=2))
        z.writestr("LEER.txt",
          "OpoAlert: archivos de lectura pública de boletines oficiales.\n"
          "Este ZIP NO acredita por sí solo 30 días completos ni anuncios vigentes.\n"
          "No contiene cookies, credenciales, direcciones IP ni archivos personales.\n"
          "Comparte el ZIP en ChatGPT para verificar las fuentes y programar los lectores.\n")
    print("\nArchivo generado:", path, flush=True)
    print("No se envía automáticamente a ningún servidor.", flush=True)

def run():
    ap = argparse.ArgumentParser(description="Recolecta evidencias públicas de boletines oficiales desde tu conexión")
    ap.add_argument("--self-test", action="store_true")
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    if args.self_test:
        self_test()
        return
    folder = Path.home() / "Documents" / "OpoAlert"
    filename = "OpoAlert_evidencias_oficiales_" + datetime.now().strftime("%Y%m%d_%H%M%S") + ".zip"
    output = args.output or folder / filename
    collect(output)
    if getattr(__import__("sys"), "frozen", False) and __import__("sys").stdin.isatty():
        input("Pulsa Intro para cerrar esta ventana...")

if __name__ == "__main__":
    run()
