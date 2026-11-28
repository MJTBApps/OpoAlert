"""Seguimiento de favoritas (1.59.0): ¿puede un anuncio ser otro paso de la misma convocatoria?

Referencia en Python de `app/.../FollowUpMatcher.kt` y de `FollowUp.swift` (iOS): la app
empareja en el móvil, con los feeds que ya descarga, porque las favoritas no salen del
teléfono. Este módulo sirve para medir el emparejador con los feeds de `docs/`
(`python backend/seguimiento.py medir`) y sus casos están en `tests/seguimiento_casos.json`,
que comprueban también Android e iOS.

Medido el 28/11/2026: 94 % de aciertos en la última muestra revisada a mano (47 de 50).
Solo organismos locales: con consejerías, ministerios y universidades casi todas las
parejas eran falsas. Se dice siempre «posible» y se pide confirmarlo en la ficha.
"""
from __future__ import annotations
import re, unicodedata

def fold(t: str) -> str:
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return t.replace("’", "'").replace("·", "")

# ---------- organismo ----------
KINDS = [
    ("ayto", r"(?:excmo\.?|excelentisimo|ilustre|iltre\.?|m\.?\s*i\.?)?\s*(?:ayuntamientos?|ajuntament|concello|udala|ayto\.?)"),
    ("dipu", r"(?:excma\.?)?\s*(?:diputacion|diputacio|deputacion)(?: provincial| foral)?"),
    ("comarca", r"(?:comarca|consell comarcal)"),
    ("manc", r"(?:mancomunidad|mancomunitat)"),
    ("cabildo", r"cabildo(?: insular)?"),
    ("consell", r"consell insular"),
    ("univ", r"(?:universidad|universitat|universidade)"),
]
ORG_STOP = {"de", "del", "d", "la", "el", "los", "las", "l", "les", "els", "a", "o", "os", "as", "y", "i", "e", "do", "da", "dos", "das"}
ORG_IN_TITLE = re.compile(
    r"\b(ayuntamiento|ajuntament|concello|diputacion provincial|diputacion|universidad|comarca|mancomunidad|cabildo insular)\s+(de |del |d')?([^,.;()]+?)(?=\s*(?:\(|,|\.|;| sobre | por | referente| relativ| de fecha| para | que | en |$))"
)

def org_from(text: str):
    t = fold(text).strip(" –-")
    t = re.sub(r"\([^)]*\)", " ", t)
    t = t.split(" - ")[0]
    kind = None
    for k, rx in KINDS:
        m = re.match(r"\s*" + rx + r"\b", t)
        if m:
            kind, t = k, t[m.end():]
            break
    toks = [w for w in re.findall(r"[a-z0-9]+", t) if w not in ORG_STOP]
    if not toks:
        return None
    return (kind or "?", " ".join(toks))

def org_key(n: dict):
    ent = n.get("entity") or ""
    title = fold(n.get("title") or "")
    m = ORG_IN_TITLE.search(title)
    from_title = org_from(m.group(1) + " " + m.group(3)) if m else None
    bad = ("recomendador" in fold(ent)) or not ent.strip()
    e = None if bad else org_from(ent)
    # Entidades de consejerías/ministerios: genéricas; preferir la del título si la hay
    if e and e[0] == "?" and from_title and from_title[0] != "?":
        return from_title
    return e or from_title

def same_org(a, b) -> bool:
    if not a or not b:
        return False
    if a[1] != b[1]:
        return False
    return a[0] == b[0] or "?" in (a[0], b[0]) and {a[0], b[0]} <= {"?", "ayto"}

