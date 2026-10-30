#!/usr/bin/env python3
"""Validate every provincial 30-day feed before public GitHub Pages deployment.

Strict enough to reject incomplete/partial/date-skipped publications and
untrusted URLs while preserving the previous published feed on failure.
"""
from __future__ import annotations

import argparse
from datetime import datetime, date, timedelta, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit

from provincial_common import ProvincialCoverageError
from clm_common import numbering_ok

SOURCES = {
    'Alicante': ('https://sede.diputacionalicante.es/consultas.bop/', 'www.dip-alicante.es', '/bop2/pdftotal/', 'AL-'),
    'Castellón': ('https://bop.dipcas.es/PortalBOP/', 'bop.dipcas.es', '/PortalBOP/api/descargarAnuncio', 'CS-'),
}


def validate(path: Path, expected_province: str, expected_end: date | None = None) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    source, official_host, official_path, prefix = SOURCES[expected_province]
    if data.get('province') != expected_province or data.get('source') != source:
        raise ProvincialCoverageError(f'{expected_province}: fuente/provincia no coincide')
    history, coverage = data.get('historyCoverage', {}), data.get('coverage', {})
    if not history.get('complete') or not coverage.get('complete'):
        raise ProvincialCoverageError(f'{expected_province}: auditoria incompleta')
    try:
        first = date.fromisoformat(history['rangeStart'])
        last = date.fromisoformat(history['rangeEnd'])
    except (ValueError, KeyError) as exc:
        raise ProvincialCoverageError('Periodo de auditoria invalido') from exc
    if (last-first).days != 29 or (expected_end is not None and last != expected_end):
        raise ProvincialCoverageError(f'{expected_province}: se exigen los 30 dias naturales terminados hoy')
    days = {first+timedelta(days=i) for i in range(30)}
    def dates(values):
        vals = list(values)
        parsed = [date.fromisoformat(d) for d in vals]
        if len(parsed) != len(set(parsed)):
            raise ProvincialCoverageError('Fechas duplicadas en la auditoria')
        return set(parsed)
    pub = dates(history.get('publicationDates', []))
    notpub = dates(history.get('nonPublicationDates', []))
    if pub & notpub or pub | notpub != days:
        raise ProvincialCoverageError(f'{expected_province}: el calendario no cubre los 30 dias')
    issues = history.get('bulletins', [])
    if len(issues) != len(pub) or len(issues) != history.get('issuesRead'):
        raise ProvincialCoverageError(f'{expected_province}: falta boletin para dia de publicacion')
    # Ediciones por fecha; en enero la numeración vuelve a empezar en 1.
    pairs = sorted(zip((date.fromisoformat(d) for d in history.get('publicationDates', [])), (int(x) for x in issues)))
    if not numbering_ok(pairs):
        raise ProvincialCoverageError(f'{expected_province}: boletines no consecutivos')
    notices = data.get('notices')
    if not isinstance(notices, list):
        raise ProvincialCoverageError(f'{expected_province}: sin lista de anuncios')
    ids = set()
    for notice in notices:
        i = notice['id']
        p = urlsplit(notice['url'])
        day = datetime.strptime(notice['date'], '%d/%m/%Y').date()
        if (not i.startswith(prefix) or i in ids or notice.get('province') != expected_province
            or day not in pub or not notice['title'].strip() or not notice['entity'].strip()
            or p.scheme != 'https' or p.hostname != official_host
            or not p.path.startswith(official_path) or p.username or p.password):
            raise ProvincialCoverageError(f'{expected_province}: ficha no valida: {i}')
        ids.add(i)
    read = coverage.get('announcementsRead')
    if not isinstance(read,int) or read < len(notices):
        raise ProvincialCoverageError(f'{expected_province}: total de anuncios incoherente')
    if (coverage.get('opportunities') != len(notices) or
        history.get('opportunities') != len(notices) or
        history.get('announcementsRead') != read):
        raise ProvincialCoverageError(f'{expected_province}: los contadores no coinciden')
    checked = datetime.fromisoformat(data['lastCheckedUTC'])
    if checked.tzinfo is None or checked > datetime.now(timezone.utc)+timedelta(minutes=5) or datetime.now(timezone.utc)-checked > timedelta(hours=3):
        raise ProvincialCoverageError(f'{expected_province}: auditoria anticuada')
    print(f'VALIDADO {expected_province}: {len(issues)} boletines, {read} edictos, {len(notices)} anuncios candidatos, {first} a {last}')
    return data


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--require-today',action='store_true')
    args=parser.parse_args()
    for slug,province in [('alicante','Alicante'),('castellon','Castellón')]:
        validate(args.directory/(slug+'.json'),province,date.today() if args.require_today else None)


if __name__ == '__main__': main()
