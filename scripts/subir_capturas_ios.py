"""Sube las capturas del iPhone a la ficha del App Store (versión en preparación).

Lo usa `.github/workflows/ios-capturas.yml`. Sustituye las capturas de iPhone
de 6,7"/6,9" del idioma indicado por las de la carpeta, en orden alfabético.
La clave de la API llega por variables de entorno (secretos de GitHub):
ASC_KEY_ID, ASC_ISSUER_ID y ASC_KEY_P8. Nunca se escribe en el repositorio.

    python scripts/subir_capturas_ios.py capturas/ --app 6831053083 --locale es-ES
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import jwt  # PyJWT, con «cryptography» para ES256

API = "https://api.appstoreconnect.apple.com/v1"
DISPLAY_TYPE = "APP_IPHONE_67"  # 6,7" y 6,9" (1290×2796, 1320×2868)


def token() -> str:
    now = int(time.time())
    return jwt.encode(
        {"iss": os.environ["ASC_ISSUER_ID"], "iat": now, "exp": now + 15 * 60, "aud": "appstoreconnect-v1"},
        os.environ["ASC_KEY_P8"],
        algorithm="ES256",
        headers={"kid": os.environ["ASC_KEY_ID"], "typ": "JWT"},
    )


def call(method: str, url: str, body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(url if url.startswith("http") else API + url, data=data, method=method)
    request.add_header("Authorization", "Bearer " + token())
    if data is not None:
        request.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            raw = response.read()
    except urllib.error.HTTPError as error:
        sys.exit(f"{method} {url}: HTTP {error.code} {error.read().decode(errors='replace')[:800]}")
    return json.loads(raw) if raw else {}


def editable_version(app: str) -> str:
    versions = call("GET", f"/apps/{app}/appStoreVersions?filter[platform]=IOS&limit=10")["data"]
    for version in versions:
        if version["attributes"]["appStoreState"] in {"PREPARE_FOR_SUBMISSION", "DEVELOPER_REJECTED", "REJECTED", "METADATA_REJECTED"}:
            return version["id"]
    sys.exit("No hay ninguna versión de iOS en preparación en App Store Connect")


def localization(version: str, locale: str) -> str:
    for item in call("GET", f"/appStoreVersions/{version}/appStoreVersionLocalizations")["data"]:
        if item["attributes"]["locale"] == locale:
            return item["id"]
    sys.exit(f"La versión no tiene el idioma {locale}")


def screenshot_set(loc: str) -> str:
    for item in call("GET", f"/appStoreVersionLocalizations/{loc}/appScreenshotSets")["data"]:
        if item["attributes"]["screenshotDisplayType"] == DISPLAY_TYPE:
            return item["id"]
    created = call("POST", "/appScreenshotSets", {"data": {
        "type": "appScreenshotSets",
        "attributes": {"screenshotDisplayType": DISPLAY_TYPE},
        "relationships": {"appStoreVersionLocalization": {"data": {"type": "appStoreVersionLocalizations", "id": loc}}},
    }})
    return created["data"]["id"]


def upload(set_id: str, path: Path) -> None:
    content = path.read_bytes()
    created = call("POST", "/appScreenshots", {"data": {
        "type": "appScreenshots",
        "attributes": {"fileName": path.name, "fileSize": len(content)},
        "relationships": {"appScreenshotSet": {"data": {"type": "appScreenshotSets", "id": set_id}}},
    }})["data"]
    for operation in created["attributes"]["uploadOperations"]:
        part = content[operation["offset"]:operation["offset"] + operation["length"]]
        request = urllib.request.Request(operation["url"], data=part, method=operation["method"])
        for header in operation.get("requestHeaders", []):
            request.add_header(header["name"], header["value"])
        with urllib.request.urlopen(request, timeout=120):
            pass
    call("PATCH", f"/appScreenshots/{created['id']}", {"data": {
        "type": "appScreenshots", "id": created["id"],
        "attributes": {"uploaded": True, "sourceFileChecksum": hashlib.md5(content).hexdigest()},
    }})
    print("Subida", path.name)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("folder", type=Path)
    parser.add_argument("--app", required=True)
    parser.add_argument("--locale", default="es-ES")
    args = parser.parse_args()
    files = sorted(p for p in args.folder.iterdir() if p.suffix.lower() in {".png", ".jpg", ".jpeg"})
    if not files:
        sys.exit("No hay capturas que subir")
    if len(files) > 10:
        sys.exit("App Store Connect admite como mucho 10 capturas por tamaño")
    set_id = screenshot_set(localization(editable_version(args.app), args.locale))
    # Se sustituyen las anteriores para que la ficha quede igual que la carpeta.
    for old in call("GET", f"/appScreenshotSets/{set_id}/appScreenshots")["data"]:
        call("DELETE", f"/appScreenshots/{old['id']}")
    for path in files:
        upload(set_id, path)
    print(f"{len(files)} capturas en la ficha ({DISPLAY_TYPE}, {args.locale})")


if __name__ == "__main__":
    main()