# ---------- puesto ----------
POS_START = re.compile(
    r"\b(?:plazas?|places?|placa|prazas?|puestos?(?: de trabajo)?|llocs?(?: de treball)?|postos?(?: de traballo)?|"
    r"bolsas?(?: de (?:trabajo|empleo|empleo temporal|trabajo temporal|traballo|emprego))?|borsas?(?: de treball| d'ocupacio)?|"
    r"categorias?(?: profesional)?|cuerpos?|escala|especialidad)\s+(?:vacantes?\s+|vacants?\s+)?(?:de |del |d'|en la categoria de |para (?:la contratacion de |cubrir )?)?"
)
POS_STOP = re.compile(
    r"[,.;:\[\"«]| mediante| por (?!cuenta)| per | pel | como | com | en regimen| vacantes?\b| del grupo| grupo | subgrupo| incluid| correspondiente|"
    r" de la plantilla| de este| de esta| del ayuntamiento| de l'ajuntament| del concello| para (?!la contratacion)| en el | en la | con caracter| turno|"
    r" sistema| personal | funcionari| laboral| escala| a traves| de la oferta| oep| en propiedad| interin| temporal| fij[oa]| de caracter| reservad| y la constitucion|"
    r" y constitucion| y creacion| y formacion| y bolsa| mas bolsa| \d{4}\b| expediente| exp\b| de administracion (?:general|especial)| del organismo| de la (?:diputacion|universidad)| d'aquest| de l'| pertenec| pertany| dins"
)
GENERIC = {
    "plaza", "plazas", "puesto", "personal", "funcionario", "funcionaria", "laboral", "fijo", "temporal", "interino", "carrera",
    "bolsa", "trabajo", "empleo", "vacante", "una", "un", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez",
    "oep", "turno", "libre", "promocion", "interna", "de", "del", "la", "el", "los", "las", "y", "e", "i", "o", "en", "para", "con",
    "d", "l", "les", "els", "dels", "per", "a", "da", "do", "das", "dos", "na", "no",
    "naturaleza", "cita", "citan", "que", "se", "al", "designacion", "designacio", "orden", "ordre", "caracter", "correspondiente",
    "correspondientes", "unico", "unica", "varias", "diversas", "distintas", "siguiente", "siguientes", "relacionan", "ofertan", "establece",
    "trabajo", "treball", "traballo", "profesional", "categoria", "cuerpo", "cuerpos", "procedimiento", "proceso", "procesos", "selectivo",
    "seleccion", "convocatoria", "convocadas", "resolucion", "esta", "este", "por", "su", "sus", "aspirantes", "aprobados", "personas",
    "enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
    "gener", "febrer", "marc", "maig", "juny", "juliol", "setembre", "octubre", "novembre", "desembre", "excepcional", "reservada",
    "reservadas", "vacantes", "contratacion", "cubrir", "cobrir", "provision", "provisio", "ambito", "ambit", "adscrita", "adscrito",
    "grupo", "grup", "marco", "concurso", "concurs", "primer", "primera", "segunda", "ingreso", "acceso", "nuevo", "nueva", "plantilla", "carrec", "cargo",
}

def stem(w: str) -> str:
    if len(w) <= 4:
        return w
    if w.endswith("es") and len(w) > 6 and w[-3] in "rlnd":  # auxiliares -> auxiliar
        w = w[:-2]
    elif w.endswith("s"):
        w = w[:-1]
    if len(w) > 4 and w[-1] in "oae":
        w = w[:-1]
    return w

NUM = r"(?:\d+|una?|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|quince|veinte|treinta|cuarenta|cincuenta|dues|quatre|sis|set|vuit|nou|deu|duas|catro|sete|oito)"
COUNT = re.compile(r"\b(" + NUM + r")(?:\s*\(\d+\))?\s+(?:plazas?|places?|placa|prazas?|puestos?|llocs?)\b")
WORDS = {"un": 1, "una": 1, "dos": 2, "dues": 2, "duas": 2, "tres": 3, "cuatro": 4, "quatre": 4, "catro": 4, "cinco": 5, "cinc": 5,
         "seis": 6, "sis": 6, "siete": 7, "set": 7, "sete": 7, "ocho": 8, "vuit": 8, "oito": 8, "nueve": 9, "nou": 9, "diez": 10, "deu": 10,
         "once": 11, "doce": 12, "quince": 15, "veinte": 20, "treinta": 30, "cuarenta": 40, "cincuenta": 50}

def clean_title(title: str) -> str:
    t = fold(title)
    t = re.sub(r"(\w)/[a-z]{1,4}\b", r"\1", t)
    return re.sub(r"\((?:a|as|os|o)\)", "", t)

def plazas_count(title: str):
    m = COUNT.search(clean_title(title))
    if not m:
        return None
    w = m.group(1)
    return int(w) if w.isdigit() else WORDS.get(w)

