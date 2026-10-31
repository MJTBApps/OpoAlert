"""Plazo de presentación escrito en el propio anuncio (sin calcular fechas).

Lee el texto del PDF oficial y busca la frase que fija el plazo para presentar
solicitudes («El plazo de presentación de solicitudes será de veinte días
hábiles contados a partir del día siguiente…»). Devuelve los días, si son
hábiles o naturales, y la frase literal con su página. NO calcula fechas: el
plazo suele empezar con una publicación posterior (extracto en el BOE) y los
festivos dependen de cada municipio. Si no hay una frase clara, no devuelve nada.
"""
from __future__ import annotations

import re
import unicodedata

# Números escritos con letra en castellano, valenciano/catalán y gallego.
WORDS = {
    "un": 1, "uno": 1, "una": 1, "dos": 2, "dues": 2, "duas": 2, "tres": 3, "cuatro": 4, "quatre": 4, "catro": 4,
    "cinco": 5, "cinc": 5, "seis": 6, "sis": 6, "siete": 7, "set": 7, "sete": 7, "ocho": 8, "vuit": 8, "oito": 8,
    "nueve": 9, "nou": 9, "nove": 9, "diez": 10, "deu": 10, "dez": 10, "once": 11, "onze": 11, "doce": 12,
    "dotze": 12, "trece": 13, "tretze": 13, "catorce": 14, "catorze": 14, "quince": 15, "quinze": 15,
    "dieciseis": 16, "setze": 16, "dezaseis": 16, "diecisiete": 17, "disset": 17, "dieciocho": 18,
    "divuit": 18, "diecinueve": 19, "dinou": 19, "veinte": 20, "vint": 20, "vinte": 20, "veintiuno": 21,
    "veintidos": 22, "veinticinco": 25, "treinta": 30, "trenta": 30, "trinta": 30, "cuarenta": 40,
    "quaranta": 40, "corenta": 40, "cuarenta y cinco": 45, "sesenta": 60, "seixanta": 60,
}
_word = "|".join(sorted((re.escape(w) for w in WORDS), key=len, reverse=True))

# «veinte (20) días hábiles», «20 días naturales», «quinze dies hàbils», «vinte días hábiles».
DAYS = re.compile(
    rf"\b(?P<num>\d{{1,3}}|{_word})(?:\s*\(\s*(?P<paren>\d{{1,3}})\s*\))?\s+"
    r"(?P<unit>dias?|dies|dia)\b(?:\s+(?P<kind>habiles|naturales|habils|naturals|natural|habil))?",
)
# La frase debe hablar del plazo para presentar solicitudes o participar:
# «El plazo de presentación de solicitudes…», «Las solicitudes se presentarán en el plazo…».
SUBJECT = re.compile(
    r"\b(?:plazo|termini|prazo)\b.{0,60}?\b(?:presentacion|presentacio|presentar|participar|"
    r"participacion|participacio|inscripcion|inscripcio)"
    r"|\b(?:presentaran|presentarse|presentarlas|presentadas|presentar|dirigiran|dirigidas|es presentaran|"
    r"presentaran|presentaren)\b.{0,320}?\b(?:plazo|termini|prazo)\b"
    r"|\bpresentacion de (?:las )?solicitudes se hara en (?:el )?plazo\b",
)
# Si el verbo va antes que «plazo», la frase tiene que nombrar la solicitud o instancia.
REQUEST = re.compile(r"\b(?:solicitud|solicitudes|instancias?|sol·licituds?|sollicituds?|candidaturas?)\b")
# ...y no de otros plazos del procedimiento (subsanar, alegar, reclamar, recurrir).
OTHER = re.compile(
    r"subsana|esmen|alegaci|al·legaci|allegaci|reclamaci|recurso|recurs\b|recurs |impugna|"
    r"exposicion publica|informacion publica|lista provisional|llista provisional|tribunal|"
    r"entrega de documentacion|aportar la documentacion|toma de posesion|presa de possessio|"
    r"antes de la finalizacion|antes del fin|antes de que finalice|informe medico|embaraz|parto\b|"
    r"excluid|exclos|persona seleccionada|aspirante seleccionad|propuesta de nombramiento|posesori|"
    r"presentar la documentacion|documentacion acreditativa|documentos acreditativos",
)


def fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in text if unicodedata.category(ch) != "Mn")


