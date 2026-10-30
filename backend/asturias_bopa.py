#!/usr/bin/env python3
"""Asturias BOPA: feed diario de los últimos 30 días (código AS).

Fuente: el sumario oficial de cada boletín en miPrincipado
(https://miprincipado.asturias.es/ast/bopa-sumario?…p_r_p_summaryDate=DD/MM/AAAA).
Cada sumario trae el número y la fecha del boletín, todas las disposiciones
con su código «Cód. AAAA-NNNNN», el organismo y el PDF original en
https://www.asturias.es/bopa/AAAA/MM/DD/AAAA-NNNNN.pdf, los suplementos
(…/AAAAMMDDSuN.pdf) y el enlace «Boletín del día anterior».

Cómo se recorre la ventana (end-29 … end, end = hoy o `audit(today=...)`):
- Se pide el sumario de `end`; si ese día no hubo BOPA, el portal devuelve el
  último boletín publicado (comprobado contra `p_r_p_summaryLastBopa=true`) y se
  retrocede un día, como mucho 4.
- Desde ahí se sigue el enlace oficial «Boletín del día anterior» hasta salir
  de la ventana. La numeración debe ir seguida (vuelve a 1 en enero:
  `clm_common.numbering_ok`) y cada sumario debe ser del día pedido.
- El portal conserva los años anteriores, así que en enero la ventana cruza el
  año sin tratamiento especial.

Se descarga el PDF original de cada convocatoria candidata y uno por boletín:
su cabecera debe llevar el código y la fecha del sumario, y su número o el
anterior (ver HEADER_NUMBER_LAG: las dos «erratas» de la instantánea de octubre
eran parte de un desfase general tras la edición del festivo 12/10/2026).

Los suplementos (p. ej. 23/10/2026, 31/12/2025) son una edición más
(«206S1»): se lee el PDF y se clasifica la disposición por su título.

Nunca se publica un feed parcial: ante cualquier incoherencia, excepción.
Este portal no responde desde GitHub Actions; se ejecuta en un PC con conexión
española.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import re
import threading
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, quote, urljoin, urlsplit

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

from clm_common import employment, numbering_ok, publish_audit, write_output
from provincial_common import ProvincialCoverageError

SOURCE = "https://miprincipado.asturias.es/ast/bopa-sumario"
SUMMARY_HOST = "miprincipado.asturias.es"
PDF_HOST = "www.asturias.es"
PROVINCE = "Asturias (BOPA)"
DAYS = 30
# Diario de lunes a viernes (con algún festivo): unas 21-22 ediciones en 30 días,
# unas 17 en Navidad.
MIN_ISSUES = 15
# Unos 25-70 anuncios por boletín (917 del 30/9 al 29/10/2026).
MIN_ANNOUNCEMENTS = 250
# Fin de semana largo: la última edición puede estar hasta 3 días dentro.
MAX_LEAD_DAYS = 4
WORKERS = 3
PORTLET = "pa_sede_bopa_web_portlet_SedeBopaSummaryWeb"
CODE_RE = re.compile(r"\[\s*C[oó]d\.\s*(\d{4}-\d{5})\s*\]")
H1_RE = re.compile(r"Bolet[ií]n\s+N[º°o]\.?\s*(\d{1,4})\s+del\s+\w+\s+(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})$")
MONTHS = {m: i for i, m in enumerate(("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                        "septiembre", "octubre", "noviembre", "diciembre"), 1)}
ROMAN = {1: "i", 2: "ii", 3: "iii", 4: "iv", 5: "v", 6: "vi", 7: "vii", 8: "viii", 9: "ix", 10: "x", 11: "xi", 12: "xii"}
# Número impreso en la cabecera de los PDF originales: el editor lo compone antes
# de cerrar el boletín y, si se intercala una edición (p. ej. la n.º 197 del festivo
# 12/10/2026, con una sola disposición), muchos PDF salen con el número anterior:
# 45 de 55 en el n.º 198 (13/10/2026) y 4 de 40 en el n.º 200 (15/10/2026) dicen
# 197 y 199. Las dos «erratas» de la instantánea de octubre (2026-08061 y
# 2026-08160) son casos de esto. Se admite el número del sumario o el anterior;
# la fecha y el código del PDF tienen que coincidir siempre.
HEADER_NUMBER_LAG = 1
# Plural del apartado -> nombre del organismo (los títulos dicen «DE GIJÓN»).
LOCAL_KINDS = {"ayuntamientos": "Ayuntamiento", "mancomunidades": "Mancomunidad",
               "parroquias rurales": "Parroquia rural", "consorcios": "Consorcio",
               "entidades locales menores": "Entidad local menor"}
SMALL_WORDS = {"de", "del", "la", "las", "los", "el", "y", "e", "en", "a", "al", "para", "por", "con", "o", "u", "d'"}
HTTP = threading.local()


def invalid(message):
    raise ProvincialCoverageError("Asturias BOPA: " + str(message))


def fold(text):
    d = unicodedata.normalize("NFD", str(text).casefold())
    return re.sub(r"\s+", " ", "".join(c for c in d if unicodedata.category(c) != "Mn")).strip()


def clean(text):
    return re.sub(r"\s+", " ", str(text).replace("\xa0", " ")).strip()


def client():
    if not hasattr(HTTP, "client"):
        s = requests.Session()
        s.headers.update({"User-Agent": "Mozilla/5.0 (compatible; OpoAlert BOPA daily audit/1.0)",
                          "Accept-Language": "es-ES,es;q=0.9"})
        HTTP.client = s
    return HTTP.client


def check_url(url, host, prefix):
    u = urlsplit(url)
    if (u.scheme != "https" or u.hostname != host or u.port not in (None, 443) or u.username
            or u.password or u.fragment or not u.path.startswith(prefix)):
        invalid("URL fuera de la sede oficial: " + url[:200])
    return u


def fetch(url, host, prefix, pdf=False, max_size=4_000_000, attempts=3):
    check_url(url, host, prefix)
    error = None
    for attempt in range(attempts):
        try:
            with client().get(url, timeout=(12, 45), stream=True, allow_redirects=False) as r:
                ctype = r.headers.get("Content-Type", "").lower()
                if r.status_code == 200 and (("pdf" in ctype) if pdf else ("html" in ctype)):
                    data = bytearray()
                    for block in r.iter_content(65536):
                        data.extend(block)
                        if len(data) > max_size:
                            invalid(f"respuesta desmesurada ({len(data)} bytes): {url}")
                    if pdf and not data.startswith(b"%PDF-"):
                        invalid("el documento original no es un PDF: " + url)
                    if not pdf and len(data) < 5000:
                        invalid("página vacía o truncada: " + url)
                    return bytes(data)
                error = f"HTTP {r.status_code} ({ctype or 'sin tipo'})"
                if r.status_code in (301, 302, 303, 307, 308, 401, 403, 404):
                    break
        except requests.RequestException as ex:
            error = str(ex)[:180]
        if attempt < attempts - 1:
            time.sleep(2 * (attempt + 1))
    invalid(f"sin acceso a {url}: {error}")


def summary_url(day=None):
    """Sumario oficial del día `day` (o el último boletín si day es None)."""
    base = SOURCE + f"?p_p_id={PORTLET}&p_p_lifecycle=0&p_p_state=normal&p_p_mode=view"
    if day is None:
        return base + "&p_r_p_summaryLastBopa=true"
    return (base + f"&_{PORTLET}_mvcRenderCommandName=%2F&p_r_p_summaryDate="
            + quote(day.strftime("%d/%m/%Y"), safe="") + "&p_r_p_summaryLastBopa=false")


def pdf_url(day, code):
    if not re.fullmatch(r"\d{4}-\d{5}", code):
        invalid("código BOPA mal formado: " + repr(code))
    return f"https://{PDF_HOST}/bopa/{day.strftime('%Y/%m/%d')}/{code}.pdf"


def smart_case(text):
    """«CONSEJERÍA DE SALUD» -> «Consejería de Salud»; respeta siglas entre paréntesis."""
    text = clean(text)
    if text != text.upper():
        return text
    out = []
    for i, word in enumerate(text.split(" ")):
        low = word.lower()
        if re.fullmatch(r"\(?[A-ZÁÉÍÓÚÑÜ]{2,}\)?[.,;]?", word) and word.startswith("("):
            out.append(word)
        elif re.fullmatch(r"[IVXLC]+[.,]?", word) and len(word.strip(".,")) > 1:
            out.append(word)
        elif i and low in SMALL_WORDS:
            out.append(low)
        else:
            # Mayúscula en la primera letra (también tras comillas o paréntesis).
            out.append("-".join(re.sub(r"^([^\w]*)(\w)", lambda m: m[1] + m[2].upper(), p)
                                for p in low.split("-")))
    return " ".join(out)


def entity_of(h5, h6, sub):
    if sub:
        return smart_case(sub)
    if not h6:
        # «VI. Otros anuncios»: la empresa o entidad va en el apartado (h5).
        if not h5:
            invalid("disposición sin organismo en el sumario")
        return smart_case(h5)
    kind = LOCAL_KINDS.get(fold(h5 or ""))
    m = re.match(r"(?i)(del?)\s+(\S.*)", smart_case(h6))
    if kind and m:
        # «DE EL FRANCO» -> «Ayuntamiento de El Franco»
        return f"{kind} {m[1].lower()} {m[2][0].upper()}{m[2][1:]}"
    return smart_case(h6)


def parse_h1(text):
    m = H1_RE.search(clean(text))
    if not m or fold(m[3]) not in MONTHS:
        invalid("cabecera de boletín ilegible: " + clean(text)[:120])
    return int(m[1]), date(int(m[4]), MONTHS[fold(m[3])], int(m[2]))


def parse_summary(html, requested=None):
    """Devuelve el boletín que muestra la página: número, fecha, anterior, anuncios y suplementos."""
    soup = BeautifulSoup(html, "html.parser")
    root = soup.find(id=f"p_p_id_{PORTLET}_") or soup
    h1s = root.find_all("h1")
    if len(h1s) != 1:
        if "formato de la fecha" in fold(root.get_text(" ")):
            invalid(f"el portal rechaza la fecha pedida {requested}")
        invalid("página sin un boletín único")
    number, day = parse_h1(h1s[0].get_text(" "))
    previous = None
    for a in root.find_all("a", href=True):
        if "dia anterior" in fold(a.get_text(" ")):
            q = parse_qs(urlsplit(a["href"]).query).get("p_r_p_summaryDate", [""])[0]
            try:
                prev = datetime.strptime(q, "%d/%m/%Y").date()
            except ValueError:
                invalid("enlace al boletín anterior ilegible")
            if previous not in (None, prev):
                invalid("dos boletines anteriores distintos")
            previous = prev
    body = root.find(id="bopa-boletin")
    supplements = []
    for a in root.find_all("a", href=True):
        href = a["href"]
        if re.search(r"Su\d+\.pdf$", href):
            url = urljoin("https://" + PDF_HOST + "/", href)
            if not re.fullmatch(rf"https://{re.escape(PDF_HOST)}/bopa/{day:%Y/%m/%d}/{day:%Y%m%d}Su(\d+)\.pdf", url):
                invalid("suplemento con enlace inesperado: " + href[:150])
            if url not in supplements:
                supplements.append(url)
    if body is None:
        invalid(f"boletín {number} sin sumario de disposiciones")
    items = []
    h4 = h5 = h6 = sub = None
    for el in body.find_all(["h4", "h5", "h6", "p", "dl"]):
        if el.name == "h4":
            h4, h5, h6, sub = clean(el.get_text(" ")), None, None, None
        elif el.name == "h5":
            h5, h6, sub = clean(el.get_text(" ")), None, None
        elif el.name == "h6":
            h6, sub = clean(el.get_text(" ")), None
        elif el.name == "p":
            if "subAuthor" in (el.get("class") or []):
                sub = clean(el.get_text(" "))
        else:
            dts = el.find_all("dt")
            if len(dts) != 1:
                invalid(f"boletín {number}: disposición sin título único")
            raw = clean(dts[0].get_text(" "))
            codes = CODE_RE.findall(raw)
            if len(codes) != 1:
                invalid(f"boletín {number}: disposición sin código BOPA: {raw[:120]}")
            code = codes[0]
            title = clean(CODE_RE.sub("", raw))
            if not 6 < len(title) <= 2800:
                invalid(f"boletín {number}: título vacío o anómalo en {code}")
            pdfs = [urljoin("https://" + PDF_HOST + "/", a["href"]) for a in el.find_all("a", href=True)
                    if a["href"].lower().endswith(".pdf")]
            if pdfs != [pdf_url(day, code)]:
                invalid(f"boletín {number}: {code} sin su PDF original ({pdfs[:2]})")
            items.append({"code": code, "title": title, "entity": entity_of(h5, h6, sub),
                          "section": h4, "url": pdfs[0]})
    return {"number": number, "day": day, "previous": previous, "items": items, "supplements": supplements}


def load_summary(day=None):
    return parse_summary(fetch(summary_url(day), SUMMARY_HOST, "/ast/bopa-sumario").decode("utf-8", "replace"), day)


def walk(end, latest, loader=load_summary):
    """Boletines de la ventana, del más reciente al más antiguo, por el enlace oficial «día anterior»."""
    start = end - timedelta(days=DAYS - 1)
    issues = []
    day = end
    for _ in range(MAX_LEAD_DAYS + 1):
        page = loader(day)
        if page["day"] == day:
            break
        # Día sin BOPA: el portal muestra el último boletín publicado.
        if (page["day"], page["number"]) != (latest["day"], latest["number"]):
            invalid(f"el sumario del {day} muestra el boletín del {page['day']}, que no es el último publicado")
        day -= timedelta(days=1)
    else:
        invalid(f"no hay boletín en los {MAX_LEAD_DAYS + 1} últimos días de la ventana ({end})")
    seen = set()
    while True:
        if page["day"] != day:
            invalid(f"se pidió el boletín del {day} y el portal devolvió el del {page['day']}")
        if day in seen:
            invalid("bucle en los enlaces de boletines anteriores")
        seen.add(day)
        issues.append(page)
        print(f"BOPA {day} n.º {page['number']}: {len(page['items'])} disposiciones"
              + (f", {len(page['supplements'])} suplemento(s)" if page["supplements"] else ""), flush=True)
        prev = page["previous"]
        if prev is None or prev >= day:
            invalid(f"boletín {page['number']} sin enlace válido al anterior")
        if prev < start:
            break
        if len(issues) > DAYS:
            invalid("demasiados boletines en 30 días")
        day = prev
        page = loader(day)
    issues.reverse()
    if not numbering_ok([(x["day"], x["number"]) for x in issues]):
        invalid("numeración de boletines no seguida: " +
                ", ".join(f"{x['day']}:{x['number']}" for x in issues))
    return issues


def first_page(data):
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
        pages = len(reader.pages)
        text = reader.pages[0].extract_text() or ""
    except Exception as ex:  # pypdf lanza varios tipos
        invalid("PDF original ilegible: " + str(ex)[:120])
    if not 1 <= pages <= 2000 or len(text) < 120:
        invalid("PDF original sin texto legible en la primera página")
    return pages, text


def verify_pdf(task):
    """Comprueba que el PDF original es del boletín, día y código del sumario."""
    day, number, code, url = task
    data = fetch(url, PDF_HOST, "/bopa/", pdf=True, max_size=25_000_000)
    pages, text = first_page(data)
    top = fold(text[:1200])
    header = re.search(rf"num[.]\s*(\d{{1,4}})\s+de\s+0?{day.day}-{ROMAN[day.month]}-{day.year}\b", top)
    if header is None or not re.search(r"\bcod[.]\s*" + re.escape(code) + r"\b", top):
        invalid(f"la cabecera del PDF {code} no es del boletín del {day}: {top[:160]!r}")
    printed = int(header[1])
    if not 0 <= number - printed <= HEADER_NUMBER_LAG:
        invalid(f"el PDF {code} dice n.º {printed} y el sumario n.º {number}")
    return {"code": code, "printedNumber": printed, "sha256": hashlib.sha256(data).hexdigest()}


TITLE_START = re.compile(r"(?im)^\s*(ley|decreto|resoluci[oó]n|acuerdo|orden|anuncio|edicto|instrucci[oó]n|"
                         r"circular|correcci[oó]n|informaci[oó]n|convocatoria|bases)\b")


def read_supplement(day, number, url):
    """Un suplemento = una edición con sus disposiciones (código y título de la primera página)."""
    data = fetch(url, PDF_HOST, "/bopa/", pdf=True, max_size=60_000_000)
    pages, text = first_page(data)
    top = fold(text[:600])
    if not re.search(rf"suplemento al num[.]\s*\S+\s+de\s+0?{day.day}-{ROMAN[day.month]}-{day.year}\b", top):
        invalid(f"cabecera del suplemento {url} no corresponde al {day}: {top[:160]!r}")
    codes = list(dict.fromkeys(re.findall(r"C[oó]d\.\s*(\d{4}-\d{5})", text)))
    if len(codes) != 1:
        invalid(f"suplemento {url}: se esperaba un código en la primera página, hay {codes}")
    m = TITLE_START.search(text)
    if not m:
        invalid(f"suplemento {url}: no se encuentra el título de la disposición")
    title = clean(re.split(r"\.\s*\n|\.\s{2,}", text[m.start():], maxsplit=1)[0]) + "."
    if not 10 < len(title) <= 2800:
        invalid(f"suplemento {url}: título ilegible")
    # Organismo: las líneas entre la sección («I. Principado…», «Autoridades y Personal •») y el título.
    code_at = re.search(r"C[oó]d\.\s*\d{4}-\d{5}", text).end()
    lines = [clean(x) for x in text[code_at:m.start()].splitlines() if clean(x)]
    lines = [x for x in lines if "•" not in x and not re.match(r"[IVX]+\.\s", x)]
    entity = smart_case(" ".join(lines).upper()) if lines else ""
    tag = re.search(r"Su(\d+)\.pdf$", url)[1]
    print(f"BOPA {day} suplemento {tag} ({pages} págs.): {codes[0]} {entity[:60]} | {title[:90]}", flush=True)
    return {"code": codes[0], "title": title, "entity": entity, "number": f"{number}S{tag}", "url": url}


# Actos de un proceso ya convocado (resolución, nombramiento, adjudicación, listas,
# rectificaciones…) que el clasificador común deja pasar en los títulos del BOPA.
FOLLOW_UP = ("se resuelve", "resuelve la convocatoria", "resuelve el proceso", "plazas a adjudicar",
             "se adjudican", "adjudicacion de puestos", "resolucion de adjudicacion", "se nombra",
             "se nombran", "nombramiento", "declara desierta", "deja sin efecto", "deja sin efectos",
             "dispone la contratacion", "se excluyen", "excluyen candidatos", "aprueba la bolsa",
             "recurso de alzada", "normas para la gestion", "no oposicion", "rectificacion", "rectifican",
             "correccion de error", "corrige error", "se modifica", "modificacion de la convocatoria",
             "modificacion de las bases", "movilidad voluntaria", "comision calificadora", "tribunal",
             "fase de practicas", "lista provisional", "lista definitiva", "relacion provisional",
             "relacion definitiva", "admitid", "excluid", "concurso de traslados", "juez de paz",
             "jueza de paz", "anuncio. contratacion, como personal")
# … salvo que el mismo acto convoque de nuevo (p. ej. «deja sin efecto … y se convocan pruebas selectivas»).
NEW_CALL = ("y se convocan pruebas selectivas", "y se convoca proceso selectivo", "y se convocan las pruebas")
NOT_JOBS = ("subvencion", "ayudas", "beca", "premio", "licitacion")
NOT_SELECTION = ("contrato de obras", "contrato de servicios", "contrato de suministro", "proyectos de",
                 "alumnado", "alumnos")


def classify(title):
    """Tipo de convocatoria de empleo, o None.

    Clasificador común (`clm_common.employment`) sin los actos de procesos ya
    convocados, y además las convocatorias municipales de «selección de
    personas a contratar» (planes de empleo, contratos formativos) que el común
    no reconoce."""
    t = fold(title)
    if any(x in t for x in NOT_JOBS):
        return None
    if any(x in t for x in FOLLOW_UP) and not any(x in t for x in NEW_CALL):
        return None
    kind = employment(title)
    if kind:
        return kind
    if (not any(x in t for x in NOT_SELECTION) and ("bases" in t or "convocatoria" in t)
            and any(x in t for x in ("seleccion de", "proceso de seleccion", "plan de empleo", "proceso selectivo"))):
        return "Bolsa de trabajo" if "bolsa" in t else "Plaza / oposición"
    return None


def notice(day, bulletin, code, title, entity, url):
    kind = classify(title)
    if not kind:
        return None
    if not entity or len(entity) > 500:
        invalid(f"{code} sin organismo")
    return {"id": "AS-" + code, "province": PROVINCE, "title": title, "entity": entity,
            "date": day.strftime("%d/%m/%Y"), "bulletin": str(bulletin), "type": kind, "url": url}


def audit(today=None):
    end = today or date.today()
    start = end - timedelta(days=DAYS - 1)
    latest = load_summary(None)
    print(f"BOPA: último boletín publicado n.º {latest['number']} del {latest['day']}; ventana {start}–{end}", flush=True)
    pages = walk(end, latest)
    codes = {}
    for p in pages:
        if not 1 <= len(p["items"]) <= 400:
            invalid(f"boletín {p['number']} vacío o desmesurado: {len(p['items'])}")
        for it in p["items"]:
            if it["code"] in codes:
                invalid(f"código {it['code']} repetido en dos boletines")
            codes[it["code"]] = p["day"]
    total = sum(len(p["items"]) for p in pages)
    if total < MIN_ANNOUNCEMENTS:
        invalid(f"histórico sospechosamente corto: {total} disposiciones")
    issues = []
    checks = {}
    supplement_tasks = []
    for p in pages:
        found = []
        for it in p["items"]:
            n = notice(p["day"], p["number"], it["code"], it["title"], it["entity"], it["url"])
            if n:
                found.append(n)
                checks[it["code"]] = (p["day"], p["number"], it["code"], it["url"])
        rep = p["items"][0]
        checks.setdefault(rep["code"], (p["day"], p["number"], rep["code"], rep["url"]))
        issues.append({"day": p["day"], "number": str(p["number"]), "read": len(p["items"]), "notices": found})
        for url in p["supplements"]:
            supplement_tasks.append((p["day"], p["number"], url))
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(verify_pdf, checks.values()))
    for day, number, url in supplement_tasks:
        s = read_supplement(day, number, url)
        if s["code"] in codes:
            invalid(f"el suplemento repite el código {s['code']}")
        codes[s["code"]] = day
        n = notice(day, s["number"], s["code"], s["title"], s["entity"], url)
        issues.append({"day": day, "number": s["number"], "read": 1, "notices": [n] if n else []})
    candidates = sum(len(x["notices"]) for x in issues)
    print(f"BOPA: {len(pages)} boletines y {len(supplement_tasks)} suplementos, {total + len(supplement_tasks)} "
          f"disposiciones, {candidates} candidatas; {len(checks)} PDF originales cotejados", flush=True)
    return publish_audit(SOURCE, PROVINCE, issues, today=end, min_issues=MIN_ISSUES)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--output", type=Path, required=True)
    args = ap.parse_args()
    write_output(args.output, audit())
