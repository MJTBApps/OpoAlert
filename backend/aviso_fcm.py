"""Aviso silencioso a los móviles cuando se publican convocatorias nuevas.

Tras desplegar la web, envía un mensaje de Firebase Cloud Messaging al tema
«convocatorias». El mensaje solo dice «hay datos nuevos»: cada móvil descarga
los feeds y compara con sus alertas, que nunca salen del teléfono.

Para no despertar los móviles en cada despliegue (hay decenas al día), solo se
envía si han cambiado los identificadores de los anuncios publicados y han
pasado al menos MIN_MINUTES desde el último aviso. El estado se guarda en la
caché de GitHub Actions (archivo --state).

Sin el secreto FIREBASE_SERVICE_ACCOUNT no hace nada (y no falla).

    python backend/aviso_fcm.py --docs docs --state .aviso/estado.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

TOPIC = "convocatorias"
MIN_MINUTES = 20
SCOPE = "https://www.googleapis.com/auth/firebase.messaging"


def fingerprint(docs: Path) -> str:
    """Huella de los anuncios publicados (solo identificadores, sin fechas de revisión)."""
    ids: list[str] = []
    for path in sorted(docs.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        notices = data.get("notices") if isinstance(data, dict) else None
        if not isinstance(notices, list):
            continue
        ids.extend(f"{path.stem}:{n.get('id')}" for n in notices if isinstance(n, dict) and n.get("id"))
    return hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()


def should_send(state: dict, current: str, now: float, min_minutes: int = MIN_MINUTES) -> bool:
    if not state.get("fingerprint"):
        # Primera vez: se guarda la huella sin avisar (no hay con qué comparar).
        return False
    if state.get("fingerprint") == current:
        return False
    return now - float(state.get("sent_at", 0)) >= min_minutes * 60


def message(topic: str = TOPIC) -> dict:
    return {
        "message": {
            "topic": topic,
            "data": {"tipo": "feeds"},
            "android": {"priority": "high", "collapse_key": "feeds", "ttl": "10800s"},
            "apns": {
                "headers": {
                    "apns-push-type": "background",
                    "apns-priority": "5",
                    "apns-collapse-id": "feeds",
                },
                "payload": {"aps": {"content-available": 1}},
            },
        }
    }


def send(service_account: dict) -> None:
    from google.auth.transport.requests import AuthorizedSession  # noqa: PLC0415
    from google.oauth2 import service_account as sa  # noqa: PLC0415

    creds = sa.Credentials.from_service_account_info(service_account, scopes=[SCOPE])
    project = service_account["project_id"]
    response = AuthorizedSession(creds).post(
        f"https://fcm.googleapis.com/v1/projects/{project}/messages:send",
        json=message(), timeout=30,
    )
    if response.status_code != 200:
        raise RuntimeError(f"FCM respondió {response.status_code}: {response.text[:300]}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--docs", default="docs")
    parser.add_argument("--state", required=True)
    args = parser.parse_args(argv)

    secret = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "").strip()
    if not secret:
        print("Sin FIREBASE_SERVICE_ACCOUNT: no se envía aviso.")
        return 0
    state_path = Path(args.state)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        state = {}
    current = fingerprint(Path(args.docs))
    now = time.time()
    if should_send(state, current, now):
        send(json.loads(secret))
        state = {"fingerprint": current, "sent_at": now}
        print("Aviso enviado al tema", TOPIC)
    elif not state.get("fingerprint"):
        state = {"fingerprint": current, "sent_at": 0}
        print("Primera ejecución: huella guardada, sin aviso.")
    else:
        # Si no ha cambiado nada o es pronto, se conserva la huella del último aviso:
        # así los cambios pendientes se avisan en el siguiente despliegue.
        print("Sin aviso (sin cambios o último aviso hace menos de", MIN_MINUTES, "min).")
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(state), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
