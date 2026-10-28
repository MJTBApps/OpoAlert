#!/usr/bin/env python3
"""Extractor sin dependencias externas del indice publicado por el BOP Valencia.

No afirma que una pagina HTML contenga TODO el boletin. Esa responsabilidad
corresponde a bop_full.py, que recorre paginas y verifica su cobertura.
"""
import argparse
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import unicodedata
from urllib.request import Request, urlopen

SOURCE = "https://bop.dival.es/bop/xhtml/portal.xhtml"
META = re.compile(
    r"N[uú]m\.?\s*(?:de\s*)?regist(?:re|ro)\s*:\s*(\d{4}/\d{3,7})"
    r".{0,110}?(?:Data|Fecha)\s+publicaci[oó]n?\s*:\s*(\d{2}/\d{2}/\d{4})"
    r".{0,100}?(?:Butllet[ií]|Bolet[ií]n|Suplement|Suplemento)\s*:\s*(\d+(?:-\d+)?)", re.I | re.S
)
ANNOUNCE = re.compile(r"\bAnunci(?:o)?\s+(?:de\s|del\s|d['’])", re.I)
ENTITY = re.compile(r"(?:Ajuntament|Ayuntamiento)\s+(?:de|del|d['’])\s+(.+)$", re.I)
HEADING = re.compile(r"(?:Butllet[ií]|Bolet[ií]n)\s+N[uú]m\.?\s*(\d+)", re.I)

class TextParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.skip = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript", "footer"):
            self.skip.append(tag)
        if not self.skip and tag in ("p", "div", "li", "br", "h1", "h2", "h3", "tr", "td", "span", "a"):
            self.parts.append(" ")

    def handle_endtag(self, tag):
        if self.skip:
            if tag == self.skip[-1]:
                self.skip.pop()
            return
        if tag in ("p", "div", "li", "br", "h1", "h2", "h3", "tr", "td", "a"):
            self.parts.append(" ")

    def handle_data(self, data):
        if not self.skip:
            self.parts.append(data)


def fold(value):
    normalized = unicodedata.normalize("NFD", value.lower())
    return "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")

def classify(title):
    t = fold(title)
    forbidden = ["subvencio", "nomenament", "nombramiento", "admes", "admitid",
                 "excluid", "exclos", "relacio definitiva", "relacion definitiva",
                 "relacio provisional", "relacion provisional", "resultat", "resultado",
                 "llista definitiva", "lista definitiva", "cessio de la borsa",
                 "cesion de la bolsa", "jutge de pau", "juez de paz", "licitacio",
                 "licitacion", "eleccions", "correccio d'errors", "correccion de errores"]
    if any(s in t for s in forbidden):
        return None
    new_process = any(s in t for s in ("convocatoria", "bases", "constitucio",
                                         "constitucion", "creacio", "creacion"))
    pool = any(s in t for s in ("borsa de treball", "bolsa de trabajo", "borsa per a",
                                 "bolsa para", "borsa d'", "bolsa de empleo",
                                 "borsa per a la provisio", "constitucio d'una borsa",
                                 "constitucion de una bolsa"))
    if pool and new_process:
        return "Bolsa de trabajo"
    position = any(s in t for s in ("placa de", "places de", "plaza de", "plazas de",
                                     "proces selectiu", "proceso selectivo",
                                     "seleccio de personal", "seleccion de personal",
                                     "proves selectives", "pruebas selectivas"))
    if new_process and position:
        return "Plaza / oposición"
    return None

