#!/usr/bin/env python3
"""BOE nacional: histórico móvil auditado de la sección II.B (oposiciones y concursos).

Solo lee sumarios JSON de la API oficial. Ante cualquier dato incompleto,
incoherente o falta de boletín, FALLA: no sobrescribe feeds ya publicados.
"""
from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
import json
import re
import time

from provincial_common import classify, fold

SOURCE = "https://www.boe.es/datosabiertos/api/boe/sumario/"
PROVINCE = "España (BOE)"
ID_RE = re.compile(r"BOE-A-\d{4}-\d{1,7}\Z")
PDF_RE = re.compile(r"/boe/dias/(\d{4})/(\d{2})/(\d{2})/pdfs/(BOE-A-\d{4}-\d{1,7})\.pdf\Z")
MAX_BYTES = 4_000_000
REQUEST_RETRIES = 3


class BoeCoverageError(ValueError):
    """The official daily summary could not be audited completely."""


def ensure_list(value, context: str) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        return [value]
    raise BoeCoverageError(f"Se esperaba lista/objeto en {context}")


def official_pdf(url: str, identifier: str, expected: date) -> bool:
    parts = urlsplit(url)
    if (parts.scheme != "https" or parts.hostname != "www.boe.es"
            or parts.username or parts.password or parts.port or parts.query or parts.fragment):
        return False
    match = PDF_RE.fullmatch(parts.path)
    return bool(match and match.group(4) == identifier and
                (int(match.group(1)), int(match.group(2)), int(match.group(3))) ==
                (expected.year, expected.month, expected.day))


def items_under(node: dict):
    """Collect items under a department / epigraph regardless of singleton lists."""
    for item in ensure_list(node.get("item"), "item"):
        if not isinstance(item, dict):
            raise BoeCoverageError("Item BOE no estructurado")
        yield item
    for ep in ensure_list(node.get("epigrafe"), "epigrafe"):
        if not isinstance(ep, dict):
            raise BoeCoverageError("Epigrafe BOE inesperado")
        yield from items_under(ep)


AGENCY_IN_TITLE = re.compile(
    r"\b(?:del|de la|de los|de las)\s+"
    r"((?:Ayuntamiento|Diputaci[oó]n(?: Provincial)?|Universidad|Cabildo|"
    r"Consejo Insular|Consorcio|Mancomunidad|Mancomunitat|Comarca|"
    r"Consejo Comarcal|Consell Comarcal|Entidad Local|"
    r"Comunidad de Villa y Tierra|Entidad Sociedad P[uú]blica Municipal|"
    r"Organismo Aut[oó]nomo)\b[^,]{2,130})",
    re.IGNORECASE
)


def entity_from_title(title: str, official_department: str) -> str:
    """Use the exact entity explicitly stated in the BOE title when available."""
    m = AGENCY_IN_TITLE.search(title)
    if m:
        return re.sub(r"\s+", " ", m.group(1)).strip()
    return official_department


def category(title: str) -> str | None:
    """Conservative public-employment screening, including eligible merit competitions.

    Metadata never states a deadline or exact number of positions without support.
    """
    t = fold(title)
    disallowed = (
        "lista de admitidos", "listas de admitidos", "admitidos y excluidos",
        "relacion de aspirantes", "relacion provisional", "relacion definitiva",
        "calificaciones", "tribunal calificador", "resultados definitivos",
        "nombramiento de", "se nombra a", "cese de", "desierto el concurso",
        "adjudicacion de destinos", "adjudicacion de puestos",
    )
    if any(phrase in t for phrase in disallowed):
        return None
    direct = classify(title)
    if direct:
        return direct
    if ("convoc" in t or "bases para" in t) and any(term in t for term in (
        "procesos selectivos", "proceso selectivo", "concurso de meritos",
        "ingreso en", "provision de puestos", "turno libre",
        "acceso libre", "personal laboral", "oposiciones",
    )):
        return "Plaza / oposición"
    return None


def parse_summary(payload: dict, requested: date):
    if str(payload.get("status", {}).get("code")) != "200":
        raise BoeCoverageError("La API BOE no confirma estado 200")
    summary = payload.get("data", {}).get("sumario")
    if not isinstance(summary, dict):
        raise BoeCoverageError("Falta sumario BOE")
    metadata = summary.get("metadatos", {})
    if (metadata.get("publicacion") != "BOE" or
            str(metadata.get("fecha_publicacion")) != requested.strftime("%Y%m%d")):
        raise BoeCoverageError(f"Fecha o publicacion BOE distintas de {requested}")
    issues = ensure_list(summary.get("diario"), "diario")
    if not issues:
        raise BoeCoverageError("Sumario sin diarios")
    numbers = []
    seen = set()
    result = []
    scanned = 0
    for issue in issues:
        if not isinstance(issue, dict):
            raise BoeCoverageError("Diario mal formado")
        number = str(issue.get("numero", "")).strip()
        if not number or number in numbers or not number.isdigit():
            raise BoeCoverageError("Numero de diario BOE vacio o duplicado")
        numbers.append(number)
        sections = ensure_list(issue.get("seccion"), "seccion")
        if not sections:
            raise BoeCoverageError(f"BOE {number}: sin secciones")
        for sec in sections:
            if not isinstance(sec, dict) or not str(sec.get("codigo", "")):
                raise BoeCoverageError("Seccion sin codigo")
            if str(sec["codigo"]) != "2B":
                continue  # only official "Oposiciones y concursos" section
            departments = ensure_list(sec.get("departamento"), "departamento")
            if not departments:
                raise BoeCoverageError(f"BOE {number}: seccion 2B sin departamentos")
            for dep in departments:
                name = dep.get("nombre", "")
                if not isinstance(name, str) or not name.strip():
                    raise BoeCoverageError("Departamento BOE sin organismo")
                for item in items_under(dep):
                    scanned += 1
                    identifier = item.get("identificador", "")
                    title = item.get("titulo", "")
                    raw_pdf = item.get("url_pdf", {})
                    pdf = raw_pdf.get("texto") if isinstance(raw_pdf, dict) else raw_pdf
                    if (not isinstance(title, str) or not title.strip() or
                        not isinstance(identifier, str) or not ID_RE.fullmatch(identifier) or
                        not isinstance(pdf, str) or not official_pdf(pdf, identifier, requested)
                        or identifier in seen):
                        raise BoeCoverageError(f"BOE {number}: documento no validado: {identifier!r}")
                    seen.add(identifier)
                    kind = category(title)
                    if kind is not None:
                        result.append({
                            "id": identifier,
                            "title": title.strip(),
                            "entity": entity_from_title(title, name.strip()),
                            "date": requested.strftime("%d/%m/%Y"),
                            "bulletin": number,
                            "province": PROVINCE,
                            "type": kind,
                            "url": pdf,
                        })
    return {"numbers": numbers, "read": scanned, "notices": result}