FILLER = re.compile(
    r"^(?:(?:unica|permanente|ordinaria|extraordinaria|urgente|urgent|d'urgencia|posibles|eventuales|futuras|vacantes?|de|del|d'|y|i|e|personal|persoal|laboral|temporal|"
    r"funcionari[oa]?|interin[oa]?|fij[oa]|fix|treball|trabajo|traballo|empleo|emprego|ocupacio|las?|los|el|les|els|categoria|cuerpo|escala)(?:\s+|(?<=')))+"
)
CODE_PAREN = re.compile(r"\((?:\s*\d|codi|cod|exp|sel|rh|ref|conv|oep|grup|subgrup|[abc][12]\b|pp\.)[^)]*\)")

def job_keys(title: str) -> list:
    """El puesto con lo que va entre paréntesis («técnico medio (inspector de actividades)») y sin ello
    («operario de servicios múltiples (oficial 1.ª)»)."""
    keys = []
    for inside in (True, False):
        key = job_key(title, inside)
        if key and key not in keys:
            keys.append(key)
    return keys


def job_key(title: str, inside_parens: bool = True):
    t = clean_title(title)
    t = CODE_PAREN.sub(" ; ", t)
    t = t.replace("(", " ").replace(")", " ") if inside_parens else re.sub(r"\([^)]*\)", " ", t)
    best = None
    for m in POS_START.finditer(t):
        before = t[max(0, m.start() - 16):m.start()]
        trigger = m.group(0)
        if re.search(NUM + r"(?:\s*\(\d+\))?\s*$", before):
            prio = 0
        elif re.match(r"(?:plazas?|places?|placa|prazas?)\b", trigger):
            prio = 1
        else:
            prio = 2
        rest = t[m.end():]
        rest = re.sub(r"^(?:\d+\s+|una?\s+|dos\s+|tres\s+|\(\d+\)\s*)+", "", rest)
        rest = re.sub(r"^(?:plazas?|places?|placa|prazas?|puestos?)\s+(?:de |d'|del )?", "", rest)
        rest = FILLER.sub("", rest)
        cut = POS_STOP.search(rest)
        seg = rest[: cut.start()] if cut else rest[:60]
        toks = [w for w in re.findall(r"[a-z0-9]+", seg) if w not in GENERIC and not w.isdigit() and not re.fullmatch(r"[abc][12]?", w)]
        toks = [stem(w) for w in toks]
        toks = [w for w in toks if w not in GENERIC_STEMS]
        if toks and len(" ".join(toks)) >= 4 and (best is None or prio < best[0]):
            best = (prio, frozenset(toks[:6]))
    return best[1] if best else None

GENERIC_STEMS = {stem(w) for w in GENERIC}

def same_job(a, b, same_bases_date: bool = False) -> bool:
    if not a or not b:
        return False
    if a == b:
        return True
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    if small <= LEVEL and not same_bases_date:  # «técnico medio», «técnico superior»…: sin especialidad, solo si son iguales
        return False
    return len(small) >= 2 and small <= big and not ((big - small) & DISCRIM)

LEVEL = {"tecnic", "mitj", "medi", "superior", "auxiliar", "administraci", "administracion", "general", "especial", "gestio", "gestion",
         "grau", "grad", "titulad", "diplomad", "licenciad", "oficial", "operari"}

DISCRIM = {"auxiliar", "superior", "mitj", "medi", "jef", "cap", "oficial", "ayudant", "ajudant", "primer", "segund", "inspector",
           "subinspector", "coordinador", "director", "responsabl", "encargad", "peon", "peo", "conserj", "administrativ", "administratiu",
           "subaltern", "ordenanz", "agent", "sargent", "cabo", "intendent", "comisari"}