def entity_from_title(title: str) -> str:
    """Identifica el organismo del propio encabezado del anuncio.

    No inventa un ayuntamiento cuando el anuncio procede de una entidad local
    menor, una mancomunidad, un consorcio u otro organismo.
    """
    match = re.match(
        r"^Anunci(?:o)?\s+(?:de\s+|del\s+|d['’]\s*)(.+?)\s+sobre\b",
        title.strip(), re.I,
    )
    if not match:
        return "Administración pública (sin identificar)"
    organization = match.group(1).strip().rstrip('.:;,')
    organization = re.sub(r"^l['’]", "", organization, flags=re.I)
    city = re.match(r"^(?:Ajuntament|Ayuntamiento)\s+(de|del|d['’])\s*(.+)$", organization, re.I)
    if city:
        preposition, city_name = city.groups()
        return f"Ayuntamiento {preposition} {city_name}".replace("d' ", "d'")
    if re.match(r"^Entitat Local Menor\b", organization, re.I):
        return re.sub(r"^Entitat Local Menor", "Entidad Local Menor", organization, flags=re.I)
    if re.match(r"^Entidad Local Menor\b", organization, re.I):
        return organization
    # Para otros organismos conservamos literalmente su denominación en lugar
    # de etiquetarlos genéricamente como 'Administración pública'.
    return organization if len(organization) <= 130 else "Administración pública (sin identificar)"


class _DatagridRows(HTMLParser):
    """Lee SOLO las fichas principales del datagrid JSF del BOP.

    PrimeFaces anida anuncios de correccion relacionados en una ficha original.
    El extractor global de texto los contaba como si fueran resultados nuevos.
    Para evitarlo recogemos una ficha por cada .ui-datagrid-column dentro de
    #list_content y tomamos su PRIMER bloque de metadatos.

    El HTML entregado por Playwright ya es DOM renderizado. No dependemos de
    IDs generados (j_idt243) ni de la fecha del anuncio relacionado.
    """
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.div_depth = 0
        self.list_depth = None
        self.row_depth = None
        self.parts = []
        self.rows = []
        self.skip_tag = None
        self.title_depth = None
        self.title_parts = []
        self.row_title = None

    def handle_starttag(self, tag, attrs):
        if self.skip_tag:
            return
        if tag in ('script', 'style', 'noscript'):
            self.skip_tag = tag
            return
        if tag == 'div':
            self.div_depth += 1
            a = dict(attrs)
            if a.get('id') == 'list_content':
                self.list_depth = self.div_depth
            elif (self.list_depth is not None and self.row_depth is None
                  and 'ui-datagrid-column' in (a.get('class') or '').split()):
                self.row_depth = self.div_depth
                self.parts = []
                self.row_title = None
            elif (self.row_depth is not None and self.title_depth is None
                  and self.row_title is None
                  and 'sumario' in (a.get('class') or '').split()):
                self.title_depth = self.div_depth
                self.title_parts = []
        if self.row_depth is not None and tag in ('div','p','li','br','tr','td','span','a'):
            self.parts.append(' ')
        if self.title_depth is not None and tag in ('div','p','li','br','span','a'):
            self.title_parts.append(' ')

    def handle_endtag(self, tag):
        if self.skip_tag:
            if tag == self.skip_tag:
                self.skip_tag = None
            return
        if self.row_depth is not None and tag in ('div','p','li','br','tr','td','span','a'):
            self.parts.append(' ')
        if self.title_depth is not None and tag in ('div','p','li','br','span','a'):
            self.title_parts.append(' ')
        if tag == 'div':
            if self.title_depth is not None and self.div_depth == self.title_depth:
                self.row_title = re.sub(r'\s+', ' ', ''.join(self.title_parts)).strip()
                self.title_parts = []
                self.title_depth = None
            if self.row_depth is not None and self.div_depth == self.row_depth:
                self.rows.append((re.sub(r'\s+', ' ', ''.join(self.parts)).strip(),
                                  self.row_title))
                self.parts = []
                self.row_title = None
                self.row_depth = None
            if self.list_depth is not None and self.div_depth == self.list_depth:
                self.list_depth = None
            self.div_depth = max(0, self.div_depth - 1)

    def handle_data(self, data):
        if self.row_depth is not None and not self.skip_tag:
            self.parts.append(data)
        if self.title_depth is not None and not self.skip_tag:
            self.title_parts.append(data)


def datagrid_row_count(html):
    """0 indica fixture simplificado/portal sin datagrid; >0, filas oficiales."""
    collector = _DatagridRows()
    collector.feed(html)
    return len(collector.rows)