def fetch_daily(day: date, timeout: int = 25) -> dict | None:
    target = SOURCE + day.strftime("%Y%m%d")
    last_error = None
    for attempt in range(REQUEST_RETRIES):
        try:
            req = Request(target, headers={
                "Accept": "application/json",
                "User-Agent": "OpoAlert/1.3 (indice publico oposiciones; repositorio MJTBApps/OpoAlert)",
                "Cache-Control": "no-cache",
            })
            with urlopen(req, timeout=timeout) as response:
                if response.status != 200:
                    raise BoeCoverageError(f"BOE {day}: HTTP {response.status}")
                content = response.read(MAX_BYTES + 1)
                if len(content) > MAX_BYTES:
                    raise BoeCoverageError(f"BOE {day}: JSON excesivo")
            return json.loads(content.decode("utf-8"))
        except HTTPError as error:
            if error.code == 404 and day.weekday() == 6:
                return None  # BOE has no regular publication on Sundays
            last_error = error
            if error.code in (400, 401, 403, 404):
                break
        except (URLError, TimeoutError, OSError, json.JSONDecodeError) as error:
            last_error = error
        if attempt + 1 < REQUEST_RETRIES:
            time.sleep(1.0 + attempt * 1.5)
    raise BoeCoverageError(f"BOE {day}: respuesta oficial no verificable: {last_error}")


def build_history(days: int = 30, until: date | None = None, fetcher=fetch_daily) -> dict:
    if days != 30:
        raise ValueError("OpoAlert solo publica periodos completos de 30 dias")
    end = until or date.today()
    start = end - timedelta(days=29)
    publication_days = []
    no_publication = []
    issues = []
    notices = []
    seen_ids = set()
    read_count = 0
    for offset in range(days):
        day = start + timedelta(days=offset)
        payload = fetcher(day)
        if payload is None:
            if day.weekday() != 6:
                raise BoeCoverageError(f"Ausencia de BOE en dia laborable: {day}")
            no_publication.append(day.isoformat())
            print(f"BOE {day.isoformat()}: domingo sin publicacion", flush=True)
            continue
        parsed = parse_summary(payload, day)
        publication_days.append(day.isoformat())
        issues.extend(parsed["numbers"])
        read_count += parsed["read"]
        for item in parsed["notices"]:
            if item["id"] in seen_ids:
                raise BoeCoverageError(f"Anuncio repetido en varios BOE: {item['id']}")
            seen_ids.add(item["id"])
            notices.append(item)
        print(f"BOE {day.isoformat()}: {len(parsed['numbers'])} diarios, "
              f"{parsed['read']} anuncios II.B, {len(parsed['notices'])} candidatos", flush=True)
        time.sleep(0.10)  # Avoid stressing official API
    if len(publication_days)+len(no_publication) != days:
        raise BoeCoverageError("Calendario nacional incompleto")
    now = datetime.now(timezone.utc).replace(microsecond=0)
    return {
        "source": SOURCE,
        "province": PROVINCE,
        "lastCheckedUTC": now.isoformat().replace("+00:00", "Z"),
        "coverage": {
            "complete": True,
            "bulletin": issues[-1] if issues else "",
            "announcementsRead": read_count,
            "opportunities": len(notices),
        },
        "historyCoverage": {
            "complete": True,
            "rangeStart": start.isoformat(),
            "rangeEnd": end.isoformat(),
            "publicationDates": publication_days,
            "nonPublicationDates": no_publication,
            "bulletins": issues,
            "issuesRead": len(issues),
            "announcementsRead": read_count,
            "opportunities": len(notices),
        },
        "notices": sorted(notices, key=lambda x:(x["date"][6:]+x["date"][3:5]+x["date"][:2], x["id"]), reverse=True)
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--days",type=int,default=30)
    parser.add_argument("--until",type=date.fromisoformat,default=None)
    args=parser.parse_args()
    result=build_history(args.days,args.until)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"BOE_TOTAL: {len(result['historyCoverage']['publicationDates'])} jornadas, "
          f"{result['historyCoverage']['announcementsRead']} titulos II.B, "
          f"{len(result['notices'])} candidatos",flush=True)


if __name__=="__main__":
    main()
