#!/usr/bin/env python3
"""OpoAlert - local official gazette connectivity test (Windows/macOS/Linux).

This is a read-only, dependency-free connectivity diagnostic. It never logs
authentication tokens, IP addresses, browser cookies or local user details.
A reachable homepage or PDF does NOT mean 30-day BOP coverage.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import json
import re
import ssl
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

SOURCES = (
    ("JA", "Jaen - BOP principal", "html", "https://bop.dipujaen.es/"),
    ("JA", "Jaen - Hemeroteca oficial", "html", "https://bophistorico.dipujaen.es/results.vm?q=parent:0000395018&view=boletin"),
    ("MA", "Malaga - BOP 01/10/2026", "html", "https://www.bopmalaga.es/sumario.php?fecha=01-10-2026"),
    ("AB", "Albacete - BOP", "html", "https://bop.dipualba.es/"),
    ("CU", "Cuenca - Diputacion BOP", "html", "https://www.dipucuenca.es/boletin-oficial-de-la-provincia"),
    ("BU", "Burgos - BOP original 051/2026", "pdf", "https://bopbur.diputaciondeburgos.es/sites/default/files/private/publicado/bopbur-2026-051/bopbur-2026-051.pdf"),
    ("VD", "Valladolid - BOP", "html", "https://bop.sede.diputaciondevalladolid.es/calendario"),
    ("AS", "Asturias - BOPA sumario oficial", "html", "https://miprincipado.asturias.es/ast/bopa-sumario?p_p_id=pa_sede_bopa_web_portlet_SedeBopaSummaryWeb&p_p_lifecycle=0&p_r_p_summaryDate=10%2F09%2F2026&p_r_p_summaryIsSearch=false"),
    ("CB", "Cantabria - BOC", "html", "https://boc.cantabria.es/boces/"),
    ("NA", "Navarra - BON", "html", "https://bon.navarra.es/es/inicio"),
    ("CE", "Ceuta - BOCCE original 6657/2026", "pdf", "https://www.ceuta.es/ceuta/component/jdownloads/finish/1982-octubre/23280-bocce-6657-02-10-2026?Itemid=534"),
    ("SA", "CONTROL Salamanca - sumario oficial", "pdf", "https://www.lasalina.es/documentacion/bop/2026/20261028/BOP-SA-20261028-000.pdf"),
    ("SG", "CONTROL Segovia - portal oficial", "html", "https://www.dipsegovia.es/bop"),
)

USER_AGENT = "Mozilla/5.0 (compatible; OpoAlert-SourceDiagnostic/1.0)"
TIMEOUT = 12


def no_accents(value: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn").lower()


def evaluate(status: int, expected: str, header: bytes, mime: str, final_url: str, original_url: str) -> tuple[str, str]:
    """Report connectivity only; this does not audit complete official issues."""
    if status != 200:
        return ("blocked", "HTTP " + str(status))
    source = urllib.parse.urlsplit(original_url)
    final = urllib.parse.urlsplit(final_url)
    if final.scheme != "https" or (source.hostname or "").lower() != (final.hostname or "").lower():
        return ("unverified", "Redireccion a otro host, revisar manualmente")
    text = no_accents(header.decode("utf-8", "replace"))
    if any(x in text for x in ("human verification", "verificacion necesaria", "verificacion de seguridad", "turnstile", "captcha")):
        return ("human_verification", "El editor exige verificacion humana")
    if expected == "pdf":
        if header.startswith(b"%PDF-"):
            return ("pdf_reachable", "Cabecera de PDF original accesible")
        return ("unverified", "No se recibio un PDF original")
    if "html" in mime.lower() and ("<html" in text or "<!doctype html" in text):
        return ("page_reachable", "Pagina oficial accesible; sin auditoria de 30 dias")
    return ("unverified", "Contenido no identificado como pagina oficial")


def inspect(item: tuple[str, str, str, str]) -> dict:
    code, name, expected, url = item
    result = {"code": code, "name": name, "expect": expected, "officialUrl": url}
    start = time.monotonic()
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "es-ES,es;q=0.9", "Accept": "application/pdf,text/html;q=0.9,*/*;q=0.8"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT, context=ssl.create_default_context()) as response:
            header = response.read(8192)
            code_http = response.status
            mime = response.headers.get("Content-Type", "")
            final = response.geturl()
        verdict, detail = evaluate(code_http, expected, header, mime, final, url)
        result.update({"http": code_http, "finalUrl": final, "mime": mime, "status": verdict, "detail": detail})
    except urllib.error.HTTPError as err:
        result.update({"http": err.code, "status": "blocked", "detail": "HTTP " + str(err.code)})
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        error = str(getattr(err, "reason", err))
        if len(error) > 200:
            error = error[:200]
        result.update({"status": "connection_error", "detail": type(err).__name__ + ": " + error})
    result["seconds"] = round(time.monotonic() - start, 1)
    return result


def self_test() -> None:
    u = "https://example.es/boletin"
    assert evaluate(200, "pdf", b"%PDF-1.7 test", "application/pdf", u, u)[0] == "pdf_reachable"
    assert evaluate(200, "pdf", b"<html>error</html>", "text/html", u, u)[0] == "unverified"
    assert evaluate(200, "html", b"<html><title>Verificacion necesaria</title></html>", "text/html", u, u)[0] == "human_verification"
    assert evaluate(403, "html", b"", "", u, u)[0] == "blocked"
    assert evaluate(200, "html", b"<html>ok</html>", "text/html", "https://other.es/page", u)[0] == "unverified"
    assert evaluate(200, "html", b"<!DOCTYPE html><html lang=es>", "text/html", u, u)[0] == "page_reachable"
    assert len(SOURCES) == 13
    assert len({x[0] for x in SOURCES}) == 12
    print("Pruebas locales superadas (6 casos y catalogo de fuentes).")


def report(results: list[dict], destination: Path) -> tuple[Path, Path]:
    destination.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = destination / ("OpoAlert_diagnostico_" + stamp + ".json")
    txt_path = destination / ("OpoAlert_diagnostico_" + stamp + ".txt")
    payload = {
        "tool": "OpoAlert-Diagnostico-Local",
        "generatedUTC": dt.datetime.now(dt.timezone.utc).isoformat(),
        "audit30DaysComplete": False,
        "privacy": "No recoge credenciales, IP publica, ubicacion ni datos del equipo. No transmite resultados.",
        "scope": "Accesibilidad de una muestra de sitios oficiales. NO equivale a cobertura provincial.",
        "results": results,
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    message = [
        "DIAGNOSTICO LOCAL OPOALERT",
        "El resultado SOLO confirma accesibilidad de URL oficiales.",
        "La auditoria de 30 dias y documentos originales debe ejecutarse despues.",
        "",
    ]
    for row in results:
        message.append(f"{row['code']:>2} | {row['status']:<21} | {row['name']}")
        message.append("     " + row["detail"])
    message += [
        "",
        "Ningun dato se ha publicado ni enviado automaticamente.",
        "Adjunta el archivo JSON a la conversacion de ChatGPT para continuar con los lectores.",
    ]
    txt_path.write_text("\n".join(message) + "\n", encoding="utf-8")
    return json_path, txt_path


def run() -> None:
    parser = argparse.ArgumentParser(description="Comprueba boletines oficiales sin publicar datos ni recoger informacion personal")
    parser.add_argument("--out", type=Path, help="Carpeta donde guardar los informes")
    parser.add_argument("--self-test", action="store_true", help="Ejecutar pruebas sin acceder a Internet")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    directory = args.out or Path.home() / "Documents" / "OpoAlert"
    print("OpoAlert: comprobando 10 ambitos pendientes y 2 controles oficiales.")
    print("La prueba NO descarga todo el BOP ni actualiza la APK.")
    print("Solo se consultan fuentes publicas, sin acceder a cuentas personales.\n")
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(inspect, SOURCES))
    for row in results:
        print(f"{row['code']:>2}  {row['status']:<20} {row['name']}  ({row['seconds']} s)")
    files = report(results, directory)
    print("\nArchivos guardados:")
    for f in files:
        print(str(f))
    print("\nComparte el archivo .json en la conversacion para poder avanzar.")
    if sys.platform == "win32" and sys.stdin.isatty() and getattr(sys, "frozen", False):
        input("Pulsa Intro para cerrar esta ventana...")


if __name__ == "__main__":
    run()
