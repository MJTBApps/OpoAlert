"""Complete index parser for one official BOP Alicante issue (no guessed rows)."""
from __future__ import annotations

from bs4 import BeautifulSoup
from provincial_common import (ProvincialCoverageError, VerifiedIssue, classify,
                               source_record, validate_issue, validate_pdf)


def parse_issue(html: str, expected_date: str | None = None) -> VerifiedIssue:
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.select("table.tabla-edictos-inner")
    if not tables:
        raise ProvincialCoverageError("Alicante: indice no disponible o sin tablas de edictos")
    rows = [tr for table in tables for tr in table.select("tr") if tr.find_all("td", recursive=False)]
    if not rows:
        raise ProvincialCoverageError("Alicante: ninguna fila en las tablas del sumario")
    all_ids: set[str] = set()
    issue_days: set[str] = set()
    issue_numbers: set[str] = set()
    opportunities: list[dict] = []
    for index, tr in enumerate(rows, 1):
        cells = tr.find_all("td", recursive=False)
        if len(cells) != 7:
            raise ProvincialCoverageError(f"Alicante: fila {index} con {len(cells)} columnas; se esperan 7")
        date, number, edict, title, locality, agency, _errata = (
            cell.get_text(" ", strip=True) for cell in cells
        )
        validate_issue(expected_date, date)
        if not number.isdigit() or not edict.isdigit():
            raise ProvincialCoverageError(f"Alicante: BOP o edicto no numerico en fila {index}")
        link = cells[3].find("a", href=True)
        if link is None or not title or not agency:
            raise ProvincialCoverageError(f"Alicante: falta extracto, organismo o PDF en fila {index}")
        pdf = link["href"]
        validate_pdf(pdf, "www.dip-alicante.es", "/bop2/pdftotal/")
        year = date[-4:]
        notice_id = f"AL-{year}-{int(edict)}"
        if notice_id in all_ids:
            raise ProvincialCoverageError(f"Alicante: edicto duplicado {edict}")
        all_ids.add(notice_id)
        issue_days.add(date)
        issue_numbers.add(number)
        kind = classify(title)
        if kind is not None:
            opportunities.append(source_record("Alicante", notice_id, title, agency,
                                               date, number, kind, pdf))
    if len(issue_days) != 1 or len(issue_numbers) != 1:
        raise ProvincialCoverageError("Alicante: mezcla de fechas o numeros BOP en un sumario")
    return VerifiedIssue("Alicante", next(iter(issue_days)), next(iter(issue_numbers)),
                         len(rows), tuple(opportunities))