# ---------- trámite ----------
STEPS = [
    ("Corrección de errores", r"correcci(?:on|o) d(?:e|')\s*(?:error|errad|erro)|rectificaci|se corrigen errores|subsanaci"),
    ("Modificación de bases", r"modificaci(?:on|o) (?:de |d'|das? )?(?:las |les |as )?bases"),
    ("Lista definitiva de admitidos", r"(?:admitid|admes|admitid|admisi).{0,60}definitiv|definitiv.{0,60}(?:admitid|admes|admisi)"),
    ("Lista provisional de admitidos", r"(?:admitid|admes|admisi).{0,60}provisional|provisional.{0,60}(?:admitid|admes|admisi)|admitidos y excluidos|admesos i exclosos|lista de admitidos"),
    ("Tribunal", r"tribunal|organo de seleccion|organ de seleccio|comision de valoracion|composicion del organo"),
    ("Fecha de examen", r"(?:fecha|data|dia|lugar|convocatoria).{0,40}(?:ejercicio|examen|prueba|exercici|proba)|primer ejercicio|celebracion d"),
    ("Aprobados o resultado", r"aprobad|aprovad|superad|resultado|resultat|calificacion|puntuacion|qualificacio|propuesta de (?:nombramiento|contratacion)|relacion definitiva|seleccionad"),
    ("Nombramiento", r"nombramiento|nomenament|nombra |toma de posesion|presa de possessio|se nombra"),
    ("Bolsa resultante", r"(?:constitucion|composicion|creacion|funcionamiento|activacion).{0,30}bolsa|lista de reserva|bolsa resultante|borsa resultant"),
    ("Extracto", r"^extracto|referente a la convocatoria|anuncio de convocatoria|extracte"),
    ("Bases y convocatoria", r"bases|convocatoria|convoca|proceso selectivo|proces selectiu"),
]

def step_of(title: str) -> str:
    t = fold(title)
    for name, rx in STEPS:
        if re.search(rx, t):
            return name
    return "Anuncio relacionado"

# ---------- modalidad (si las dos la dicen y no coincide, no es el mismo proceso) ----------
MODES = [
    ("interna", r"promocion interna|promocio interna|promocion intern"),
    ("movilidad", r"movilidad|mobilitat|concurso de traslados|comision de servicios|comissio de serveis"),
    ("libre_designacion", r"libre designacion|lliure designacio"),
    ("estabilizacion", r"estabilizacion|estabilitzacio|excepcional"),
    ("bolsa", r"bolsa|borsa|lista de (?:espera|reserva)|interin|temporal|substitu|sustitu"),
    ("fija", r"en propiedad|personal laboral fijo|laboral fix|funcionari[oa]s? de carrera|funcionari de carrera|plazas? vacantes?|oferta de empleo publico|turno libre|torn lliure"),
]
def modes(title: str) -> set:
    t = fold(title)
    return {k for k, rx in MODES if re.search(rx, t)}

def compatible(a_title: str, b_title: str) -> bool:
    a, b = modes(a_title), modes(b_title)
    # «una plaza … y constitución de bolsa»: la bolsa acompaña a la plaza
    if "bolsa" in a and plazas_count(a_title): a = a | {"fija"}
    if "bolsa" in b and plazas_count(b_title): b = b | {"fija"}
    if not a or not b:
        return True
    # «bolsa» y «fija» pueden ir juntas (plaza fija + bolsa resultante); basta con que compartan alguna
    return bool(a & b)

# ---------- solo organismos locales ----------
REGIONAL = re.compile(
    r"\b(?:consejeria|conselleria|departament|departamento|ministerio|servicio|servei|servizo|comunidad|comunitat|administracion|"
    r"direccion|direccio|instituto|institut|agencia|osakidetza|organismo|organisme|junta|gobierno|govern|generalitat|xunta|consorci|"
    r"consorcio|fundacion|fundacio|escuela|escola|sociedad|empresa|entidad|ente|parlamento|tribunal|corporacion|universidad|"
    r"hospital|area|seccion|presidencia|vicepresidencia|educacion|sanidad|salud|justicia|hacienda|economia|empleo|trabajo|cultura|turismo|"
    r"interior|igualdad|derechos|bienestar|medio ambiente|agricultura|industria|vivienda|transportes|deporte|juventud|familia|politica)\b"
)
LOCAL_KINDS = {"ayto", "dipu", "comarca", "manc", "cabildo", "consell"}

def local_org(n: dict):
    o = org_key(n)
    if not o:
        return None
    if o[0] in LOCAL_KINDS:
        return o
    if o[0] == "?" and not REGIONAL.search(o[1]):
        return ("ayto", o[1])
    return None

STEP_BASES = "Bases y convocatoria"
STEP_BOE = "Extracto en el BOE"


def step_for(title: str, is_boe: bool = False) -> str:
    found = step_of(title)
    if is_boe and found in ("Anuncio relacionado", "Extracto", STEP_BASES):
        return STEP_BOE
    return found


