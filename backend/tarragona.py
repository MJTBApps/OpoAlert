#!/usr/bin/env python3
"""BOPT Tarragona: auditoria estricta de 30 dias antes de publicar.

Se comprueba cada fecha, todas las paginas, total oficial y PDF de cada
convocatoria. Cuando un documento falla no se emite feed parcial.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from math import ceil
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

from provincial_common import ProvincialCoverageError, classify, fold

ROOT = "https://aplicacions.dipta.cat"
SOURCE = ROOT + "/bopt/web/anteriores/"
PDF_PREFIX = "/bopt/web/anuncio/descargar-pdf/"
PROVINCE = "Tarragona"
REG = re.compile(r"\b(\d{4}-\d{5})\b")
DETAIL_PATH = re.compile(r"/bopt/web/anuncio/(\d+)/[a-z0-9-]+\Z")
TOTAL_MANY = re.compile(r"Se (?:encontraron|han encontrado)\s+([\d.,]+)\s+resultados", re.I)
TOTAL_ONE = re.compile(r"Se ha encontrado\s+1\s+resultado", re.I)
PAGE_RANGE = re.compile(r"Se muestran del\s+(\d+)\s+al\s+(\d+)", re.I)
MAX_PAGES = 25
PAGE_SIZE = 20


def official(address: str, path_prefix: str, *, allow_fragment: bool = False) -> bool:
    parsed = urlsplit(address)
    return (parsed.scheme == "https" and parsed.hostname == "aplicacions.dipta.cat"
            and parsed.port in (None, 443) and not parsed.username and not parsed.password
            and (not parsed.fragment or allow_fragment) and not parsed.query
            and parsed.path.startswith(path_prefix))


def request_html(url: str, *, max_bytes: int = 1_500_000, sleep: float = 0.08) -> str:
    if not official(url, "/bopt/web/"):
        raise ProvincialCoverageError(f"BOPT: URL de consulta no oficial: {url}")
    last = None
    for attempt in range(3):
        try:
            req = Request(url, headers={
                "User-Agent": "OpoAlert/1.4 (proyecto independiente; https://github.com/MJTBApps/OpoAlert)",
                "Accept-Language": "es-ES,es;q=0.9,ca;q=0.8",
                "Accept": "text/html",
            })
            with urlopen(req, timeout=26) as response:
                if response.status != 200 or not official(response.url, "/bopt/web/"):
                    raise ProvincialCoverageError(f"BOPT: redireccion/HTTP inesperado {url}")
                blob = response.read(max_bytes + 1)
                if len(blob) > max_bytes:
                    raise ProvincialCoverageError("BOPT: HTML excesivo")
                header = response.headers.get_content_charset() or "utf-8"
            time.sleep(sleep)
            return blob.decode(header, "replace")
        except (HTTPError, URLError, OSError, TimeoutError) as exc:
            last = exc
            if attempt < 2:
                time.sleep(1.0 + attempt)
    raise ProvincialCoverageError(f"BOPT: error descargando {url}: {last}")


def parse_index(html: str, day: date, page: int = 1) -> tuple[int, list[dict]]:
    soup = BeautifulSoup(html, "html.parser")
    heading = soup.title.get_text(" ", strip=True) if soup.title else ""
    expected = day.strftime("%d/%m/%Y")
    if expected not in heading or "Bolet" not in heading:
        raise ProvincialCoverageError(f"BOPT {day}: cabecera oficial no coincide: {heading[:120]}")
    body = soup.get_text(" ", strip=True)
    result = TOTAL_MANY.search(body)
    if result:
        total = int(result.group(1).replace(".", "").replace(",", ""))
    elif TOTAL_ONE.search(body):
        total = 1
    elif re.search(r"(?:No se ha encontrado ning[uú]n resultado|No se han encontrado resultados|0 resultados)", body, re.I):
        total = 0
    else:
        raise ProvincialCoverageError(f"BOPT {day}: sin total oficial comprobable")
    if not 0 <= total <= MAX_PAGES * PAGE_SIZE:
        raise ProvincialCoverageError(f"BOPT {day}: total anomalo {total}")

    rows = []
    for card in soup.select("div.card.bg-white"):
        anchor = card.select_one('h3.card-title a[href*="/bopt/web/anuncio/"]')
        if anchor is None:
            continue
        detail = urljoin(ROOT, anchor.get("href", ""))
        if not official(detail, "/bopt/web/anuncio/") or not DETAIL_PATH.fullmatch(urlsplit(detail).path):
            raise ProvincialCoverageError(f"BOPT {day}: enlace de anuncio no reconocido: {detail}")
        paragraph = card.select_one("div.card-body > p")
        title = paragraph.get_text(" ", strip=True) if paragraph else ""
        entity = anchor.get_text(" ", strip=True)
        raw = card.get_text(" ", strip=True)
        found = re.search(r"Registro\s*:\s*(\d{4}-\d{5})\b", raw, re.I)
        published = re.search(r"Fecha de publicaci[oó]n\s*:\s*(\d{2}/\d{2}/\d{4})", raw, re.I)
        if (not title or not entity or not found or not published or
                published.group(1) != expected):
            raise ProvincialCoverageError(f"BOPT {day}: ficha incompleta o de otra fecha: {raw[:150]}")
        rows.append({"registry": found.group(1), "title": title, "entity": entity, "detail": detail})

    expected_pages = max(1, ceil(total / PAGE_SIZE))
    if page > expected_pages:
        raise ProvincialCoverageError(f"BOPT {day}: pagina {page} fuera del indice oficial")
    expected_rows = max(0, min(PAGE_SIZE, total - (page - 1) * PAGE_SIZE))
    if len(rows) != expected_rows:
        raise ProvincialCoverageError(
            f"BOPT {day} pag {page}: {len(rows)} fichas, {expected_rows} esperadas de {total}"
        )
    if total > PAGE_SIZE:
        page_range = PAGE_RANGE.search(body)
        first = (page - 1) * PAGE_SIZE + 1
        last = first + expected_rows - 1
        if not page_range or (int(page_range.group(1)), int(page_range.group(2))) != (first, last):
            raise ProvincialCoverageError(f"BOPT {day}: paginacion oficial incoherente")
    if len(set(x["registry"] for x in rows)) != len(rows):
        raise ProvincialCoverageError(f"BOPT {day}: registros duplicados")
    return total, rows


def extract_pdf(detail_html: str, number: str, registry: str, day: date) -> str:
    soup = BeautifulSoup(detail_html, "html.parser")
    text = soup.get_text(" ", strip=True)
    date_match = re.search(r"Fecha de publicaci[oó]n\s*:\s*(\d{2}/\d{2}/\d{4})", text, re.I)
    reg_match = re.search(r"N[uú]mero de Registro\s*:\s*(\d{4}-\d{5})", text, re.I)
    if (not date_match or date_match.group(1) != day.strftime("%d/%m/%Y") or
            not reg_match or reg_match.group(1) != registry):
        raise ProvincialCoverageError(f"BOPT {registry}: registro/fecha no coinciden en ficha oficial")
    direct = ROOT + PDF_PREFIX + number
    urls = [urljoin(ROOT, x.get("href", "")) for x in soup.select('a[href*="/bopt/web/anuncio/descargar-pdf/"]')]
    if direct not in urls or not official(direct, PDF_PREFIX):
        raise ProvincialCoverageError(f"BOPT {registry}: no hay enlace PDF oficial")
    return direct


def scan_day(day: date, fetcher=request_html) -> dict:
    source = SOURCE + day.isoformat()
    total, first_rows = parse_index(fetcher(source), day)
    rows = list(first_rows)
    for page in range(2, ceil(total / PAGE_SIZE) + 1):
        part_total, part_rows = parse_index(fetcher(source + f"/{page}"), day, page)
        if part_total != total:
            raise ProvincialCoverageError(f"BOPT {day}: el total cambia entre paginas")
        rows.extend(part_rows)
    if len(rows) != total or len({r["registry"] for r in rows}) != total:
        raise ProvincialCoverageError(f"BOPT {day}: indice incompleto o repetido")
    opportunities = []
    for row in rows:
        kind = classify(row["title"])
        if kind is None:
            continue
        match = DETAIL_PATH.fullmatch(urlsplit(row["detail"]).path)
        if match is None:
            raise ProvincialCoverageError(f"BOPT {day}: enlace de detalle invalido")
        pdf = extract_pdf(fetcher(row["detail"]), match.group(1), row["registry"], day)
        opportunities.append({
            "id": "TA-" + row["registry"], "title": row["title"],
            "entity": row["entity"], "date": day.strftime("%d/%m/%Y"),
            "bulletin": day.strftime("%d/%m/%Y"), "province": PROVINCE,
            "type": kind, "url": pdf,
        })
    return {"date": day, "total": total, "notices": opportunities,
            "pages": max(1, ceil(total / PAGE_SIZE))}


def build_history(days: int = 30, until: date | None = None, scanner=scan_day) -> dict:
    if days != 30:
        raise ValueError("Solo se publican auditorias completas de 30 dias")
    end = until or date.today()
    start = end - timedelta(days=29)
    all_rows, published, absent = [], [], []
    for offset in range(30):
        day = start + timedelta(days=offset)
        result = scanner(day)
        if result["date"] != day or result["total"] < len(result["notices"]):
            raise ProvincialCoverageError(f"BOPT {day}: datos de auditoria incoherentes")
        all_rows.append(result)
        if result["total"] > 0:
            published.append(day.isoformat())
        else:
            absent.append(day.isoformat())
        print(f"Tarragona {day.isoformat()}: {result['total']} anuncios, "
              f"{result['pages']} pags, {len(result['notices'])} candidatos", flush=True)

    if len(published) < 8:
        raise ProvincialCoverageError("BOPT: pocas ediciones en 30 dias, posible error del lector")
    items = [n for row in all_rows for n in row["notices"]]
    if len(items) != len({n["id"] for n in items}):
        raise ProvincialCoverageError("BOPT: identificadores duplicados entre fechas")
    read = sum(x["total"] for x in all_rows)
    pages = sum(x["pages"] for x in all_rows)
    items.sort(key=lambda item:(datetime.strptime(item["date"], "%d/%m/%Y"),item["id"]),reverse=True)
    return {
        "schemaVersion": 1, "source": SOURCE, "province": PROVINCE,
        "lastCheckedUTC": datetime.now(timezone.utc).isoformat(),
        "coverage": {
            "complete": True, "bulletin": published[-1],
            "pagesVisited": pages, "announcementsRead": read,
            "opportunities": len(items), "status": "complete",
        },
        "historyCoverage": {
            "complete": True, "rangeStart": start.isoformat(), "rangeEnd": end.isoformat(),
            "publicationDates": published, "nonPublicationDates": absent,
            "bulletins": published, "issuesRead": len(published),
            "pagesVisited": pages, "announcementsRead": read,
            "opportunities": len(items),
        },
        "notices": items,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--until", type=date.fromisoformat)
    args = parser.parse_args()
    output = build_history(args.days, args.until)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"BOPT 30 dias: {len(output['historyCoverage']['publicationDates'])} ediciones, "
          f"{output['coverage']['announcementsRead']} anuncios, "
          f"{len(output['notices'])} convocatorias candidatas", flush=True)


if __name__ == "__main__":
    main()
