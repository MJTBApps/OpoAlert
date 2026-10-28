"""Common validated model for Alicante/Castellon public bulletin indexes.

A bulletin index is considered complete only if its whole official index was
read and every row/title has an identifiable PDF and issue metadata.
Classification is best-effort and deliberately separate from coverage checks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
import unicodedata
from urllib.parse import urlsplit


class ProvincialCoverageError(ValueError):
    """The index could not be verified; do not publish partial data."""


@dataclass(frozen=True)
class VerifiedIssue:
    province: str
    date: str  # dd/MM/yyyy
    number: str
    announcements_read: int
    opportunities: tuple[dict, ...]


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.casefold())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def classify(title: str) -> str | None:
    """Conservative title-only screening, no invented deadlines or positions."""
    t = fold(title)
    t = re.sub(r"\s+", " ", t)
    excluded = (
        "subvencion", "subvencio", "licitacion", "licitacio", "beca", "ayuda econ",
        "nombramiento", "nomenament", "admitid", "admes", "excluid", "exclos",
        "lista provisional", "lista definitiva", "llista provisional", "llista definitiva",
        "resultados", "resultat", "tribunal", "correccion de errores", "juez de paz",
        "jueza de paz", "jutge de pau", "plaza aparcamiento", "plaza mayor",
        "plaza publica", "urbanismo", "aprobacion padron",
    )
    if any(term in t for term in excluded):
        return None
    if re.search(r"\b(?:bolsa|borsa)\b", t) and any(x in t for x in (
        "trabaj", "treball", "empleo", "ocupacio", "personal", "contractacio",
    )):
        if any(x in t for x in ("convocatoria", "bases", "constitucio", "creacio", "formacion")):
            return "Bolsa de trabajo"
    if any(x in t for x in ("convocatoria", "bases", "oposicion", "oposicio",
                           "proceso selectivo", "proces selectiu", "concurso", "concurs")):
        if re.search(r"\b(?:plaz[ao]s?|places?|placa|puestos?|llocs?|dotacion(?:es)?|personal|funcionari[oa]s?|oposicion|oposicio)\b", t):
            return "Plaza / oposición"
    return None


def valid_date(raw: str) -> datetime:
    try:
        return datetime.strptime(raw, "%d/%m/%Y")
    except ValueError as exc:
        raise ProvincialCoverageError(f"Fecha oficial no valida: {raw!r}") from exc


def validate_pdf(url: str, host: str, begins: str) -> None:
    p = urlsplit(url)
    if p.scheme != "https" or p.hostname != host or not p.path.startswith(begins) or p.username:
        raise ProvincialCoverageError(f"Enlace PDF inesperado: {url[:130]}")


def validate_issue(expected_date: str | None, actual_date: str):
    valid_date(actual_date)
    if expected_date is not None and expected_date != actual_date:
        raise ProvincialCoverageError(
            f"El BOP mostrado corresponde a {actual_date} y se pidio {expected_date}"
        )


def source_record(province: str, unique_id: str, title: str, agency: str,
                  date: str, bulletin: str, kind: str, url: str):
    return {
        "id": unique_id, "province": province, "title": title.strip(),
        "entity": agency.strip(), "date": date, "bulletin": bulletin,
        "type": kind, "url": url,
    }