def clean(text: str) -> str:
    """Une palabras partidas al final de línea («há- biles») y los saltos de línea."""
    text = re.sub(r"(\w)-\s*\n\s*(\w)", r"\1\2", text)
    return re.sub(r"\s+", " ", text).strip()


def sentences(text: str):
    """Frases aproximadas: corta en punto seguido de mayúscula (no en «núm.» ni «art.»)."""
    start = 0
    for match in re.finditer(r"(?<!\bnúm)(?<!\bart)(?<!\bapdo)(?<!\bpág)\.\s+(?=[A-ZÁÉÍÓÚÑÀÈÒÇ0-9«“\"(])", text):
        yield text[start:match.end()].strip()
        start = match.end()
    if start < len(text):
        yield text[start:].strip()


def quote(sentence: str, anchor: int, limit: int = 320) -> str:
    """La frase literal; si es muy larga, desde un poco antes de «plazo» y con «…»."""
    text = sentence
    if len(text) > limit and anchor > 80:
        cut = text.rfind(" ", 0, anchor - 40)
        text = "…" + text[cut + 1:] if cut > 0 else text
    if len(text) > limit:
        cut = text.rfind(" ", 0, limit)
        text = text[:cut if cut > 0 else limit] + "…"
    return text


def find_in_text(text: str) -> dict | None:
    """Primera frase que fija los días para presentar solicitudes."""
    for sentence in sentences(clean(text)):
        if len(sentence) > 1500:
            continue
        folded = fold(sentence)
        subject = SUBJECT.search(folded)
        if not subject or OTHER.search(folded):
            continue
        if not folded[subject.start():subject.start() + 12].startswith(("plazo", "termini", "prazo", "presentacion de")) \
                and not REQUEST.search(folded):
            continue
        # Los días tienen que venir después de «plazo» («dos días antes de que acabe el plazo» no vale).
        anchor = re.search(r"\b(?:plazo|termini|prazo)\b", folded)
        found = []
        for match in DAYS.finditer(folded, anchor.start() if anchor else 0):
            raw = match.group("num")
            number = int(raw) if raw.isdigit() else WORDS.get(raw)
            paren = match.group("paren")
            if paren and number is not None and int(paren) != number:
                number = None  # «veinte (15) días»: contradictorio, no se usa
            # Solo si dice si son hábiles o naturales.
            if number and match.group("kind"):
                found.append((number, match.group("kind")))
        # Una sola cifra de días en la frase; si hay varias distintas, es ambiguo.
        if len({n for n, _ in found}) != 1:
            continue
        days, kind = found[0]
        if not 1 <= days <= 90:
            continue
        kind = {"habiles": "hábiles", "habils": "hábiles", "habil": "hábiles",
                "naturales": "naturales", "naturals": "naturales", "natural": "naturales"}.get(kind or "")
        return {"days": days, "kind": kind, "text": quote(sentence, anchor.start() if anchor else 0)}
    return None


def find_in_pdf(data: bytes, first_page: int = 1, max_pages: int = 6) -> dict | None:
    """Busca el plazo en las primeras páginas del anuncio (desde `first_page`, 1 = primera)."""
    import pymupdf

    with pymupdf.open(stream=data, filetype="pdf") as document:
        last = min(document.page_count, first_page - 1 + max_pages)
        for index in range(first_page - 1, last):
            result = find_in_text(document[index].get_text())
            if result:
                result["page"] = index + 1
                return result
    return None


# ---------------------------------------------------------------------------
# Archivos diarios: docs/plazos/<feed>.json, uno por fuente (la app solo descarga
# los de los boletines que sigue). Cada anuncio se lee una sola vez: lo que ya se
# miró se conserva y solo se descargan los PDF de los anuncios nuevos.
# ---------------------------------------------------------------------------
import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

NOT_FEEDS = {"fuentes_activas.json", "version.json"}
KINDS = {"hábiles", "naturales"}
MAX_PDF_BYTES = 30 * 1024 * 1024
MAX_TRIES = 3


def candidate_notices(feed: dict):
    """Anuncios marcados como posible convocatoria con enlace a un PDF suelto."""
    for value in feed.values():
        if not isinstance(value, list):
            continue
        for item in value:
            if not isinstance(item, dict) or not item.get("type"):
                continue
            url = str(item.get("url") or "")
            # «#page=N»: boletín entero; el plazo podría ser del anuncio siguiente.
            if url.startswith("https://") and "#" not in url:
                yield url


