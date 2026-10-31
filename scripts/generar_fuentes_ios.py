"""Genera la lista de fuentes de la app iOS a partir de la app Android.

Android es la referencia: Province.kt (feed, fuente oficial, dominio y ruta de
los PDF, patrón de identificador), SourceCatalog.kt (comunidad, provincia,
orden y nombre de cada fuente), RemoteFeedReader.kt (siglas) y
NoticeDetailActivity.kt (nombre completo del boletín). Así iOS valida los
feeds con las mismas reglas que Android y que el validador común.

    python scripts/generar_fuentes_ios.py          # escribe el archivo Swift
    python scripts/generar_fuentes_ios.py --check  # falla si no está al día
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KOTLIN = ROOT / "app/src/main/java/es/opoalert/app"
OUTPUT = ROOT / "ios/OpoAlertCore/Sources/OpoAlertCore/Fuentes.generated.swift"

STRING = r'"((?:[^"\\]|\\.)*)"'


def kotlin_string(value: str) -> str:
    return re.sub(r"\\(.)", r"\1", value)


def swift_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def swift_raw(value: str) -> str:
    return '#"' + value + '"#'


def provinces() -> list[dict]:
    text = (KOTLIN / "Province.kt").read_text(encoding="utf-8")
    entry = re.compile(r"\n {4}([A-Z_]+)\(\s*" + r",\s*".join([STRING] * 6) + r',\s*Regex\(' + STRING + r"\)")
    found = []
    for m in entry.finditer(text):
        key, code, label, feed, source, host, prefix, pattern = m.groups()
        found.append({"key": key, "code": code, "label": kotlin_string(label), "feed": feed,
                      "source": kotlin_string(source), "host": host, "prefix": prefix,
                      "pattern": kotlin_string(pattern), "extra": []})
    by_key = {p["key"]: p for p in found}
    if len(found) != len(set(p["code"] for p in found)) or len(found) != text.count("Regex("):
        raise SystemExit("Province.kt: no se han podido leer todas las fuentes")
    for key, path in re.findall(r"this == ([A-Z_]+) && path == " + STRING, text):
        by_key[key]["extra"].append(kotlin_string(path))
    prefixes = [(kotlin_string(p), key) for p, key in
                re.findall(r"id\.startsWith\(" + STRING + r"\) -> ([A-Z_]+)", text)]
    fallback = re.search(r"else -> ([A-Z_]+)\n\s*}\n\s*}\n}", text)
    if not prefixes or not fallback:
        raise SystemExit("Province.kt: no se ha podido leer fromNoticeId")
    return found, prefixes, fallback[1]


def catalog(found: list[dict]) -> tuple[list[str], dict[str, list[str]], list[str]]:
    text = (KOTLIN / "SourceCatalog.kt").read_text(encoding="utf-8")
    by_key = {p["key"]: p for p in found}
    for keys, community, territory in re.findall(
            r"\n\s+(Province\.[A-Z_]+(?:,\s*Province\.[A-Z_]+)*) -> Territory\(" + STRING + r",\s*" + STRING + r"\)",
            text):
        for key in re.findall(r"Province\.([A-Z_]+)", keys):
            by_key[key]["community"] = kotlin_string(community)
            by_key[key]["territory"] = kotlin_string(territory)
    missing = [p["key"] for p in found if p["key"] != "BOE" and "community" not in p]
    if missing:
        raise SystemExit("SourceCatalog.kt: fuentes sin territorio: " + ", ".join(missing))
    order = re.search(r"communityOrder = listOf\((.*?)\)\n", text, re.S)[1]
    communities = [kotlin_string(s) for s in re.findall(STRING, order)]
    block = re.search(r"provinceOrder = mapOf\((.*?)\n {4}\)\n", text, re.S)[1]
    territories: dict[str, list[str]] = {}
    for community, values in re.findall(STRING + r" to listOf\((.*?)\)", block):
        # Como en Kotlin (mapOf): si una comunidad se repite, vale la última.
        territories[kotlin_string(community)] = [kotlin_string(s) for s in re.findall(STRING, values)]
    names = re.search(r"fun sourceName\(source: Province\): String =(.*?)\n\n|fun sourceName\(source: Province\): String =(.*)$",
                      text, re.S)
    names_text = names[1] or names[2]
    for keys, name in re.findall(r"if \((source == Province\.[A-Z_]+(?: \|\| source == Province\.[A-Z_]+)*)\) " + STRING,
                                 names_text):
        for key in re.findall(r"Province\.([A-Z_]+)", keys):
            by_key[key]["name"] = kotlin_string(name)
    cido_name = re.search(r"else if \(isCido\(source\)\) " + STRING, names_text)[1]
    default_name = re.search(r"\n\s+else " + STRING, names_text)[1]
    cido = re.search(r"fun isCido\(source: Province\): Boolean = source in setOf\((.*?)\)", text, re.S)[1]
    cido_keys = re.findall(r"Province\.([A-Z_]+)", cido)
    for p in found:
        p["cido"] = p["key"] in cido_keys
        p.setdefault("name", cido_name if p["cido"] else default_name)
    pending = re.search(r"val pendingDailyFeed: Set<Province> = setOf\((.*?)\)", text, re.S)[1]
    return communities, territories, re.findall(r"Province\.([A-Z_]+)", pending)


def abbreviations(found: list[dict]) -> None:
    text = (KOTLIN / "RemoteFeedReader.kt").read_text(encoding="utf-8")
    block = re.search(r"when \(province\) \{(.*?)\}", text)[1]
    pairs = dict(re.findall(r"Province\.([A-Z_]+) -> " + STRING, block))
    default = re.search(r"else -> " + STRING, block)[1]
    for p in found:
        p["short"] = pairs.get(p["key"], default)


def full_names(found: list[dict]) -> None:
    text = (KOTLIN / "NoticeDetailActivity.kt").read_text(encoding="utf-8")
    block = re.search(r'"Valencia" -> "Boletín Oficial de la Provincia de Valencia"(.*?)else -> ' + STRING, text, re.S)
    names = {"Valencia": "Boletín Oficial de la Provincia de Valencia"}
    plain = r'"(?:[^"\\]|\\.)*"'
    for labels, name in re.findall(r"\n\s+((?:" + plain + r",?\s*)+) -> " + STRING, block[0]):
        for label in re.findall(STRING, labels):
            names[kotlin_string(label)] = kotlin_string(name)
    for p in found:
        p["full"] = names.get(p["label"], kotlin_string(block[2]))


def render() -> str:
    found, prefixes, fallback = provinces()
    communities, territories, pending = catalog(found)
    abbreviations(found)
    full_names(found)
    codes = {p["key"]: p["code"] for p in found}
    lines = [
        "// Generado por scripts/generar_fuentes_ios.py a partir de la app Android",
        "// (Province.kt, SourceCatalog.kt, RemoteFeedReader.kt y NoticeDetailActivity.kt).",
        "// No editar a mano: cambiar Android y volver a generar.",
        "",
        "public enum Fuentes {",
        "    public static let all: [Source] = [",
    ]
    for p in found:
        lines.append("        Source(")
        lines.append(f"            code: {swift_string(p['code'])}, label: {swift_string(p['label'])},")
        lines.append(f"            feedURL: {swift_string(p['feed'])},")
        lines.append(f"            expectedSource: {swift_string(p['source'])},")
        lines.append(f"            pdfHost: {swift_string(p['host'])}, pdfPathPrefix: {swift_string(p['prefix'])},")
        extra = ", ".join(swift_string(x) for x in p["extra"])
        lines.append(f"            idPattern: {swift_raw(p['pattern'])}, extraPaths: [{extra}],")
        community = swift_string(p["community"]) if "community" in p else "nil"
        territory = swift_string(p["territory"]) if "territory" in p else "nil"
        lines.append(f"            community: {community}, territory: {territory},")
        lines.append(f"            name: {swift_string(p['name'])}, shortName: {swift_string(p['short'])},")
        lines.append(f"            fullName: {swift_string(p['full'])}, isCido: {'true' if p['cido'] else 'false'}")
        lines.append("        ),")
    lines += ["    ]", "", "    /// Prefijo del identificador → código de la fuente (Province.fromNoticeId).",
              "    public static let idPrefixes: [(String, String)] = ["]
    lines += [f"        ({swift_string(prefix)}, {swift_string(codes[key])})," for prefix, key in prefixes]
    lines += ["    ]", f"    public static let fallbackCode = {swift_string(codes[fallback])}", "",
              "    public static let communityOrder: [String] = ["]
    lines += [f"        {swift_string(c)}," for c in communities]
    lines += ["    ]", "", "    public static let territoryOrder: [String: [String]] = ["]
    lines += [f"        {swift_string(c)}: [{', '.join(swift_string(t) for t in ts)}]," for c, ts in territories.items()]
    lines += ["    ]", "",
              "    /// Fuentes sin feed diario: se ocultan (SourceCatalog.pendingDailyFeed).",
              "    public static let pendingDailyFeed: Set<String> = [" + ", ".join(swift_string(codes[k]) for k in pending) + "]",
              "}", ""]
    return "\n".join(lines)


def main() -> int:
    content = render()
    if "--check" in sys.argv:
        current = OUTPUT.read_text(encoding="utf-8") if OUTPUT.exists() else ""
        if current != content:
            print(f"{OUTPUT.relative_to(ROOT)} no está al día: ejecuta python scripts/generar_fuentes_ios.py")
            return 1
        print("Fuentes de iOS al día con Android")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content, encoding="utf-8")
    print(f"Escrito {OUTPUT.relative_to(ROOT)}: {content.count('Source(')} fuentes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
