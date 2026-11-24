"""Fecha orientativa del último día de un plazo de presentación.

Solo se estima cuando la frase literal del anuncio dice que el plazo cuenta desde el día
siguiente a la publicación **en el mismo boletín** del que sale el anuncio (o «de este
anuncio»), porque entonces la fecha de inicio es la del propio boletín, que ya conocemos.
Si cuenta desde el BOE, desde otro diario oficial o desde la «última publicación», no se
estima nada.

La estimación es **conservadora**: nunca da un día posterior al real.
- Días hábiles (Ley 39/2015): se saltan sábados, domingos y solo las fiestas nacionales
  que ninguna comunidad puede cambiar. Los festivos autonómicos y locales que no se
  descuentan solo pueden alargar el plazo real.
- Días naturales: se cuentan todos; si el último cae en día inhábil, el plazo real se
  alarga al siguiente hábil.
Por eso la app la muestra como «como pronto» y recuerda comprobar el anuncio.
"""
from __future__ import annotations

import re
from datetime import date, timedelta

from plazos import fold

# Cómo se nombra cada boletín en los anuncios (texto sin tildes y en minúsculas).
_BOP = (r"boletin oficial de (?:la )?provincia|boletin oficial da provincia|butlleti oficial de la provincia"
        r"|\bb\.?\s?o\.?\s?p\b\.?|\bbop[b-z]?\b")
ALIASES = {
    "BOE": r"boletin oficial del estado|\bb\.?\s?o\.?\s?e\b\.?",
    "BOP": _BOP,
    "DOGV": r"diari oficial de la (?:comunitat|generalitat) valenciana|diario oficial de la (?:comunidad|generalitat) valenciana|\bdogv\b|\bdocv\b",
    "DOGC": r"diari oficial de la generalitat de catalunya|diario oficial de la generalitat de cataluna|\bdogc\b",
    "BOJA": r"boletin oficial de la junta de andalucia|\bboja\b",
    "BOA": r"boletin oficial de aragon|\bboa\b",
    "BOIB": r"boletin oficial de las illes balears|butlleti oficial de les illes balears|\bboib\b",
    "BOC_IC": r"boletin oficial de canarias",
    "BOC_CN": r"boletin oficial de cantabria",
    "BOCYL": r"boletin oficial de castilla y leon|\bbocyl\b",
    "DOCM": r"diario oficial de castilla-?\s?la mancha|\bdocm\b",
    "DOE": r"diario oficial de extremadura|\bdoe\b",
    "DOG": r"diario oficial de galicia|\bdog\b",
    "BOCM": r"boletin oficial de la comunidad de madrid|\bbocm\b",
    "BORM": r"boletin oficial de la region de murcia|\bborm\b",
    "BON": r"boletin oficial de navarra|\bbon\b",
    "BOPV": r"boletin oficial del pais vasco|euskal herriko agintaritzaren aldizkaria|\bbopv\b",
    "BOR": r"boletin oficial de la rioja|\bbor\b",
    "BOPA": r"boletin oficial del principado de asturias|\bbopa\b",
    "BOCCE": r"boletin oficial de (?:la ciudad (?:autonoma )?de )?ceuta|\bbocce\b",
    "BOME": r"boletin oficial de (?:la ciudad (?:autonoma )?de )?melilla|\bbome\b",
    "BOB": r"boletin oficial de bizkaia|bizkaiko aldizkari ofiziala|\bbob\b",
    "BOG": r"boletin oficial de gipuzkoa|gipuzkoako aldizkari ofiziala|\bbog\b",
    "BOTHA": r"boletin oficial del territorio historico de alava|\bbotha\b",
    "BOP_LP": r"boletin oficial de la provincia de las palmas",
}
_COMPILED = {k: re.compile(v) for k, v in ALIASES.items()}