def download(url: str) -> bytes | None:
    import requests

    with requests.get(url, timeout=(15, 40), stream=True, headers={"User-Agent": "OpoAlert-plazos/1.0"}) as response:
        response.raise_for_status()
        if not response.url.startswith("https://"):
            raise ValueError("redirección no segura")
        data = bytearray()
        for chunk in response.iter_content(65536):
            data.extend(chunk)
            if len(data) > MAX_PDF_BYTES:
                raise ValueError("PDF demasiado grande")
    return bytes(data) if bytes(data[:5]) == b"%PDF-" else None


def problem(url: str, item: dict, urls: set[str]) -> str | None:
    """Lo mismo que comprueba la app antes de mostrar un plazo (None si está bien)."""
    if url not in urls or not url.startswith("https://"):
        return "enlace que no está en el feed"
    if not (isinstance(item.get("days"), int) and 1 <= item["days"] <= 90 and item.get("kind") in KINDS):
        return "plazo no válido"
    text = item.get("text")
    if not (isinstance(item.get("page"), int) and item["page"] >= 1 and isinstance(text, str) and 20 <= len(text) <= 400):
        return "cita no válida"
    if not re.search(rf"\b{item['days']}\b", text) and not any(
            re.search(rf"\b{re.escape(word)}\b", fold(text)) for word, number in WORDS.items() if number == item["days"]):
        return "la cita no contiene los días"
    return None


def validate(document: dict, urls: set[str]) -> None:
    if document.get("schemaVersion") != 1:
        raise ValueError("schemaVersion")
    for url, item in document["items"].items():
        error = problem(url, item, urls)
        if error:
            raise ValueError(f"{error}: {url[:90]}")


def update(docs: Path, limit: int, workers: int = 6) -> dict:
    out_dir = docs / "plazos"
    out_dir.mkdir(exist_ok=True)
    stats = {"leidos": 0, "con_plazo": 0, "fallidos": 0, "pendientes": 0}
    jobs = []
    states = {}
    for feed_path in sorted(docs.glob("*.json")):
        if feed_path.name in NOT_FEEDS:
            continue
        try:
            feed = json.loads(feed_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(feed, dict):
            continue
        urls = list(dict.fromkeys(candidate_notices(feed)))
        target = out_dir / feed_path.name
        old = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
        # Se quedan solo los anuncios que siguen en el feed (ventana de 30 días).
        state = {
            "items": {u: v for u, v in old.get("items", {}).items() if u in urls},
            "none": [u for u in old.get("none", []) if u in urls],
            "tries": {u: n for u, n in old.get("tries", {}).items() if u in urls},
        }
        states[feed_path.name] = (state, set(urls))
        done = set(state["items"]) | set(state["none"])
        for url in urls:
            if url not in done and state["tries"].get(url, 0) < MAX_TRIES:
                jobs.append((feed_path.name, url))
    stats["pendientes"] = max(0, len(jobs) - limit)

    def work(job):
        name, url = job
        try:
            data = download(url)
            return name, url, "ok", find_in_pdf(data) if data else None
        except Exception as error:  # red, servidor o PDF dañado: se reintenta otro día
            return name, url, type(error).__name__, None

    with ThreadPoolExecutor(workers) as pool:
        for name, url, status, found in pool.map(work, jobs[:limit]):
            state = states[name][0]
            if status != "ok":
                state["tries"][url] = state["tries"].get(url, 0) + 1
                stats["fallidos"] += 1
                continue
            stats["leidos"] += 1
            state["tries"].pop(url, None)
            if found and not problem(url, found, states[name][1]):
                state["items"][url] = found
                stats["con_plazo"] += 1
            else:
                state["none"].append(url)

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    for name, (state, urls) in states.items():
        document = {"schemaVersion": 1, "updatedUTC": now, "items": state["items"],
                    "none": sorted(state["none"]), "tries": state["tries"]}
        validate(document, urls)
        (out_dir / name).write_text(json.dumps(document, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    # Archivos de fuentes que ya no existen.
    for stale in out_dir.glob("*.json"):
        if stale.name not in states:
            stale.unlink()
    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Lee el plazo de presentación de los anuncios nuevos")
    parser.add_argument("command", choices=["update"])
    parser.add_argument("--docs", default="docs")
    parser.add_argument("--limit", type=int, default=500, help="PDF como máximo en esta ejecución")
    args = parser.parse_args()
    started = time.time()
    print(json.dumps(update(Path(args.docs), args.limit), ensure_ascii=False), f"{time.time() - started:.0f} s")