def _entry(fragment, title_override=None):
    """Extrae SOLO el primer registro de una ficha principal.

    Una correccion enlazada puede contener un segundo 'Num. registre' y una
    segunda fecha. No son un nuevo resultado de la busqueda.
    """
    match = META.search(fragment)
    if not match:
        return None
    if title_override is not None:
        title = title_override.strip()[:1400]
    else:
        hits = list(ANNOUNCE.finditer(fragment[:match.start()]))
        if not hits:
            return None
        title = fragment[hits[-1].start():match.start()].strip()[:1400]
    if not title:
        return None
    reg, day, bulletin = match.groups()
    return {
        'id': reg, 'title': title, 'entity': entity_from_title(title),
        'date': day, 'bulletin': bulletin, 'type': classify(title),
        'url': f"https://bop.dival.es/bop/downloads?anuncioNumReg={reg.replace('/', '%2F')}&lang=es",
    }


def extract_index(html):
    """Devuelve (anuncios del listado principal, boletin del encabezado).

    En el BOP real la fuente de verdad es #list_content .ui-datagrid-column.
    SOLO para HTML reducido de pruebas/otros portales se usa el lector antiguo
    de texto plano. Los anuncios asociados se excluyen por estructura.
    """
    parser = TextParser()
    parser.feed(html)
    raw = re.sub(r"\s+", " ", "".join(parser.parts)).strip()
    heading_match = HEADING.search(raw)
    heading = heading_match.group(1) if heading_match else None

    collector = _DatagridRows()
    collector.feed(html)
    if collector.rows:
        results = []
        for idx, (row_text, row_title) in enumerate(collector.rows, 1):
            entry = _entry(row_text, title_override=row_title)
            if entry is None:
                raise ValueError(
                    f'Ficha principal {idx}/{len(collector.rows)} sin titulo o '
                    'metadatos interpretables; no se asume cobertura completa')
            results.append(entry)
        if len({e['id'] for e in results}) != len(results):
            raise ValueError('El BOP devuelve un ID duplicado entre las fichas principales')
        return results, heading

    # Compatibilidad con los fixtures antiguos sin estructura de datagrid.
    matches = list(META.finditer(raw))
    if not matches:
        raise ValueError('No se encontro ningun anuncio: portal modificado o acceso denegado')
    pos = 0
    results = []
    for match in matches:
        prefix = raw[pos:match.end()]
        pos = match.end()
        entry = _entry(prefix)
        if entry:
            results.append(entry)
    return list({obj['id']: obj for obj in results}.values()), heading

def extract(html):
    all_entries, _ = extract_index(html)
    return [notice for notice in all_entries if notice["type"]]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--input', type=Path, help='HTML local para pruebas')
    ap.add_argument('--output', type=Path, default=Path('backend/resultado.json'))
    args = ap.parse_args()
    if args.input:
        html = args.input.read_text(encoding='utf-8')
    else:
        req = Request(SOURCE, headers={
            'User-Agent': 'Mozilla/5.0 (compatible; OpoAlert/0.2)',
            'Accept-Language': 'ca-ES,es-ES;q=0.9',
        })
        with urlopen(req, timeout=25) as response:
            html = response.read().decode('utf-8', errors='replace')
    current = extract(html)
    previous = []
    if args.output.exists():
        obj = json.loads(args.output.read_text(encoding='utf-8'))
        previous = obj.get('notices', [])
    all_notices = {entry['id']: entry for entry in previous}
    all_notices.update({entry['id']: entry for entry in current})
    all_notices = sorted(all_notices.values(), key=lambda x: (x['date'][6:]+x['date'][3:5]+x['date'][:2], x['id']), reverse=True)[:500]
    payload = {
        'source': SOURCE, 'lastCheckedUTC': datetime.now(timezone.utc).isoformat(),
        'countLastPage': len(current), 'notices': all_notices,
        'coverage': 'Solo anuncios de la portada visible; puede haber paginacion y omisiones.'
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(f"Detectadas en la portada: {len(current)}. Historico guardado: {len(all_notices)}")
    print(f"Archivo: {args.output}")

if __name__ == '__main__':
    main()