def item(notice: dict, source: str, cido: bool = False, extract: dict | None = None) -> dict:
    """Anuncio preparado para emparejar (como `FollowUpMatcher.Item`)."""
    is_boe = str(notice.get("url", "")).startswith("https://www.boe.es/")
    return {"url": notice["url"], "title": notice["title"], "entity": notice.get("entity", ""),
            "date": notice.get("date", ""), "source": source, "cido": cido, "extract": extract,
            "org": local_org(notice), "step": step_for(notice["title"], is_boe)}


def texts(it: dict) -> list:
    ex = it.get("extract")
    return list(ex["items"]) if ex and ex.get("items") else [it["title"]]


def texts_match(fav: str, cand: str, same_bases_date: bool) -> bool:
    # Sin paréntesis solo por un lado: si los dos los llevan y dicen cosas distintas, son plazas distintas.
    pairs = [(f, c) for i, f in enumerate(job_keys(fav)) for j, c in enumerate(job_keys(cand))
             if (i == 0 or j == 0) and not (i + j and f <= LEVEL) and same_job(f, c, same_bases_date)]
    if not pairs:
        return False
    fj = pairs[0][0]
    if not compatible(fav, cand):
        return False
    a, b = plazas_count(fav), plazas_count(cand)
    if a and b and a != b:
        return False
    ma, mb = modes(fav), modes(cand)
    if (a and "bolsa" not in ma and "bolsa" in mb and not b) or (b and "bolsa" not in mb and "bolsa" in ma and not a):
        return False
    if fj <= LEVEL and not (a and b) and not same_bases_date:
        return False
    return True


def is_followup(fav: dict, cand: dict) -> bool:
    """¿Puede «cand» ser otro paso de la convocatoria guardada en «fav»? (ver `item`)."""
    if cand["cido"] or cand["url"] == fav["url"]:
        return False
    if not same_org(fav["org"], cand["org"]):
        return False
    if fav["source"] == cand["source"] and fav["step"] == cand["step"] == STEP_BASES:
        return False
    fx, cx = fav.get("extract") or {}, cand.get("extract") or {}
    same_bases_date = (cx.get("basesDate") == fav["date"]) or (fx.get("basesDate") == cand["date"])
    return any(texts_match(f, c, same_bases_date) for f in texts(fav) for c in texts(cand))


CIDO = {"barcelona.json", "girona.json", "lleida.json", "tarragona_cido.json"}


def medir(docs: str = "docs") -> dict:
    """Parejas posibles entre todos los feeds publicados (para revisar a mano)."""
    import glob
    import itertools
    import json
    import os
    from collections import defaultdict

    extracts = {}
    try:
        with open(os.path.join(docs, "plazos", "boe.json"), encoding="utf-8") as handle:
            boe = json.load(handle)
        for url, value in boe.get("proveer", {}).items():
            extracts[url] = {"items": value["items"], "basesDate": (value.get("bases") or {}).get("fecha")}
    except (OSError, ValueError):
        pass
    groups = defaultdict(list)
    total = 0
    for path in sorted(glob.glob(os.path.join(docs, "*.json"))):
        name = os.path.basename(path)
        try:
            with open(path, encoding="utf-8") as handle:
                feed = json.load(handle)
        except ValueError:
            continue
        if not isinstance(feed, dict) or "notices" not in feed:
            continue
        for notice in feed["notices"]:
            total += 1
            it = item(notice, name, name in CIDO, extracts.get(notice["url"]))
            if it["org"]:
                groups[it["org"][1]].append(it)
    pairs = []
    for group in groups.values():
        for a, b in itertools.combinations(group, 2):
            if is_followup(a, b) or is_followup(b, a):
                pairs.append((a, b))
    return {"anuncios": total, "locales": sum(len(g) for g in groups.values()), "parejas": len(pairs),
            "muestra": [[{k: x[k] for k in ("source", "date", "step", "title")} for x in p] for p in pairs]}


if __name__ == "__main__":
    import json
    import sys

    result = medir(sys.argv[2] if len(sys.argv) > 2 else "docs")
    print(json.dumps({k: v for k, v in result.items() if k != "muestra"}, ensure_ascii=False))
