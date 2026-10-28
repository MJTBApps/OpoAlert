"""Complete index parser for one BOP Castellon carousel bulletin (PrimeFaces)."""
from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit
from bs4 import BeautifulSoup
from provincial_common import (ProvincialCoverageError, VerifiedIssue, classify,
                               source_record, validate_issue, validate_pdf)


def parse_issue(html: str, expected_date: str | None = None,
                expected_number: str | None = None) -> VerifiedIssue:
    soup = BeautifulSoup(html, "html.parser")
    form = soup.select_one('form[id="busquedaBoletinesForm"]')
    if form is None:
        raise ProvincialCoverageError("Castellon: no se encontro el sumario JSF")
    # Labels in the official detail: e.g. Sumario BOP Nº 130 / 27/10/2026.
    header = form.find(string=re.compile(r"Sumario\s+BOP\s+N[ºoúu]m?\.?\s*\d+", re.I))
    if not header:
        raise ProvincialCoverageError("Castellon: falta numero oficial del boletin")
    match = re.search(r"N[ºoúu]m?\.?\s*(\d+)", str(header), re.I)
    if not match:
        raise ProvincialCoverageError("Castellon: numero de BOP no interpretable")
    number = match.group(1)
    if expected_number is not None and number != expected_number:
        raise ProvincialCoverageError(f"Castellon: se pidio {expected_number} y aparece {number}")
    label = header.parent
    row = label.find_parent("tr") if label else None
    date_match = re.search(r"\b\d{2}/\d{2}/\d{4}\b", row.get_text(" ", strip=True) if row else "")
    if not date_match:
        raise ProvincialCoverageError("Castellon: falta fecha de la edicion oficial")
    date = date_match.group()
    validate_issue(expected_date, date)
    official_links = form.select('a[href*="/api/descargarAnuncio?idAnuncio="]')
    titles = form.select('span.titulo4')
    if not titles or len(titles) != len(official_links):
        raise ProvincialCoverageError(
            f"Castellon: {len(titles)} extractos frente a {len(official_links)} enlaces PDF"
        )
    opportunities: list[dict] = []
    all_ids: set[str] = set()
    sections = form.select('span.titulo2,span.titulo3,span.titulo4')
    agency = ""
    pdf_index = 0
    for node in sections:
        classes = node.get("class", [])
        if "titulo3" in classes:
            agency = node.get_text(" ", strip=True)
            continue
        if "titulo2" in classes:
            agency = node.get_text(" ", strip=True)
            continue
        if "titulo4" not in classes:
            continue
        title = node.get_text(" ", strip=True)
        if not title or not agency or pdf_index >= len(official_links):
            raise ProvincialCoverageError("Castellon: anuncio sin titulo o entidad")
        # The official site lays out one PDF link directly before each titulo4.
        pdf = official_links[pdf_index]["href"]
        pdf_index += 1
        validate_pdf(pdf, "bop.dipcas.es", "/PortalBOP/api/descargarAnuncio")
        ids = parse_qs(urlsplit(pdf).query).get("idAnuncio", [])
        if len(ids) != 1 or not ids[0].isdigit():
            raise ProvincialCoverageError("Castellon: falta ID oficial del anuncio")
        unique_id = "CS-" + ids[0]
        if unique_id in all_ids:
            raise ProvincialCoverageError("Castellon: PDF repetido en sumario")
        all_ids.add(unique_id)
        kind = classify(title)
        if kind is not None:
            opportunities.append(source_record("Castellón", unique_id, title, agency,
                                               date, number, kind, pdf))
    if len(all_ids) != len(titles):
        raise ProvincialCoverageError("Castellon: faltan anuncios en un sumario")
    return VerifiedIssue("Castellón", date, number, len(titles), tuple(opportunities))