# Boletín propio de cada feed. Sin entrada (CIDO, catálogos agregados): no se estima.
OWN = {
    "boe.json": "BOE", "valencia_dogv.json": "DOGV", "cataluna_dogc.json": "DOGC",
    "andalucia_boja.json": "BOJA", "aragon_boa.json": "BOA", "baleares_boib.json": "BOIB",
    "canarias_boc.json": "BOC_IC", "cantabria_boc.json": "BOC_CN", "castilla_leon_bocyl.json": "BOCYL",
    "castilla_mancha_docm.json": "DOCM", "extremadura_doe.json": "DOE", "galicia_dog.json": "DOG",
    "madrid_bocm.json": "BOCM", "murcia_borm.json": "BORM", "navarra_bon.json": "BON",
    "pais_vasco_bopv.json": "BOPV", "rioja_bor.json": "BOR", "asturias_bopa.json": "BOPA",
    "ceuta_bocce.json": "BOCCE", "melilla_bome.json": "BOME", "bizkaia_bob.json": "BOB",
    "gipuzkoa_bog.json": "BOG", "alava_botha.json": "BOTHA",
}
# Los BOP: «Boletín Oficial de la Provincia», «BOP», «BOPG»…
BOP_FEEDS = {
    "convocatorias.json", "alicante.json", "castellon.json", "albacete_bop.json", "almeria_bop.json",
    "avila_bop.json", "badajoz_bop.json", "barcelona_bop.json", "burgos_bop.json", "caceres_bop.json",
    "cadiz_bop.json", "canarias_las_palmas.json", "canarias_santa_cruz.json", "ciudad_real_bop.json",
    "cordoba_bop.json", "cuenca_bop.json", "galicia_coruna.json", "galicia_lugo.json",
    "galicia_ourense.json", "galicia_pontevedra.json", "girona_bop.json", "granada_bop.json",
    "guadalajara_bop.json", "huelva_bop.json", "huesca_bop.json", "jaen_bop.json", "leon_bop.json",
    "lleida_bop.json", "palencia_bop.json", "salamanca_bop.json", "segovia_bop.json", "sevilla_bop.json",
    "soria_bop.json", "tarragona_bop.json", "teruel_bop.json", "toledo_bop.json", "valladolid_bop.json",
    "zamora_bop.json", "zaragoza_bop.json",
}

# «a partir del día siguiente al de la publicación», «des de l'endemà de la publicació»,
# «dende o día seguinte ao da publicación».
FROM_NEXT_DAY = re.compile(r"(?:dia )?siguiente|endema|dia seguent|seguinte")
PUBLICATION = re.compile(r"publicacio(?:n)?\b|publicacion")
THIS_NOTICE = re.compile(
    r"(?:este|presente|dicho) (?:anuncio|edicto|extracto)|(?:aquest|aquesta|el present) (?:anunci|edicte)"
    r"|(?:deste|este|o presente) (?:anuncio|edicto)")
# Varias publicaciones: el plazo empieza con la última, que no sabemos cuándo es.
SEVERAL = re.compile(r"ultim[ao]|darrer[ao]|ultima de|posterior|ambos|ambdos|integro|integra")


def starts_with_own_bulletin(feed_name: str, text: str) -> bool:
    """True solo si la frase hace contar el plazo desde este mismo boletín."""
    own = OWN.get(feed_name) or ("BOP" if feed_name in BOP_FEEDS else None)
    if not own or not text or text.rstrip().endswith("…"):
        return False
    folded = fold(text)
    if not (FROM_NEXT_DAY.search(folded) and PUBLICATION.search(folded)) or SEVERAL.search(folded):
        return False
    named = {k for k, rx in _COMPILED.items() if rx.search(folded)}
    if own == "BOP":
        # «Boletín Oficial de la Provincia de Las Palmas» es un BOP: no cuenta como otro.
        named.discard("BOP_LP")
    if named:
        return named == {own}
    return bool(THIS_NOTICE.search(folded))


def easter(year: int) -> date:
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month, day = divmod(h + l - 7 * m + 114, 31)
    return date(year, month, day + 1)


def national_holidays(year: int) -> set[date]:
    """Fiestas nacionales que ninguna comunidad sustituye (Viernes Santo incluido)."""
    fixed = [(1, 1), (5, 1), (8, 15), (10, 12), (11, 1), (12, 6), (12, 8), (12, 25)]
    return {date(year, m, d) for m, d in fixed} | {easter(year) - timedelta(days=2)}


def estimate_end(published: date, days: int, kind: str) -> date | None:
    """Último día del plazo como pronto, contando desde el día siguiente a «published»."""
    if not 1 <= days <= 90:
        return None
    if kind == "naturales":
        return published + timedelta(days=days)
    if kind != "hábiles":
        return None
    day, left = published, days
    while left:
        day += timedelta(days=1)
        if day.weekday() < 5 and day not in national_holidays(day.year):
            left -= 1
    return day


def parse_feed_date(value: object) -> date | None:
    m = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", str(value or ""))
    if not m:
        return None
    try:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    except ValueError:
        return None


def end_for(feed_name: str, item: dict, published: date | None) -> str | None:
    """«AAAA-MM-DD» o None si no se puede estimar con seguridad."""
    if published is None or not starts_with_own_bulletin(feed_name, item.get("text", "")):
        return None
    end = estimate_end(published, item.get("days", 0), item.get("kind", ""))
    return end.isoformat() if end else None
